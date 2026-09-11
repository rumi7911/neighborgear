import hashlib
import time
import pytest
import boto3
from moto import mock_aws
from backend.domain import seed
from backend.app import create_app
from fastapi.testclient import TestClient
from backend.worker import process_run
from infra.repository import DynamoRepository, Conflict


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
    with mock_aws():
        db = boto3.resource("dynamodb", region_name="eu-west-1")
        db.create_table(TableName="neighborgear-test", KeySchema=[{"AttributeName":"pk","KeyType":"HASH"}], AttributeDefinitions=[{"AttributeName":"pk","AttributeType":"S"}], BillingMode="PAY_PER_REQUEST")
        controls = db.create_table(TableName="neighborgear-controls-test", KeySchema=[{"AttributeName":"pk","KeyType":"HASH"}], AttributeDefinitions=[{"AttributeName":"pk","AttributeType":"S"}], BillingMode="PAY_PER_REQUEST")
        controls.put_item(Item={"pk":"CONTROL", "enabled":True, "starts_at":int(time.time())-1, "expires_at":int(time.time())+21599})
        monkeypatch.setenv("NEIGHBORGEAR_CONTROL_TABLE", controls.name)
        repo = DynamoRepository("neighborgear-test", resource=db)
        client = TestClient(create_app(repo, start_worker=False))
        session = client.post("/api/sessions", headers={"Idempotency-Key":"create-first"}).json()
        client.headers["X-Sandbox-Token"] = session["token"]
        yield repo, client, session


def test_cloud_queue_is_atomic_deduplicated_and_survives_reopen(env):
    repo, client, session = env
    body = {"name":"Example","text":"rollator"}
    first = client.post("/api/requests", json=body, headers={"Idempotency-Key":"same"}).json()
    assert first == client.post("/api/requests", json=body, headers={"Idempotency-Key":"same"}).json()
    assert len(repo.pending()) == 1
    reopened = DynamoRepository(repo.table.name, resource=repo.resource)
    process_run(reopened, first["run_id"])
    process_run(reopened, first["run_id"])
    assert len(reopened.snapshot(session["session_id"])["requests"]) == 7
    assert reopened.pending() == []


def test_cloud_cas_fences_stale_worker_and_reset(env):
    repo, _, session = env
    sid = session["session_id"]
    with pytest.raises(Conflict):
        with repo.transaction(sid) as stale:
            stale["equipment"][0]["status"] = "retired"
            repo.reset(sid, seed(sid), "reset-1")
    assert repo.snapshot(sid)["equipment"][0]["status"] != "retired"


def test_cloud_session_auth_creation_replay_and_isolation(env):
    repo, client, session = env
    assert client.post("/api/sessions", headers={"Idempotency-Key":"create-first"}).json() == session
    other = client.post("/api/sessions").json()
    result = client.post("/api/requests", json={"name":"Only here","text":"rollator"}).json()
    assert client.post(f"/api/requests/{result['request_id']}/clarify", json={}, headers={"X-Sandbox-Token":other["token"]}).status_code == 409
    repo.reset(session["session_id"], seed(session["session_id"]), "reset")
    assert len(repo.snapshot(other["session_id"])["requests"]) == 6
    assert repo.authenticate(hashlib.sha256(other["token"].encode()).hexdigest()) == other["session_id"]
    assert repo.get_run(result["run_id"]) is None


def test_cloud_queue_order_and_retry_link(env):
    repo, client, session = env
    first = client.post("/api/requests/request_1/events", json={"type":"return_equipment"}).json()
    second = client.post("/api/clock", json={"days":1}).json()
    assert repo.has_predecessor(second["run_id"])
    process_run(repo, second["run_id"])
    assert repo.snapshot(session["session_id"])["session"]["now"] == "2026-09-05"
    process_run(repo, first["run_id"])
    retry = client.post(f"/api/runs/{first['run_id']}/retry").json()
    assert repo.get_run(retry["run_id"])["payload"]["request_id"] == "request_1"
    assert next(r for r in repo.snapshot(session["session_id"])["runs"] if r["id"] == retry["run_id"])["request_id"] == "request_1"


def test_cloud_size_limit_rolls_back(env):
    repo, _, session = env
    with pytest.raises(ValueError, match="size"):
        with repo.transaction(session["session_id"]) as state:
            state["padding"] = "x"*400_000
    assert "padding" not in repo.snapshot(session["session_id"])


def test_cloud_attempt_lease_and_hard_limit(env):
    repo, client, session = env
    run_id = client.post("/api/clock", json={"days":1}).json()["run_id"]
    assert repo.claim(run_id, now=100)
    assert not repo.claim(run_id, now=101)
    assert repo.claim(run_id, now=200)
    assert repo.claim(run_id, now=300)
    assert not repo.claim(run_id, now=400)
    run = next(r for r in repo.snapshot(session["session_id"])["runs"] if r["id"] == run_id)
    assert run["status"] == "failed" and "attempt" in run["error"]


def test_cloud_queue_publish_and_repair(env):
    from infra.dispatch import publish, sweep
    repo, client, _ = env
    sqs = boto3.client("sqs", region_name="eu-west-1")
    url = sqs.create_queue(QueueName="runs.fifo", Attributes={"FifoQueue":"true"})["QueueUrl"]
    run_id = client.post("/api/clock", json={"days":1}).json()["run_id"]
    # No publish occurred at intake. The scheduled sweep repairs that gap.
    sweep(repo, sqs, url)
    received = sqs.receive_message(QueueUrl=url)["Messages"]
    import json
    assert json.loads(received[0]["Body"])["run_id"] == run_id
    process_run(repo, run_id)
    assert publish(repo, sqs, url, run_id) is False


def test_cloud_live_budget_not_reset_by_sandbox_reset(env):
    repo, _, session = env
    assert repo.consume_budget(2)
    repo.reset(session["session_id"], seed(session["session_id"]), "r")
    assert repo.consume_budget(2)
    assert not repo.consume_budget(2)
