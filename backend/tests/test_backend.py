from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.store import Repository
from backend.worker import process_run


@pytest.fixture
def env(tmp_path):
    repo = Repository(tmp_path / "test.sqlite3")
    client = TestClient(create_app(repo, start_worker=False))
    session = client.post("/api/sessions").json()
    client.headers["X-Sandbox-Token"] = session["token"]
    return repo, client, session


def flush(repo):
    for queued in repo.pending():
        process_run(repo, queued["id"])


def mutate(env, path, data=None, key=None):
    repo, client, _ = env
    response = client.post("/api" + path, json=data, headers={"Idempotency-Key": key} if key else {})
    assert response.status_code == 200, response.text
    flush(repo)
    return response.json()


def snapshot(env):
    return env[1].get("/api/snapshot").json()


def test_cancellation_requires_driver_binding(env):
    result = mutate(env, "/requests/request_3/events", {"type": "cancel_driver"})
    state = snapshot(env)
    run = next(r for r in state["runs"] if r["id"] == result["run_id"])
    assert run["status"] == "failed"
    assert next(r for r in state["requests"] if r["id"] == "request_3")["driver_id"] == "driver_5"


def test_retry_preserves_request_and_event_link(env):
    first = mutate(env, "/requests/request_1/events", {"type": "return_equipment"})
    retry = mutate(env, f"/runs/{first['run_id']}/retry")
    state = snapshot(env)
    assert next(r for r in state["runs"] if r["id"] == retry["run_id"])["request_id"] == "request_1"
    assert next(e for e in state["events"] if e["id"] == retry["event_id"])["request_id"] == "request_1"


def test_seed_and_auth_isolation(env):
    repo, client, session = env
    state = snapshot(env)
    assert [len(state[k]) for k in ("depots", "equipment", "drivers", "requests")] == [3, 24, 6, 6]
    second = client.post("/api/sessions").json()
    created = mutate(env, "/requests", {"name": "Example", "text": "rollator"})
    assert client.post(f"/api/requests/{created['request_id']}/clarify", json={}, headers={"X-Sandbox-Token": second["token"]}).status_code == 409
    assert client.get("/api/snapshot", headers={"X-Sandbox-Token": session["session_id"]}).status_code == 401
    assert len(repo.snapshot(second["session_id"])["requests"]) == 6


def test_complete_lifecycle_and_deduplication(env):
    result = mutate(env, "/requests", {"name": "Jess example", "text": "A rollator in North, handles 80-95 cm, 90 kg, needed 2026-09-06 until 2026-09-08, 10:00 to 16:00"}, key="create-once")
    req_id = result["request_id"]
    req = next(r for r in snapshot(env)["requests"] if r["id"] == req_id)
    assert req["status"] == "awaiting_approval"
    item = next(c["equipment_id"] for c in req["candidates"] if c["eligible"])
    mutate(env, f"/requests/{req_id}/approve", dict(equipment_id=item, proposal_version=req["proposal_version"]))
    req = next(r for r in snapshot(env)["requests"] if r["id"] == req_id)
    first_driver = req["driver_id"]
    mutate(env, f"/requests/{req_id}/events", dict(type="cancel_driver", driver_id=first_driver), key="cancel-once")
    req = next(r for r in snapshot(env)["requests"] if r["id"] == req_id)
    assert req["driver_id"] != first_driver and req["status"] == "delivery_scheduled"
    mutate(env, f"/requests/{req_id}/events", dict(type="confirm_delivery"))
    mutate(env, f"/requests/{req_id}/events", dict(type="confirm_delivery"))
    mutate(env, "/clock", dict(days=3))
    mutate(env, "/clock", dict(days=1))
    state = snapshot(env)
    assert len([m for m in state["messages"] if m["request_id"] == req_id and m["subject"] == "Return Reminder"]) == 1
    assert len([l for l in state["loans"] if l["request_id"] == req_id]) == 1
    mutate(env, f"/requests/{req_id}/events", dict(type="return_equipment"))
    assert next(i for i in snapshot(env)["equipment"] if i["id"] == item)["status"] == "inspection"
    mutate(env, f"/requests/{req_id}/events", dict(type="pass_inspection"))
    state = snapshot(env)
    assert next(i for i in state["equipment"] if i["id"] == item)["status"] == "available"
    assert next(r for r in state["requests"] if r["id"] == req_id)["status"] == "completed"


