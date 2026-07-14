"""
Harbor LifeLine - Hub Server
"When the grid dies, the Harbor stays lit."

The bridge service (the "brain stem"). Runs on the Hub laptop and:
  1. Serves a FastAPI LAN endpoint (/api/chat) for phones on the hotspot
  2. Listens for raw RFCOMM Bluetooth connections (Linux/PyBluez)
  3. Checks survival_kb first for instant answers to common crises
  4. Falls back to local Ollama (llama3.2:3b) for anything else
  5. Logs every interaction to survival_mesh.db (WAL mode)

Usage:
    python3 db_setup.py          # once, to create the DB
    ./harbor up ollama            # start Ollama via Harbor
    ollama pull llama3.2:3b       # once, to pull the model
    python3 hub_server.py         # starts FastAPI (:8001) + RFCOMM listener

Env overrides:
    OLLAMA_HOST   default http://localhost:11434
    HUB_PORT      default 8001
    OLLAMA_MODEL  default llama3.2:3b
"""

import asyncio
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "survival_mesh.db")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
HUB_PORT = int(os.environ.get("HUB_PORT", "8001"))

# RFCOMM channel to bind on. 1 is conventional for a single custom service.
RFCOMM_CHANNEL = int(os.environ.get("RFCOMM_CHANNEL", "1"))

LOCKED_SYSTEM_PROMPT = (
    "You are Harbor LifeLine, an offline survival AI. Reply in under 50 words. "
    "Use short bulleted, imperative steps. Never speculate; if unsure say "
    "'Insufficient data — conserve energy and wait.' Prioritize: "
    "1) stop bleeding, 2) breathing, 3) shelter, 4) water, 5) signal."
)

INFERENCE_OPTIONS = {
    "temperature": 0.2,
    "num_predict": 120,  # max tokens out
}

BLE_MTU_CHUNK_SIZE = 180  # bytes, matches the transport matrix in the blueprint


# --------------------------------------------------------------------------
# Database helpers
# --------------------------------------------------------------------------

@contextmanager
def get_conn():
    """Short-lived WAL-mode connection per call. WAL allows concurrent
    readers/writers across the RFCOMM thread and the FastAPI event loop
    without locking the whole file."""
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _normalize(text: str) -> str:
    """Lowercase and collapse to single spaces so phrasing differences
    (e.g. 'snake bite' vs 'snakebite', 'snake-bite') don't cause a KB miss.
    Keeps letters/digits/spaces only."""
    import re
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def kb_lookup(message: str):
    """Match the incoming message against survival_kb keywords. This is the
    fast path: common crises get an instant, pre-vetted answer with zero LLM
    latency and zero hallucination risk (see Risk Register: 'LLM hallucinates
    dangerous advice').

    Matching is normalized and space-insensitive on both sides, so a
    single-word keyword like 'snakebite' matches a two-word message like
    'snake bite', and a multi-word keyword like 'cardiac arrest' matches
    regardless of extra whitespace/punctuation. Longer keywords are checked
    first so a more specific match (e.g. 'arterial bleed') wins over a
    shorter one that might also be present.
    """
    msg_norm = _normalize(message)
    msg_squashed = msg_norm.replace(" ", "")

    with get_conn() as conn:
        rows = conn.execute("SELECT keyword, answer FROM survival_kb").fetchall()

    rows_sorted = sorted(rows, key=lambda kv: len(kv[0]), reverse=True)

    for keyword, answer in rows_sorted:
        keyword_norm = _normalize(keyword)
        keyword_squashed = keyword_norm.replace(" ", "")
        if keyword_norm in msg_norm or keyword_squashed in msg_squashed:
            return keyword, answer

    return None, None


