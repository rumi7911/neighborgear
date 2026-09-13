import json
from types import SimpleNamespace
import boto3
from infra.tests.test_repository import env


def api_event(path, body, headers):
    return {"version":"2.0", "routeKey":"ANY /api/{proxy+}", "rawPath":path, "rawQueryString":"", "headers":headers,
            "requestContext":{"http":{"method":"POST","path":path,"sourceIp":"127.0.0.1","protocol":"HTTP/1.1"},"stage":"$default"},
            "body":json.dumps(body),"isBase64Encoded":False}


def test_lambda_api_preserves_accepted_run_when_sqs_is_unavailable(env, monkeypatch):
    from infra import handlers
    repo, _, session = env
    monkeypatch.setenv("NEIGHBORGEAR_JUDGE_KEY","private-fictional-judge-key")
    monkeypatch.setenv("NEIGHBORGEAR_QUEUE_URL","unavailable")
    monkeypatch.setattr(handlers,"repository",lambda:repo)
    monkeypatch.setattr(handlers,"client",lambda service:boto3.client(service,region_name="eu-west-1"))
    handlers.api_adapter.cache_clear()
    result = handlers.api_handler(api_event("/api/requests",{"name":"Example","text":"rollator"},{"content-type":"application/json","x-sandbox-token":session["token"]}), SimpleNamespace())
    assert result["statusCode"] == 200
    receipt = json.loads(result["body"])
    assert repo.get_run(receipt["run_id"])["status"] == "queued"
    handlers.api_adapter.cache_clear()


def test_lambda_api_fails_closed_without_judge_configuration(monkeypatch):
    from infra.handlers import api_handler
    monkeypatch.delenv("NEIGHBORGEAR_JUDGE_KEY",raising=False)
    assert api_handler({},None)["statusCode"] == 503


def test_worker_executes_simulator_run_without_agentcore(env, monkeypatch):
    from infra import handlers
    repo, _, _ = env
    calls = []
    monkeypatch.setenv("NEIGHBORGEAR_MODE", "simulator")
    monkeypatch.setattr(handlers, "repository", lambda: repo)
    monkeypatch.setattr(handlers, "execute", lambda actual_repo, run_id: calls.append((actual_repo, run_id)) or {"status": "succeeded"}, raising=False)
    monkeypatch.setattr(handlers, "client", lambda service: (_ for _ in ()).throw(AssertionError("simulator must not create an AgentCore client")))
    event = {"Records": [{"messageId": "message-1", "body": json.dumps({"run_id": "run-1"})}]}

    assert handlers.worker_handler(event, None) == {"batchItemFailures": []}
    assert calls == [(repo, "run-1")]
