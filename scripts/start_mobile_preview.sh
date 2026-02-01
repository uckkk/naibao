#!/bin/bash

# 一键启动：后端（docker compose）+ 前端 H5（5173）+ Cloudflare 临时外网地址
# 目的：方便“外网手机验收”，无需部署到服务器。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FRONT_DIR="${ROOT_DIR}/frontend"
DEV_LOG="${FRONT_DIR}/dev-h5.log"
DEV_PID_FILE="${FRONT_DIR}/dev-h5.pid"

TUN_LOG="${FRONT_DIR}/cloudflared.log"
TUN_PID_FILE="${FRONT_DIR}/cloudflared.pid"

echo "[1/4] start backend (docker compose)..."
docker compose -f "${ROOT_DIR}/docker-compose.yml" up -d --build >/dev/null

echo "[2/4] start frontend (uni-h5 dev server)..."
if [ -f "${DEV_PID_FILE}" ]; then
  OLD_PID="$(cat "${DEV_PID_FILE}" 2>/dev/null || true)"
  if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
    echo "frontend already running (pid=${OLD_PID})"
  else
    rm -f "${DEV_PID_FILE}"
  fi
fi

if [ ! -f "${DEV_PID_FILE}" ]; then
  (cd "${FRONT_DIR}" && nohup npm run dev:h5 >"${DEV_LOG}" 2>&1 & echo $! > "${DEV_PID_FILE}")
fi

echo "[3/4] wait frontend ready..."
python3 - <<PY
import time, urllib.request
url = "http://127.0.0.1:5173/#/pages/login/index"
for _ in range(60):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            if r.status == 200:
                print("ok")
                break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("frontend not ready on :5173")
PY

echo "[4/4] start cloudflared tunnel..."
command -v cloudflared >/dev/null 2>&1 || {
  echo "cloudflared not found. Install on macOS: brew install cloudflared" >&2
  exit 1
}

if [ -f "${TUN_PID_FILE}" ]; then
  OLD_PID="$(cat "${TUN_PID_FILE}" 2>/dev/null || true)"
  if [ -n "${OLD_PID}" ] && kill -0 "${OLD_PID}" 2>/dev/null; then
    echo "cloudflared already running (pid=${OLD_PID})"
  else
    rm -f "${TUN_PID_FILE}"
  fi
fi

if [ ! -f "${TUN_PID_FILE}" ]; then
  (cd "${FRONT_DIR}" && nohup cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:5173" >"${TUN_LOG}" 2>&1 & echo $! > "${TUN_PID_FILE}")
fi

python3 - <<PY
import re, time, pathlib
log = pathlib.Path(r"${TUN_LOG}")
pat = re.compile(r"https://[a-z0-9-]+\\.trycloudflare\\.com", re.I)
for _ in range(60):
    try:
        txt = log.read_text(errors="ignore")
        m = pat.search(txt)
        if m:
            print(m.group(0))
            break
    except Exception:
        pass
    time.sleep(1)
else:
    raise SystemExit("cloudflared url not found in log: " + str(log))
PY

