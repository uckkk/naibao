#!/usr/bin/env bash

# Start (or open) the mobile acceptance preview (Cloudflare quick tunnel) without a terminal.
# Intended to be invoked by a macOS AppleScript .app wrapper.
#
# What it does:
# - Starts backend (docker compose), frontend dev server, and cloudflared quick tunnel
# - Waits for `frontend/mobile-preview.url`
# - Opens the URL in browser + copies it to clipboard
#
# Logs:
# - .naibao_runtime/mobile_preview.app.log

set -euo pipefail

# AppleScript `do shell script` runs with a very minimal PATH (often missing Homebrew),
# which makes `docker` / `npm` look "not installed" even when they are.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${HOME:-}/.orbstack/bin:/Applications/Docker.app/Contents/Resources/bin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR="$ROOT_DIR/.naibao_runtime"
LOG_FILE="$RUNTIME_DIR/mobile_preview.app.log"
URL_FILE="$ROOT_DIR/frontend/mobile-preview.url"
PID_FILE="$ROOT_DIR/frontend/cloudflared.pid"

mkdir -p "$RUNTIME_DIR"

notify() {
  local msg="$1"
  /usr/bin/osascript - "$msg" <<'APPLESCRIPT' >/dev/null 2>&1 || true
on run argv
  set msg to item 1 of argv
  display notification msg with title "奶宝"
end run
APPLESCRIPT
}

dialog() {
  local title="$1"
  local msg="$2"
  /usr/bin/osascript - "$title" "$msg" <<'APPLESCRIPT' >/dev/null 2>&1 || true
on run argv
  set t to item 1 of argv
  set msg to item 2 of argv
  display dialog msg with title t buttons {"好"} default button 1
end run
APPLESCRIPT
}

open_url() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  fi
  if command -v pbcopy >/dev/null 2>&1; then
    printf "%s" "$url" | pbcopy || true
  fi
}

read_url() {
  if [ -f "$URL_FILE" ]; then
    tr -d '[:space:]' <"$URL_FILE" | head -n 1
  fi
}

is_alive() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

# If tunnel already running, just open the existing URL.
if [ -f "$PID_FILE" ]; then
  PID="$(tr -d '[:space:]' <"$PID_FILE" | head -n 1 || true)"
  if [[ "${PID:-}" =~ ^[0-9]+$ ]] && is_alive "$PID"; then
    URL="$(read_url)"
    if [[ "${URL:-}" =~ ^https:// ]]; then
      open_url "$URL"
      notify "外网验收链接已打开并复制"
      echo "$URL"
      exit 0
    fi
  fi
fi

notify "正在启动手机外网验收（首次可能较慢）"

# Run in background so the .app doesn't need to keep a terminal open.
nohup bash "$ROOT_DIR/scripts/start_mobile_preview.sh" >"$LOG_FILE" 2>&1 &

# Wait for URL file
for _ in $(seq 1 180); do
  URL="$(read_url)"
  if [[ "${URL:-}" =~ ^https:// ]]; then
    open_url "$URL"
    notify "外网验收链接已打开并复制"
    echo "$URL"
    exit 0
  fi
  sleep 1
done

dialog "启动超时" "没有在预期时间内拿到外网验收链接。\n\n你可以查看日志：\n${LOG_FILE}\n\n常见原因：cloudflared 临时隧道不稳定、网络受限、或前端 dev server 未起来。"
exit 1
