"""Shared process_run entrypoint for local polling and cloud event delivery."""
import copy
import json
import threading
from .agent import extract, coordinate
from .domain import apply, event


def process_run(repository, run_id):
    queued = repository.get_run(run_id)
    if not queued:
        return
    if hasattr(repository, "has_predecessor") and repository.has_predecessor(run_id):
        return
    sid = queued["session_id"]
    payload = json.loads(queued["payload"]) if isinstance(queued["payload"], str) else queued["payload"]
    # The repository transaction serializes the complete session, including the
    # read/check/reserve operation. Re-delivery sees a terminal run and exits.
    status = "failed"
    with repository.transaction(sid) as state:
        run = next((r for r in state["runs"] if r["id"] == run_id), None)
        if run is None:
            return
        if run["status"] in ("succeeded", "failed"):
            status = run["status"]
        else:
            trial = copy.deepcopy(state)
            trial_run = next(r for r in trial["runs"] if r["id"] == run_id)
            try:
                extracted, trace = ({}, {"adapter": "domain_rules", "bedrock_used": False, "tool_calls": 0})
                if state["session"]["mode"] == "live":
                    trial, trace = coordinate(trial, payload)
                    trial_run = next(r for r in trial["runs"] if r["id"] == run_id)
                else:
                    if payload["operation"] == "create":
                        extracted, trace = extract(payload["data"].get("text", ""), "simulator")
                        from .schemas import Specification
                        extracted = Specification.model_validate(extracted).model_dump(mode="json", exclude_none=True)
                    apply(trial, payload, extracted)
                trial_run.update(trace)
                trial_run["status"] = status = "succeeded"
                event(trial, payload.get("request_id"), "run_succeeded", f"{payload['operation']} completed ({trace['adapter']}).")
                state.clear()
                state.update(trial)
            except Exception as exc:
                import os
                attempted = state["session"]["mode"] == "live" and os.getenv("NEIGHBORGEAR_CREDITS_VERIFIED") == "true"
                run.update(status="failed", error=str(exc)[:1000], bedrock_used=trace.get("bedrock_used") if trace.get("bedrock_used") else (None if attempted else False), bedrock_attempted=attempted, adapter="strands_bedrock" if state["session"]["mode"] == "live" else "deterministic_simulator")
                event(state, payload.get("request_id"), "run_failed", str(exc)[:500])
    # If the process dies between these writes, the committed terminal run is
    # authoritative; next delivery only repairs the queue acknowledgement.
    repository.finish_queue(run_id, status)


class LocalWorker:
    def __init__(self, repository):
        self.repository = repository
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True, name="neighborgear-events")

    def loop(self):
        while not self.stop_event.is_set():
            for item in self.repository.pending():
                if self.stop_event.is_set():
                    break
                try:
                    process_run(self.repository, item["id"])
                except Exception:
                    # The durable queue remains pending after transient DB errors.
                    import logging
                    logging.exception("Queue processing interrupted; retained for recovery")
            self.stop_event.wait(0.2)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=2)
