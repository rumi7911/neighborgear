from concurrent.futures import ThreadPoolExecutor

import pytest

from infra.tests.test_repository import env


def put_control(repo, **overrides):
    item = {"pk":"CONTROL", "enabled":True, "starts_at":1000, "expires_at":22600}
    item.update(overrides)
    repo.resource.Table("neighborgear-controls-test").put_item(Item=item)


@pytest.mark.parametrize("change,now", [
    ({"enabled":False}, 1001), ({}, 22600), ({}, 999),
    ({"expires_at":22601}, 1001), ({"enabled":"true"}, 1001),
])
def test_invalid_disabled_or_expired_window_fails_closed(env, change, now):
    repo, _, _ = env
    put_control(repo, **change)
    assert hasattr(repo, "control_reason")
    assert repo.control_reason(now=now) is not None


def test_window_survives_restart_and_reset_without_being_extended(env):
    from infra.repository import DynamoRepository
    from backend.domain import seed
    repo, _, session = env
    put_control(repo)
    assert hasattr(repo, "control_reason")
    assert repo.control_reason(now=1001) is None
    repo.reset(session["session_id"], seed(session["session_id"]))
    reopened = DynamoRepository(repo.table.name, resource=repo.resource)
    assert reopened.control_reason(now=22599) is None
    assert reopened.control_reason(now=22600) is not None


def test_missing_control_cannot_open_the_demo(env):
    repo, _, _ = env
    repo.resource.Table("neighborgear-controls-test").delete_item(Key={"pk":"CONTROL"})
    assert hasattr(repo, "control_reason")
    assert repo.control_reason() is not None


def test_global_budget_never_accepts_more_than_ten_even_if_caller_asks_for_more(env):
    repo, _, session = env
    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(lambda _: repo.consume_budget(200), range(24)))
    assert sum(outcomes) == 10
    from infra.repository import DynamoRepository
    reopened = DynamoRepository(repo.table.name, resource=repo.resource)
    assert not reopened.consume_budget(200)
    from backend.domain import seed
    repo.reset(session["session_id"], seed(session["session_id"]))
    assert not reopened.consume_budget(10)


def test_expired_runtime_does_not_execute_even_simulator_work(env):
    from infra.runtime import execute
    repo, client, session = env
    run = client.post("/api/clock", json={"days":1}).json()["run_id"]
    put_control(repo, enabled=False)
    assert execute(repo, run)["status"] == "stopped"
    assert repo.snapshot(session["session_id"])["session"]["now"] == "2026-09-05"


def test_api_and_sweep_stop_before_intake_or_publishing(env, monkeypatch):
    from infra import handlers
    repo, _, _ = env
    put_control(repo, enabled=False)
    monkeypatch.setenv("NEIGHBORGEAR_JUDGE_KEY", "fictional-key")
    monkeypatch.setattr(handlers, "repository", lambda: repo)
    assert handlers.api_handler({}, None)["statusCode"] == 503
    assert handlers.sweep_handler({}, None)["status"] == "stopped"


def test_stopped_worker_acknowledges_wakeup_without_invoking_runtime(env, monkeypatch):
    from infra import handlers
    repo, _, _ = env
    put_control(repo, enabled=False)
    monkeypatch.setattr(handlers, "repository", lambda: repo)
    assert handlers.worker_handler({"Records":[{"messageId":"1", "body":"{}"}]}, None) == {"batchItemFailures":[]}


def test_control_read_error_fails_closed(env, monkeypatch):
    repo, _, _ = env
    def unavailable(*args, **kwargs):
        raise RuntimeError("Read unavailable")
    monkeypatch.setattr(repo.resource, "Table", unavailable)
    assert "could not be verified" in repo.control_reason()
    assert not repo.consume_budget(10)


def test_failed_live_attempt_is_not_refunded_or_reset_by_new_session(env, monkeypatch):
    from infra import runtime
    repo, client, session = env
    monkeypatch.setenv("NEIGHBORGEAR_CREDITS_VERIFIED", "true")
    with repo.transaction(session["session_id"]) as state:
        state["session"]["mode"] = "live"
    run = client.post("/api/clock", json={"days":1}).json()["run_id"]
    # External model-work boundary fails after its atomic attempt ticket is taken.
    def failed_model_work(*args):
        raise RuntimeError("Simulated model failure")
    monkeypatch.setattr(runtime, "process_run", failed_model_work)
    with pytest.raises(RuntimeError, match="Simulated model failure"):
        runtime.execute(repo, run)
    client.post("/api/sessions")
    assert sum(repo.consume_budget(10) for _ in range(12)) == 9


@pytest.mark.parametrize("limit", [0, -1, True, "10"])
def test_invalid_budget_limit_never_issues_a_ticket(env, limit):
    repo, _, _ = env
    assert repo.consume_budget(limit) is False
