#!/bin/bash

# 停止 start_mobile_preview.sh 启动的前端 dev server 与 cloudflared（不动 docker compose）。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONT_DIR="${ROOT_DIR}/frontend"

DEV_PID_FILE="${FRONT_DIR}/dev-h5.pid"
TUN_PID_FILE="${FRONT_DIR}/cloudflared.pid"

safe_rm() {
  python3 - <<PY
import os
path = r"$1"
try:
    os.remove(path)
except FileNotFoundError:
    pass
PY
}

stop_pid() {
  local pid_file="$1"
  local name="$2"
  if [ ! -f "${pid_file}" ]; then
    echo "${name}: not running"
    return 0
  fi
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [ -z "${pid}" ]; then
    safe_rm "${pid_file}"
    echo "${name}: not running"
    return 0
  fi
  if kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true
    echo "${name}: stopped (pid=${pid})"
  else
    echo "${name}: stale pid file (pid=${pid})"
  fi
  safe_rm "${pid_file}"
}

stop_pid "${TUN_PID_FILE}" "cloudflared"
stop_pid "${DEV_PID_FILE}" "frontend"
