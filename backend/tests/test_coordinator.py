"""Actual Strands event-loop tests with a scripted Model; no AWS/network calls."""
import copy
import json
import pytest
from fastapi.testclient import TestClient
from strands.models import Model
from backend.coordinator import CommandTools, ToolBudget, run_coordinator
from backend.domain import seed
from backend.app import create_app
from backend.store import Repository


class FixtureModel(Model):
    """Emit recorded-style tool-use events, exercising real SDK tool dispatch."""
    def __init__(self, actions):
        self.actions = iter(actions)
        self.turns = 0
        self.messages = []

    def update_config(self, **kwargs): pass
    def get_config(self): return {"model_id": "fixture-no-inference", "context_window_limit": 32000}
    async def structured_output(self, *args, **kwargs):
        raise NotImplementedError
        yield

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.messages = copy.deepcopy(messages)
        self.turns += 1
        action = next(self.actions, None)
        yield {"messageStart": {"role": "assistant"}}
        if isinstance(action, Exception):
            raise action
        if action:
            name, arguments = action
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"fixture-{self.turns}", "name": name}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(arguments)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockDelta": {"delta": {"text": "Fixture outcome; no inference performed."}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}


def run(state, payload, *names):
    actions = [(name, {}) if isinstance(name, str) else name for name in names]
    return run_coordinator(state, payload, FixtureModel(actions))


def test_create_extracts_facts_and_persists_human_handoff():
    state = seed("fixture")
    original = copy.deepcopy(state)
    facts = {"equipment_type": "rollator", "min_height_cm": 80, "max_height_cm": 95, "user_weight_kg": 90,
             "needed_by": "2026-09-06", "return_by": "2026-09-12", "area": "North", "window_start": "10:00", "window_end": "16:00"}
    payload = {"operation": "create", "request_id": "fixture_request", "data": {"name": "Example", "text": "Explicit fixture facts: " + json.dumps(facts)}}
    updated, trace = run(state, payload, "read_request", ("propose_request", {"specification_json": json.dumps(facts)}), "search_inventory", "write_outbox")
    req = next(r for r in updated["requests"] if r["id"] == "fixture_request")
    assert req["status"] == "awaiting_approval" and req["equipment_id"] is None
    assert updated["reservations"] == original["reservations"]
    assert any(e["type"] == "human_handoff" and e["request_id"] == req["id"] for e in updated["events"])
    assert trace["tool_calls"] == 4 and trace["human_handoff"] is True
    assert state == original  # caller state remains untouched until worker commit


def test_staff_approval_reserve_assign_and_outbox():
    state = seed("fixture")
    req = state["requests"][0]
    item = next(c["equipment_id"] for c in req["candidates"] if c["eligible"])
    payload = {"operation": "approve", "request_id": req["id"], "data": {"equipment_id": item, "proposal_version": req["proposal_version"]}}
    updated, trace = run(state, payload, "read_request", "search_inventory", "reserve_approved_equipment", "assign_driver", "write_outbox")
    req = updated["requests"][0]
    assert req["status"] == "delivery_scheduled" and req["equipment_id"] == item
    assert any(a["request_id"] == req["id"] for a in updated["approvals"])
    assert any(a["request_id"] == req["id"] for a in updated["assignments"])
    assert any(m["request_id"] == req["id"] and m["simulated"] for m in updated["messages"])
    assert trace["domain_tools"] == ["reserve_approved_equipment", "assign_driver", "write_outbox"]


def test_model_cannot_self_approve_or_change_approved_item():
    state = seed("fixture")
    tools = CommandTools(state, {"operation": "create", "request_id": "new", "data": {"name": "Example", "text": "rollator"}})
    with pytest.raises(ValueError, match="not authorized"):
        tools.reserve_approved_equipment()
    with pytest.raises(ValueError):
        tools.propose_request('{"equipment_id":"gear_01","approved":true}')
    # The tool has no model-supplied item, request or approval arguments.
    import inspect
    assert list(inspect.signature(tools.reserve_approved_equipment).parameters) == []


def test_clarification_missing_fields_outbox_and_bound_human_data():
    state = seed("fixture")
    payload = {"operation": "clarify", "request_id": "request_2", "data": {"user_weight_kg": 80}}
    updated, _ = run(state, payload, "propose_request", "search_inventory", "write_outbox")
    assert updated["requests"][1]["status"] == "awaiting_approval"
    with pytest.raises(ValueError, match="bound human"):
        CommandTools(state, payload).propose_request('{"user_weight_kg":50}')
    payload = {"operation": "create", "request_id": "missing", "data": {"name": "Example", "text": "rollator"}}
    updated, _ = run(state, payload, ("propose_request", {"specification_json": '{"equipment_type":"rollator"}'}), "write_outbox")
    assert updated["requests"][-1]["status"] == "needs_information"
    assert any(m["request_id"] == "missing" for m in updated["messages"])


@pytest.mark.parametrize("request_id,kind,status", [("request_3", "confirm_delivery", "on_loan"), ("request_4", "return_equipment", "inspection"), ("request_5", "pass_inspection", "completed"), ("request_5", "fail_inspection", "completed")])
def test_lifecycle_tools(request_id, kind, status):
    updated, _ = run(seed("fixture"), {"operation": "event", "request_id": request_id, "data": {"type": kind}}, "record_lifecycle_event", "write_outbox")
    assert next(r for r in updated["requests"] if r["id"] == request_id)["status"] == status


