#!/usr/bin/env bash

# Start (or open) the local ops console without a terminal window.
# This script is intended to be invoked by a macOS AppleScript .app wrapper.

set -euo pipefail

# AppleScript `do shell script` runs with a very minimal PATH (often missing Homebrew),
# which makes `docker`, `npm`, etc. look "not installed" even when they are.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${HOME:-}/.orbstack/bin:/Applications/Docker.app/Contents/Resources/bin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR="$ROOT_DIR/.naibao_runtime"
PID_FILE="$RUNTIME_DIR/ops_console.pid"
PORT_FILE="$RUNTIME_DIR/ops_console.port"
LOG_FILE="$RUNTIME_DIR/ops_console.app.log"

BIND="127.0.0.1"
DEFAULT_PORT="17623"

is_alive() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

read_port() {
  if [ -f "$PORT_FILE" ]; then
    tr -d '[:space:]' <"$PORT_FILE" | head -n 1
  fi
}

open_url() {
  local port="$1"
  local url="http://${BIND}:${port}/"
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  fi
  echo "$url"
}

mkdir -p "$RUNTIME_DIR"

# 如果 pid 文件缺失但 port 文件存在，通常是上次异常退出留下的脏数据。
# 这里先清掉，避免误判“已启动”而直接打开一个并不存在的端口。
if [ ! -f "$PID_FILE" ] && [ -f "$PORT_FILE" ]; then
  rm -f "$PORT_FILE" >/dev/null 2>&1 || true
fi

# If an existing console is alive, just open it.
if [ -f "$PID_FILE" ]; then
  PID="$(tr -d '[:space:]' <"$PID_FILE" | head -n 1 || true)"
  if [[ "${PID:-}" =~ ^[0-9]+$ ]] && is_alive "$PID"; then
    PORT="$(read_port)"
    PORT="${PORT:-$DEFAULT_PORT}"
    open_url "$PORT"
    exit 0
  fi
  # Stale pid/port files.
  rm -f "$PID_FILE" "$PORT_FILE" >/dev/null 2>&1 || true
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found" >&2
  exit 2
fi

# Start in background (no terminal). The console itself will write pid/port files.
nohup python3 "$ROOT_DIR/scripts/local_ops_console.py" --bind "$BIND" --port "$DEFAULT_PORT" >"$LOG_FILE" 2>&1 &

# Wait a bit for the server to bind and write the port file.
for _ in $(seq 1 40); do
  PORT="$(read_port)"
  if [[ "${PORT:-}" =~ ^[0-9]+$ ]]; then
    open_url "$PORT"
    exit 0
  fi
  sleep 0.1
done

# Fallback: assume default port.
open_url "$DEFAULT_PORT"