def test_clarification_safety_and_stale_proposal(env):
    mutate(env, "/requests/request_2/clarify", {"user_weight_kg": 90})
    req = next(r for r in snapshot(env)["requests"] if r["id"] == "request_2")
    assert req["status"] == "awaiting_approval"
    unsafe = next(c["equipment_id"] for c in req["candidates"] if not c["eligible"])
    result = mutate(env, "/requests/request_2/approve", dict(equipment_id=unsafe, proposal_version=req["proposal_version"]))
    assert next(r for r in snapshot(env)["runs"] if r["id"] == result["run_id"])["status"] == "failed"
    result = mutate(env, "/requests/request_2/approve", dict(equipment_id="gear_01", proposal_version=1))
    assert next(r for r in snapshot(env)["runs"] if r["id"] == result["run_id"])["status"] == "failed"
    assert next(r for r in snapshot(env)["requests"] if r["id"] == "request_6")["status"] == "needs_attention"


def test_concurrent_reservation_and_queue_replay(env):
    repo, client, _ = env
    mutate(env, "/requests/request_2/clarify", {"user_weight_kg": 80, "equipment_type": "rollator"})
    state = snapshot(env)
    a, b = [next(r for r in state["requests"] if r["id"] == rid) for rid in ("request_1", "request_2")]
    item = next(c["equipment_id"] for c in a["candidates"] if c["eligible"])
    results = [client.post(f"/api/requests/{req['id']}/approve", json=dict(equipment_id=item, proposal_version=req["proposal_version"])).json() for req in (a,b)]
    with ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda r: process_run(repo, r["run_id"]), results * 2))
    flush(repo)
    state = snapshot(env)
    assert sum(r["equipment_id"] == item for r in state["reservations"]) == 1
    assert sorted(next(r["status"] for r in state["runs"] if r["id"] == result["run_id"]) for result in results) == ["failed", "succeeded"]


def test_idempotency_and_restart(env):
    repo, client, _ = env
    body = {"name": "Example", "text": "walking frame"}
    first = client.post("/api/requests", json=body, headers={"Idempotency-Key": "a"}).json()
    second = client.post("/api/requests", json=body, headers={"Idempotency-Key": "a"}).json()
    assert first == second
    assert client.post("/api/requests", json={**body, "text": "rollator"}, headers={"Idempotency-Key": "a"}).status_code == 409
    reopened = Repository(repo.path)
    flush(reopened)
    assert len(snapshot(env)["requests"]) == 7
    process_run(reopened, first["run_id"])
    assert len(snapshot(env)["requests"]) == 7


def test_transport_capacity_and_deadline(env):
    repo, _, sid = env
    with repo.transaction(sid["session_id"]) as state:
        for driver in state["drivers"]:
            driver["capacity"] = 0
    req = next(r for r in snapshot(env)["requests"] if r["id"] == "request_1")
    item = next(c["equipment_id"] for c in req["candidates"] if c["eligible"])
    mutate(env, "/requests/request_1/approve", dict(equipment_id=item, proposal_version=req["proposal_version"]))
    req = next(r for r in snapshot(env)["requests"] if r["id"] == "request_1")
    assert req["status"] == "needs_attention" and req["driver_id"] is None
    mutate(env, "/requests/request_2/clarify", dict(user_weight_kg=80, needed_by="2026-09-01"))
    assert next(r for r in snapshot(env)["requests"] if r["id"] == "request_2")["status"] == "needs_attention"


def test_invalid_transition_and_failed_inspection(env):
    result = mutate(env, "/requests/request_1/events", {"type": "return_equipment"})
    assert next(r for r in snapshot(env)["runs"] if r["id"] == result["run_id"])["status"] == "failed"
    mutate(env, "/requests/request_5/events", {"type": "fail_inspection"})
    req = next(r for r in snapshot(env)["requests"] if r["id"] == "request_5")
    assert next(i for i in snapshot(env)["equipment"] if i["id"] == req["equipment_id"])["status"] == "retired"


def test_live_credit_gate_no_fallback(monkeypatch):
    from backend.agent import coordinate
    monkeypatch.delenv("NEIGHBORGEAR_CREDITS_VERIFIED", raising=False)
    with pytest.raises(ValueError, match="credits"):
        coordinate({}, {})


def test_validation_error_shape(env):
    response = env[1].post("/api/clock", json={"days": 31})
    assert response.status_code == 422 and isinstance(response.json()["detail"], str)


def test_queue_preserves_order_when_consumers_race(env):
    repo, client, _ = env
    first = client.post("/api/requests/request_2/clarify", json={"user_weight_kg": 80}).json()
    second = client.post("/api/requests/request_2/clarify", json={"user_weight_kg": 180}).json()
    process_run(repo, second["run_id"])
    assert next(r for r in snapshot(env)["runs"] if r["id"] == second["run_id"])["status"] == "queued"
    flush(repo)
    assert next(r for r in snapshot(env)["requests"] if r["id"] == "request_2")["user_weight_kg"] == 180


