"""Small judge-sandbox repository with whole-document optimistic transactions.

API writes never hold a lock during inference. A conflicting worker commit is
rejected and remains queued for retry. This favours safety over model-call cost;
use a small protected demo, not unbounded public/production traffic.
"""
import copy
import hashlib
import json
import os
import time
import math
from contextlib import contextmanager
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.config import Config


class Conflict(ValueError):
    pass


class DynamoRepository:
    def __init__(self, table_name=None, resource=None):
        self.resource = resource or boto3.resource("dynamodb", config=Config(connect_timeout=3, read_timeout=5, retries={"total_max_attempts":2,"mode":"standard"}))
        self.table = self.resource.Table(table_name or os.environ["NEIGHBORGEAR_TABLE"])
        self.client = self.table.meta.client

    def control_reason(self, now=None):
        """Read owner control on every entry; never cache or initialize it here."""
        name = os.getenv("NEIGHBORGEAR_CONTROL_TABLE")
        if not name:
            return "Demo stopped: owner control is not configured"
        try:
            item = self.resource.Table(name).get_item(Key={"pk":"CONTROL"}, ConsistentRead=True).get("Item", {})
            if item.get("enabled") is not True:
                return "Demo stopped by owner or control is missing"
            start, expiry = float(item["starts_at"]), float(item["expires_at"])
            current = time.time() if now is None else now
            if not all(math.isfinite(v) for v in (start, expiry, current)) or not 0 < expiry-start <= 21600:
                return "Demo stopped: invalid six-hour window"
            if not start <= current < expiry:
                return "Demo stopped: outside the approved six-hour window"
        except Exception:
            return "Demo stopped: owner control could not be verified"
        return None

    def _get(self, pk):
        item = self.table.get_item(Key={"pk":pk}, ConsistentRead=True).get("Item")
        return item if item and int(item["expires_at"]) > time.time() else None

    def _document(self, sid):
        item = self._get("SESSION#"+sid)
        if not item:
            raise ValueError("Sandbox expired or not found")
        return item

    def _commit(self, item):
        previous = int(item["version"])
        updated = {**item, "version":previous+1}
        if len(json.dumps(updated, default=int).encode()) > 340_000:
            raise ValueError("Sandbox size limit reached; reset the fictional sandbox")
        try:
            self.table.put_item(Item=updated, ConditionExpression=Attr("version").eq(previous))
        except self.client.exceptions.ConditionalCheckFailedException as exc:
            raise Conflict("Sandbox changed concurrently; retry the operation") from exc

    def _update(self, sid, action):
        for _ in range(5):
            item = self._document(sid)
            state, meta = json.loads(item["state"]), json.loads(item["meta"])
            result = action(state, meta)
            item.update(state=json.dumps(state), meta=json.dumps(meta))
            try:
                self._commit(item)
                return result
            except Conflict:
                continue
        raise Conflict("Sandbox busy; retry shortly")

    def create(self, sid, token_hash, state, creation_key=None, response=None):
        expiry = int(time.time()) + 7*86400
        creation_pk = "CREATE#"+hashlib.sha256(creation_key.encode()).hexdigest() if creation_key else None
        if creation_pk:
            existing = self._get(creation_pk)
            if existing:
                return json.loads(existing["response"])
        items = [{"pk":"SESSION#"+sid, "kind":"session", "version":0, "expires_at":expiry, "state":json.dumps(state), "meta":json.dumps({"queue":[],"keys":{}})},
                 {"pk":"AUTH#"+token_hash, "sid":sid, "expires_at":expiry}]
        if creation_pk:
            items.append({"pk":creation_pk,"response":json.dumps(response),"expires_at":expiry})
        try:
            self.client.transact_write_items(TransactItems=[{"Put":{"TableName":self.table.name,"Item":item,"ConditionExpression":"attribute_not_exists(pk)"}} for item in items])
        except self.client.exceptions.TransactionCanceledException as exc:
            existing = self._get(creation_pk) if creation_pk else None
            if existing:
                return json.loads(existing["response"])
            raise Conflict("Sandbox creation conflict; retry") from exc
        return response

    def authenticate(self, token_hash):
        item = self._get("AUTH#"+token_hash)
        return item["sid"] if item else None

    def snapshot(self, sid):
        return json.loads(self._document(sid)["state"])

    @contextmanager
    def transaction(self, sid):
        item = self._document(sid)
        state = json.loads(item["state"])
        yield state
        item["state"] = json.dumps(state)
        self._commit(item)

    def enqueue(self, sid, payload, key, fingerprint, run, event):
        def action(state, meta):
            prior = meta["keys"].get(key) if key else None
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise ValueError("Idempotency-Key already used for a different operation")
                return prior["response"]
            if len(state["runs"]) >= 60:
                raise ValueError("Sandbox run limit reached; reset the fictional sandbox")
            command = copy.deepcopy(payload)
            if command.get("request_id") and command["operation"] != "create" and not any(r["id"] == command["request_id"] for r in state["requests"]):
                raise ValueError("Request not found in this sandbox")
            if command["operation"] == "retry":
                original = next((r for r in state["runs"] if r["id"] == command["original_run_id"] and r["status"] == "failed"), None)
                if not original:
                    raise ValueError("Only failed runs in this sandbox can be retried")
                command = copy.deepcopy(original["payload"])
            queued = {**run,"request_id":command.get("request_id"),"payload":command}
            state["runs"].append(queued)
            state["events"].append({**event,"request_id":command.get("request_id")})
            meta["queue"].append({"id":run["id"],"session_id":sid,"payload":command,"status":"queued"})
            response = {"run_id":run["id"],"event_id":event["id"]}
            if command["operation"] == "create":
                response["request_id"] = command["request_id"]
            if key:
                meta["keys"][key] = {"fingerprint":fingerprint,"response":response}
            return response
        return self._update(sid, action)

    def documents(self):
        # Paginated scan is deliberately a small-demo compromise; no GSI lag in recovery.
        for page in self.client.get_paginator("scan").paginate(TableName=self.table.name, FilterExpression="#k = :k", ExpressionAttributeNames={"#k":"kind"}, ExpressionAttributeValues={":k":"session"}, ConsistentRead=True):
            for item in page["Items"]:
                if int(item["expires_at"]) > time.time():
                    yield item

    def pending(self):
        return [run for doc in self.documents() for run in json.loads(doc["meta"])["queue"] if run["status"] in ("queued","running")]

    def get_run(self, run_id):
        return next((run for doc in self.documents() for run in json.loads(doc["meta"])["queue"] if run["id"] == run_id), None)

    def has_predecessor(self, run_id):
        run = self.get_run(run_id)
        if not run:
            return False
        for previous in json.loads(self._document(run["session_id"])["meta"])["queue"]:
            if previous["id"] == run_id:
                return False
            if previous["status"] in ("queued","running"):
                return True
        return False

    def finish_queue(self, run_id, status):
        run = self.get_run(run_id)
        if run:
            def action(state, meta):
                for queued in meta["queue"]:
                    if queued["id"] == run_id:
                        queued["status"] = status
            self._update(run["session_id"], action)

    def reset(self, sid, state, key=None):
        def action(current, meta):
            prior = meta["keys"].get(key) if key else None
            if prior:
                if prior["fingerprint"] != "reset":
                    raise ValueError("Idempotency-Key already used for a different operation")
                return
            current.clear()
            current.update(copy.deepcopy(state))
            meta["queue"] = []
            meta["keys"] = {k:v for k,v in meta["keys"].items() if v["fingerprint"] == "reset"}
            if key:
                meta["keys"][key] = {"fingerprint":"reset","response":{}}
        self._update(sid, action)

    def claim(self, run_id, now=None):
        run = self.get_run(run_id)
        if not run or self.has_predecessor(run_id):
            return False
        now = time.time() if now is None else now
        def action(state, meta):
            queued = next((r for r in meta["queue"] if r["id"] == run_id), None)
            if not queued or queued["status"] not in ("queued", "running") or queued.get("lease_until", 0) > now:
                return False
            if queued.get("attempts", 0) >= 3:
                queued["status"] = "failed"
                result = next(r for r in state["runs"] if r["id"] == run_id)
                result.update(status="failed", error="Cloud attempt limit reached; review and retry explicitly")
                return False
            queued.update(attempts=queued.get("attempts", 0)+1, lease_until=now+75)
            return True
        return self._update(run["session_id"], action)

    def consume_budget(self, limit):
        if type(limit) is not int or limit < 1 or self.control_reason():
            return False
        limit = min(limit, 10)
        try:
            self.table.update_item(Key={"pk":"BUDGET"}, UpdateExpression="ADD #used :one", ConditionExpression=Attr("used").not_exists() | Attr("used").lt(limit), ExpressionAttributeNames={"#used":"used"}, ExpressionAttributeValues={":one":1})
            return True
        except self.client.exceptions.ConditionalCheckFailedException:
            return False
