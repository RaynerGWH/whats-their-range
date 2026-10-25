import asyncio
import os
import secrets
from contextlib import asynccontextmanager, suppress

from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from .models import Control, TournamentConfig
from .store import Store
from .workers import TableManager

origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")


def valid_token(value):
    token = os.getenv("CONTROL_TOKEN", "")
    return not token or (
        isinstance(value, str) and secrets.compare_digest(value, token)
    )


def authorized(authorization: str = Header(default="")):
    if not valid_token(authorization.removeprefix("Bearer ")):
        raise HTTPException(401, "Enter the server access token to connect.")


@asynccontextmanager
async def lifespan(app):
    if os.getenv("WTR_PUBLIC", "false").lower() == "true" and not os.getenv(
        "CONTROL_TOKEN"
    ):
        raise RuntimeError("Public deployment requires CONTROL_TOKEN")
    store = Store()
    store.initialize()
    app.state.store, app.state.manager = store, TableManager(store)

    async def reap_workers():
        while True:
            await asyncio.to_thread(app.state.manager.poll)
            await asyncio.sleep(0.5)

    monitor = asyncio.create_task(reap_workers())
    try:
        yield
    finally:
        monitor.cancel()
        with suppress(asyncio.CancelledError):
            await monitor
        await asyncio.to_thread(app.state.manager.close)
        store.engine.dispose()


app = FastAPI(title="What's Their Range?", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config", dependencies=[Depends(authorized)])
def config():
    return {
        "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "default_model": os.getenv("OPENROUTER_MODEL", ""),
        "tracing": os.getenv("LANGSMITH_TRACING", "false").lower() == "true",
        "storage": "postgres"
        if app.state.store.engine.dialect.name == "postgresql"
        else "sqlite",
        "max_tables": 2,
        "agent_call_limit": int(os.getenv("AGENT_MAX_CALLS", "100")),
    }


@app.get("/api/tables", dependencies=[Depends(authorized)])
def tables():
    return app.state.store.list()


@app.post("/api/tables", dependencies=[Depends(authorized)], status_code=201)
async def create_table(config: TournamentConfig):
    if config.mode == "openrouter":
        if not os.getenv("OPENROUTER_API_KEY"):
            raise HTTPException(
                400, "Set OPENROUTER_API_KEY in the backend .env first."
            )
        config.model = config.model or os.getenv("OPENROUTER_MODEL", "")
        if not config.model:
            raise HTTPException(400, "Choose an OpenRouter model ID.")
    try:
        return {"id": app.state.manager.create(config.model_dump())}
    except ValueError as e:
        raise HTTPException(409, str(e)) from None


@app.post(
    "/api/tables/{table_id}/control",
    dependencies=[Depends(authorized)],
    status_code=202,
)
async def control(table_id: str, command: Control):
    try:
        app.state.manager.control(table_id, command.model_dump())
    except ValueError as e:
        raise HTTPException(409, str(e)) from None
    return {"accepted": True, "note": "Applied at the next action boundary."}


@app.get("/api/tables/{table_id}/history", dependencies=[Depends(authorized)])
def history(
    table_id: str,
    before: int = Query(default=2**31 - 1, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
):
    return app.state.store.history(table_id, before, limit)


@app.websocket("/api/live")
async def live(ws: WebSocket):
    if ws.headers.get("origin") not in origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    try:
        auth = await asyncio.wait_for(ws.receive_json(), 5)
        if not isinstance(auth, dict) or not valid_token(auth.get("token")):
            await ws.close(code=1008)
            return
        last = None
        while True:
            # This only fans out snapshots; it never schedules poker decisions.
            app.state.manager.poll()
            data = await asyncio.to_thread(app.state.store.list)
            stamp = [
                (
                    s["id"],
                    s.get("version"),
                    s["status"],
                    s.get("phase"),
                    s.get("active_trace_id"),
                )
                for s in data
            ]
            if stamp != last:
                await ws.send_json({"type": "tables", "tables": data})
                last = stamp
            await asyncio.sleep(0.25)
    except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
        pass


@app.get("/api/tables/{table_id}/traces", dependencies=[Depends(authorized)])
def traces(
    table_id: str,
    hand: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None, max_length=512),
):
    if not app.state.store.has_table(table_id):
        raise HTTPException(404, "Table not found")
    try:
        return app.state.store.list_traces(table_id, hand, limit, cursor)
    except ValueError:
        raise HTTPException(400, "Invalid trace cursor") from None


@app.get("/api/tables/{table_id}/traces/{trace_id}", dependencies=[Depends(authorized)])
def trace(table_id: str, trace_id: str):
    result = app.state.store.get_trace(table_id, trace_id)
    if result is None:
        raise HTTPException(404, "Trace not found")
    return result
