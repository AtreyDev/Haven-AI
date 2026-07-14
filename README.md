# Harbor LifeLine

**When the grid dies, the Harbor stays lit.**

An offline survival mesh network for post-disaster scenarios. When cellular
networks, power grids, and internet access fail, Harbor LifeLine keeps
life-saving knowledge accessible over Bluetooth or LAN — with zero external
API calls.

Built for **OSDHack 2026**, theme: **"On Device AI."**

> Harbor LifeLine runs `llama3.2:3b` 100% locally via [Harbor](https://github.com/av/harbor)
> and Ollama, fully provable in Airplane mode with Wi-Fi disconnected — a direct
> answer to the **On Device AI** theme this event is built around.

## The Core Loop

A laptop acting as a **Hub** runs a local `llama3.2:3b` model via Harbor +
Ollama. Nearby devices (phones, tablets, other laptops) connect over
**Bluetooth (RFCOMM/BLE)** or **LAN** to ask urgent survival questions and
get short, actionable, imperative instructions back. Every interaction is
logged to a serverless **SQLite** file in **WAL mode**, so critical data
survives unexpected power cycles and crashes.

Common crises (snakebite, cardiac arrest, hypothermia, arterial bleed, and
16 others) are answered **instantly from a pre-vetted knowledge base**,
bypassing LLM latency and hallucination risk entirely. Anything outside
that set falls back to the local model, which runs under a locked system
prompt that refuses to speculate.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HUB NODE (Laptop)                             │
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐        │
│  │  Bluetooth   │    │  LAN HTTP    │    │   Local Web UI    │        │
│  │ RFCOMM/BLE   │    │  FastAPI     │    │    (optional)      │        │
│  │  Listener    │    │  :8001/api   │    │                    │        │
│  └──────┬───────┘    └──────┬───────┘    └──────────────────┘        │
│         │                   │                                          │
│         └──────────┬────────┘                                          │
│                     ▼                                                  │
│         ┌───────────────────┐                                         │
│         │   Bridge Service  │  (Python; the "brain stem")             │
│         │    hub_server.py  │                                         │
│         └─────┬─────────┬───┘                                         │
│               │         │                                              │
│               ▼         ▼                                              │
│      ┌───────────────┐ ┌──────────────────────┐                      │
│      │ Ollama/Harbor │ │       SQLite          │                      │
│      │  llama3.2:3b  │ │  survival_mesh.db     │                      │
│      │    :11434     │ │  (single file, WAL)   │                      │
│      └───────────────┘ └──────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
        ▲                                    ▲
        │ RFCOMM / BLE                       │ Wi-Fi Direct / hotspot
        │                                     │ (fallback)
 ┌──────┴─────────────┐              ┌────────┴────────────┐
 │  DISTRESS CLIENT    │              │   MOBILE CLIENT      │
 │  (python client.py  │              │  (Expo React Native   │
 │   on 2nd laptop)     │              │       app)            │
 └─────────────────────┘              └──────────────────────┘
```

**Transport priority:** RFCOMM (Linux laptop-to-laptop) → BLE GATT
(required for iOS, since RFCOMM is blocked by Apple) → LAN/Wi-Fi Direct
(fallback if Bluetooth is disabled).

## Repository Layout

```
harbor-lifeline/
├── db_setup.py              # Creates survival_mesh.db, seeds 20 KB entries
├── hub_server.py            # FastAPI LAN endpoint + Ollama bridge + RFCOMM listener
├── client.py                # CLI distress client (RFCOMM or --lan fallback)
├── run_integration_test.sh  # End-to-end smoke test (Hub + client + DB)
├── requirements.txt
├── Makefile                 # make setup / make up / make demo
├── LICENSE                  # MIT
└── mobile/                  # Expo React Native client (see mobile/README.md)
```

## Setup

```bash
# 1. Install Python deps
pip install -r requirements.txt --break-system-packages

# 2. Start Ollama via Harbor (one-command setup, no Docker Compose needed)
./harbor up ollama

# 3. Pull the model (do this BEFORE the event — see Risk Register below)
ollama pull llama3.2:3b

# 4. Create the database and seed the survival knowledge base
python3 db_setup.py
```

## Running the Hub

```bash
python3 hub_server.py
```

This starts:
- **FastAPI** on `http://0.0.0.0:8001` — `/api/chat`, `/api/health`,
  `/api/peers`, `/api/logs`
- **RFCOMM listener** in a background thread (Linux + PyBluez only; the
  Hub degrades gracefully and logs a clear message if PyBluez/Bluetooth
  isn't available — LAN transport keeps working regardless)

## Trying It — LAN Client

```bash
# Interactive
python3 client.py --lan --host localhost --port 8001

# One-shot (good for demos/CI)
python3 client.py --lan --host localhost --port 8001 --once "snake bite on right calf, no swelling yet"
```

## Trying It — RFCOMM Client (Bluetooth, Linux)

```bash
# Discover nearby Hubs
python3 client.py --scan

# Connect
python3 client.py --address AA:BB:CC:DD:EE:FF
```

Uses **insecure RFCOMM** (no pairing auth) by design — see Risk Register.

## One-Command Demo

```bash
make demo
```

Starts the Hub, waits for it to be healthy, sends a canonical distress
question over LAN, prints the KB-instant response with timing, then tears
the Hub down. This is the fastest way to prove the pipeline works end to
end.

## Database Schema

`survival_mesh.db`, `PRAGMA journal_mode=WAL`:

- **`distress_logs`** — every question/answer pair, transport used,
  latency, token count, and whether it was answered by the KB or the LLM.
- **`peers`** — devices that have connected, by MAC/IP, with first/last
  seen timestamps.
- **`survival_kb`** — 20 seeded keyword→answer pairs for instant, hallucination-free
  answers to common crises (snakebite, hypothermia, cardiac arrest,
  arterial bleed, choking, burns, fracture, dehydration, heatstroke,
  seizure, drowning, and more).

## Locked System Prompt

```
You are Harbor LifeLine, an offline survival AI. Reply in under 50 words.
Use short bulleted, imperative steps. Never speculate; if unsure say
'Insufficient data — conserve energy and wait.' Prioritize:
1) stop bleeding, 2) breathing, 3) shelter, 4) water, 5) signal.
```

Inference: temperature `0.2`, max tokens `120`.

## Risk Register (from the original blueprint)

| Risk | Mitigation |
|---|---|
| Judges test on iOS (RFCOMM blocked by Apple) | BLE GATT via `bleak`, fallback to LAN/hotspot |
| Poor venue Wi-Fi blocks model download | Pre-pull `llama3.2:3b` before the event; back up the `.gguf` on USB |
| Bluetooth pairing dialogs stall the demo | Insecure RFCOMM (no auth) or pre-pair devices beforehand |
| LLM hallucinates dangerous advice | Locked system prompt + `survival_kb` hardcoded lookups checked *before* inference |
| Laptop battery dies mid-demo | SQLite WAL survives power cycles; reboot and resume instantly |
| "Why not just use ChatGPT?" | Core narrative: no cell towers, no grid, real disaster zones — demo Airplane mode |

## Mobile Client

See [`mobile/`](./mobile) for the Expo React Native distress node (SOS
home screen, chat interface, BLE peer scanning, `expo-speech` TTS for
hands-free/low-visibility use).

## Testing

```bash
./run_integration_test.sh
```

Starts the Hub, exercises it via `client.py` with a KB-matching question
and a non-KB question (to prove graceful degradation when Ollama is
unreachable), then verifies both interactions were durably logged to
SQLite.

## License

MIT — see [`LICENSE`](./LICENSE). All dependencies (Ollama, Llama, FastAPI,
PyBluez, SQLite) are open source.
