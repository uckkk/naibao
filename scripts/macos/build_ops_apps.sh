#!/usr/bin/env bash

# Build macOS double-clickable .app wrappers (no terminal).
# - Local ops console (start/stop)
# - Mobile acceptance preview (start/stop)
#
# Note: The generated .app should stay in the repo root (same directory level as scripts/).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ "$(uname -s)" != "Darwin" ]; then
  echo "ERROR: This script is for macOS (Darwin) only." >&2
  exit 2
fi

if ! command -v osacompile >/dev/null 2>&1; then
  echo "ERROR: osacompile not found (AppleScript tool missing)." >&2
  exit 2
fi

build_app() {
  local app_name="$1"
  local rel_sh="$2"
  local out="$ROOT_DIR/${app_name}.app"

  if [ -e "$out" ]; then
    echo "SKIP: already exists: $out"
    return 0
  fi

  osacompile -o "$out" - <<APPLESCRIPT
on run
  set appPath to POSIX path of (path to me)
  set repoDir to do shell script "dirname " & quoted form of appPath
  set target to repoDir & "/${rel_sh}"
  set ok to do shell script "test -f " & quoted form of target & " && echo ok || echo no"
  if ok is not "ok" then
    display dialog "找不到脚本：" & target & return & "请把本 App 放在 naibao 仓库根目录（与 scripts/ 同级）。" buttons {"好"} default button 1
    return
  end if
  do shell script "bash " & quoted form of target
end run
APPLESCRIPT

  echo "OK: $out"
}

build_app "奶宝运营台" "scripts/macos/ops_app_start.sh"
build_app "停止奶宝运营台" "scripts/macos/ops_app_stop.sh"
build_app "奶宝手机验收" "scripts/macos/mobile_preview_app_start.sh"
build_app "停止奶宝手机验收" "scripts/macos/mobile_preview_app_stop.sh"

echo ""
echo "完成。你现在可以在仓库根目录双击："
echo "- 奶宝运营台.app"
echo "- 停止奶宝运营台.app"
echo "- 奶宝手机验收.app"
echo "- 停止奶宝手机验收.app"