def test_capacity_race_different_equipment(env):
    repo, client, session = env
    with repo.transaction(session["session_id"]) as state:
        for driver in state["drivers"]:
            driver["capacity"] = 0
        state["drivers"][1]["capacity"] = 1
    mutate(env, "/requests/request_2/clarify", {"user_weight_kg": 80, "area": "North"})
    state = snapshot(env)
    results = []
    for rid in ("request_1", "request_2"):
        req = next(r for r in state["requests"] if r["id"] == rid)
        item = next(c["equipment_id"] for c in req["candidates"] if c["eligible"])
        results.append(client.post(f"/api/requests/{rid}/approve", json={"equipment_id": item, "proposal_version": req["proposal_version"]}).json())
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda r: process_run(repo, r["run_id"]), results))
    flush(repo)
    statuses = [r["status"] for r in snapshot(env)["requests"] if r["id"] in ("request_1", "request_2")]
    assert sorted(statuses) == ["delivery_scheduled", "needs_attention"]


def test_retry_failed_run_and_reset_isolation(env):
    result = mutate(env, "/requests/request_1/events", {"type": "return_equipment"})
    retried = mutate(env, f"/runs/{result['run_id']}/retry")
    assert next(r for r in snapshot(env)["runs"] if r["id"] == retried["run_id"])["status"] == "failed"
    other = env[1].post("/api/sessions").json()
    mutate(env, "/clock", {"days": 10})
    assert env[1].post("/api/reset").status_code == 200
    assert snapshot(env)["session"]["now"] == "2026-09-05"
    assert env[0].snapshot(other["session_id"])["session"]["now"] == "2026-09-05"


def test_invalid_clarification_rolls_back(env):
    mutate(env, "/requests/request_2/clarify", {"user_weight_kg": 80, "min_height_cm": 100, "max_height_cm": 80})
    req = next(r for r in snapshot(env)["requests"] if r["id"] == "request_2")
    assert req["min_height_cm"] == 80 and req["user_weight_kg"] is None


def test_non_overlapping_window_cannot_schedule(env):
    mutate(env, "/requests/request_1/clarify", {"window_start": "18:00", "window_end": "19:00"})
    req = next(r for r in snapshot(env)["requests"] if r["id"] == "request_1")
    item = next(c["equipment_id"] for c in req["candidates"] if c["eligible"])
    mutate(env, "/requests/request_1/approve", {"equipment_id": item, "proposal_version": req["proposal_version"]})
    assert next(r for r in snapshot(env)["requests"] if r["id"] == "request_1")["status"] == "needs_attention"


def test_session_creation_and_reset_idempotency(env):
    client = env[1]
    headers = {"Idempotency-Key": "opaque-session-creation-example"}
    assert client.post("/api/sessions", headers=headers).json() == client.post("/api/sessions", headers=headers).json()
    headers = {"Idempotency-Key": "reset-a"}
    assert client.post("/api/reset", headers=headers).status_code == 200
    mutate(env, "/clock", {"days": 2})
    assert client.post("/api/reset", headers=headers).status_code == 200
    assert snapshot(env)["session"]["now"] == "2026-09-07"


def test_local_worker_consumes_persisted_queue(env):
    import time
    repo, client, session = env
    response = client.post("/api/requests", json={"name": "Example", "text": "walking frame"}).json()
    with TestClient(create_app(repo, start_worker=True)):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if any(r["id"] == response["request_id"] for r in repo.snapshot(session["session_id"])["requests"]):
                break
            time.sleep(0.02)
        else:
            pytest.fail("Worker did not consume persisted queue")


def test_live_adapter_deadline_terminates_process(monkeypatch):
    import backend.agent as module
    class Process:
        terminated = False
        waits = []
        def start(self): pass
        def join(self, seconds): self.waits.append(seconds)
        def is_alive(self): return True
        def terminate(self): self.terminated = True
    proc = Process()
    class Queue:
        def get(self, timeout):
            assert timeout == 60
            import queue
            raise queue.Empty()
        def close(self): pass
    class Context:
        def Queue(self): return Queue()
        def Process(self, **kwargs): return proc
    monkeypatch.setenv("NEIGHBORGEAR_CREDITS_VERIFIED", "true")
    monkeypatch.setattr(module.multiprocessing, "get_context", lambda _: Context())
    with pytest.raises(TimeoutError, match="no simulator fallback"):
        module.coordinate({}, {})
    assert proc.terminated and proc.waits == [5]
