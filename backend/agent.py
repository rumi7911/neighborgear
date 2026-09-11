"""Explicit simulator and bounded real Strands coordinator adapters."""
import multiprocessing
import os
import re
import queue

DEFAULT_MODEL_ID = "eu.amazon.nova-lite-v1:0"


def simulator_extract(text):
    """Only extract explicit supported facts; never invent missing values."""
    result = {}
    lower = text.lower()
    if "rollator" in lower:
        result["equipment_type"] = "rollator"
    elif "walking frame" in lower or "walking_frame" in lower:
        result["equipment_type"] = "walking_frame"
    for area in ("North", "Central", "South"):
        if re.search(rf"\b{area}\b", text, re.I):
            result["area"] = area
    height = re.search(r"(\d{2,3})\s*(?:-|–|to)\s*(\d{2,3})\s*cm", lower)
    if height:
        result.update(min_height_cm=float(height[1]), max_height_cm=float(height[2]))
    weight = re.search(r"(\d{2,3}(?:\.\d+)?)\s*kg", lower)
    if weight:
        result["user_weight_kg"] = float(weight[1])
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
    if dates:
        result["needed_by"] = dates[0]
    if len(dates) > 1:
        result["return_by"] = dates[1]
    times = re.findall(r"\b(?:[01]\d|2[0-3]):[0-5]\d\b", text)
    if len(times) >= 2:
        result.update(window_start=times[0], window_end=times[1])
    return result


def _live_child(state, payload, output):
    try:
        from strands.models import BedrockModel
        from .coordinator import run_coordinator
        model_id = os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)
        model = BedrockModel(model_id=model_id, region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "eu-west-1")), max_tokens=2048)
        updated, trace = run_coordinator(state, payload, model)
        output.put({"ok": True, "state": updated, "trace": {**trace, "model_id": model_id}})
    except Exception as exc:
        output.put({"ok": False, "error": str(exc)[:600]})


def extract(text, mode):
    if mode == "simulator":
        return simulator_extract(text), {"adapter": "deterministic_simulator", "bedrock_used": False, "tool_calls": 0}
    raise ValueError("Live requests must use the bound coordinator, not an extraction-only adapter")


def coordinate(state, payload):
    if os.getenv("NEIGHBORGEAR_CREDITS_VERIFIED") != "true":
        raise ValueError("Live Bedrock calls disabled: verify user-owned access and credits, then set NEIGHBORGEAR_CREDITS_VERIFIED=true")
    # A child process enforces a hard wall-clock deadline, including SDK retries.
    ctx = multiprocessing.get_context("spawn")
    output = ctx.Queue()
    proc = ctx.Process(target=_live_child, args=(state, payload, output))
    proc.start()
    # Read while the child is alive: large trial states otherwise deadlock the
    # multiprocessing queue's feeder thread when a parent joins before draining.
    try:
        result = output.get(timeout=60)
    except queue.Empty as exc:
        raise TimeoutError("Live agent exceeded 60 second execution budget; no simulator fallback") from exc
    finally:
        if proc.is_alive():
            proc.terminate()
        proc.join(5)
        output.close()
    if not result["ok"]:
        raise RuntimeError("Live coordination failed: " + result["error"])
    return result["state"], {"adapter": "strands_bedrock", "bedrock_used": True, **result["trace"]}
