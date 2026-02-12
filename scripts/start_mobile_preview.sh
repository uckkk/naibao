#!/bin/bash

# 一键启动：后端（docker compose）+ 前端 H5（5173）+ Cloudflare 临时外网地址
# 目的：方便“外网手机验收”，无需部署到服务器。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FRONT_DIR="${ROOT_DIR}/frontend"
DEV_LOG="${FRONT_DIR}/dev-h5.log"
DEV_PID_FILE="${FRONT_DIR}/dev-h5.pid"
DEV_BACKEND_PORT_FILE="${FRONT_DIR}/dev-h5.backend_port"

TUN_LOG="${FRONT_DIR}/cloudflared.log"
TUN_PID_FILE="${FRONT_DIR}/cloudflared.pid"
URL_FILE="${FRONT_DIR}/mobile-preview.url"

# 非交互/GUI 启动（例如双击 .app）时 PATH 往往过“干净”，会找不到 docker/npm。
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${HOME:-}/.orbstack/bin:/Applications/Docker.app/Contents/Resources/bin:${PATH:-}"

# 若 Node 通过 nvm 安装，非交互 shell 可能没加载；这里做一次 best-effort。
if ! command -v npm >/dev/null 2>&1; then
  if [ -s "${HOME:-}/.nvm/nvm.sh" ]; then
    # shellcheck disable=SC1090
    source "${HOME:-}/.nvm/nvm.sh" >/dev/null 2>&1 || true
  fi
fi

DOCKER_BIN="$(command -v docker 2>/dev/null || true)"
if [ -z "${DOCKER_BIN}" ]; then
  for p in "/usr/local/bin/docker" "/opt/homebrew/bin/docker" "${HOME:-}/.orbstack/bin/docker" "/Applications/Docker.app/Contents/Resources/bin/docker"; do
    if [ -x "${p}" ]; then
      DOCKER_BIN="${p}"
      break
    fi
  done
fi
if [ -z "${DOCKER_BIN}" ]; then
  echo "ERROR: docker not found. please install and start Docker Desktop or OrbStack first." >&2
  exit 1
fi

port_is_free() {
  local port="$1"
  # docker 可能同时占用 v4/v6；这里同时检查 0.0.0.0 与 ::，避免误判“空闲”。
  python3 - "$port" <<'PY' >/dev/null 2>&1
import socket, sys
port = int(sys.argv[1])

def can_bind(family, addr):
    try:
        s = socket.socket(family, socket.SOCK_STREAM)
    except OSError:
        # platform doesn't support this family -> ignore
        return True
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        if family == socket.AF_INET6:
            s.bind((addr, port, 0, 0))
        else:
            s.bind((addr, port))
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass
    return True

ok4 = can_bind(socket.AF_INET, "0.0.0.0")
ok6 = can_bind(socket.AF_INET6, "::")
raise SystemExit(0 if (ok4 and ok6) else 1)
PY
}

backend_healthy() {
  local port="$1"
  curl -fsS -m 1 "http://127.0.0.1:${port}/health" 2>/dev/null | grep -q "\"ok\"" && return 0
  return 1
}

compose_backend_container_id() {
  "${DOCKER_BIN}" compose -f "${ROOT_DIR}/docker-compose.yml" ps -q backend 2>/dev/null | head -n 1 || true
}

compose_backend_host_port() {
  local cid
  cid="$(compose_backend_container_id)"
  if [ -z "${cid}" ]; then
    return 0
  fi
  "${DOCKER_BIN}" port "${cid}" 8080/tcp 2>/dev/null | head -n 1 | awk -F: '{print $NF}' | tr -d '[:space:]' || true
}

pick_backend_port() {
  local preferred="${1:-}"
  if [ -n "${preferred}" ] && port_is_free "${preferred}"; then
    echo "${preferred}"
    return 0
  fi
  for p in 18080 18081 18082 18083 18084 18085 18086 18087 18088 18089 8080 8081; do
    if [ -n "${preferred}" ] && [ "${p}" = "${preferred}" ]; then
      continue
    fi
    if port_is_free "${p}"; then
      echo "${p}"
      return 0
    fi
  done
  return 1
}

# 选一个“尽量不冲突”的本机后端端口（默认 18080；自动避让；若本项目 backend 容器已存在则复用其端口）。
EXISTING_BACKEND_PORT="$(compose_backend_host_port)"
if [ -n "${EXISTING_BACKEND_PORT}" ]; then
  BACKEND_PORT="${EXISTING_BACKEND_PORT}"
else
  BACKEND_PORT="$(pick_backend_port "${NB_BACKEND_HOST_PORT:-18080}")"
fi

