"""Durable database queue is authoritative; SQS messages are wake-up hints."""
import hashlib
import json
import time
from backend.domain import uid


def publish(repo, sqs, queue_url, run_id):
    if repo.control_reason():
        return False
    run = repo.get_run(run_id)
    if not run or run["status"] not in ("queued", "running"):
        return False
    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"run_id":run_id}), MessageGroupId=run["session_id"], MessageDeduplicationId=f"{run_id}-{int(time.time())//300}")
    return True


def sweep(repo, sqs, queue_url):
    if repo.control_reason():
        return
    for document in repo.documents():
        state = json.loads(document["state"])
        due = [r["id"] for r in state["requests"] if r["status"] == "on_loan" and r["return_by"] <= state["session"]["now"] and not any(m["dedupe_key"] == f"{r['id']}:return_reminder" for m in state["messages"])]
        if due:
            key = "reminders:"+hashlib.sha256(json.dumps(sorted(due)).encode()).hexdigest()
            now = state["session"]["now"]
            repo.enqueue(state["session"]["id"], {"operation":"clock","request_id":None,"data":{"days":0}}, key, key,
                         {"id":uid("run"),"request_id":None,"status":"queued","error":None,"created_at":now},
                         {"id":uid("evt"),"request_id":None,"type":"reminders_queued","summary":"Checking reminders against the scenario clock","created_at":now})
    for run in repo.pending():
        publish(repo, sqs, queue_url, run["id"])
