import pytest
from infra.tests.test_repository import env


def test_runtime_commits_domain_result_and_replays_without_effects(env):
    from infra.runtime import execute
    repo, client, session = env
    run_id = client.post("/api/clock", json={"days":1}).json()["run_id"]
    assert execute(repo, run_id)["status"] == "succeeded"
    assert execute(repo, run_id)["status"] == "succeeded"
    assert repo.snapshot(session["session_id"])["session"]["now"] == "2026-09-06"


def test_runtime_live_gate_marks_failure_without_model_call(env, monkeypatch):
    from infra.runtime import execute
    repo, client, session = env
    with repo.transaction(session["session_id"]) as state:
        state["session"]["mode"] = "live"
    monkeypatch.setenv("NEIGHBORGEAR_CREDITS_VERIFIED", "false")
    run_id = client.post("/api/clock", json={"days":1}).json()["run_id"]
    assert execute(repo, run_id)["status"] == "failed"
    state = repo.snapshot(session["session_id"])
    assert state["session"]["now"] == "2026-09-05"
    assert "credits" in state["runs"][0]["error"]


def test_runtime_rejects_out_of_order_command(env):
    from infra.runtime import execute
    repo, client, session = env
    client.post("/api/clock", json={"days":1})
    second = client.post("/api/clock", json={"days":1}).json()["run_id"]
    with pytest.raises(RuntimeError, match="pending"):
        execute(repo, second)
    assert repo.snapshot(session["session_id"])["session"]["now"] == "2026-09-05"