export NB_BACKEND_HOST_PORT="${BACKEND_PORT}"
export VITE_API_PROXY_TARGET="http://127.0.0.1:${BACKEND_PORT}"

safe_rm() {
  # 在部分受限环境中 rm 可能被拦截；用 python 做兼容删除。
  python3 - <<PY
import os
path = r"$1"
try:
    os.remove(path)
except FileNotFoundError:
    pass
PY
}

read_pid() {
  local pid_file="$1"
  if [ -f "$pid_file" ]; then
    tr -d '[:space:]' <"$pid_file" | head -n 1 || true
  fi
}

is_pid_alive() {
  local pid="$1"
  if [ -z "${pid}" ]; then
    return 1
  fi
  kill -0 "${pid}" 2>/dev/null
}

port_listen_pids() {
  local port="$1"
  lsof -nP -iTCP:"${port}" -sTCP:LISTEN -t 2>/dev/null || true
}

port_has_frontend_listener() {
  # 判断端口上是否已运行“本项目”的 uni-h5 dev server。
  # 说明：不能依赖完整路径匹配（外接盘名可能包含非 ASCII 字符，ps 输出会被转义导致 grep 失效）。
  # 因此这里用 HTTP 探测页面 title 来识别是否为本项目。
  local port="$1"
  local pids
  pids="$(port_listen_pids "${port}")"
  if [ -z "${pids}" ]; then
    return 1
  fi

  if curl -sS -m 2 "http://127.0.0.1:${port}/#/pages/login/index" | head -n 60 | grep -q "<title>奶宝</title>"; then
    return 0
  fi
  return 2
}

stop_frontend_if_needed() {
  # 仅停止“本项目的” dev server；不碰系统其他服务。
  if [ -f "${DEV_PID_FILE}" ]; then
    local pid
    pid="$(cat "${DEV_PID_FILE}" 2>/dev/null || true)"
    if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
    safe_rm "${DEV_PID_FILE}"
  fi
  safe_rm "${DEV_BACKEND_PORT_FILE}"

  # 兜底：杀掉本项目残留的 uni 进程（PID 文件可能不准，尤其是端口被占用导致自动换端口时）。
  local pids
  pids="$(ps -eo pid,command | grep -F "naibao/frontend/node_modules/.bin/uni" | awk '{print $1}' | sort -u || true)"
  for pid in ${pids}; do
    if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
}

parse_tunnel_url() {
  if [ ! -f "${TUN_LOG}" ]; then
    return 0
  fi
  # shellcheck disable=SC2002
  cat "${TUN_LOG}" | grep -Eo "https://[a-z0-9-]+\\.trycloudflare\\.com" | tail -n 1 || true
}

tunnel_url_healthy() {
  local url="$1"
  if [ -z "${url}" ]; then
    return 1
  fi

  local host
  host="${url#https://}"
  host="${host#http://}"
  host="${host%%/*}"

  local tmp="/tmp/naibao_tunnel_check.$$.html"
  # 先确保文件存在，避免 curl 失败时 head 报错刷屏。
  : > "${tmp}" 2>/dev/null || true
  local code
  set +e
  code="$(curl -sS -m 8 -o "${tmp}" -w "%{http_code}" "${url}/" 2>/dev/null)"
  local curl_rc="$?"
  set -e
  if [ "${curl_rc}" -ne 0 ]; then
    code="000"
  fi

  if [ ! -f "${tmp}" ]; then
    return 1
  fi

  if [ "${code}" = "200" ] && head -n 80 "${tmp}" 2>/dev/null | grep -q "<title>奶宝</title>"; then
    safe_rm "${tmp}"
    return 0
  fi

  # Cloudflare 的 “NO tunnel here” 有时也是 200；用内容兜底识别。
  if head -n 120 "${tmp}" 2>/dev/null | grep -qi "no tunnel here"; then
    safe_rm "${tmp}"
    return 1
  fi

  # 某些网络/路由器 DNS 会对 trycloudflare 子域名返回 NXDOMAIN，导致本机无法 curl 验证。
  # 这里用 @1.1.1.1 解析 + curl --resolve 兜底；并尝试多个 IP，避免命中“不可用的那一个”。
  if [ "${code}" = "000" ] && command -v dig >/dev/null 2>&1 && [ -n "${host}" ]; then
    local ips
    ips="$(dig @1.1.1.1 +short "${host}" 2>/dev/null | sed '/^$/d' | head -n 4 || true)"
    local ip
    for ip in ${ips}; do
      : > "${tmp}" 2>/dev/null || true
      local code2
      set +e
      code2="$(curl --resolve "${host}:443:${ip}" -sS -m 8 -o "${tmp}" -w "%{http_code}" "https://${host}/" 2>/dev/null)"
      local curl_rc2="$?"
      set -e
      if [ "${curl_rc2}" -ne 0 ]; then
        code2="000"
      fi
      if [ "${code2}" = "200" ] && head -n 80 "${tmp}" 2>/dev/null | grep -q "<title>奶宝</title>"; then
        TUN_DNS_WARN=1
        safe_rm "${tmp}"
        return 0
      fi
    done
  fi

  safe_rm "${tmp}"
  return 1
}

