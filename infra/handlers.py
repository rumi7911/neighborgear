"""AWS Lambda API, SQS worker and scheduled repair entrypoints."""
import json
import logging
import os
from functools import lru_cache
from uuid import uuid4
import boto3
from botocore.config import Config
from infra.repository import DynamoRepository
from infra.dispatch import publish, sweep
from infra.runtime import execute


@lru_cache
def repository():
    return DynamoRepository()


@lru_cache
def client(service):
    return boto3.client(service, config=Config(connect_timeout=3, read_timeout=85 if service == "bedrock-agentcore" else 5, retries={"total_max_attempts":1,"mode":"standard"}))


@lru_cache
def api_adapter():
    os.environ["NEIGHBORGEAR_SKIP_DEFAULT_APP"] = "true"
    from backend.app import create_app
    from mangum import Mangum
    return Mangum(create_app(repository(), start_worker=False), lifespan="off")


def api_handler(event, context):
    if not os.getenv("NEIGHBORGEAR_JUDGE_KEY"):
        return {"statusCode":503,"body":json.dumps({"detail":"Judge access not configured"})}
    reason = repository().control_reason()
    if reason:
        return {"statusCode":503,"headers":{"content-type":"application/json"},"body":json.dumps({"detail":reason})}
    response = api_adapter()(event, context)
    if response["statusCode"] < 300:
        receipt = json.loads(response.get("body") or "{}")
        if isinstance(receipt, dict) and receipt.get("run_id"):
            try:
                publish(repository(), client("sqs"), os.environ["NEIGHBORGEAR_QUEUE_URL"], receipt["run_id"])
            except Exception:
                # The accepted command is durable in DynamoDB. Scheduled repair
                # will re-publish it; do not misreport the accepted API write.
                logging.exception("SQS wake-up failed; durable command awaits scheduled repair")
    return response


def worker_handler(event, context):
    if repository().control_reason():
        # Acknowledge the wake-up, not the durable command. Owner recovery can
        # explicitly resume pending work; never loop SQS retries while stopped.
        return {"batchItemFailures":[]}
    failures = []
    for record in event["Records"]:
        try:
            run_id = json.loads(record["body"])["run_id"]
            if os.getenv("NEIGHBORGEAR_MODE", "simulator") == "live":
                result = client("bedrock-agentcore").invoke_agent_runtime(agentRuntimeArn=os.environ["NEIGHBORGEAR_RUNTIME_ARN"], runtimeSessionId=str(uuid4()), payload=json.dumps({"run_id":run_id}).encode(), contentType="application/json")
                with result["response"] as body:
                    outcome = json.loads(body.read())
            else:
                outcome = execute(repository(), run_id)
            if outcome.get("status") not in ("succeeded", "failed", "discarded", "stopped"):
                raise RuntimeError("Agent runtime did not report a terminal result")
        except Exception:
            logging.exception("Runtime invocation failed; SQS will retry")
            failures.append({"itemIdentifier":record["messageId"]})
    return {"batchItemFailures":failures}


def sweep_handler(event, context):
    reason = repository().control_reason()
    if reason:
        return {"status":"stopped", "reason":reason}
    sweep(repository(), client("sqs"), os.environ["NEIGHBORGEAR_QUEUE_URL"])
    return {"status":"checked"}
