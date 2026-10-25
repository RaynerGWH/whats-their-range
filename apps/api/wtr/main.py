import asyncio
from contextlib import asynccontextmanager
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    FastAPI,
    Depends,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Query,
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
    try:
        yield
    finally:
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
                (s["id"], s.get("version"), s["status"], s.get("phase")) for s in data
            ]
            if stamp != last:
                await ws.send_json({"type": "tables", "tables": data})
                last = stamp
            await asyncio.sleep(0.25)
    except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
        pass