def test_cancel_reassign_and_clock_reminders():
    state = seed("fixture")
    previous_driver = state["requests"][2]["driver_id"]
    updated, _ = run(state, {"operation": "event", "request_id": "request_3", "data": {"type": "cancel_driver", "driver_id": previous_driver}}, "record_lifecycle_event", "assign_driver", "write_outbox")
    assert updated["requests"][2]["driver_id"] != previous_driver
    updated, _ = run(updated, {"operation": "clock", "data": {"days": 8}}, "advance_clock_and_remind", "write_outbox")
    assert updated["session"]["now"] == "2026-09-13"
    assert any(m["subject"] == "Return Reminder" for m in updated["messages"])


def test_incomplete_or_failed_model_never_returns_commit_state():
    state = seed("fixture")
    original = copy.deepcopy(state)
    payload = {"operation": "clock", "data": {"days": 1}}
    with pytest.raises(RuntimeError, match="before completing"):
        run(state, payload, "advance_clock_and_remind")
    with pytest.raises(RuntimeError, match="fixture provider failure"):
        run_coordinator(state, payload, FixtureModel([("advance_clock_and_remind", {}), RuntimeError("fixture provider failure")]))
    assert state == original


def test_actual_strands_tool_budget_stops_repeated_calls():
    state = seed("fixture")
    model = FixtureModel([("read_request", {})] * 20)
    with pytest.raises(RuntimeError, match="budget"):
        run_coordinator(state, {"operation": "clock", "data": {"days": 1}}, model)
    assert model.turns == 12


def test_judge_gate_and_cors(tmp_path, monkeypatch):
    monkeypatch.setenv("NEIGHBORGEAR_JUDGE_KEY", "example-invitation")
    client = TestClient(create_app(Repository(tmp_path / "gate.sqlite3"), start_worker=False))
    assert client.post("/api/sessions").status_code == 401
    assert client.post("/api/sessions", headers={"X-Judge-Key": "wrong"}).status_code == 401
    assert client.post("/api/sessions", headers={"X-Judge-Key": "example-invitation"}).status_code == 200
    response = client.options("/api/sessions", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-judge-key"})
    assert response.status_code == 200 and "x-judge-key" in response.headers["access-control-allow-headers"].lower()


def fixture_child(state, payload, output):
    """Spawn-safe test process; deliberately has no Bedrock provider."""
    updated, trace = run(state, payload, "advance_clock_and_remind", "write_outbox")
    output.put({"ok": True, "state": updated, "trace": {**trace, "adapter": "strands_fixture", "bedrock_used": False}})


def test_child_process_returns_large_state_without_queue_deadlock(monkeypatch):
    import backend.agent as adapter
    monkeypatch.setenv("NEIGHBORGEAR_CREDITS_VERIFIED", "true")
    monkeypatch.setattr(adapter, "_live_child", fixture_child)
    state = seed("fixture")
    # Larger than the pipe buffer, previously vulnerable to join-before-read.
    state["padding_for_fixture"] = "x" * 150_000
    updated, trace = adapter.coordinate(state, {"operation": "clock", "data": {"days": 1}})
    assert updated["session"]["now"] == "2026-09-06"
    assert trace["bedrock_used"] is False and trace["adapter"] == "strands_fixture"


def test_worker_commits_coordinator_result_once(tmp_path, monkeypatch):
    from backend import worker
    monkeypatch.setenv("NEIGHBORGEAR_MODE", "live")
    repo = Repository(tmp_path / "worker.sqlite3")
    client = TestClient(create_app(repo, start_worker=False))
    session = client.post("/api/sessions").json()
    client.headers["X-Sandbox-Token"] = session["token"]
    response = client.post("/api/clock", json={"days": 2}).json()
    calls = []
    def fixture_coordinate(state, payload):
        calls.append(payload["operation"])
        updated, trace = run(state, payload, "advance_clock_and_remind", "write_outbox")
        return updated, {**trace, "adapter": "strands_fixture", "bedrock_used": False}
    monkeypatch.setattr(worker, "coordinate", fixture_coordinate)
    worker.process_run(repo, response["run_id"])
    worker.process_run(repo, response["run_id"])
    state = repo.snapshot(session["session_id"])
    assert state["session"]["now"] == "2026-09-07" and calls == ["clock"]
    assert state["runs"][-1]["status"] == "succeeded"
    assert state["runs"][-1]["domain_tools"] == ["advance_clock_and_remind", "write_outbox"]


def test_failed_live_worker_keeps_original_state(tmp_path, monkeypatch):
    from backend import worker
    monkeypatch.setenv("NEIGHBORGEAR_MODE", "live")
    repo = Repository(tmp_path / "worker-fail.sqlite3")
    client = TestClient(create_app(repo, start_worker=False))
    session = client.post("/api/sessions").json()
    client.headers["X-Sandbox-Token"] = session["token"]
    response = client.post("/api/clock", json={"days": 2}).json()
    def incomplete(state, payload):
        return run(state, payload, "advance_clock_and_remind")
    monkeypatch.setattr(worker, "coordinate", incomplete)
    worker.process_run(repo, response["run_id"])
    state = repo.snapshot(session["session_id"])
    assert state["session"]["now"] == "2026-09-05" and state["runs"][-1]["status"] == "failed"


def test_live_child_defaults_nova_and_reports_provider_error(monkeypatch):
    import strands.models
    import backend.coordinator as coordinator
    from backend.agent import _live_child
    import queue
    configured = {}
    def fake_model(**kwargs):
        configured.update(kwargs)
        return object()
    def fail(*args):
        raise RuntimeError("fixture provider denied")
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.setattr(strands.models, "BedrockModel", fake_model)
    monkeypatch.setattr(coordinator, "run_coordinator", fail)
    output = queue.Queue()
    _live_child({}, {}, output)
    assert configured["model_id"] == "eu.amazon.nova-lite-v1:0"
    assert output.get()["error"] == "fixture provider denied"
