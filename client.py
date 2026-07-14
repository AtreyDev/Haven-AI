"""
Harbor LifeLine - Distress Client (CLI)
Simulates the "second laptop" distress node from the architecture diagram.

Primary mode: connects to the Hub over raw RFCOMM Bluetooth (requires
PyBluez + a paired/discoverable Hub).

Fallback mode: --lan lets you point at the Hub's FastAPI endpoint instead,
so the KB/LLM pipeline can be exercised and demoed even without Bluetooth
hardware in the room (useful for judges' laptops, CI, or this sandbox).

Usage:
    python3 client.py --scan                     # discover nearby Hubs (RFCOMM)
    python3 client.py --address AA:BB:CC:DD:EE:FF # connect over RFCOMM
    python3 client.py --lan --host 192.168.1.5    # connect over LAN instead
    python3 client.py --lan --host localhost --port 8001 --once "snake bite"
"""

import argparse
import json
import sys
import time

import httpx


def run_rfcomm(address: str, channel: int):
    try:
        import bluetooth  # PyBluez
    except ImportError:
        print("[client] PyBluez not installed. Install with:")
        print("         pip install pybluez --break-system-packages")
        print("[client] Or use --lan to test over Wi-Fi instead.")
        sys.exit(1)

    print(f"[client] Connecting to Hub at {address} on RFCOMM channel {channel}...")
    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    try:
        sock.connect((address, channel))
    except Exception as e:
        print(f"[client] Connection failed: {e}")
        print("[client] Check the Hub is running, discoverable, and pre-paired "
              "(see Risk Register: 'Bluetooth pairing dialogs stall demo').")
        sys.exit(1)

    print("[client] Connected. Type a distress message and press Enter.")
    print("[client] Ctrl+C to quit.\n")

    try:
        while True:
            message = input("YOU> ").strip()
            if not message:
                continue

            payload = json.dumps({"message": message, "peer": "cli-client"}) + "\n"
            start = time.monotonic()
            sock.send(payload.encode("utf-8"))

            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(1024)
                if not chunk:
                    raise ConnectionError("Hub closed connection")
                buf += chunk

            line, _ = buf.split(b"\n", 1)
            result = json.loads(line.decode("utf-8"))
            rtt_ms = int((time.monotonic() - start) * 1000)

            print_response(result, rtt_ms)

    except KeyboardInterrupt:
        print("\n[client] Disconnecting.")
    finally:
        sock.close()


def run_lan(host: str, port: int, once: str = None):
    base_url = f"http://{host}:{port}"
    print(f"[client] Using LAN fallback transport -> {base_url}")

    try:
        health = httpx.get(f"{base_url}/api/health", timeout=5.0).json()
        print(f"[client] Hub reachable. Ollama reachable: {health.get('ollama_reachable')}, "
              f"model: {health.get('model')}\n")
    except httpx.HTTPError as e:
        print(f"[client] Could not reach Hub at {base_url}: {e}")
        sys.exit(1)

    def ask(message: str):
        start = time.monotonic()
        try:
            r = httpx.post(
                f"{base_url}/api/chat",
                json={"message": message, "peer_id": "cli-lan-client", "alias": "cli-client"},
                timeout=35.0,
            )
            r.raise_for_status()
            result = r.json()
        except httpx.HTTPError as e:
            print(f"[client] Request failed: {e}")
            return
        rtt_ms = int((time.monotonic() - start) * 1000)
        print_response(result, rtt_ms)

    if once:
        ask(once)
        return

    print("[client] Type a distress message and press Enter. Ctrl+C to quit.\n")
    try:
        while True:
            message = input("YOU> ").strip()
            if not message:
                continue
            ask(message)
    except KeyboardInterrupt:
        print("\n[client] Disconnecting.")


def print_response(result: dict, rtt_ms: int):
    source_tag = "[KB-INSTANT]" if result.get("source") == "kb" else "[AI-INFERRED]"
    print(f"HARBOR {source_tag} ({rtt_ms}ms round-trip, "
          f"{result.get('latency_ms')}ms server-side):")
    print(result.get("response", "(no response)"))
    print()


def main():
    parser = argparse.ArgumentParser(description="Harbor LifeLine distress client")
    parser.add_argument("--address", help="Hub Bluetooth MAC address (RFCOMM mode)")
    parser.add_argument("--channel", type=int, default=1, help="RFCOMM channel (default 1)")
    parser.add_argument("--scan", action="store_true", help="Scan for nearby Bluetooth Hubs")
    parser.add_argument("--lan", action="store_true", help="Use LAN/HTTP transport instead of RFCOMM")
    parser.add_argument("--host", default="localhost", help="Hub host for --lan mode")
    parser.add_argument("--port", type=int, default=8001, help="Hub port for --lan mode")
    parser.add_argument("--once", help="Send a single message and exit (non-interactive, for demos/CI)")
    args = parser.parse_args()

    if args.scan:
        try:
            import bluetooth
        except ImportError:
            print("[client] PyBluez not installed. Install with: "
                  "pip install pybluez --break-system-packages")
            sys.exit(1)
        print("[client] Scanning for nearby Bluetooth devices (5s)...")
        devices = bluetooth.discover_devices(duration=5, lookup_names=True)
        if not devices:
            print("[client] No devices found.")
        for addr, name in devices:
            print(f"  {addr}  {name}")
        return

    if args.lan:
        run_lan(args.host, args.port, once=args.once)
    elif args.address:
        run_rfcomm(args.address, args.channel)
    else:
        parser.error("Provide --address for RFCOMM mode, --lan for LAN mode, or --scan to discover Hubs.")


if __name__ == "__main__":
    main()
