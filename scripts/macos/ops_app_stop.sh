#!/usr/bin/env bash

# Stop the local ops console (best effort).
# Prefer graceful shutdown via HTTP API, fallback to SIGTERM.

set -euo pipefail

# AppleScript `do shell script` runs with a very minimal PATH (often missing Homebrew).
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${HOME:-}/.orbstack/bin:/Applications/Docker.app/Contents/Resources/bin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR="$ROOT_DIR/.naibao_runtime"
PID_FILE="$RUNTIME_DIR/ops_console.pid"
PORT_FILE="$RUNTIME_DIR/ops_console.port"

BIND="127.0.0.1"
DEFAULT_PORT="17623"

read_port() {
  if [ -f "$PORT_FILE" ]; then
    tr -d '[:space:]' <"$PORT_FILE" | head -n 1
  fi
}

read_pid() {
  if [ -f "$PID_FILE" ]; then
    tr -d '[:space:]' <"$PID_FILE" | head -n 1
  fi
}

is_alive() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

PORT="$(read_port)"
PORT="${PORT:-$DEFAULT_PORT}"

PID="$(read_pid)"

status_matches_repo() {
  local port="$1"
  local url="http://${BIND}:${port}/api/status"
  if command -v curl >/dev/null 2>&1; then
    local out
    out="$(curl -fsS -m 1 "$url" 2>/dev/null || true)"
    echo "$out" | grep -F "$ROOT_DIR" >/dev/null 2>&1 && return 0
    return 1
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - <<PY >/dev/null 2>&1 || return 1
import json, urllib.request
url = ${url@Q}
with urllib.request.urlopen(url, timeout=1) as r:
    raw = r.read(20000).decode("utf-8", errors="ignore")
if ${ROOT_DIR@Q} in raw:
    raise SystemExit(0)
raise SystemExit(1)
PY
    return 0
  fi

  return 1
}

shutdown_via_http_port() {
  local port="$1"
  local url="http://${BIND}:${port}/api/action"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -m 2 -X POST -H "Content-Type: application/json" -d '{"action":"ops_shutdown"}' "$url" >/dev/null 2>&1 || return 1
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - <<PY >/dev/null 2>&1 || return 1
import json, urllib.request
url = ${url@Q}
data = json.dumps({"action":"ops_shutdown"}).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=2) as r:
    r.read()
PY
    return 0
  fi

  return 1
}

# 先尽量用 HTTP 优雅关闭：优先读 PORT_FILE，其次默认端口。
for p in "$PORT" "$DEFAULT_PORT"; do
  if [[ "${p:-}" =~ ^[0-9]+$ ]] && status_matches_repo "$p"; then
    shutdown_via_http_port "$p" || true
    break
  fi
done

if [[ "${PID:-}" =~ ^[0-9]+$ ]] && is_alive "$PID"; then
  # Give it a moment to exit gracefully.
  for _ in $(seq 1 20); do
    if ! is_alive "$PID"; then
      rm -f "$PID_FILE" "$PORT_FILE" >/dev/null 2>&1 || true
      exit 0
    fi
    sleep 0.1
  done
  kill "$PID" >/dev/null 2>&1 || true
fi

# 清理运行时文件，避免下次误判。
rm -f "$PID_FILE" "$PORT_FILE" >/dev/null 2>&1 || true
