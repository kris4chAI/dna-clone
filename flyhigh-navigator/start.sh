#!/usr/bin/env bash
# Start FlyHigh Navigator (macOS / Linux). Usage: ./start.sh   ·   stop: docker compose down
set -euo pipefail
cd "$(dirname "$0")"
command -v docker >/dev/null || { echo "Docker is not installed. Install Docker Desktop: https://www.docker.com/products/docker-desktop/"; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker is installed but not running. Start Docker Desktop and retry."; exit 1; }
[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example (add LLM_API_KEY there to enable LLM drafting)."; }
docker compose up -d --build
PORT=$(grep -E '^FLYHIGH_PORT=' .env | cut -d= -f2); PORT=${PORT:-8080}
echo -n "Waiting for FlyHigh Navigator on http://localhost:${PORT} "
for i in $(seq 1 90); do
  if curl -fsS "http://localhost:${PORT}/api/health" >/dev/null 2>&1; then
    echo; echo "Ready: http://localhost:${PORT}"
    (command -v open >/dev/null && open "http://localhost:${PORT}") || (command -v xdg-open >/dev/null && xdg-open "http://localhost:${PORT}") || true
    exit 0
  fi
  echo -n "."; sleep 2
done
echo; echo "Not ready yet. Check: docker compose logs app"; exit 1
