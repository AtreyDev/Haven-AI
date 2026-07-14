.PHONY: setup db up demo clean

# One-time setup: install deps, pull the model, create the DB.
setup:
	pip install -r requirements.txt --break-system-packages
	./harbor up ollama
	ollama pull llama3.2:3b
	python3 db_setup.py

# Just (re)create the DB with the seeded survival KB.
db:
	python3 db_setup.py

# Start the Hub (FastAPI on :8001 + RFCOMM listener if PyBluez is present).
up:
	python3 hub_server.py

# Demo script: starts the Hub in the background, waits for it to be ready,
# fires a canonical distress question through client.py over LAN so the
# whole pipeline (Hub -> KB/Ollama -> SQLite -> reply) is proven live in
# one command, then tears the Hub down again.
demo:
	@echo "Starting Hub..."
	@python3 hub_server.py > /tmp/harbor_hub.log 2>&1 & echo $$! > /tmp/harbor_hub.pid
	@for i in $$(seq 1 30); do \
		curl -s http://localhost:8001/api/health > /dev/null 2>&1 && break; \
		sleep 0.3; \
	done
	@echo ""
	@echo "Hub health:"
	@curl -s http://localhost:8001/api/health
	@echo ""
	@echo ""
	@echo "Sending distress question over LAN transport..."
	@python3 client.py --lan --host localhost --port 8001 --once "snake bite on right calf, no swelling yet"
	@echo "Stopping Hub..."
	@kill `cat /tmp/harbor_hub.pid` 2>/dev/null || true
	@rm -f /tmp/harbor_hub.pid

clean:
	rm -f survival_mesh.db survival_mesh.db-wal survival_mesh.db-shm
	rm -f /tmp/harbor_hub.log /tmp/harbor_hub.pid