def log_interaction(peer_id: str, transport: str, user_message: str,
                     ai_response: str, latency_ms: int, tokens_out: int,
                     source: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO distress_logs
               (peer_mac, transport, user_message, ai_response,
                latency_ms, tokens_out, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (peer_id, transport, user_message, ai_response,
             latency_ms, tokens_out, source),
        )


def touch_peer(peer_id: str, alias: str = None):
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO peers (mac, alias, last_seen)
               VALUES (?, ?, ?)
               ON CONFLICT(mac) DO UPDATE SET
                   last_seen = excluded.last_seen,
                   alias = COALESCE(excluded.alias, peers.alias)""",
            (peer_id, alias, now),
        )


# --------------------------------------------------------------------------
# Core answer pipeline (shared by RFCOMM, BLE, and LAN paths)
# --------------------------------------------------------------------------

async def get_survival_answer(user_message: str, peer_id: str, transport: str) -> dict:
    """Single entry point every transport calls. KB-first, LLM-fallback.
    Returns dict with response text + metadata for logging/UI."""
    start = time.monotonic()

    keyword, kb_answer = kb_lookup(user_message)
    if kb_answer:
        latency_ms = int((time.monotonic() - start) * 1000)
        log_interaction(peer_id, transport, user_message, kb_answer,
                         latency_ms, len(kb_answer.split()), source="kb")
        return {
            "response": kb_answer,
            "source": "kb",
            "matched_keyword": keyword,
            "latency_ms": latency_ms,
        }

    # Fallback to Ollama
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": LOCKED_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "stream": False,
                    "options": INFERENCE_OPTIONS,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            ai_text = data.get("message", {}).get("content", "").strip()
            tokens_out = data.get("eval_count", len(ai_text.split()))
    except (httpx.HTTPError, httpx.TimeoutException, ConnectionError) as e:
        ai_text = ("Insufficient data — conserve energy and wait. "
                    "(Hub AI unreachable: check Ollama is running.)")
        tokens_out = 0
        print(f"[hub_server] Ollama error: {e}")

    latency_ms = int((time.monotonic() - start) * 1000)
    log_interaction(peer_id, transport, user_message, ai_text,
                     latency_ms, tokens_out, source="llm")

    return {
        "response": ai_text,
        "source": "llm",
        "matched_keyword": None,
        "latency_ms": latency_ms,
    }


def chunk_for_ble(text: str, size: int = BLE_MTU_CHUNK_SIZE):
    """Split a response into BLE-MTU-safe byte chunks for RX_CHAR writes."""
    encoded = text.encode("utf-8")
    return [encoded[i:i + size] for i in range(0, len(encoded), size)]


# --------------------------------------------------------------------------
# FastAPI app (LAN / Wi-Fi Direct transport — priority 3 fallback)
# --------------------------------------------------------------------------

app = FastAPI(title="Harbor LifeLine Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN-only hotspot demo; tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    peer_id: str = "lan-unknown"
    alias: str | None = None


class ChatResponse(BaseModel):
    response: str
    source: str
    matched_keyword: str | None
    latency_ms: int


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    touch_peer(req.peer_id, req.alias)
    result = await get_survival_answer(req.message, req.peer_id, transport="lan")
    return ChatResponse(**result)


@app.get("/api/health")
async def health():
    """Used by the mobile app's connection pill (BLE/LAN/Offline indicator)."""
    ollama_up = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            ollama_up = r.status_code == 200
    except Exception:
        pass
    return {"status": "ok", "ollama_reachable": ollama_up, "model": OLLAMA_MODEL}


@app.get("/api/peers")
async def list_peers():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT mac, alias, first_seen, last_seen FROM peers ORDER BY last_seen DESC"
        ).fetchall()
    return [
        {"mac": r[0], "alias": r[1], "first_seen": r[2], "last_seen": r[3]}
        for r in rows
    ]