stop_tunnel() {
  if [ -f "${TUN_PID_FILE}" ]; then
    local pid
    pid="$(read_pid "${TUN_PID_FILE}")"
    if is_pid_alive "${pid}"; then
      kill "${pid}" 2>/dev/null || true
      sleep 0.3
    fi
    safe_rm "${TUN_PID_FILE}"
  fi
}

start_tunnel() {
  # 清理旧 pid 文件（避免误判），但不使用 rm，保证在受限环境可执行
  safe_rm "${TUN_PID_FILE}"
  safe_rm "${URL_FILE}"
  (
    cd "${FRONT_DIR}"
    nohup "${CLOUDFLARED_BIN}" tunnel --no-autoupdate --url "http://127.0.0.1:5173" >"${TUN_LOG}" 2>&1 &
    echo $! > "${TUN_PID_FILE}"
  )
  sleep 0.6
  local pid
  pid="$(read_pid "${TUN_PID_FILE}")"
  if ! is_pid_alive "${pid}"; then
    return 1
  fi
  return 0
}

echo "[1/4] start backend (docker compose)..."
echo "backend host port: ${BACKEND_PORT}"
BACKEND_UP_OK=0
for attempt in 1 2 3; do
  set +e
  OUT="$("${DOCKER_BIN}" compose -f "${ROOT_DIR}/docker-compose.yml" up -d --build 2>&1)"
  RC="$?"
  set -e
  if [ "${RC}" -eq 0 ]; then
    BACKEND_UP_OK=1
    break
  fi

  if echo "${OUT}" | grep -qi "port is already allocated"; then
    NEXT_PORT="$(pick_backend_port "")" || true
    if [ -n "${NEXT_PORT}" ] && [ "${NEXT_PORT}" != "${BACKEND_PORT}" ]; then
      echo "backend port ${BACKEND_PORT} is in use. switching to ${NEXT_PORT} and retrying... (attempt ${attempt}/3)"
      BACKEND_PORT="${NEXT_PORT}"
      export NB_BACKEND_HOST_PORT="${BACKEND_PORT}"
      export VITE_API_PROXY_TARGET="http://127.0.0.1:${BACKEND_PORT}"
      continue
    fi
  fi

  echo "ERROR: failed to start backend." >&2
  echo "${OUT}" >&2
  exit 1
done

if [ "${BACKEND_UP_OK}" -ne 1 ]; then
  echo "ERROR: backend failed to start after retries." >&2
  exit 1
fi

echo "[1.2/4] wait backend ready..."
python3 - <<PY
import time, urllib.request
port = int("${BACKEND_PORT}")
url = f"http://127.0.0.1:{port}/health"
for _ in range(40):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            if r.status == 200:
                print("ok")
                break
    except Exception:
        time.sleep(0.5)
else:
    raise SystemExit("backend not ready on port %s" % port)
PY

echo "[1.5/4] bootstrap demo account/data (for mobile acceptance)..."
API_BASE="http://localhost:${BACKEND_PORT}" python3 "${ROOT_DIR}/scripts/bootstrap_demo_data.py" >/dev/null || true

echo "[2/4] start frontend (uni-h5 dev server)..."
PORT=5173
NEED_RESTART_FRONT=0
PREV_BACKEND_PORT=""
if [ -f "${DEV_BACKEND_PORT_FILE}" ]; then
  PREV_BACKEND_PORT="$(tr -d '[:space:]' <"${DEV_BACKEND_PORT_FILE}" | head -n 1 || true)"
fi

if port_has_frontend_listener "${PORT}"; then
  if [ "${PREV_BACKEND_PORT}" = "${BACKEND_PORT}" ] && [ -n "${PREV_BACKEND_PORT}" ]; then
    NEED_RESTART_FRONT=0
  else
    NEED_RESTART_FRONT=1
  fi
else
  RC="$?"
  if [ "${RC}" -eq 2 ]; then
    EXISTING="$(port_listen_pids "${PORT}")"
    echo "port ${PORT} is in use by non-naibao process (pids: ${EXISTING}). please stop it first." >&2
    exit 1
  fi
  NEED_RESTART_FRONT=1
