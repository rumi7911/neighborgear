import hashlib
import json
import os
import secrets
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .domain import seed, uid
from .store import Repository
from .worker import LocalWorker
from .schemas import Specification, CreateRequest, Approval, LifecycleEvent, ClockChange


def create_app(repository=None, start_worker=True):
    repo = repository or Repository()
    mode = os.getenv("NEIGHBORGEAR_MODE", "simulator")
    if mode not in ("simulator", "live"):
        raise ValueError("NEIGHBORGEAR_MODE must be simulator or live")

    @asynccontextmanager
    async def lifespan(app):
        worker = LocalWorker(repo)
        if start_worker:
            worker.start()
        yield
        if start_worker:
            worker.stop()

    app = FastAPI(title="NeighborGear sandbox", lifespan=lifespan)
    app.state.repository = repo
    origins = [origin.strip() for origin in os.getenv("NEIGHBORGEAR_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Sandbox-Token", "Idempotency-Key", "X-Judge-Key"])

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(status_code=422, content={"detail": "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors())})

    def session(x_sandbox_token: str | None = Header(None)):
        if not x_sandbox_token:
            raise HTTPException(401, "X-Sandbox-Token required")
        sid = repo.authenticate(hashlib.sha256(x_sandbox_token.encode()).hexdigest())
        if not sid:
            raise HTTPException(401, "Invalid sandbox token")
        return sid

    def enqueue(sid, operation, data=None, request_id=None, key=None, original_run_id=None):
        payload = dict(operation=operation, data=data or {}, request_id=request_id)
        if original_run_id:
            payload["original_run_id"] = original_run_id
        fingerprint_payload = dict(payload)
        if operation == "create":
            fingerprint_payload["request_id"] = None
        fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True).encode()).hexdigest()
        now = repo.snapshot(sid)["session"]["now"]
        run = dict(id=uid("run"), request_id=request_id, status="queued", error=None, created_at=now)
        event = dict(id=uid("evt"), request_id=request_id, type="run_queued", summary=f"{operation.replace('_',' ').title()} queued", created_at=now)
        try:
            return repo.enqueue(sid, payload, key, fingerprint, run, event)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": mode}

    @app.post("/api/sessions")
    def create_session(idempotency_key: str | None = Header(None), x_judge_key: str | None = Header(None)):
        judge_key = os.getenv("NEIGHBORGEAR_JUDGE_KEY")
        if judge_key and (not x_judge_key or not secrets.compare_digest(x_judge_key.encode(), judge_key.encode())):
            raise HTTPException(401, "Valid X-Judge-Key required to create a sandbox")
        sid, token = uid("session"), secrets.token_urlsafe(32)
        state = seed(sid, mode)
        response = dict(token=token, session_id=sid, mode=mode, now=state["session"]["now"])
        return repo.create(sid, hashlib.sha256(token.encode()).hexdigest(), state, idempotency_key, response)

    @app.get("/api/snapshot")
    def snapshot(sid=Depends(session)):
        result = repo.snapshot(sid)
        # Internal queue payloads are unnecessary for UI; records remain auditable.
        for run in result["runs"]:
            run.pop("payload", None)
        return result

    @app.post("/api/requests")
    def create_request(body: CreateRequest, sid=Depends(session), idempotency_key: str | None = Header(None)):
        return enqueue(sid, "create", body.model_dump(mode="json"), uid("request"), idempotency_key)

    @app.post("/api/requests/{request_id}/clarify")
    def clarify(request_id: str, body: Specification, sid=Depends(session), idempotency_key: str | None = Header(None)):
        return enqueue(sid, "clarify", body.model_dump(mode="json", exclude_none=True), request_id, idempotency_key)

    @app.post("/api/requests/{request_id}/approve")
    def approve(request_id: str, body: Approval, sid=Depends(session), idempotency_key: str | None = Header(None)):
        return enqueue(sid, "approve", body.model_dump(), request_id, idempotency_key)

    @app.post("/api/requests/{request_id}/events")
    def lifecycle_event(request_id: str, body: LifecycleEvent, sid=Depends(session), idempotency_key: str | None = Header(None)):
        return enqueue(sid, "event", body.model_dump(), request_id, idempotency_key)

    @app.post("/api/runs/{run_id}/retry")
    def retry(run_id: str, sid=Depends(session), idempotency_key: str | None = Header(None)):
        return enqueue(sid, "retry", key=idempotency_key, original_run_id=run_id)

    @app.post("/api/clock")
    def clock(body: ClockChange, sid=Depends(session), idempotency_key: str | None = Header(None)):
        return enqueue(sid, "clock", body.model_dump(), key=idempotency_key)

    @app.post("/api/reset")
    def reset(sid=Depends(session), idempotency_key: str | None = Header(None)):
        try:
            repo.reset(sid, seed(sid, mode), idempotency_key)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"status": "reset", "session_id": sid}

    return app


app = None if os.getenv("NEIGHBORGEAR_SKIP_DEFAULT_APP") == "true" else create_app()
