"""AgentCore runtime operation. No service clients are created on import."""
import json
import os
from backend.worker import process_run


def execute(repo, run_id):
    reason = repo.control_reason()
    if reason:
        return {"status":"stopped", "reason":reason}
    queued = repo.get_run(run_id)
    if not queued:
        return {"status":"discarded", "reason":"Sandbox reset or expired"}
    if queued["status"] in ("succeeded", "failed"):
        return {"status":queued["status"], "session_id":queued["session_id"]}
    if not repo.claim(run_id):
        latest = repo.get_run(run_id)
        if latest and latest["status"] == "failed":
            return {"status":"failed", "session_id":queued["session_id"]}
        raise RuntimeError("Run pending: predecessor or active worker lease")
    sid = queued["session_id"]
    state = repo.snapshot(sid)
    reason = None
    if state["session"]["mode"] == "live":
        if os.getenv("NEIGHBORGEAR_CREDITS_VERIFIED") != "true":
            reason = "Live calls disabled: credits have not been verified"
        elif not repo.consume_budget(int(os.getenv("NEIGHBORGEAR_MAX_LIVE_RUNS", "10"))):
            reason = "Deployment model-run allowance exhausted; operator decision required"
    if reason:
        with repo.transaction(sid) as current:
            run = next(r for r in current["runs"] if r["id"] == run_id)
            run.update(status="failed", error=reason, bedrock_used=False)
        repo.finish_queue(run_id, "failed")
    else:
        process_run(repo, run_id)
    final = repo.get_run(run_id)
    if final and final["status"] in ("queued", "running"):
        raise RuntimeError("Run still pending after worker invocation")
    return {"status":final["status"] if final else "discarded", "session_id":sid}


def main():
    import boto3
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
    from infra.repository import DynamoRepository
    app = BedrockAgentCoreApp()
    repo = DynamoRepository()
    s3 = boto3.client("s3")

    @app.entrypoint
    def invoke(payload):
        result = execute(repo, payload["run_id"])
        if result.get("session_id"):
            state = repo.snapshot(result["session_id"])
            # Only business records; no model messages/private reasoning or bearer tokens.
            safe = {k:state[k] for k in ("session","requests","equipment","events","messages","approvals","reservations","assignments","loans")}
            s3.put_object(Bucket=os.environ["NEIGHBORGEAR_SESSION_BUCKET"], Key=f"sessions/{result['session_id']}/{payload['run_id']}.json", Body=json.dumps(safe).encode(), ContentType="application/json", ServerSideEncryption="AES256")
        return result
    app.run()


if __name__ == "__main__":
    main()
