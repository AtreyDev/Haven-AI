#!/bin/bash
set -e
PROJECT_DIR="/home/claude/harbor-lifeline"
cd "$PROJECT_DIR"

echo "=== Starting hub_server.py ==="
python3 "$PROJECT_DIR/hub_server.py" > /tmp/hub_server.log 2>&1 &
HUB_PID=$!
echo "PID: $HUB_PID"

for i in $(seq 1 30); do
  if curl -s http://localhost:8001/api/health > /dev/null 2>&1; then
    echo "Hub is up after $i checks"
    break
  fi
  sleep 0.3
done

echo ""
echo "=== /api/health ==="
curl -s http://localhost:8001/api/health
echo ""
echo ""

echo "=== client.py --lan --once (arterial bleed -> should hit KB) ==="
python3 "$PROJECT_DIR/client.py" --lan --host localhost --port 8001 --once "arterial bleed on forearm, spurting blood"

echo "=== client.py --lan --once (obscure question -> LLM fallback, graceful degrade expected) ==="
python3 "$PROJECT_DIR/client.py" --lan --host localhost --port 8001 --once "what's the best route up K2"

echo "=== Verifying DB rows written by these two requests ==="
python3 -c "
import sqlite3
conn = sqlite3.connect('$PROJECT_DIR/survival_mesh.db')
rows = conn.execute('SELECT peer_mac, transport, user_message, source, latency_ms FROM distress_logs ORDER BY id DESC LIMIT 2').fetchall()
for r in rows:
    print(r)
conn.close()
"

echo ""
echo "=== Stopping hub_server (PID $HUB_PID) ==="
kill $HUB_PID 2>/dev/null || true
wait $HUB_PID 2>/dev/null || true
echo "Done."
