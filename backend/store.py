"""Durable session documents and queue. Every domain mutation is one transaction.

Cloud repositories implement transaction(session_id) and the queue methods with
conditional version writes; domain code never relies on a SQLite connection.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Repository:
    def __init__(self, path=None):
        self.path = str(path or os.getenv("NEIGHBORGEAR_DB", "backend/data/neighborgear.sqlite3"))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, token_hash TEXT UNIQUE, state TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS queue(id TEXT PRIMARY KEY, session_id TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS idempotency(session_id TEXT,key TEXT, fingerprint TEXT, response TEXT, PRIMARY KEY(session_id,key));
              CREATE TABLE IF NOT EXISTS session_creations(key_hash TEXT PRIMARY KEY, response TEXT NOT NULL);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA journal_mode=WAL")
        db.row_factory = sqlite3.Row
        return db

    def create(self, sid, token_hash, state, creation_key=None, response=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if creation_key:
                import hashlib
                key_hash = hashlib.sha256(creation_key.encode()).hexdigest()
                prior = db.execute("SELECT response FROM session_creations WHERE key_hash=?", (key_hash,)).fetchone()
                if prior:
                    return json.loads(prior[0])
            db.execute("INSERT INTO sessions VALUES(?,?,?)", (sid, token_hash, json.dumps(state)))
            if creation_key:
                db.execute("INSERT INTO session_creations VALUES(?,?)", (key_hash, json.dumps(response)))
            return response

    def authenticate(self, token_hash):
        with self.connect() as db:
            row = db.execute("SELECT id FROM sessions WHERE token_hash=?", (token_hash,)).fetchone()
            return row["id"] if row else None

    @contextmanager
    def transaction(self, sid):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()
            if not row:
                raise ValueError("Sandbox not found")
            state = json.loads(row["state"])
            yield state
            db.execute("UPDATE sessions SET state=? WHERE id=?", (json.dumps(state), sid))
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def snapshot(self, sid):
        with self.connect() as db:
            row = db.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()
            return json.loads(row["state"]) if row else None

    def enqueue(self, sid, payload, key, fingerprint, run, event):
        # Queue insertion, projection and idempotency claim commit together.
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            if key:
                prior = db.execute("SELECT * FROM idempotency WHERE session_id=? AND key=?", (sid, key)).fetchone()
                if prior:
                    if prior["fingerprint"] != fingerprint:
                        raise ValueError("Idempotency-Key already used for a different operation")
                    return json.loads(prior["response"])
            state = json.loads(db.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()[0])
            if payload.get("request_id") and payload["operation"] != "create":
                if not any(r["id"] == payload["request_id"] for r in state["requests"]):
                    raise ValueError("Request not found in this sandbox")
            if payload["operation"] == "retry":
                original = next((r for r in state["runs"] if r["id"] == payload["original_run_id"]), None)
                if not original or original["status"] != "failed":
                    raise ValueError("Only failed runs in this sandbox can be retried")
                payload = dict(original["payload"])
                run["request_id"] = payload.get("request_id")
                event["request_id"] = payload.get("request_id")
            run["payload"] = payload
            state["runs"].append(run)
            state["events"].append(event)
            response = {"run_id": run["id"], "event_id": event["id"]}
            if payload["operation"] == "create":
                response["request_id"] = payload["request_id"]
            db.execute("INSERT INTO queue VALUES(?,?,?,?)", (run["id"], sid, json.dumps(payload), "queued"))
            db.execute("UPDATE sessions SET state=? WHERE id=?", (json.dumps(state), sid))
            if key:
                db.execute("INSERT INTO idempotency VALUES(?,?,?,?)", (sid, key, fingerprint, json.dumps(response)))
            db.commit()
            return response
        finally:
            db.close()

    def pending(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM queue WHERE status IN ('queued','running') ORDER BY rowid")]

    def get_run(self, run_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM queue WHERE id=?", (run_id,)).fetchone()
            return dict(row) if row else None

    def has_predecessor(self, run_id):
        """Queue order is authoritative even when several consumers race."""
        with self.connect() as db:
            return bool(db.execute("SELECT 1 FROM queue earlier JOIN queue current ON earlier.session_id=current.session_id WHERE current.id=? AND earlier.rowid<current.rowid AND earlier.status IN ('queued','running') LIMIT 1", (run_id,)).fetchone())

    def finish_queue(self, run_id, status):
        with self.connect() as db:
            db.execute("UPDATE queue SET status=? WHERE id=?", (status, run_id))

    def reset(self, sid, state, key=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if key:
                previous = db.execute("SELECT fingerprint FROM idempotency WHERE session_id=? AND key=?", (sid, key)).fetchone()
                if previous:
                    if previous[0] != "reset":
                        raise ValueError("Idempotency-Key already used for a different operation")
                    return
            db.execute("UPDATE sessions SET state=? WHERE id=?", (json.dumps(state), sid))
            db.execute("DELETE FROM queue WHERE session_id=?", (sid,))
            db.execute("DELETE FROM idempotency WHERE session_id=? AND fingerprint != 'reset'", (sid,))
            if key:
                db.execute("INSERT INTO idempotency VALUES(?,?,?,?)", (sid, key, "reset", "{}"))