@app.get("/api/logs")
async def recent_logs(limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, peer_mac, transport, user_message, ai_response,
                      latency_ms, source, timestamp
               FROM distress_logs ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    cols = ["id", "peer_mac", "transport", "user_message", "ai_response",
            "latency_ms", "source", "timestamp"]
    return [dict(zip(cols, r)) for r in rows]


# --------------------------------------------------------------------------
# RFCOMM listener (Priority 1 transport — Linux laptop-to-laptop)
# --------------------------------------------------------------------------
#
# Requires PyBluez + a Linux Bluetooth adapter. Runs in a background thread
# so it doesn't block the FastAPI event loop. Uses insecure RFCOMM (no
# pairing auth) per the Risk Register mitigation for "pairing dialogs
# stall demo" — devices should be pre-paired or auth-free for the pitch.
#
# Protocol: client sends one UTF-8 JSON line: {"message": "...", "peer": "..."}
# Server replies with one UTF-8 JSON line: {"response": "...", "source": "...", "latency_ms": N}

def rfcomm_listener():
    try:
        import bluetooth  # PyBluez
    except ImportError:
        print("[hub_server] PyBluez not installed — RFCOMM listener disabled.")
        print("[hub_server] Install with: pip install pybluez --break-system-packages")
        print("[hub_server] (LAN transport at :{} still fully functional.)".format(HUB_PORT))
        return

    loop = asyncio.new_event_loop()

    try:
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", RFCOMM_CHANNEL))
        server_sock.listen(1)

        bluetooth.advertise_service(
            server_sock,
            "HarborLifeLineHub",
            service_id="0000LIFE-0000-1000-8000-00805F9B34FB",
            service_classes=[bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE],
        )

        port = server_sock.getsockname()[1]
        print(f"[hub_server] RFCOMM listening on channel {port} "
              f"(insecure, no-auth per demo risk mitigation)")

        while True:
            client_sock, client_info = server_sock.accept()
            peer_mac = client_info[0]
            print(f"[hub_server] RFCOMM connection from {peer_mac}")
            threading.Thread(
                target=handle_rfcomm_client,
                args=(client_sock, peer_mac, loop),
                daemon=True,
            ).start()

    except Exception as e:
        print(f"[hub_server] RFCOMM listener failed to start: {e}")
        print("[hub_server] (Bluetooth adapter may be missing/disabled. "
              "LAN transport still functional.)")


def handle_rfcomm_client(client_sock, peer_mac: str, loop: asyncio.AbstractEventLoop):
    """One thread per connected distress client. Reads newline-delimited
    JSON requests, runs the async answer pipeline via run_coroutine_threadsafe,
    writes the JSON reply back."""
    try:
        touch_peer(peer_mac, alias="rfcomm-peer")
        buf = b""
        while True:
            data = client_sock.recv(1024)
            if not data:
                break
            buf += data
            if b"\n" not in buf:
                continue
            line, buf = buf.split(b"\n", 1)
            try:
                payload = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue

            message = payload.get("message", "")
            if not message:
                continue

            future = asyncio.run_coroutine_threadsafe(
                get_survival_answer(message, peer_mac, transport="rfcomm"), loop
            )
            result = future.result(timeout=35)

            reply = json.dumps(result) + "\n"
            client_sock.send(reply.encode("utf-8"))

    except Exception as e:
        print(f"[hub_server] RFCOMM client {peer_mac} error: {e}")
    finally:
        client_sock.close()
        print(f"[hub_server] RFCOMM connection closed: {peer_mac}")


def start_rfcomm_background():
    """Runs the RFCOMM listener's own event loop in a daemon thread so
    get_survival_answer() (async) can still be awaited from sync socket code."""
    def runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        rfcomm_listener()
        loop.run_forever()

    t = threading.Thread(target=runner, daemon=True)
    t.start()


# --------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    if not os.path.exists(DB_PATH):
        print("[hub_server] survival_mesh.db not found — run db_setup.py first.")
        raise SystemExit(1)

    print("=" * 60)
    print("  Harbor LifeLine Hub")
    print("  When the grid dies, the Harbor stays lit.")
    print("=" * 60)
    print(f"  Model:      {OLLAMA_MODEL} @ {OLLAMA_HOST}")
    print(f"  LAN API:    http://0.0.0.0:{HUB_PORT}/api/chat")
    print(f"  DB:         {DB_PATH}")
    print("=" * 60)

    start_rfcomm_background()

    uvicorn.run(app, host="0.0.0.0", port=HUB_PORT, log_level="info")