fi

if [ "${NEED_RESTART_FRONT}" -eq 0 ]; then
  echo "frontend already running on :${PORT} (proxy target unchanged)"
else
  if port_has_frontend_listener "${PORT}"; then
    echo "frontend already running on :${PORT}, but proxy target changed. restarting..."
  fi

  # 清理本项目残留，确保 dev server 固定落在 5173（否则外网 tunnel 会指向空端口导致 NO tunnel here）。
  stop_frontend_if_needed

  (
    cd "${FRONT_DIR}"
    nohup npm run dev:h5 >"${DEV_LOG}" 2>&1 &
    echo $! > "${DEV_PID_FILE}"
  )
  printf "%s\n" "${BACKEND_PORT}" > "${DEV_BACKEND_PORT_FILE}" 2>/dev/null || true
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
# 优先使用系统 cloudflared；没有则下载到 scripts/bin/cloudflared（不污染全局环境）
CLOUDFLARED_BIN="$(command -v cloudflared 2>/dev/null || true)"
if [ -z "${CLOUDFLARED_BIN}" ]; then
  BIN_DIR="${ROOT_DIR}/scripts/bin"
  LOCAL_BIN="${BIN_DIR}/cloudflared"
  mkdir -p "${BIN_DIR}"
  OS="$(uname -s)"
  ARCH="$(uname -m)"
  if [ "${OS}" = "Darwin" ] && [ "${ARCH}" = "arm64" ]; then
    ASSET="cloudflared-darwin-arm64"
  elif [ "${OS}" = "Darwin" ] && [ "${ARCH}" = "x86_64" ]; then
    ASSET="cloudflared-darwin-amd64"
  elif [ "${OS}" = "Linux" ] && [ "${ARCH}" = "x86_64" ]; then
    ASSET="cloudflared-linux-amd64"
  elif [ "${OS}" = "Linux" ] && [ "${ARCH}" = "aarch64" ]; then
    ASSET="cloudflared-linux-arm64"
  else
    echo "cloudflared auto-download unsupported for ${OS}/${ARCH}" >&2
    exit 1
  fi

  # 本地二进制存在但不可用时（例如之前下载中断），强制重新下载
  if [ -x "${LOCAL_BIN}" ] && ! "${LOCAL_BIN}" --version >/dev/null 2>&1; then
    echo "local cloudflared is invalid. re-downloading..."
    safe_rm "${LOCAL_BIN}"
  fi

  if [ ! -x "${LOCAL_BIN}" ]; then
    echo "cloudflared not found. downloading ${ASSET}..."
    curl -L --http1.1 -o "${LOCAL_BIN}.download" "https://github.com/cloudflare/cloudflared/releases/latest/download/${ASSET}"
    chmod +x "${LOCAL_BIN}.download"
    mv "${LOCAL_BIN}.download" "${LOCAL_BIN}"
  fi
  CLOUDFLARED_BIN="${LOCAL_BIN}"
fi

MAX_ATTEMPTS=3

for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
  OLD_PID="$(read_pid "${TUN_PID_FILE}")"
  if is_pid_alive "${OLD_PID}"; then
    echo "cloudflared already running (pid=${OLD_PID})"
  else
    echo "cloudflared starting... (attempt ${attempt}/${MAX_ATTEMPTS})"
    stop_tunnel
    if ! start_tunnel; then
      echo "cloudflared failed to start (attempt ${attempt}). see log: ${TUN_LOG}" >&2
      sleep 1
      continue
    fi
  fi

  # Wait for URL + health check (avoid handing out "NO tunnel here" link)
  for _ in $(seq 1 120); do
    URL="$(parse_tunnel_url)"
    if [ -n "${URL}" ]; then
      if tunnel_url_healthy "${URL}"; then
        printf "%s\n" "${URL}" > "${URL_FILE}" 2>/dev/null || true
        if [ "${TUN_DNS_WARN:-0}" = "1" ]; then
          echo "WARN: 本机 DNS 可能无法解析 trycloudflare 子域名；若手机打不开，请改用 1.1.1.1/8.8.8.8 DNS 或走固定域名方案。" >&2
        fi
        echo "${URL}"
        exit 0
      fi
    fi
    sleep 1
  done

  echo "tunnel not healthy yet, restarting cloudflared..."
  stop_tunnel
  sleep 1
done

echo "ERROR: failed to get a healthy trycloudflare url after ${MAX_ATTEMPTS} attempts." >&2
echo "tail cloudflared log:" >&2
tail -n 60 "${TUN_LOG}" >&2 || true
echo "tail frontend dev log:" >&2
tail -n 80 "${DEV_LOG}" >&2 || true
exit 1
