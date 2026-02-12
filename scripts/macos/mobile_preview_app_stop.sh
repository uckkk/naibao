#!/usr/bin/env bash

# Stop the mobile acceptance preview (frontend dev + cloudflared) without a terminal.
# Intended to be invoked by a macOS AppleScript .app wrapper.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

RUNTIME_DIR="$ROOT_DIR/.naibao_runtime"
LOG_FILE="$RUNTIME_DIR/mobile_preview.app.log"

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

bash "$ROOT_DIR/scripts/stop_mobile_preview.sh" >>"$LOG_FILE" 2>&1 || true
notify "已停止手机外网验收"

