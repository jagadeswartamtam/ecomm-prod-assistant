#!/bin/bash
set -euo pipefail

echo "Starting MCP server..."
python prod_assistant/mcp_server/product_search_server.py > /tmp/mcp_server.log 2>&1 &
MCP_PID=$!

echo "Waiting for MCP server to accept connections on port 8000..."
for i in $(seq 1 60); do
  if python - <<'PY'
import socket
import sys
s = socket.socket()
s.settimeout(1)
try:
    s.connect(("127.0.0.1", 8000))
    s.close()
    sys.exit(0)
except OSError:
    sys.exit(1)
PY
  then
    echo "MCP server is ready"
    break
  fi
  sleep 1
done

if ! python - <<'PY'
import socket
import sys
s = socket.socket()
s.settimeout(1)
try:
    s.connect(("127.0.0.1", 8000))
    s.close()
    sys.exit(0)
except OSError:
    sys.exit(1)
PY
then
  echo "MCP server did not become ready in time" >&2
  tail -n 50 /tmp/mcp_server.log >&2 || true
  exit 1
fi

echo "Starting FastAPI application..."
exec uvicorn prod_assistant.router.main:app --host 0.0.0.0 --port 8001 --workers 2
