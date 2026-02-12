#!/usr/bin/env python3

"""
奶宝 · 本机托管运营台（Local Ops Console）

目标：
- 运行一个本地网页，展示当前运行状态（docker services + API health + tunnel）
- 提供一键启动/重启能力，降低“本机挂着跑容易忘/崩了不知道怎么恢复”的成本

默认只绑定 127.0.0.1，避免暴露到局域网/公网。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import secrets
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from shutil import which
from typing import Any, Dict, List, Optional, Tuple


ROOT_DIR = Path(__file__).resolve().parent.parent
HOME_COMPOSE_FILE = ROOT_DIR / "deploy" / "docker-compose.home.yml"
HOME_ENV_FILE = ROOT_DIR / "deploy" / ".env.home"
HOME_ENV_EXAMPLE = ROOT_DIR / "deploy" / ".env.home.example"

RUNTIME_DIR = ROOT_DIR / ".naibao_runtime"
TUN_PID = RUNTIME_DIR / "cloudflared_api.pid"
TUN_LOG = RUNTIME_DIR / "cloudflared_api.log"
TUN_CFG = RUNTIME_DIR / "cloudflared_named.yml"
NAMED_INIT_PID = RUNTIME_DIR / "named_tunnel_init.pid"
NAMED_INIT_LOG = RUNTIME_DIR / "named_tunnel_init.log"
OPS_PID = RUNTIME_DIR / "ops_console.pid"
OPS_PORT = RUNTIME_DIR / "ops_console.port"
ALERTS_ENV_FILE = RUNTIME_DIR / "alerts.env"
ALERTS_STATE_FILE = RUNTIME_DIR / "alerts_state.json"
ALERTS_LOG = RUNTIME_DIR / "alerts.log"

FRONTEND_DIR = ROOT_DIR / "frontend"
MOBILE_PREVIEW_URL = FRONTEND_DIR / "mobile-preview.url"
MOBILE_PREVIEW_TUN_PID = FRONTEND_DIR / "cloudflared.pid"
MOBILE_PREVIEW_TUN_LOG = FRONTEND_DIR / "cloudflared.log"
MOBILE_PREVIEW_DEV_PID = FRONTEND_DIR / "dev-h5.pid"
MOBILE_PREVIEW_DEV_LOG = FRONTEND_DIR / "dev-h5.log"
MOBILE_PREVIEW_START_PID = RUNTIME_DIR / "mobile_preview_start.pid"
MOBILE_PREVIEW_START_LOG = RUNTIME_DIR / "mobile_preview_start.log"

DEFAULT_BACKEND_HOST_PORT = 18080

_CACHE: Dict[str, Tuple[float, Any]] = {}

# /api/status can be "slow by nature" (docker + dns + https checks). If it ever blocks,
# the ops UI becomes a blank page. We therefore compute status in background and serve
# a cached snapshot immediately.
_STATUS_LOCK = threading.Lock()
_STATUS_THREAD: Optional[threading.Thread] = None
_STATUS: Dict[str, Any] = {
    "ts": 0.0,
    "data": None,  # last successful payload (dict) or None
    "updating": False,
    "last_ok": False,
    "last_error": "",
    "last_duration_ms": 0,
}
STATUS_CACHE_MAX_AGE_S = 2.0


def humanize_error(msg: str) -> str:
    s = (msg or "").strip()
    if not s:
        return ""

    low = s.lower()

    # docker / docker compose
    if "no such file or directory" in low and "'docker'" in low:
        return "未检测到 Docker 命令（请先安装并启动 Docker Desktop 或 OrbStack）"
    if "docker not found in path" in low:
        return "未检测到 Docker 命令（请先安装并启动 Docker Desktop 或 OrbStack）"
    if "cannot connect to the docker daemon" in low or "docker daemon not reachable" in low:
        return "Docker 引擎未启动或无法连接（请先打开 Docker Desktop 或 OrbStack）"
    if "bind for" in low and "port is already allocated" in low:
        m = re.search(r"bind\\s+for\\s+.*:(\\d+)\\s+failed:\\s+port\\s+is\\s+already\\s+allocated", low)
        if m:
            return f"端口 {m.group(1)} 被占用（请在「后端端口」卡片里处理）"
        return "端口被占用（请在「后端端口」卡片里处理）"
    if "required variable postgres_password" in low and "missing a value" in low:
        return "环境变量 POSTGRES_PASSWORD 未配置（请检查 deploy/.env.home）"
    if "jwt_secret" in low and "required" in low:
        return "环境变量 JWT_SECRET 未配置（请检查 deploy/.env.home）"

    # DNS / network
    if "no records" in low:
        return "未配置记录"
    if "temporary failure in name resolution" in low or "name or service not known" in low:
        return "域名解析失败（DNS 未生效或网络受限）"
    if "timed out" in low or "context deadline exceeded" in low:
        return "请求超时（网络较差或服务未就绪）"
    if "connection refused" in low:
        return "连接被拒绝（服务未启动或端口未通）"
    if "eof occurred in violation of protocol" in low:
        return "TLS/HTTPS 连接失败（可能是网络问题、域名未生效或证书未就绪）"

    return s


def cached(key: str, ttl_s: int, fn) -> Any:
    now = time.time()
    hit = _CACHE.get(key)
    if hit and (now - float(hit[0])) < float(ttl_s):
        return hit[1]
    v = fn()
    _CACHE[key] = (now, v)
    return v


def _status_meta(now: Optional[float] = None) -> Dict[str, Any]:
    n = float(now if now is not None else time.time())
    with _STATUS_LOCK:
        ts = float(_STATUS.get("ts") or 0.0)
        data = _STATUS.get("data")
        updating = bool(_STATUS.get("updating", False))
        last_ok = bool(_STATUS.get("last_ok", False))
        last_error = str(_STATUS.get("last_error") or "")
        last_dur = int(_STATUS.get("last_duration_ms") or 0)
        th = _STATUS_THREAD

    age_s = int(max(0.0, n - ts)) if ts > 0 else 0
    th_alive = bool(th and th.is_alive())
    return {
        "has_data": bool(isinstance(data, dict) and data),
        "updating": bool(updating or th_alive),
        "age_s": int(age_s),
        "last_ok": bool(last_ok),
        "last_error": last_error,
        "last_duration_ms": int(last_dur),
    }


def _status_update_worker() -> None:
    global _STATUS_THREAD
    t0 = time.time()
    ok = True
    err = ""
    data: Optional[Dict[str, Any]] = None
    try:
        payload = status_payload()
        if not isinstance(payload, dict):
            raise ValueError("status_payload 返回格式异常")
        data = payload
    except Exception as e:
        ok = False
        err = humanize_error(str(e)) or str(e)
        data = None

    dur_ms = int(max(0.0, (time.time() - t0) * 1000.0))
    with _STATUS_LOCK:
        _STATUS["updating"] = False
        _STATUS["last_ok"] = bool(ok)
        _STATUS["last_error"] = str(err or "")
        _STATUS["last_duration_ms"] = int(dur_ms)
        # Only replace cached snapshot when we have a valid dict.
        if ok and isinstance(data, dict) and data:
            _STATUS["data"] = data
            _STATUS["ts"] = float(data.get("ts") or time.time())
        _STATUS_THREAD = None


def ensure_status_update(force: bool = False) -> None:
    """
    Best-effort background refresh for /api/status.
    - force: refresh even if cache is fresh
    """
    global _STATUS_THREAD
    now = time.time()
    with _STATUS_LOCK:
        ts = float(_STATUS.get("ts") or 0.0)
        th = _STATUS_THREAD
        th_alive = bool(th and th.is_alive())
        fresh = (ts > 0) and ((now - ts) <= float(STATUS_CACHE_MAX_AGE_S))
        if th_alive:
            _STATUS["updating"] = True
            return
        if (not force) and fresh:
            return
        _STATUS["updating"] = True
        _STATUS_THREAD = threading.Thread(target=_status_update_worker, daemon=True)
        _STATUS_THREAD.start()


def status_payload_cached() -> Dict[str, Any]:
    """
    Return a cached snapshot immediately; trigger a background update when stale.
    """
    ensure_status_update(force=False)
    meta = _status_meta()
    with _STATUS_LOCK:
        data = _STATUS.get("data")
    if isinstance(data, dict) and data:
        out = dict(data)
    else:
        # Minimal placeholder: UI will show a loading card when has_data=false.
        out = {"ts": 0, "root_dir": str(ROOT_DIR)}
    out["_meta"] = meta
    return out


def _sh(cmd: List[str], timeout_s: int = 120, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout_s,
        check=check,
    )


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def ensure_alerts_env_file() -> None:
    if ALERTS_ENV_FILE.exists():
        return
    ensure_runtime_dir()
    # Keep it beginner-friendly: plain KEY=VALUE, can be edited in TextEdit.
    content = (
        "# 奶宝 · 告警配置（只在本机生效，不会提交到仓库）\n"
        "#\n"
        "# 开启方式：\n"
        "# 1) 先配置一个渠道（企业微信/Telegram/Bark）\n"
        "# 2) 把 ALERT_ENABLED 改成 1\n"
        "#\n"
        "\n"
        "ALERT_ENABLED=0\n"
        "ALERT_INTERVAL_S=30\n"
        "ALERT_REPEAT_MINUTES=30\n"
        "ALERT_SEND_RECOVERY=1\n"
        "# 是否把“上线配置未完成（DNS/Pages/固定外网初始化）”也当成告警\n"
        "ALERT_INCLUDE_SETUP=0\n"
        "\n"
        "# 静默时段（可选，留空=不静默）。跨天也支持。\n"
        "ALERT_SILENCE_START=\n"
        "ALERT_SILENCE_END=\n"
        "\n"
        "# 微信（推荐在中国使用）：企业微信(WeCom) 群机器人 Webhook\n"
        "# 形如：https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx\n"
        "ALERT_WECOM_WEBHOOK=\n"
        "\n"
        "# Telegram（可选，需要网络可用）\n"
        "ALERT_TG_BOT_TOKEN=\n"
        "ALERT_TG_CHAT_ID=\n"
        "\n"
        "# iOS 推送（更高效）：Bark（填你的 Bark URL 前缀）\n"
        "# 形如：https://api.day.app/<你的Key>\n"
        "ALERT_BARK_URL=\n"
    )
    ALERTS_ENV_FILE.write_text(content, encoding="utf-8")


def _append_alert_log(line: str) -> None:
    try:
        ensure_runtime_dir()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        s = (line or "").rstrip("\n")
        with ALERTS_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {s}\n")
    except Exception:
        pass


def write_ops_runtime_files(port: int) -> None:
    # Used by macOS wrapper apps/scripts to locate & stop an existing console
    # without requiring a terminal window.
    try:
        ensure_runtime_dir()
        OPS_PID.write_text(str(os.getpid()), encoding="utf-8")
        OPS_PORT.write_text(str(int(port)), encoding="utf-8")
    except Exception:
        pass


def cleanup_ops_runtime_files() -> None:
    for p in (OPS_PID, OPS_PORT):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass


def ensure_home_env_file() -> None:
    if HOME_ENV_FILE.exists():
        return

    # 生成一个可直接跑起来的最小配置（写入本机文件，不提交到仓库）。
    pg_pass = secrets.token_urlsafe(24)
    jwt_secret = secrets.token_urlsafe(48)
    content = (
        "# Auto-generated by scripts/local_ops_console.py\n"
        f"POSTGRES_DB=naibao\n"
        f"POSTGRES_USER=naibao_user\n"
        f"POSTGRES_PASSWORD={pg_pass}\n"
        f"JWT_SECRET={jwt_secret}\n"
        "ADMIN_USER_IDS=\n"
        "NB_BACKEND_HOST_PORT=18080\n"
        "NB_PUBLIC_DOMAIN=naibao.me\n"
        "CORS_ALLOW_ORIGINS=https://naibao.me,https://www.naibao.me\n"
        "NB_TUNNEL_MODE=named\n"
        "NB_TUNNEL_NAME=naibao-api\n"
        "NB_TUNNEL_HOSTNAME=api.naibao.me\n"
    )

    # 若 example 存在，优先给用户一份可读的模板（但仍填入随机密钥）。
    if HOME_ENV_EXAMPLE.exists():
        # 简单替换占位符，避免引入依赖/复杂模板引擎。
        tpl = HOME_ENV_EXAMPLE.read_text(encoding="utf-8", errors="ignore")
        tpl = tpl.replace("CHANGE_ME_STRONG_PASSWORD", pg_pass)
        tpl = tpl.replace("CHANGE_ME_LONG_RANDOM_SECRET", jwt_secret)
        content = tpl

    HOME_ENV_FILE.write_text(content, encoding="utf-8")


def read_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def env_bool(env: Dict[str, str], key: str, default: bool = False) -> bool:
    v = str(env.get(key) or "").strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    return bool(default)


def env_int(env: Dict[str, str], key: str, default: int, min_v: int, max_v: int) -> int:
    raw = str(env.get(key) or "").strip()
    try:
        v = int(raw)
    except Exception:
        v = int(default)
    if v < int(min_v):
        return int(min_v)
    if v > int(max_v):
        return int(max_v)
    return int(v)


def parse_hhmm(s: str) -> Optional[int]:
    t = (s or "").strip()
    if not t:
        return None
    m = re.match(r"^([0-9]{1,2}):([0-9]{2})$", t)
    if not m:
        return None
    try:
        hh = int(m.group(1))
        mm = int(m.group(2))
    except Exception:
        return None
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return hh * 60 + mm


def is_in_silence_window(env: Dict[str, str], now_ts: Optional[int] = None) -> bool:
    start = parse_hhmm(str(env.get("ALERT_SILENCE_START") or ""))
    end = parse_hhmm(str(env.get("ALERT_SILENCE_END") or ""))
    if start is None or end is None:
        return False
    ts = int(now_ts or time.time())
    lt = time.localtime(ts)
    now_m = int(lt.tm_hour) * 60 + int(lt.tm_min)
    if start == end:
        # Treat as "no silence" to avoid surprising behaviour.
        return False
    if start < end:
        return start <= now_m < end
    # Cross-day window (e.g. 23:00-07:00)
    return now_m >= start or now_m < end


def _parse_port(value: str, default_port: int) -> int:
    s = (value or "").strip()
    try:
        v = int(s)
    except Exception:
        return int(default_port)
    if 1 <= v <= 65535:
        return int(v)
    return int(default_port)


def backend_host_port(env: Dict[str, str]) -> int:
    return _parse_port(env.get("NB_BACKEND_HOST_PORT") or "", DEFAULT_BACKEND_HOST_PORT)


def is_tcp_port_free(port: int, bind: str = "0.0.0.0") -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((bind, int(port)))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def set_env_kv(path: Path, key: str, value: str, comment: str = "") -> bool:
    # Minimal in-place update: replace first KEY= line, or append at end.
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

    lines = raw.splitlines()
    out: List[str] = []
    found = False
    changed = False
    for ln in lines:
        if not found and ln.strip().startswith(f"{key}="):
            new_ln = f"{key}={value}"
            out.append(new_ln)
            found = True
            if ln != new_ln:
                changed = True
            continue
        out.append(ln)

    if not found:
        if out and out[-1].strip():
            out.append("")
        if comment:
            for c in comment.splitlines():
                c = c.strip()
                if c:
                    out.append("# " + c)
        out.append(f"{key}={value}")
        changed = True

    if not changed:
        return False

    txt = "\n".join(out) + "\n"
    try:
        path.write_text(txt, encoding="utf-8")
        return True
    except Exception:
        return False


def choose_backend_host_port(env: Dict[str, str]) -> int:
    # Prefer user's config; otherwise choose a safe default and auto-avoid common conflicts.
    want = backend_host_port(env)
    candidates: List[int] = []
    if (env.get("NB_BACKEND_HOST_PORT") or "").strip():
        candidates.append(want)
    candidates.extend(
        [
            DEFAULT_BACKEND_HOST_PORT,
            DEFAULT_BACKEND_HOST_PORT + 1,
            DEFAULT_BACKEND_HOST_PORT + 2,
            8080,  # legacy default
        ]
    )
    seen: set[int] = set()
    for p in candidates:
        if not p or p in seen:
            continue
        seen.add(int(p))
        if is_tcp_port_free(int(p), bind="0.0.0.0"):
            return int(p)
    return int(pick_free_port("0.0.0.0"))


def find_docker_bin() -> Optional[Path]:
    # macOS 通过 .app/GUI 启动时 PATH 往往不包含 /usr/local/bin 或 /opt/homebrew/bin，
    # 会导致“明明装了 Docker，却提示未检测到”。这里做一次绝对路径兜底探测。
    p = which("docker")
    if p:
        return Path(p)

    os_name = platform.system()
    home = Path.home()
    candidates: List[Path] = []
    if os_name == "Darwin":
        candidates = [
            Path("/usr/local/bin/docker"),
            Path("/opt/homebrew/bin/docker"),
            home / ".orbstack" / "bin" / "docker",
            Path("/Applications/Docker.app/Contents/Resources/bin/docker"),
        ]
    else:
        candidates = [
            Path("/usr/bin/docker"),
            Path("/usr/local/bin/docker"),
            Path("/snap/bin/docker"),
        ]

    for c in candidates:
        try:
            if c.exists() and os.access(str(c), os.X_OK):
                return c
        except Exception:
            continue
    return None


def docker_compose_cmd(args: List[str]) -> List[str]:
    # 统一走 home compose（更接近“生产”，且带 restart policy）
    docker_bin = find_docker_bin()
    docker_exe = str(docker_bin) if docker_bin else "docker"
    return [
        docker_exe,
        "compose",
        "--env-file",
        str(HOME_ENV_FILE),
        "-f",
        str(HOME_COMPOSE_FILE),
        *args,
    ]


def docker_ps() -> List[Dict[str, Any]]:
    try:
        res = _sh(docker_compose_cmd(["ps", "--format", "json"]), timeout_s=30)
    except Exception as e:
        return [{"Service": "docker", "State": "error", "Status": humanize_error(str(e))}]

    items: List[Dict[str, Any]] = []
    for line in (res.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            # 兜底：不阻断页面渲染
            items.append({"Service": "未知", "State": "未知", "Status": line})
    return items


def docker_up() -> Tuple[bool, str]:
    try:
        # 端口冲突是“最常见、最让非技术同学崩溃”的问题；这里做一次自动避让。
        ensure_home_env_file()
        env = read_env_file(HOME_ENV_FILE)
        before = backend_host_port(env)
        # 若当前端口已经被本项目后端占用，视为“正常”（避免每次点击都自动换端口）。
        owners = docker_port_owners(int(before))
        if owners.get("ok") and any("deploy-backend" in str(x) for x in (owners.get("owners") or [])):
            chosen = int(before)
        else:
            chosen = choose_backend_host_port(env)
        changed = False
        if chosen != before or not (env.get("NB_BACKEND_HOST_PORT") or "").strip():
            changed = set_env_kv(
                HOME_ENV_FILE,
                "NB_BACKEND_HOST_PORT",
                str(int(chosen)),
                comment="本机后端端口（宿主机端口映射到容器 8080）。macOS 下 OrbStack 可能占用 8080，建议用 18080。",
            )

        res = _sh(docker_compose_cmd(["up", "-d", "--build"]), timeout_s=600)
        out = res.stdout or ""
        if res.returncode == 0 and changed:
            out = (f"已自动选择可用端口：{chosen}（避免端口冲突）\n\n" + out).strip()
        return res.returncode == 0, out
    except Exception as e:
        return False, humanize_error(str(e))


def validate_backend_host_port(port: int) -> Tuple[bool, str]:
    # Ops 用户可理解的校验：不通过就明确提示原因，避免“默默改成别的端口”。
    p = int(port)
    if p < 1024 or p > 65535:
        return False, "端口需为 1024-65535 的整数"

    owners = docker_port_owners(p)
    owner_names = [str(x or "").strip() for x in (owners.get("owners") or []) if str(x or "").strip()]
    if owners.get("ok") and owner_names:
        # 允许“当前就由奶宝后端占用”的端口（等价于不改）。
        if any("deploy-backend" in n for n in owner_names):
            return True, f"端口 {p} 可用（当前由奶宝后端占用）"
        return False, f"端口 {p} 已被 Docker 容器占用：{', '.join(owner_names[:3])}"

    host = host_port_listeners(p)
    listeners = host.get("listeners") if isinstance(host, dict) else []
    if host.get("ok") and listeners:
        # macOS 上 OrbStack 监听端口属于“容器端口映射”表现；上面的 docker owners 会识别 deploy-backend。
        procs: List[str] = []
        for x in listeners:
            try:
                cmd = str((x or {}).get("cmd") or "").strip() or "未知进程"
                pid = int((x or {}).get("pid") or 0)
            except Exception:
                cmd, pid = "未知进程", 0
            procs.append(f"{cmd}({pid})" if pid else cmd)
        txt = "、".join([t for t in procs if t]) or "本机进程"
        return False, f"端口 {p} 已被本机进程占用：{txt}"

    if not is_tcp_port_free(p, bind="0.0.0.0"):
        return False, f"端口 {p} 可能被占用或不可用（请换一个端口）"

    return True, f"端口 {p} 可用"


def set_backend_host_port(port_text: str) -> Tuple[bool, str]:
    s = (port_text or "").strip()
    try:
        p = int(s)
    except Exception:
        return False, "端口格式不正确（请输入数字）"

    ok, msg = validate_backend_host_port(p)
    if not ok:
        return False, msg

    ensure_home_env_file()
    env = read_env_file(HOME_ENV_FILE)
    current = backend_host_port(env)
    _ = set_env_kv(
        HOME_ENV_FILE,
        "NB_BACKEND_HOST_PORT",
        str(int(p)),
        comment="本机后端端口（宿主机端口映射到容器 8080）。建议用 18080/18081/18082。",
    )

    # 尽量“验证通过即生效”：Docker 可用则立刻让 compose 重新创建后端容器。
    if not docker_daemon_status().get("ok"):
        return True, f"已保存：后端端口 {p}（Docker 未启动，稍后点「一键启动/修复」生效）"

    # 端口未变化且当前已经由奶宝后端占用：无需重启，直接返回“已生效”。
    if int(current) == int(p):
        owners = docker_port_owners(int(p))
        if owners.get("ok") and any("deploy-backend" in str(x) for x in (owners.get("owners") or [])):
            return True, f"已生效：后端端口 {p}"

    try:
        res = _sh(docker_compose_cmd(["up", "-d", "--build", "backend"]), timeout_s=600)
        if res.returncode != 0:
            return False, humanize_error(res.stdout or f"exit={res.returncode}")
        return True, f"已生效：后端端口 {p}"
    except Exception as e:
        return False, humanize_error(str(e))


def docker_down() -> Tuple[bool, str]:
    try:
        res = _sh(docker_compose_cmd(["down"]), timeout_s=180)
        return res.returncode == 0, res.stdout or ""
    except Exception as e:
        return False, humanize_error(str(e))


def docker_restart(service: str) -> Tuple[bool, str]:
    svc = service.strip()
    if not svc:
        return False, "缺少服务名"
    try:
        res = _sh(docker_compose_cmd(["restart", svc]), timeout_s=180)
        return res.returncode == 0, res.stdout or ""
    except Exception as e:
        return False, humanize_error(str(e))


def docker_stop_container(name: str) -> Tuple[bool, str]:
    # 仅用于“端口被占用/栈冲突”场景的兜底恢复；不删除容器与数据。
    n = name.strip()
    if not n:
        return False, "缺少容器名"
    try:
        docker_bin = find_docker_bin()
        docker_exe = str(docker_bin) if docker_bin else "docker"
        res = _sh([docker_exe, "stop", n], timeout_s=60)
        return res.returncode == 0, res.stdout or ""
    except Exception as e:
        return False, humanize_error(str(e))


def docker_logs(service: str, tail: int = 120) -> str:
    svc = service.strip()
    if not svc:
        return ""
    try:
        res = _sh(docker_compose_cmd(["logs", "--tail", str(int(tail)), svc]), timeout_s=30)
        return res.stdout or ""
    except Exception as e:
        return humanize_error(str(e))


def http_health(url: str, timeout_s: int = 3) -> Tuple[bool, str]:
    try:
        # Cloudflare Bot/WAF may block default Python user agents (e.g. error code 1010),
        # causing false negatives in our health checks. Use a browser-like UA to match
        # real user access.
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Safari/605.1.15"
                ),
                "Accept": "application/json,text/plain,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            code = getattr(r, "status", 0)
            return code == 200, ("200 正常" if code == 200 else f"HTTP {code}")
    except urllib.error.HTTPError as e:
        # cloudflare error pages are still valid HTTP responses (e.g. 403 + "error code: 1014")
        code = int(getattr(e, "code", 0) or 0)
        body = ""
        try:
            body = (e.read(256) or b"").decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        low = body.lower()
        if "error code: 1014" in low or ("1014" in low and "cloudflare" in low):
            return False, "Cloudflare 1014（多半是 api 未绑定到 Tunnel 或 CNAME 指向不属于当前账号）"
        if "error code: 1010" in low or ("1010" in low and "cloudflare" in low):
            return False, "Cloudflare 1010（被 WAF/Bot 规则拦截：请检查 Cloudflare 安全策略/放行该域名）"
        return False, (f"HTTP {code}" if code else str(e))
    except Exception as e:
        return False, humanize_error(str(e))


def _http_json_post(url: str, payload: Any, timeout_s: int = 6) -> Tuple[bool, str]:
    try:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            method="POST",
            data=raw,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "naibao-ops-alert/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=int(timeout_s)) as r:
            code = int(getattr(r, "status", 0) or 0)
            return (code >= 200 and code < 300), (f"HTTP {code}" if code else "ok")
    except urllib.error.HTTPError as e:
        code = int(getattr(e, "code", 0) or 0)
        return False, f"HTTP {code}"
    except Exception as e:
        return False, humanize_error(str(e))


def alert_send_wecom(webhook_url: str, title: str, body: str) -> Tuple[bool, str]:
    url = (webhook_url or "").strip()
    if not url:
        return False, "缺少企业微信 Webhook"
    t = (title or "").strip()
    b = (body or "").strip()
    # WeCom markdown is widely supported and readable on phone.
    content = f"**{t}**\n\n{b}".strip()
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    return _http_json_post(url, payload, timeout_s=6)


def alert_send_telegram(bot_token: str, chat_id: str, title: str, body: str) -> Tuple[bool, str]:
    token = (bot_token or "").strip()
    cid = (chat_id or "").strip()
    if not token or not cid:
        return False, "缺少 Telegram token/chat_id"
    text = (f"{(title or '').strip()}\n{(body or '').strip()}").strip()
    api = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": cid,
        "text": text,
        "disable_web_page_preview": True,
    }
    return _http_json_post(api, payload, timeout_s=8)


def alert_send_bark(bark_url_prefix: str, title: str, body: str) -> Tuple[bool, str]:
    prefix = (bark_url_prefix or "").strip().rstrip("/")
    if not prefix:
        return False, "缺少 Bark URL"
    # Bark uses URL path segments for title/body. Make sure we escape "/" as well,
    # otherwise URLs inside the message (https://...) will break the path and cause 404.
    t = urllib.parse.quote((title or "").strip()[:80], safe="")
    b = urllib.parse.quote((body or "").strip()[:1800], safe="")
    url = f"{prefix}/{t}/{b}?group=naibao&isArchive=1"
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "naibao-ops-alert/1.0"},
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            code = int(getattr(r, "status", 0) or 0)
            return (code >= 200 and code < 300), (f"HTTP {code}" if code else "ok")
    except urllib.error.HTTPError as e:
        code = int(getattr(e, "code", 0) or 0)
        return False, f"HTTP {code}"
    except Exception as e:
        return False, humanize_error(str(e))


def _looks_like_bark_key(seg: str) -> bool:
    s = (seg or "").strip()
    if len(s) < 10:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9]+", s))


def normalize_bark_url_prefix(url: str) -> str:
    """
    Users often copy a full Bark example URL (with /title/body/params).
    We need the prefix only:
      - official: https://api.day.app/<key>
      - self-hosted (common): https://host/<key> OR https://host/bark/<key>
    Heuristics:
      - If host ends with day.app -> keep first path segment as key
      - Else if path has >=4 segments and 2nd looks like key -> keep first two segments
      - Else if path has >=3 segments and 1st looks like key -> keep first segment
      - Else -> keep as-is (but strip query/fragment and trailing slash)
    """
    s = (url or "").strip()
    if not s:
        return ""
    # Common user input: only the Bark Key (alphanumeric).
    if "://" not in s and "/" not in s and _looks_like_bark_key(s):
        return f"https://api.day.app/{s}"
    # Common user input: missing scheme.
    if "://" not in s and s.lower().startswith("api.day.app/"):
        s = "https://" + s
    try:
        u = urllib.parse.urlparse(s)
        if not u.scheme or not u.netloc:
            return s.rstrip("/")
        parts = [p for p in (u.path or "").split("/") if p]
        host = (u.netloc or "").lower()
        keep: List[str] = []
        if not parts:
            keep = []
        elif host.endswith("day.app"):
            keep = [parts[0]]
        elif len(parts) >= 4 and _looks_like_bark_key(parts[1]):
            keep = [parts[0], parts[1]]
        elif len(parts) >= 3 and _looks_like_bark_key(parts[0]):
            keep = [parts[0]]
        else:
            keep = parts
        path = "/" + "/".join(keep) if keep else ""
        return urllib.parse.urlunparse((u.scheme, u.netloc, path, "", "", "")).rstrip("/")
    except Exception:
        return s.rstrip("/")


def find_cloudflared_bin() -> Optional[Path]:
    # 1) PATH
    p = which("cloudflared")
    if p:
        return Path(p)

    # 2) scripts/bin/cloudflared（复用现有“验收预览”下载位置）
    local = ROOT_DIR / "scripts" / "bin" / "cloudflared"
    if local.exists():
        return local
    return None


def download_cloudflared(to_path: Path) -> Tuple[bool, str]:
    os_name = platform.system()
    arch = platform.machine().lower()
    if os_name == "Darwin" and arch in ("arm64", "aarch64"):
        asset = "cloudflared-darwin-arm64"
    elif os_name == "Darwin" and arch in ("x86_64", "amd64"):
        asset = "cloudflared-darwin-amd64"
    elif os_name == "Linux" and arch in ("x86_64", "amd64"):
        asset = "cloudflared-linux-amd64"
    elif os_name == "Linux" and arch in ("arm64", "aarch64"):
        asset = "cloudflared-linux-arm64"
    else:
        return False, f"当前平台不支持自动下载 cloudflared：{os_name}/{arch}"

    url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/{asset}"
    to_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = to_path.with_suffix(".download")
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = r.read()
        tmp.write_bytes(data)
        os.chmod(tmp, 0o755)
        tmp.replace(to_path)
        return True, f"已下载 cloudflared（{asset}）"
    except Exception as e:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        return False, humanize_error(str(e))


def read_pid(path: Path) -> Optional[int]:
    try:
        s = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not s:
            return None
        v = int(s)
        return v if v > 0 else None
    except Exception:
        return None


def is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def stop_tunnel() -> Tuple[bool, str]:
    pid = read_pid(TUN_PID)
    if not pid:
        return True, "未运行"
    try:
        if is_pid_alive(pid):
            os.kill(pid, 15)
            time.sleep(0.3)
        try:
            TUN_PID.unlink()
        except Exception:
            pass
        return True, "已停止"
    except Exception as e:
        return False, humanize_error(str(e))


def start_tunnel(env: Dict[str, str]) -> Tuple[bool, str]:
    ensure_runtime_dir()

    # Already running?
    pid = read_pid(TUN_PID)
    if pid and is_pid_alive(pid):
        return True, f"已在运行（pid={pid}）"

    # Resolve binary
    bin_path = find_cloudflared_bin()
    if not bin_path:
        # 尝试自动下载（不污染全局）
        local = ROOT_DIR / "scripts" / "bin" / "cloudflared"
        ok, msg = download_cloudflared(local)
        if not ok:
            return False, f"下载 cloudflared 失败：{msg}"
        bin_path = local

    mode = (env.get("NB_TUNNEL_MODE") or "named").strip().lower()
    name = (env.get("NB_TUNNEL_NAME") or "naibao-api").strip()
    hostname = (env.get("NB_TUNNEL_HOSTNAME") or "api.naibao.me").strip()
    local_port = backend_host_port(env)

    if mode == "quick":
        cmd = [str(bin_path), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{int(local_port)}"]
    else:
        # named tunnel：需要用户自行完成 cloudflared login + create + route dns
        if TUN_CFG.exists():
            # 配置文件里可能写死了旧端口（例如 8080）；这里根据当前本机端口做一次自愈同步，
            # 避免“后端已改端口但 tunnel 仍指向旧端口”的隐蔽故障。
            try:
                raw = TUN_CFG.read_text(encoding="utf-8", errors="ignore")
                patched = re.sub(
                    r"(service:\\s*http://127\\.0\\.0\\.1:)\\d+",
                    lambda m: m.group(1) + str(int(local_port)),
                    raw,
                )
                if patched != raw:
                    TUN_CFG.write_text(patched, encoding="utf-8")
            except Exception:
                pass
            # 使用项目运行时目录的 config（不污染 ~/.cloudflared/config.yml）
            cmd = [str(bin_path), "tunnel", "--no-autoupdate", "--config", str(TUN_CFG), "run", name]
        else:
            cmd = [str(bin_path), "tunnel", "--no-autoupdate", "run", name]

    with TUN_LOG.open("a", encoding="utf-8") as f:
        f.write("\n")
        f.write(f"[ops] starting cloudflared: {' '.join(cmd)}\n")
        f.flush()
        try:
            p = subprocess.Popen(
                cmd,
                cwd=str(ROOT_DIR),
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as e:
            return False, humanize_error(str(e))

    TUN_PID.write_text(str(p.pid), encoding="utf-8")

    # Wait a bit and check if process exited quickly
    time.sleep(0.6)
    if not is_pid_alive(p.pid):
        tail = tail_file(TUN_LOG, 40)
        return False, f"外网通道启动失败（请查看通道日志）：\n{tail}"

    if mode == "quick":
        return True, "已启动（临时外网）。外网链接会从日志中自动识别。"
    return True, f"已启动（固定外网）。预期域名：https://{hostname}"


def tail_file(path: Path, lines: int = 120) -> str:
    if not path.exists():
        return ""
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(txt[-max(1, int(lines)) :])
    except Exception as e:
        return humanize_error(str(e))


def parse_named_tunnel_config(path: Path) -> Dict[str, str]:
    """
    Parse the minimal fields we care about from cloudflared named tunnel config.
    Avoid adding YAML dependencies; this file is generated by our script and simple.
    """
    out = {"tunnel_id": "", "credentials_file": "", "hostname": "", "service": ""}
    if not path.exists():
        return out
    try:
        for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("tunnel:") and not out["tunnel_id"]:
                out["tunnel_id"] = s.split(":", 1)[1].strip()
                continue
            if s.startswith("credentials-file:") and not out["credentials_file"]:
                out["credentials_file"] = s.split(":", 1)[1].strip()
                continue
            if s.startswith("hostname:") and not out["hostname"]:
                out["hostname"] = s.split(":", 1)[1].strip()
                continue
            if s.startswith("service:") and not out["service"]:
                v = s.split(":", 1)[1].strip()
                if "http_status" not in v:
                    out["service"] = v
    except Exception:
        return out
    return out


def named_tunnel_init() -> Tuple[bool, str]:
    """
    Run the one-time Named Tunnel init script in background:
    - cloudflared tunnel login (browser)
    - create/reuse tunnel
    - route dns api.<domain>
    - write .naibao_runtime/cloudflared_named.yml
    """
    ensure_runtime_dir()

    pid = read_pid(NAMED_INIT_PID)
    if pid and is_pid_alive(pid):
        return True, f"正在初始化（pid={pid}）。请完成浏览器授权后回到本页刷新。"

    script = ROOT_DIR / "scripts" / "setup_named_tunnel.sh"
    if not script.exists():
        return False, "缺少脚本：scripts/setup_named_tunnel.sh"

    cmd = ["bash", str(script)]
    with NAMED_INIT_LOG.open("a", encoding="utf-8") as f:
        f.write("\n")
        f.write(f"[ops] starting named tunnel init: {' '.join(cmd)}\n")
        f.flush()
        try:
            p = subprocess.Popen(
                cmd,
                cwd=str(ROOT_DIR),
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as e:
            return False, humanize_error(str(e))

    NAMED_INIT_PID.write_text(str(p.pid), encoding="utf-8")

    # If it fails fast, surface a helpful message.
    time.sleep(0.8)
    rc = p.poll()
    if rc is not None:
        tail = tail_file(NAMED_INIT_LOG, 80)
        try:
            NAMED_INIT_PID.unlink()
        except Exception:
            pass
        if int(rc) == 0:
            return True, "初始化已完成。请回到本页刷新，并在「外网通道」卡片里点击启动。"
        return False, f"初始化失败（请查看初始化日志）：\n{tail}"

    return True, f"已开始初始化（pid={p.pid}）。将打开浏览器进行 Cloudflare 授权；完成后回到本页刷新。"


def parse_quick_tunnel_url() -> str:
    if not TUN_LOG.exists():
        return ""
    pat = re.compile(r"https://[a-z0-9-]+\\.trycloudflare\\.com", re.I)
    try:
        m = pat.search(TUN_LOG.read_text(encoding="utf-8", errors="ignore"))
        return m.group(0) if m else ""
    except Exception:
        return ""


def read_first_line(path: Path, max_len: int = 4096) -> str:
    try:
        if not path.exists():
            return ""
        txt = path.read_text(encoding="utf-8", errors="ignore")
        if max_len and len(txt) > int(max_len):
            txt = txt[: int(max_len)]
        for ln in txt.splitlines():
            s = ln.strip()
            if s:
                return s
        return ""
    except Exception:
        return ""


def mobile_preview_start() -> Tuple[bool, str]:
    ensure_runtime_dir()

    pid = read_pid(MOBILE_PREVIEW_START_PID)
    if pid and is_pid_alive(pid):
        return True, f"已在启动中（pid={pid}）"

    cmd = ["bash", str(ROOT_DIR / "scripts" / "start_mobile_preview.sh")]
    with MOBILE_PREVIEW_START_LOG.open("a", encoding="utf-8") as f:
        f.write("\n")
        f.write(f"[ops] starting mobile preview: {' '.join(cmd)}\n")
        f.flush()
        try:
            p = subprocess.Popen(
                cmd,
                cwd=str(ROOT_DIR),
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as e:
            return False, humanize_error(str(e))

    MOBILE_PREVIEW_START_PID.write_text(str(p.pid), encoding="utf-8")
    return True, f"已启动（pid={p.pid}）。等待生成外网链接：{MOBILE_PREVIEW_URL}"


def mobile_preview_stop() -> Tuple[bool, str]:
    # Best-effort:
    # 1) stop the start script (if still running)
    # 2) stop tunnel + dev server via existing script
    # 3) cleanup the url file to avoid handing out stale links
    pid = read_pid(MOBILE_PREVIEW_START_PID)
    if pid and is_pid_alive(pid):
        try:
            os.kill(pid, 15)
        except Exception:
            pass
        time.sleep(0.3)
    try:
        MOBILE_PREVIEW_START_PID.unlink()
    except Exception:
        pass

    ok, out = _safe_cmd(["bash", str(ROOT_DIR / "scripts" / "stop_mobile_preview.sh")], timeout_s=60)

    try:
        if MOBILE_PREVIEW_URL.exists():
            MOBILE_PREVIEW_URL.unlink()
    except Exception:
        pass
    return bool(ok), out or ("已停止" if ok else "停止失败")


def mobile_preview_logs() -> str:
    # Merge the most useful logs so non-technical users can paste one thing.
    parts: List[str] = []
    if MOBILE_PREVIEW_START_LOG.exists():
        parts.append("== mobile_preview_start.log ==")
        parts.append(tail_file(MOBILE_PREVIEW_START_LOG, 120))
    if MOBILE_PREVIEW_TUN_LOG.exists():
        parts.append("\n== frontend/cloudflared.log ==")
        parts.append(tail_file(MOBILE_PREVIEW_TUN_LOG, 80))
    if MOBILE_PREVIEW_DEV_LOG.exists():
        parts.append("\n== frontend/dev-h5.log ==")
        parts.append(tail_file(MOBILE_PREVIEW_DEV_LOG, 80))
    return "\n".join([p for p in parts if p.strip()]) or "暂无日志"


def get_lan_ip() -> str:
    # best-effort: get outbound interface IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def pick_free_port(bind: str) -> int:
    # 绑定端口冲突时，给运营同学一个“永远能打开”的兜底端口
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((bind, 0))
        return int(s.getsockname()[1])
    finally:
        try:
            s.close()
        except Exception:
            pass


def is_ops_console_running(bind: str, port: int) -> bool:
    url = f"http://{bind}:{int(port)}/api/status"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.2) as r:
            code = getattr(r, "status", 0)
            if code != 200:
                return False
            raw = r.read(8192).decode("utf-8", errors="ignore") or "{}"
            data = json.loads(raw)
            return str(data.get("root_dir") or "") == str(ROOT_DIR)
    except Exception:
        return False


def _safe_cmd(cmd: List[str], timeout_s: int = 8) -> Tuple[bool, str]:
    try:
        res = _sh(cmd, timeout_s=timeout_s)
        out = (res.stdout or "").strip()
        if res.returncode == 0:
            return True, out
        return False, humanize_error(out or f"exit={res.returncode}")
    except Exception as e:
        return False, humanize_error(str(e))


def docker_cli_status() -> Dict[str, Any]:
    p = find_docker_bin()
    if not p:
        return {"ok": False, "path": "", "msg": "未检测到 Docker 命令（请先安装并启动 Docker Desktop 或 OrbStack）"}

    ok, out = _safe_cmd([str(p), "version", "--format", "{{.Server.Version}}"], timeout_s=6)
    # daemon 未启动时，这里会失败；我们把详细错误文案也透出给 UI。
    if ok:
        return {"ok": True, "path": str(p), "msg": out or "ok"}
    return {"ok": False, "path": str(p), "msg": humanize_error(out or "docker daemon not reachable")}


def docker_daemon_status() -> Dict[str, Any]:
    # Avoid showing "Client:" (the first line of plain `docker info`) which is not meaningful to ops users.
    p = find_docker_bin()
    if not p:
        return {"ok": False, "msg": "未检测到 Docker 命令（请先安装并启动 Docker Desktop 或 OrbStack）"}
    ok, out = _safe_cmd([str(p), "info", "--format", "{{.ServerVersion}} · {{.OperatingSystem}} · {{.Name}}"], timeout_s=6)
    if ok:
        return {"ok": True, "msg": out or "ok"}
    return {"ok": False, "msg": humanize_error(out or "docker daemon not reachable")}


def docker_port_owners(port: int) -> Dict[str, Any]:
    p = find_docker_bin()
    docker_exe = str(p) if p else "docker"
    ok, out = _safe_cmd([docker_exe, "ps", "--filter", f"publish={int(port)}", "--format", "{{.Names}}"], timeout_s=5)
    if not ok:
        return {"ok": False, "port": int(port), "owners": [], "msg": out}
    owners = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
    return {"ok": True, "port": int(port), "owners": owners, "msg": ""}


def host_port_listeners(port: int) -> Dict[str, Any]:
    # `lsof` returns exit code 1 when nothing is listening (which is OK for us).
    p = which("lsof")
    if not p:
        return {"ok": False, "port": int(port), "listeners": [], "msg": "未检测到 lsof（无法识别本机进程占用）"}

    try:
        res = _sh([p, "-nP", f"-iTCP:{int(port)}", "-sTCP:LISTEN"], timeout_s=4)
        out = (res.stdout or "").strip()
        if res.returncode != 0 and not out:
            return {"ok": True, "port": int(port), "listeners": [], "msg": ""}
        listeners: List[Dict[str, Any]] = []
        for i, ln in enumerate((out or "").splitlines()):
            s = ln.strip()
            if not s:
                continue
            if i == 0 and s.upper().startswith("COMMAND"):
                continue
            parts = s.split()
            if len(parts) < 2:
                continue
            cmd = parts[0]
            try:
                pid = int(parts[1])
            except Exception:
                pid = 0
            listeners.append({"pid": pid, "cmd": cmd})
        return {"ok": True, "port": int(port), "listeners": listeners, "msg": ""}
    except Exception as e:
        return {"ok": False, "port": int(port), "listeners": [], "msg": humanize_error(str(e))}


def git_commit() -> str:
    ok, out = _safe_cmd(["git", "rev-parse", "--short", "HEAD"], timeout_s=4)
    return out.strip() if ok else ""


def git_remote_origin() -> str:
    ok, out = _safe_cmd(["git", "remote", "get-url", "origin"], timeout_s=4)
    return out.strip() if ok else ""


def git_branch() -> str:
    ok, out = _safe_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout_s=4)
    b = out.strip() if ok else ""
    if b == "HEAD":
        return ""
    return b


def git_ahead_behind(ref: str = "origin/main") -> Tuple[int, int]:
    """
    Return (behind, ahead) counts vs the given ref.
    - behind: commits in ref but not in HEAD
    - ahead: commits in HEAD but not in ref
    """
    ok, out = _safe_cmd(["git", "rev-list", "--left-right", "--count", f"{ref}...HEAD"], timeout_s=6)
    if not ok:
        return 0, 0
    parts = re.split(r"\\s+", (out or "").strip())
    if len(parts) >= 2:
        try:
            return int(parts[0]), int(parts[1])
        except Exception:
            return 0, 0
    return 0, 0


def git_porcelain(paths: List[str]) -> Tuple[bool, List[str], str]:
    cmd = ["git", "status", "--porcelain=v1"]
    if paths:
        cmd += ["--", *paths]
    ok, out = _safe_cmd(cmd, timeout_s=8)
    if not ok:
        return False, [], out
    lines = [ln.rstrip("\n") for ln in (out or "").splitlines() if ln.strip()]
    return True, lines, ""


def git_change_summary(paths: List[str], max_files: int = 8) -> Dict[str, Any]:
    ok, lines, msg = git_porcelain(paths)
    if not ok:
        return {"ok": False, "count": 0, "files": [], "msg": msg}

    files: List[str] = []
    for ln in lines:
        # format: XY <path>   (or: XY <old> -> <new>)
        p = ln[3:] if len(ln) >= 4 else ln
        p = p.strip()
        if " -> " in p:
            p = p.split(" -> ", 1)[1].strip()
        if p:
            files.append(p)
    return {"ok": True, "count": len(files), "files": files[: int(max_files)], "msg": ""}


def git_file_exists_in_ref(ref: str, path: str) -> bool:
    try:
        res = _sh(["git", "cat-file", "-e", f"{ref}:{path}"], timeout_s=6)
        return res.returncode == 0
    except Exception:
        return False


def _git_run(args: List[str], timeout_s: int = 120) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Avoid blocking the ops console on interactive credential prompts.
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        args,
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=int(timeout_s),
        env=env,
    )


def humanize_git_error(msg: str) -> str:
    s = (msg or "").strip()
    low = s.lower()
    if "terminal prompts disabled" in low or "could not read username" in low:
        return "GitHub 未登录/无权限（请先在终端完成一次 GitHub 登录，再回这里重试）"
    if "please tell me who you are" in low or "unable to auto-detect email address" in low:
        return "Git 未配置提交身份（请先设置 git user.name / user.email）"
    if "non-fast-forward" in low or "fetch first" in low:
        return "推送被拒绝（远端有更新，需要先拉取/处理冲突）"
    if "repository not found" in low:
        return "仓库不存在或无权限（请检查 GitHub 仓库权限/remote origin）"
    if "permission denied" in low and "publickey" in low:
        return "SSH 权限不足（请检查 GitHub SSH Key 配置或改用 HTTPS + Token）"
    return s or "操作失败"

def _git_parse_name_status(raw: str) -> List[Dict[str, str]]:
    """
    Parse `git diff --name-status` output.
    Return a list of dicts:
      - {status, path}
      - {status, old, new} for rename/copy
    """
    out: List[Dict[str, str]] = []
    for ln in (raw or "").splitlines():
        s = ln.strip("\n").strip()
        if not s:
            continue
        # Prefer tab-separated form: <status>\t<path>[\t<path2>]
        parts = s.split("\t")
        if len(parts) == 1:
            parts = re.split(r"\s+", s)
        if not parts:
            continue
        st = (parts[0] or "").strip()
        if not st:
            continue
        k = st[0].upper()
        if k in ("R", "C"):
            old = (parts[1] if len(parts) > 1 else "").strip()
            new = (parts[2] if len(parts) > 2 else "").strip()
            out.append({"status": st, "old": old, "new": new})
        else:
            p = (parts[1] if len(parts) > 1 else "").strip()
            out.append({"status": st, "path": p})
    return out


def _git_changelog_zh(entries: List[Dict[str, str]]) -> str:
    """
    Build a concise Simplified Chinese changelog, but with a complete file list.
    """
    if not entries:
        return "修改日志：\n- 无（仅推送）"

    def _verb(st: str) -> str:
        k = (st or "")[:1].upper()
        if k == "A":
            return "新增"
        if k == "M":
            return "修改"
        if k == "D":
            return "删除"
        if k == "R":
            return "重命名"
        if k == "C":
            return "复制"
        if k == "T":
            return "类型变更"
        if k == "U":
            return "未合并"
        return "变更"

    lines: List[str] = ["修改日志："]
    for e in entries:
        st = str(e.get("status") or "").strip()
        v = _verb(st)
        if st[:1].upper() in ("R", "C"):
            old = str(e.get("old") or "").strip()
            new = str(e.get("new") or "").strip()
            if old and new:
                lines.append(f"- {v} {old} -> {new}")
            else:
                lines.append(f"- {v} {old or new or '（未知）'}")
            continue
        p = str(e.get("path") or "").strip() or "（未知）"
        lines.append(f"- {v} {p}")
    return "\n".join(lines).strip()


def _git_commit_message(title: str, entries: List[Dict[str, str]]) -> str:
    # Keep the title short; put full file list in the body.
    t = (title or "").strip() or "发布"
    t = t.splitlines()[0].strip() or "发布"
    ts = time.strftime("%Y-%m-%d %H:%M")
    body = "\n".join(
        [
            f"时间：{ts}",
            f"文件：{len(entries)}",
            "",
            _git_changelog_zh(entries),
        ]
    ).strip()
    return (t + "\n\n" + body).strip()


def git_publish(paths: List[str], user_title: str, kind: str = "") -> Tuple[bool, str, str]:
    # KISS: only support pushing on main to avoid accidental deploy to wrong branch.
    detail_parts: List[str] = []

    def _add(title: str, out: str) -> None:
        t = (title or "").strip()
        s = (out or "").strip()
        if not t and not s:
            return
        if t:
            detail_parts.append("== " + t + " ==")
        if s:
            detail_parts.append(s)

    b = git_branch()
    if b and b != "main":
        msg = f"当前分支是 {b}，请先切换到 main 再发布（避免影响自动部署）"
        _add("分支检查", msg)
        return False, msg, "\n\n".join(detail_parts).strip()

    ok0, st0 = _safe_cmd(["git", "status", "-sb"], timeout_s=8)
    if ok0:
        _add("执行前 · Git 状态", st0)

    # Stage selected paths
    add = _git_run(["git", "add", "--", *paths], timeout_s=60)
    if add.returncode != 0:
        raw = (add.stdout or "").strip() or f"exit={add.returncode}"
        _add("git add", raw)
        return False, humanize_git_error(raw), "\n\n".join(detail_parts).strip()
    if (add.stdout or "").strip():
        _add("git add", add.stdout)

    staged = _git_run(["git", "diff", "--cached", "--name-only", "--", *paths], timeout_s=12)
    staged_files = [ln.strip() for ln in (staged.stdout or "").splitlines() if ln.strip()]
    if staged_files:
        _add("已暂存文件", "\n".join(staged_files[:120]))

    # Commit if needed
    if staged_files:
        base_title = "发布：前端更新" if (kind or "").strip().lower() == "frontend" else "发布：部署工作流"
        # Build a complete file list for this commit.
        ns = _git_run(["git", "diff", "--cached", "--name-status", "--", *paths], timeout_s=18)
        entries = _git_parse_name_status(ns.stdout or "")
        msg = _git_commit_message((user_title or "").strip() or base_title, entries)
        _add("提交说明（自动生成）", msg)

        ensure_runtime_dir()
        tmp = None
        try:
            tmp = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=str(RUNTIME_DIR),
                prefix="gitmsg_",
                suffix=".txt",
            )
            tmp.write(msg + "\n")
            tmp.flush()
            tmp.close()
            c = _git_run(["git", "commit", "-F", tmp.name], timeout_s=90)
        finally:
            try:
                if tmp and tmp.name and Path(tmp.name).exists():
                    Path(tmp.name).unlink()
            except Exception:
                pass

        if c.returncode != 0:
            out = (c.stdout or "").strip()
            # "nothing to commit" isn't fatal in our workflow.
            if "nothing to commit" not in out.lower():
                raw = out or f"exit={c.returncode}"
                _add("git commit", raw)
                return False, humanize_git_error(raw), "\n\n".join(detail_parts).strip()
        if (c.stdout or "").strip():
            _add("git commit", c.stdout)

    # Push (even when no staged changes, HEAD may be ahead)
    push = _git_run(["git", "push", "origin", "main"], timeout_s=180)
    if push.returncode != 0:
        raw = (push.stdout or "").strip() or f"exit={push.returncode}"
        _add("git push", raw)
        return False, humanize_git_error(raw), "\n\n".join(detail_parts).strip()
    if (push.stdout or "").strip():
        _add("git push", push.stdout)

    ok1, st1 = _safe_cmd(["git", "status", "-sb"], timeout_s=8)
    if ok1:
        _add("执行后 · Git 状态", st1)

    k = (kind or "").strip().lower()
    if k == "workflow":
        msg = "已推送到 GitHub（部署工作流已更新）"
    else:
        msg = "已推送到 GitHub（Actions 将自动部署前端）"
    return True, msg, "\n\n".join(detail_parts).strip()


def git_status_text(scope: str = "") -> str:
    """
    Human-readable git status for ops users (used in /api/logs?target=git).
    scope:
      - ''        : repo summary
      - 'workflow': pages workflow file only
      - 'frontend': frontend publish scope
    """
    s = (scope or "").strip().lower()
    workflow_path = ".github/workflows/pages.yml"
    frontend_scope = [
        "frontend/src",
        "frontend/index.html",
        "frontend/package.json",
        "frontend/package-lock.json",
        "frontend/vite.config.js",
        "frontend/.npmrc",
    ]
    if s == "workflow":
        ok, out = _safe_cmd(["git", "status", "-sb", "--", workflow_path], timeout_s=8)
        ok2, out2 = _safe_cmd(["git", "status", "--porcelain=v1", "--", workflow_path], timeout_s=8)
        lines = ["== Git 状态：部署工作流 ==", out or ""]
        if ok2:
            lines.append("")
            lines.append(out2 or "（无改动）")
        return "\n".join([x for x in lines if x is not None]).strip() or "暂无输出"

    if s == "frontend":
        ok, out = _safe_cmd(["git", "status", "-sb", "--", *frontend_scope], timeout_s=10)
        ok2, out2 = _safe_cmd(["git", "status", "--porcelain=v1", "--", *frontend_scope], timeout_s=10)
        lines = ["== Git 状态：前端发布范围 ==", out or ""]
        if ok2:
            lines.append("")
            lines.append(out2 or "（无改动）")
        return "\n".join([x for x in lines if x is not None]).strip() or "暂无输出"

    ok, out = _safe_cmd(["git", "status", "-sb"], timeout_s=8)
    if ok:
        behind, ahead = git_ahead_behind("origin/main")
        extra = f"\n\n== 同步状态（origin/main）==\nbehind: {behind}\nahead: {ahead}\n"
        return (out.strip() + extra).strip()
    return out.strip() if out else "未检测到 Git 状态（请确认当前目录是 Git 仓库）"

def parse_github_repo_from_remote(remote_url: str) -> Dict[str, str]:
    s = (remote_url or "").strip()
    if not s:
        return {}

    # Common forms:
    # - https://github.com/<owner>/<repo>.git
    # - git@github.com:<owner>/<repo>.git
    # - ssh://git@github.com/<owner>/<repo>.git
    m = re.search(r"(?:github\.com[/:])([^/]+)/([^/]+?)(?:\.git)?$", s)
    if not m:
        return {}

    owner = m.group(1).strip()
    repo = m.group(2).strip()
    if not owner or not repo:
        return {}

    base = f"https://github.com/{owner}/{repo}"
    return {
        "owner": owner,
        "repo": repo,
        "repo_url": base,
        "pages_settings_url": f"{base}/settings/pages",
        "actions_url": f"{base}/actions",
        "pages_workflow_url": f"{base}/actions/workflows/pages.yml",
    }


def resolve_hostname(hostname: str) -> Dict[str, Any]:
    hn = (hostname or "").strip()
    if not hn:
        return {"ok": False, "hostname": "", "ips": [], "msg": "域名为空"}
    try:
        infos = socket.getaddrinfo(hn, 443, type=socket.SOCK_STREAM)
        ips = sorted({i[4][0] for i in infos if i and len(i) >= 5 and i[4]})
        return {"ok": bool(ips), "hostname": hn, "ips": ips, "msg": "" if ips else "未配置记录"}
    except Exception as e:
        return {"ok": False, "hostname": hn, "ips": [], "msg": humanize_error(str(e))}


def dns_resolve(name: str, qtype: str, timeout_s: int = 2) -> Dict[str, Any]:
    # 优先用本机 DNS 工具（更适合中国网络环境），失败再退化到 DoH。
    n = (name or "").strip()
    t = (qtype or "").strip().upper()
    if not n or not t:
        return {"ok": False, "name": n, "type": t, "status": -1, "answers": [], "msg": "缺少域名或记录类型"}

    dig = which("dig")
    if dig:
        ok, out = _safe_cmd(
            [dig, "+short", f"+timeout={int(max(1, timeout_s))}", "+tries=1", "-t", t, n],
            timeout_s=int(max(2, timeout_s) + 1),
        )
        answers = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
        if ok:
            if answers:
                return {"ok": True, "name": n, "type": t, "status": 0, "answers": answers, "msg": ""}
            return {"ok": False, "name": n, "type": t, "status": 1, "answers": [], "msg": "未配置记录"}
        # dig 返回非 0 时，out 里通常有错误原因
        return {"ok": False, "name": n, "type": t, "status": -1, "answers": [], "msg": humanize_error(out or "dig failed")}

    # fallback: DoH (可能在部分网络不可达)
    url = "https://dns.google/resolve?" + urllib.parse.urlencode({"name": n, "type": t})
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=int(timeout_s)) as r:
            raw = r.read() or b"{}"
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
        status = int(payload.get("Status", -1))
        answers: List[str] = []
        for a in payload.get("Answer") or []:
            if not isinstance(a, dict):
                continue
            v = str(a.get("data") or "").strip()
            if v:
                answers.append(v)
        ok = status == 0 and len(answers) > 0
        msg = ""
        if not ok:
            msg = "未配置记录" if status == 0 else f"DNS 查询失败（Status={status}）"
        return {"ok": ok, "name": n, "type": t, "status": status, "answers": answers, "msg": msg}
    except Exception as e:
        return {"ok": False, "name": n, "type": t, "status": -1, "answers": [], "msg": humanize_error(str(e))}


def looks_like_cloudflare_ns(ns: List[str]) -> bool:
    for x in ns or []:
        s = str(x or "").lower().strip()
        if s.endswith(".ns.cloudflare.com.") or s.endswith(".ns.cloudflare.com"):
            return True
    return False


def disk_usage(path: Path) -> Dict[str, Any]:
    try:
        st = os.statvfs(str(path))
        total = int(st.f_blocks * st.f_frsize)
        free = int(st.f_bavail * st.f_frsize)
        used = max(0, total - free)
        free_pct = (float(free) / float(total)) if total > 0 else 0.0
        return {"ok": True, "total": total, "free": free, "used": used, "free_pct": free_pct}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def _mac_mem() -> Optional[Dict[str, Any]]:
    # macOS: 用 sysctl + vm_stat 做 best-effort，可用内存为可回收/空闲页近似值
    ok_total, out_total = _safe_cmd(["sysctl", "-n", "hw.memsize"], timeout_s=2)
    if not ok_total:
        return None
    try:
        total = int(out_total.strip())
    except Exception:
        return None

    ok_vm, out_vm = _safe_cmd(["vm_stat"], timeout_s=2)
    if not ok_vm:
        return {"ok": True, "total": total, "avail": 0, "avail_pct": 0.0, "note": "vm_stat failed"}

    page_size = 4096
    m = re.search(r"page size of (\\d+) bytes", out_vm)
    if m:
        try:
            page_size = int(m.group(1))
        except Exception:
            page_size = 4096

    pages: Dict[str, int] = {}
    for line in out_vm.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip().lower()
        v = v.strip().strip(".")
        v = v.replace(".", "").replace(",", "")
        try:
            pages[k] = int(v)
        except Exception:
            continue

    # 经验：free + speculative + inactive 近似可用（inactive 可回收）
    free_pages = pages.get("pages free", 0)
    spec_pages = pages.get("pages speculative", 0)
    inact_pages = pages.get("pages inactive", 0)
    avail = int((free_pages + spec_pages + inact_pages) * page_size)
    avail_pct = (float(avail) / float(total)) if total > 0 else 0.0
    return {"ok": True, "total": total, "avail": avail, "avail_pct": avail_pct, "note": ""}


def _linux_mem() -> Optional[Dict[str, Any]]:
    p = Path("/proc/meminfo")
    if not p.exists():
        return None
    m: Dict[str, int] = {}
    try:
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().split()[0]
            try:
                m[k] = int(v) * 1024  # kB -> bytes
            except Exception:
                continue
    except Exception:
        return None

    total = m.get("MemTotal", 0)
    avail = m.get("MemAvailable", 0) or m.get("MemFree", 0)
    if total <= 0:
        return None
    return {"ok": True, "total": int(total), "avail": int(avail), "avail_pct": float(avail) / float(total), "note": ""}


def mem_usage() -> Dict[str, Any]:
    os_name = platform.system()
    if os_name == "Darwin":
        r = _mac_mem()
        if r:
            return r
    if os_name == "Linux":
        r = _linux_mem()
        if r:
            return r
    return {"ok": False, "msg": "当前平台不支持内存指标获取"}


def cpu_load() -> Dict[str, Any]:
    try:
        la = os.getloadavg()
        return {"ok": True, "load1": float(la[0]), "load5": float(la[1]), "load15": float(la[2])}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def host_uptime_s() -> Dict[str, Any]:
    os_name = platform.system()
    if os_name == "Darwin":
        ok, out = _safe_cmd(["sysctl", "-n", "kern.boottime"], timeout_s=2)
        if not ok:
            return {"ok": False, "msg": out}
        m = re.search(r"sec\s*=\s*(\d+)", out)
        if not m:
            return {"ok": False, "msg": "解析 kern.boottime 失败"}
        try:
            boot = int(m.group(1))
            return {"ok": True, "uptime_s": int(time.time()) - boot}
        except Exception as e:
            return {"ok": False, "msg": str(e)}
    if os_name == "Linux":
        p = Path("/proc/uptime")
        if p.exists():
            try:
                v = (p.read_text(encoding="utf-8", errors="ignore").strip().split() or ["0"])[0]
                return {"ok": True, "uptime_s": int(float(v))}
            except Exception as e:
                return {"ok": False, "msg": str(e)}
    return {"ok": False, "msg": "当前平台不支持开机时长指标获取"}


def open_docker_desktop() -> Tuple[bool, str]:
    # 给“非技术运营”一个尽可能可用的一键修复入口（macOS 最常见：Docker Desktop）
    if platform.system() == "Darwin":
        ok, out = _safe_cmd(["open", "-a", "Docker"], timeout_s=6)
        return (True, "已打开 Docker Desktop") if ok else (False, out or "打开 Docker Desktop 失败")
    return False, "仅支持 macOS 一键打开 Docker Desktop"


def open_text_file(path: Path) -> Tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        return False, f"文件不存在：{p}"
    if platform.system() == "Darwin":
        ok, out = _safe_cmd(["open", "-a", "TextEdit", str(p)], timeout_s=6)
        return (True, "已打开配置文件") if ok else (False, out or "打开配置文件失败")
    opener = which("xdg-open")
    if opener:
        ok, out = _safe_cmd([opener, str(p)], timeout_s=6)
        return (True, "已打开配置文件") if ok else (False, out or "打开配置文件失败")
    return False, f"无法自动打开文件，请手动打开：{p}"


def docker_restart_all() -> Tuple[bool, str]:
    try:
        res = _sh(docker_compose_cmd(["restart"]), timeout_s=240)
        return res.returncode == 0, res.stdout or ""
    except Exception as e:
        return False, humanize_error(str(e))


def docker_prune() -> Tuple[bool, str]:
    # 安全默认：不删除 volume（避免影响用户数据），只清理无用容器/网络/悬挂镜像/构建缓存。
    try:
        docker_bin = find_docker_bin()
        docker_exe = str(docker_bin) if docker_bin else "docker"
        res1 = _sh([docker_exe, "system", "prune", "-f"], timeout_s=600)
        # builder prune 可能在部分环境不可用；失败不阻断主流程
        res2 = _sh([docker_exe, "builder", "prune", "-f"], timeout_s=600)
        out = (res1.stdout or "").strip()
        out2 = (res2.stdout or "").strip()
        if out2:
            out = (out + "\n\n" + out2).strip()
        return True, out or "完成"
    except Exception as e:
        return False, humanize_error(str(e))


def status_payload() -> Dict[str, Any]:
    ensure_home_env_file()
    env = read_env_file(HOME_ENV_FILE)
    ensure_alerts_env_file()
    alerts_env = read_env_file(ALERTS_ENV_FILE)
    alerts_st = _load_json(ALERTS_STATE_FILE)

    containers = docker_ps()

    api_local_port = backend_host_port(env)
    api_local_ok, api_local_msg = http_health(f"http://127.0.0.1:{int(api_local_port)}/health", timeout_s=2)
    public_domain = (env.get("NB_PUBLIC_DOMAIN") or "naibao.me").strip()
    api_public = (env.get("NB_TUNNEL_HOSTNAME") or "api.naibao.me").strip()
    api_public_ok, api_public_msg = cached(
        f"api_public_health:{api_public}",
        15,
        lambda: http_health(f"https://{api_public}/api/health", timeout_s=2),
    )
    frontend_ok, frontend_msg = cached(
        f"frontend_https:{public_domain}",
        30,
        lambda: http_health(f"https://{public_domain}", timeout_s=2),
    )

    tunnel_pid = read_pid(TUN_PID)
    tunnel_alive = bool(tunnel_pid and is_pid_alive(tunnel_pid))
    tunnel_mode = (env.get("NB_TUNNEL_MODE") or "named").strip().lower()
    tunnel_name = (env.get("NB_TUNNEL_NAME") or "naibao-api").strip()
    tunnel_url = f"https://{api_public}" if tunnel_mode != "quick" else parse_quick_tunnel_url()
    tunnel_cfg = str(TUN_CFG) if TUN_CFG.exists() else ""

    named_pid = read_pid(NAMED_INIT_PID)
    named_alive = bool(named_pid and is_pid_alive(named_pid))
    named_cfg = parse_named_tunnel_config(TUN_CFG)
    cred_raw = (named_cfg.get("credentials_file") or "").strip()
    cred_path = Path(os.path.expanduser(cred_raw)) if cred_raw else None
    cred_ok = bool(cred_path and cred_path.exists())
    cert_ok = bool((Path.home() / ".cloudflared" / "cert.pem").exists())
    config_ok = bool(TUN_CFG.exists() and (named_cfg.get("tunnel_id") or "").strip() and cred_ok)

    host_disk = disk_usage(ROOT_DIR)
    host_mem = mem_usage()
    host_cpu = cpu_load()
    host_uptime = host_uptime_s()
    docker_cli = cached("docker_cli", 15, docker_cli_status)
    docker_daemon = cached("docker_daemon", 10, docker_daemon_status)
    api_dns = cached(f"dns_resolve:{api_public}", 30, lambda: resolve_hostname(api_public))

    zone_ns = cached(f"dns_ns:{public_domain}", 300, lambda: dns_resolve(public_domain, "NS", timeout_s=2))
    zone_a = cached(f"dns_a:{public_domain}", 300, lambda: dns_resolve(public_domain, "A", timeout_s=2))
    www_cname = cached(
        f"dns_cname:www.{public_domain}",
        300,
        lambda: dns_resolve(f"www.{public_domain}", "CNAME", timeout_s=2),
    )
    api_cname = cached(f"dns_cname:{api_public}", 300, lambda: dns_resolve(api_public, "CNAME", timeout_s=2))

    cf_bin = find_cloudflared_bin()
    cf_ok = bool(cf_bin)
    cf_ver = cached(
        f"cloudflared_ver:{str(cf_bin) if cf_bin else ''}",
        300,
        lambda: (_safe_cmd([str(cf_bin), "--version"], timeout_s=4) if cf_bin else (False, "")),
    )
    if isinstance(cf_ver, tuple):
        ok, out = cf_ver
        cf_ver = (out.splitlines()[0] if out else "").strip() if ok else (out or "").strip()
    port_backend_docker = cached(f"port_backend_docker:{int(api_local_port)}", 5, lambda: docker_port_owners(int(api_local_port)))
    port_backend_host = cached(f"port_backend_host:{int(api_local_port)}", 5, lambda: host_port_listeners(int(api_local_port)))

    mobile_url = read_first_line(MOBILE_PREVIEW_URL)
    mobile_tun_pid = read_pid(MOBILE_PREVIEW_TUN_PID)
    mobile_tun_alive = bool(mobile_tun_pid and is_pid_alive(mobile_tun_pid))
    mobile_dev_pid = read_pid(MOBILE_PREVIEW_DEV_PID)
    mobile_dev_alive = bool(mobile_dev_pid and is_pid_alive(mobile_dev_pid))
    mobile_start_pid = read_pid(MOBILE_PREVIEW_START_PID)
    mobile_start_alive = bool(mobile_start_pid and is_pid_alive(mobile_start_pid))

    origin = git_remote_origin()
    github = parse_github_repo_from_remote(origin)
    branch = git_branch()
    behind, ahead = git_ahead_behind("origin/main")
    workflow_path = ".github/workflows/pages.yml"
    workflow_on_origin = git_file_exists_in_ref("origin/main", workflow_path)
    changes_all = git_change_summary([], max_files=8)
    changes_workflow = git_change_summary([workflow_path], max_files=8)
    frontend_scope = [
        "frontend/src",
        "frontend/index.html",
        "frontend/package.json",
        "frontend/package-lock.json",
        "frontend/vite.config.js",
        "frontend/.npmrc",
    ]
    changes_frontend = git_change_summary(frontend_scope, max_files=8)

    return {
        "ts": int(time.time()),
        "root_dir": str(ROOT_DIR),
        "compose_file": str(HOME_COMPOSE_FILE),
        "env_file": str(HOME_ENV_FILE),
        "alerts": {
            "env_file": str(ALERTS_ENV_FILE),
            "enabled": env_bool(alerts_env, "ALERT_ENABLED", False),
            "include_setup": env_bool(alerts_env, "ALERT_INCLUDE_SETUP", False),
            "interval_s": env_int(alerts_env, "ALERT_INTERVAL_S", 30, 10, 600),
            "repeat_minutes": env_int(alerts_env, "ALERT_REPEAT_MINUTES", 30, 5, 1440),
            "send_recovery": env_bool(alerts_env, "ALERT_SEND_RECOVERY", True),
            "silence": {
                "start": str(alerts_env.get("ALERT_SILENCE_START") or "").strip(),
                "end": str(alerts_env.get("ALERT_SILENCE_END") or "").strip(),
                "active_now": is_in_silence_window(alerts_env),
            },
            "channels": {
                "wecom": bool(str(alerts_env.get("ALERT_WECOM_WEBHOOK") or "").strip()),
                "telegram": bool(str(alerts_env.get("ALERT_TG_BOT_TOKEN") or "").strip() and str(alerts_env.get("ALERT_TG_CHAT_ID") or "").strip()),
                "bark": bool(str(alerts_env.get("ALERT_BARK_URL") or "").strip()),
            },
            "last": {
                "level": str(alerts_st.get("last_level") or "ok"),
                "signature": str(alerts_st.get("last_signature") or ""),
                "sent_ts": int(alerts_st.get("last_sent_ts") or 0),
                "send_ok": bool(alerts_st.get("last_send_ok", True)),
                "send_msg": str(alerts_st.get("last_send_msg") or ""),
            },
            "state_file": str(ALERTS_STATE_FILE),
            "log": str(ALERTS_LOG),
        },
        "git": {
            "commit": git_commit(),
            "origin": origin,
            "github": github,
            "branch": branch,
            "ahead": int(ahead),
            "behind": int(behind),
            "dirty": bool(changes_all.get("count") or 0),
            "scopes": {
                "all": changes_all,
                "workflow": {
                    **changes_workflow,
                    "path": workflow_path,
                    "on_origin": bool(workflow_on_origin),
                },
                "frontend": {**changes_frontend, "paths": frontend_scope},
            },
        },
        "host": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "cpu_count": int(os.cpu_count() or 0),
            "disk": host_disk,
            "mem": host_mem,
            "cpu": host_cpu,
            "uptime": host_uptime,
        },
        "docker": {"cli": docker_cli, "daemon": docker_daemon},
        "cloudflared": {"ok": cf_ok, "path": str(cf_bin) if cf_bin else "", "version": cf_ver},
        "ports": {"backend": {"port": int(api_local_port), "docker": port_backend_docker, "host": port_backend_host}},
        "containers": containers,
        "api": {
            "local": {"ok": api_local_ok, "msg": api_local_msg, "port": int(api_local_port), "url": f"http://127.0.0.1:{int(api_local_port)}/health"},
            "public": {"ok": api_public_ok, "msg": api_public_msg, "url": f"https://{api_public}"},
        },
        "frontend": {"ok": frontend_ok, "msg": frontend_msg, "url": f"https://{public_domain}"},
        "mobile_preview": {
            "ok": bool(mobile_url),
            "url": mobile_url,
            "url_file": str(MOBILE_PREVIEW_URL),
            "starter_pid": mobile_start_pid or 0,
            "starter_alive": mobile_start_alive,
            "frontend_pid": mobile_dev_pid or 0,
            "frontend_alive": mobile_dev_alive,
            "tunnel_pid": mobile_tun_pid or 0,
            "tunnel_alive": mobile_tun_alive,
        },
        "tunnel": {
            "pid": tunnel_pid or 0,
            "alive": tunnel_alive,
            "mode": tunnel_mode,
            "name": tunnel_name,
            "hostname": api_public,
            "url": tunnel_url,
            "config": tunnel_cfg,
        },
        "named_init": {
            "pid": named_pid or 0,
            "alive": named_alive,
            "log": str(NAMED_INIT_LOG),
            "config": str(TUN_CFG) if TUN_CFG.exists() else "",
            "config_ok": config_ok,
            "tunnel_id": (named_cfg.get("tunnel_id") or "").strip(),
            "credentials_file": cred_raw,
            "credentials_ok": cred_ok,
            "cert_ok": cert_ok,
        },
        "dns": {
            "api": api_dns,
            "zone": {"domain": public_domain, "ns": zone_ns, "a": zone_a, "cloudflare": looks_like_cloudflare_ns(zone_ns.get("answers") or [])},
            "www": {"hostname": f"www.{public_domain}", "cname": www_cname},
            "api_record": {"hostname": api_public, "cname": api_cname},
        },
        "links": {
            "frontend": f"https://{public_domain}",
            "api_health": f"https://{api_public}/api/health",
        },
        "lan": {"ip": get_lan_ip()},
    }


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not raw:
            return {}
        obj = json.loads(raw)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _save_json(path: Path, obj: Dict[str, Any]) -> None:
    try:
        ensure_runtime_dir()
        path.write_text(json.dumps(obj or {}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def alerts_state() -> Dict[str, Any]:
    st = _load_json(ALERTS_STATE_FILE)
    if not isinstance(st.get("seen"), dict):
        st["seen"] = {}
    st.setdefault("last_level", "ok")
    st.setdefault("last_signature", "")
    st.setdefault("last_sent_ts", 0)
    st.setdefault("last_send_ok", True)
    st.setdefault("last_send_msg", "")
    return st


def _alerts_signature(issues: List[Dict[str, str]]) -> str:
    keys = [str(i.get("key") or "").strip() for i in (issues or []) if str(i.get("key") or "").strip()]
    keys = sorted(set(keys))
    return ",".join(keys)


def _alerts_enabled(alerts_env: Dict[str, str]) -> bool:
    return env_bool(alerts_env, "ALERT_ENABLED", False)


def _alerts_channels(alerts_env: Dict[str, str]) -> Dict[str, bool]:
    return {
        "wecom": bool(str(alerts_env.get("ALERT_WECOM_WEBHOOK") or "").strip()),
        "telegram": bool(str(alerts_env.get("ALERT_TG_BOT_TOKEN") or "").strip() and str(alerts_env.get("ALERT_TG_CHAT_ID") or "").strip()),
        "bark": bool(str(alerts_env.get("ALERT_BARK_URL") or "").strip()),
    }


def _alerts_any_channel_configured(alerts_env: Dict[str, str]) -> bool:
    ch = _alerts_channels(alerts_env)
    return bool(ch.get("wecom") or ch.get("telegram") or ch.get("bark"))


def alerts_evaluate(alerts_env: Dict[str, str], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate "runtime incidents" and generate a short runbook.
    Default is conservative (avoid spamming during initial setup).
    """
    ensure_home_env_file()
    env = read_env_file(HOME_ENV_FILE)

    include_setup = env_bool(alerts_env, "ALERT_INCLUDE_SETUP", False)
    seen = state.get("seen") if isinstance(state.get("seen"), dict) else {}
    seen_frontend_ok = bool(seen.get("frontend_ok"))
    seen_api_public_ok = bool(seen.get("api_public_ok"))

    public_domain = (env.get("NB_PUBLIC_DOMAIN") or "naibao.me").strip()
    api_public = (env.get("NB_TUNNEL_HOSTNAME") or "api.naibao.me").strip()
    api_local_port = backend_host_port(env)

    # Core checks (local)
    docker_daemon = docker_daemon_status()
    docker_ok = bool(docker_daemon.get("ok"))
    api_local_ok, api_local_msg = http_health(f"http://127.0.0.1:{int(api_local_port)}/health", timeout_s=2)

    # Tunnel / named config
    tunnel_mode = (env.get("NB_TUNNEL_MODE") or "named").strip().lower()
    need_named = tunnel_mode != "quick"
    named_cfg = parse_named_tunnel_config(TUN_CFG)
    cred_raw = (named_cfg.get("credentials_file") or "").strip()
    cred_path = Path(os.path.expanduser(cred_raw)) if cred_raw else None
    cred_ok = bool(cred_path and cred_path.exists())
    cert_ok = bool((Path.home() / ".cloudflared" / "cert.pem").exists())
    config_ok = bool(TUN_CFG.exists() and (named_cfg.get("tunnel_id") or "").strip() and cred_ok)

    tunnel_pid = read_pid(TUN_PID)
    tunnel_alive = bool(tunnel_pid and is_pid_alive(tunnel_pid))

    # Public checks (only alert after it has been OK at least once, unless include_setup=1)
    api_public_ok, api_public_msg = cached(
        f"alerts_api_public_health:{api_public}",
        15,
        lambda: http_health(f"https://{api_public}/api/health", timeout_s=3),
    )
    frontend_ok, frontend_msg = cached(
        f"alerts_frontend_https:{public_domain}",
        30,
        lambda: http_health(f"https://{public_domain}", timeout_s=3),
    )

    # Update "seen ok" flags (for future suppression).
    if api_public_ok:
        seen_api_public_ok = True
    if frontend_ok:
        seen_frontend_ok = True

    issues: List[Dict[str, str]] = []

    if not docker_ok:
        issues.append(
            {
                "key": "docker",
                "title": "Docker 引擎不可用",
                "detail": str(docker_daemon.get("msg") or ""),
                "fix": "打开 Docker Desktop/OrbStack，等待就绪后点「一键启动/修复」。",
            }
        )
    if docker_ok and not api_local_ok:
        issues.append(
            {
                "key": "api_local",
                "title": "API 本机不可用",
                "detail": (api_local_msg or "").strip(),
                "fix": "点「一键启动/修复」；仍失败就重启后端并查看后端日志。",
            }
        )

    if need_named:
        if not config_ok:
            if include_setup:
                issues.append(
                    {
                        "key": "named_init",
                        "title": "固定外网未初始化",
                        "detail": "未生成 cloudflared named 配置/凭据",
                        "fix": "先完成域名 NS 接入 Cloudflare，再点「固定外网初始化（一次性）」。",
                    }
                )
        else:
            if not tunnel_alive:
                issues.append(
                    {
                        "key": "tunnel",
                        "title": "外网通道未运行",
                        "detail": "cloudflared 未在运行",
                        "fix": "点「启动外网通道」或「重启外网通道」。",
                    }
                )

    # Only alert on public endpoints if it was OK before, or user explicitly includes setup.
    if include_setup or seen_api_public_ok or config_ok:
        if not api_public_ok:
            issues.append(
                {
                    "key": "api_public",
                    "title": "API 外网不可用",
                    "detail": (api_public_msg or "").strip(),
                    "fix": "先确保「API 本机」正常；再重启外网通道；若提示 1014 重新做固定外网初始化。",
                }
            )
    if include_setup or seen_frontend_ok:
        if not frontend_ok:
            issues.append(
                {
                    "key": "frontend",
                    "title": "前端不可访问",
                    "detail": (frontend_msg or "").strip(),
                    "fix": "检查 Cloudflare DNS（根域 A / www）与 GitHub Pages 域名/HTTPS 配置。",
                }
            )

    level = "ok" if not issues else "bad"
    sig = _alerts_signature(issues)

    # persist seen flags for suppression
    state.setdefault("seen", {})
    if isinstance(state["seen"], dict):
        state["seen"]["frontend_ok"] = bool(seen_frontend_ok)
        state["seen"]["api_public_ok"] = bool(seen_api_public_ok)

    return {
        "level": level,
        "signature": sig,
        "issues": issues,
        "urls": {
            "frontend": f"https://{public_domain}",
            "api_health": f"https://{api_public}/api/health",
        },
        "local": {"api_port": int(api_local_port), "api_url": f"http://127.0.0.1:{int(api_local_port)}/health"},
        "named": {"need_named": bool(need_named), "config_ok": bool(config_ok), "cert_ok": bool(cert_ok)},
    }


def alerts_message(summary: Dict[str, Any], is_recovery: bool) -> Tuple[str, str]:
    ts = time.strftime("%Y-%m-%d %H:%M")
    issues = summary.get("issues") if isinstance(summary.get("issues"), list) else []
    urls = summary.get("urls") if isinstance(summary.get("urls"), dict) else {}
    api = str(urls.get("api_health") or "").strip()
    fe = str(urls.get("frontend") or "").strip()

    title = "奶宝：已恢复" if is_recovery else "奶宝：异常"
    lines: List[str] = [f"时间：{ts}"]

    if not is_recovery:
        if issues:
            lines.append("异常：")
            for it in issues[:12]:
                t = str(it.get("title") or "").strip() or "异常"
                d = str(it.get("detail") or "").strip()
                lines.append(f"- {t}" + (f"（{d}）" if d else ""))
            lines.append("")
            lines.append("建议：")
            # Deduplicate fix steps
            fixes: List[str] = []
            for it in issues:
                fx = str(it.get("fix") or "").strip()
                if fx and fx not in fixes:
                    fixes.append(fx)
            for i, fx in enumerate(fixes[:6], start=1):
                lines.append(f"{i}. {fx}")
        else:
            lines.append("异常：未知（请打开运营台查看详情）")
    else:
        lines.append("状态：所有关键检查已恢复正常")

    if fe:
        lines.append("")
        lines.append(f"前端：{fe}")
    if api:
        lines.append(f"API：{api}")

    return title, "\n".join([x for x in lines if x is not None]).strip()


def alerts_send_all(alerts_env: Dict[str, str], title: str, body: str) -> Tuple[bool, str]:
    ch = _alerts_channels(alerts_env)
    results: List[str] = []
    ok_any = False

    if ch.get("wecom"):
        ok, msg = alert_send_wecom(str(alerts_env.get("ALERT_WECOM_WEBHOOK") or "").strip(), title, body)
        results.append(f"微信(企业微信)：{'成功' if ok else '失败'}" + (f"（{msg}）" if msg else ""))
        ok_any = ok_any or ok

    if ch.get("telegram"):
        ok, msg = alert_send_telegram(
            str(alerts_env.get("ALERT_TG_BOT_TOKEN") or "").strip(),
            str(alerts_env.get("ALERT_TG_CHAT_ID") or "").strip(),
            title,
            body,
        )
        results.append(f"Telegram：{'成功' if ok else '失败'}" + (f"（{msg}）" if msg else ""))
        ok_any = ok_any or ok

    if ch.get("bark"):
        ok, msg = alert_send_bark(str(alerts_env.get("ALERT_BARK_URL") or "").strip(), title, body)
        results.append(f"Bark：{'成功' if ok else '失败'}" + (f"（{msg}）" if msg else ""))
        ok_any = ok_any or ok

    if not results:
        return False, "未配置任何告警渠道（alerts.env）"
    return bool(ok_any), "\n".join(results).strip()


def alerts_worker(stop_event: Optional[threading.Event] = None) -> None:
    _append_alert_log("告警守护启动")
    while True:
        if stop_event and stop_event.is_set():
            _append_alert_log("告警守护停止")
            return
        try:
            ensure_alerts_env_file()
            aenv = read_env_file(ALERTS_ENV_FILE)
            interval_s = env_int(aenv, "ALERT_INTERVAL_S", 30, 10, 600)

            if not _alerts_enabled(aenv):
                time.sleep(max(10, interval_s))
                continue
            if not _alerts_any_channel_configured(aenv):
                _append_alert_log("告警已开启，但未配置渠道（alerts.env）")
                time.sleep(max(30, interval_s))
                continue
            if is_in_silence_window(aenv):
                time.sleep(max(20, interval_s))
                continue

            st = alerts_state()
            summary = alerts_evaluate(aenv, st)
            level = str(summary.get("level") or "ok")
            sig = str(summary.get("signature") or "")

            last_level = str(st.get("last_level") or "ok")
            last_sig = str(st.get("last_signature") or "")
            last_sent_ts = int(st.get("last_sent_ts") or 0)
            repeat_minutes = env_int(aenv, "ALERT_REPEAT_MINUTES", 30, 5, 1440)
            repeat_s = int(repeat_minutes) * 60
            send_recovery = env_bool(aenv, "ALERT_SEND_RECOVERY", True)

            now = int(time.time())

            should_send = False
            is_recovery = False
            if level != last_level:
                if level == "ok":
                    is_recovery = True
                    should_send = bool(send_recovery)
                else:
                    should_send = True
            elif level != "ok" and sig != last_sig:
                should_send = True
            elif level != "ok" and (now - last_sent_ts) >= repeat_s:
                should_send = True

            if should_send:
                title, body = alerts_message(summary, is_recovery=is_recovery)
                ok, report = alerts_send_all(aenv, title, body)
                st["last_sent_ts"] = now
                st["last_send_ok"] = bool(ok)
                st["last_send_msg"] = str(report or "")
                _append_alert_log(("已发送" if ok else "发送失败") + "：\n" + report)

            st["last_level"] = level
            st["last_signature"] = sig
            _save_json(ALERTS_STATE_FILE, st)
        except Exception as e:
            _append_alert_log("告警守护异常：" + humanize_error(str(e)))

        # Re-read env each loop to make config changes take effect quickly.
        try:
            aenv2 = read_env_file(ALERTS_ENV_FILE)
            sleep_s = env_int(aenv2, "ALERT_INTERVAL_S", 30, 10, 600)
        except Exception:
            sleep_s = 30
        time.sleep(int(sleep_s))


def alerts_config_payload() -> Dict[str, Any]:
    ensure_alerts_env_file()
    env = read_env_file(ALERTS_ENV_FILE)

    def _get(k: str) -> str:
        return str(env.get(k) or "").strip()

    def _mask_str(s: str, head: int = 6, tail: int = 4) -> str:
        v = str(s or "").strip()
        if not v:
            return ""
        if len(v) <= (head + tail + 3):
            if len(v) <= 4:
                return v[0:1] + "…"
            return v[0:2] + "…" + v[-2:]
        return v[:head] + "…" + v[-tail:]

    def _mask_secret_display(v: str) -> str:
        raw = str(v or "").strip()
        if not raw:
            return ""
        # Try to display URL-like secrets in a readable, yet safe, way.
        try:
            u = urllib.parse.urlparse(raw)
            if u.scheme and u.netloc:
                host = u.netloc
                parts = [p for p in (u.path or "").split("/") if p]
                q = urllib.parse.parse_qs(u.query or "")
                # Bark official: https://api.day.app/<key>
                if host.endswith("day.app") and parts:
                    return f"{u.scheme}://{host}/{_mask_str(parts[0], 4, 4)}"
                # Bark self-hosted common: /<key> or /bark/<key>
                if len(parts) >= 2 and _looks_like_bark_key(parts[1]):
                    return f"{u.scheme}://{host}/{parts[0]}/{_mask_str(parts[1], 4, 4)}"
                if parts and _looks_like_bark_key(parts[0]):
                    return f"{u.scheme}://{host}/{_mask_str(parts[0], 4, 4)}"
                # WeCom webhook: ...?key=xxxx
                if "key" in q and q.get("key"):
                    return f"{u.scheme}://{host}{u.path}?key={_mask_str(str(q['key'][0]), 4, 4)}"
                short = f"{u.scheme}://{host}{u.path}"
                if u.query:
                    short += "?…"
                return _mask_str(short, 26, 4)
        except Exception:
            pass
        return _mask_str(raw, 10, 4)

    # Sensitive items are not returned in plain text by default.
    secrets = ["ALERT_WECOM_WEBHOOK", "ALERT_TG_BOT_TOKEN", "ALERT_TG_CHAT_ID", "ALERT_BARK_URL"]
    values = {
        "ALERT_ENABLED": _get("ALERT_ENABLED") or "0",
        "ALERT_INTERVAL_S": _get("ALERT_INTERVAL_S") or "30",
        "ALERT_REPEAT_MINUTES": _get("ALERT_REPEAT_MINUTES") or "30",
        "ALERT_SEND_RECOVERY": _get("ALERT_SEND_RECOVERY") or "1",
        "ALERT_INCLUDE_SETUP": _get("ALERT_INCLUDE_SETUP") or "0",
        "ALERT_SILENCE_START": _get("ALERT_SILENCE_START"),
        "ALERT_SILENCE_END": _get("ALERT_SILENCE_END"),
        "ALERT_WECOM_WEBHOOK": "",
        "ALERT_TG_BOT_TOKEN": "",
        "ALERT_TG_CHAT_ID": "",
        "ALERT_BARK_URL": "",
    }
    configured = {k: bool(_get(k)) for k in secrets}
    masked = {k: _mask_secret_display(_get(k)) for k in secrets}

    return {
        "ok": True,
        "env_file": str(ALERTS_ENV_FILE),
        "values": values,
        "configured": configured,
        "masked": masked,
        "links": {
            "wecom_bot": "https://developer.work.weixin.qq.com/document/path/91770",
            "telegram_botfather": "https://t.me/BotFather",
            "telegram_api": "https://core.telegram.org/bots/api",
            "bark": "https://github.com/Finb/Bark",
        },
    }


def alerts_config_save(payload: Dict[str, Any]) -> Tuple[bool, str, str]:
    ensure_alerts_env_file()
    env0 = read_env_file(ALERTS_ENV_FILE)

    values = payload.get("values") if isinstance(payload.get("values"), dict) else {}
    clear = payload.get("clear") if isinstance(payload.get("clear"), dict) else {}

    def _b(key: str, default: bool) -> str:
        raw = values.get(key, None)
        if raw is None:
            return "1" if default else "0"
        v = str(raw).strip().lower()
        return "1" if v in ("1", "true", "yes", "y", "on") else "0"

    changed: List[str] = []

    def _set(key: str, value: str, comment: str = "") -> None:
        if set_env_kv(ALERTS_ENV_FILE, key, value, comment=comment):
            changed.append(key)

    # Basic
    if "ALERT_ENABLED" in values:
        _set("ALERT_ENABLED", _b("ALERT_ENABLED", env_bool(env0, "ALERT_ENABLED", False)))
    if "ALERT_INCLUDE_SETUP" in values:
        _set("ALERT_INCLUDE_SETUP", _b("ALERT_INCLUDE_SETUP", env_bool(env0, "ALERT_INCLUDE_SETUP", False)))
    if "ALERT_SEND_RECOVERY" in values:
        _set("ALERT_SEND_RECOVERY", _b("ALERT_SEND_RECOVERY", env_bool(env0, "ALERT_SEND_RECOVERY", True)))

    if "ALERT_INTERVAL_S" in values:
        try:
            v = int(str(values.get("ALERT_INTERVAL_S") or "").strip())
        except Exception:
            v = env_int(env0, "ALERT_INTERVAL_S", 30, 10, 600)
        v = max(10, min(600, int(v)))
        _set("ALERT_INTERVAL_S", str(v))

    if "ALERT_REPEAT_MINUTES" in values:
        try:
            v = int(str(values.get("ALERT_REPEAT_MINUTES") or "").strip())
        except Exception:
            v = env_int(env0, "ALERT_REPEAT_MINUTES", 30, 5, 1440)
        v = max(5, min(1440, int(v)))
        _set("ALERT_REPEAT_MINUTES", str(v))

    # Silence window (empty allowed)
    for k in ("ALERT_SILENCE_START", "ALERT_SILENCE_END"):
        if k not in values:
            continue
        s = str(values.get(k) or "").strip()
        if s and parse_hhmm(s) is None:
            return False, f"静默时段格式不正确：{k}（示例 23:00）", ""
        _set(k, s)

    # Secrets: only set when user provided non-empty, or explicitly cleared.
    secret_keys = ["ALERT_WECOM_WEBHOOK", "ALERT_TG_BOT_TOKEN", "ALERT_TG_CHAT_ID", "ALERT_BARK_URL"]
    for k in secret_keys:
        if bool(clear.get(k)):
            _set(k, "")
            continue
        if k not in values:
            continue
        s = str(values.get(k) or "").strip()
        if s:
            low = s.lower()
            # Guardrails: prevent obvious cross-field pasting.
            if k == "ALERT_WECOM_WEBHOOK":
                if "api.day.app" in low or "day.app/" in low:
                    return False, "看起来你把 Bark URL 填进了「微信 Webhook」。请把它填到「Bark URL」。", ""
            if k == "ALERT_BARK_URL":
                if "qyapi.weixin.qq.com" in low or "work.weixin.qq.com" in low:
                    return False, "看起来你把 企业微信 Webhook 填进了「Bark URL」。请把它填到「微信 Webhook」。", ""
            if k == "ALERT_BARK_URL":
                s2 = normalize_bark_url_prefix(s)
                s = s2
            _set(k, s)

    env1 = read_env_file(ALERTS_ENV_FILE)
    ch_wecom = bool(str(env1.get("ALERT_WECOM_WEBHOOK") or "").strip())
    ch_tg = bool(str(env1.get("ALERT_TG_BOT_TOKEN") or "").strip() and str(env1.get("ALERT_TG_CHAT_ID") or "").strip())
    ch_bark = bool(str(env1.get("ALERT_BARK_URL") or "").strip())
    ch_txt = "、".join([x for x in ["微信" if ch_wecom else "", "Telegram" if ch_tg else "", "Bark" if ch_bark else ""] if x]) or "无"

    msg = f"已保存（修改 {len(changed)} 项）" if changed else "未修改（无需保存）"
    detail_lines = ["== 保存结果 ==", msg]
    detail_lines.append("")
    detail_lines.append("已配置渠道：" + ch_txt)
    if changed:
        detail_lines.append("")
        detail_lines.append("已修改：")
        for k in changed:
            detail_lines.append(f"- {k}")
    detail_lines.append("")
    detail_lines.append(f"配置文件：{ALERTS_ENV_FILE}")
    return True, msg, "\n".join(detail_lines).strip()


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>奶宝 · 本机托管运营台</title>
    <style>
      :root{
        /* iOS-like: clean + grouped background + subtle separators */
        --bg: #f2f2f7;
        --card: #ffffff;
        --text: #111111;
        --muted: rgba(60,60,67,.60);
        --border: rgba(60,60,67,.12);
        --separator: rgba(60,60,67,.12);
        --primary: #007aff;
        --ok: #34c759;
        --warn: #ff9500;
        --bad: #ff3b30;
        --shadow: 0 10px 30px rgba(0,0,0,.08);
      }
      html,body{height:100%;}
      body{
        margin:0;
        font-family: "PingFang SC","HarmonyOS Sans SC","Noto Sans SC","Microsoft YaHei",system-ui,sans-serif;
        color:var(--text);
        background: var(--bg);
      }
      .wrap{max-width:980px;margin:0 auto;padding:18px 14px 44px;}
      .top{display:flex;gap:14px;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;}
      .h1{font-size:20px;font-weight:750;letter-spacing:.2px;}
      .sub{font-size:12px;color:var(--muted);line-height:1.5;}
      .mono{font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;}

      .topRight{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
      .iconBtn{
        height:40px;
        padding:0 12px;
        border-radius:999px;
        border:1px solid var(--border);
        background:rgba(255,255,255,.70);
        font-weight:750;
        font-size:12px;
        color:var(--text);
        cursor:pointer;
      }
      .pill{
        display:inline-flex;align-items:center;gap:6px;
        padding:6px 12px;border-radius:999px;border:1px solid var(--border);
        font-size:12px;font-weight:650;
        background:rgba(255,255,255,.70);
      }
      .pill.ok{color:var(--ok);border-color:rgba(52,199,89,.22);background:rgba(52,199,89,.10);}
      .pill.warn{color:var(--warn);border-color:rgba(255,149,0,.22);background:rgba(255,149,0,.10);}
      .pill.bad{color:var(--bad);border-color:rgba(255,59,48,.22);background:rgba(255,59,48,.10);}

      .section{margin-top:14px;}

      /* Linear steps (iOS grouped list style) */
      .steps{margin-top:14px;}
      .step{margin-top:16px;}
      .step:first-child{margin-top:0;}
      .stepHead{
        display:flex;
        align-items:flex-end;
        justify-content:space-between;
        gap:10px;
        padding:0 4px;
        cursor:pointer;
        user-select:none;
      }
      .stepLeft{min-width:220px;}
      .stepTitle{font-size:13px;font-weight:700;letter-spacing:.2px;color:rgba(60,60,67,.60);}
      .stepDesc{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.4;word-break:break-word;}
      .stepRight{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
      .expander{font-size:12px;color:var(--muted);}
      .stepCard{
        margin-top:10px;
        background:var(--card);
        border:1px solid var(--border);
        border-radius:16px;
        overflow:hidden;
        box-shadow: var(--shadow);
      }
      .stepCard.hidden{display:none;}

      .cell{
        display:flex;
        gap:10px;
        align-items:center;
        justify-content:space-between;
        padding:13px 14px;
      }
      .cell + .cell{border-top:1px solid var(--separator);}
      .cellMain{min-width:0;flex:1;}
      .cellTitle{font-size:15px;font-weight:650;letter-spacing:.1px;}
      .cellSub{
        font-size:12px;
        color:var(--muted);
        margin-top:4px;
        line-height:1.35;
        display:-webkit-box;
        -webkit-line-clamp:2;
        -webkit-box-orient:vertical;
        overflow:hidden;
      }
      .cellRight{display:flex;align-items:center;gap:10px;flex-shrink:0;}
      .cellValue{
        font-size:13px;
        color:var(--muted);
        max-width:160px;
        text-align:right;
        white-space:nowrap;
        overflow:hidden;
        text-overflow:ellipsis;
      }
      .dot{width:10px;height:10px;border-radius:999px;background:rgba(60,60,67,.28);flex-shrink:0;}
      .cell.ok .dot{background:var(--ok);}
      .cell.warn .dot{background:var(--warn);}
      .cell.bad .dot{background:var(--bad);}
      .chev{
        width:7px;height:7px;
        border-right:2px solid rgba(60,60,67,.30);
        border-bottom:2px solid rgba(60,60,67,.30);
        transform: rotate(-45deg);
        margin-left:2px;
      }

      .btn{
        height:40px;
        padding:0 14px;
        border-radius:12px;
        border:1px solid var(--border);
        background:rgba(255,255,255,.86);
        font-weight:650;
        font-size:13px;
        cursor:pointer;
      }
      .btn.primary{
        background: var(--primary);
        border-color: rgba(0,0,0,0);
        color:#fff;
      }
      .btn.danger{background:rgba(255,59,48,.10);border-color:rgba(255,59,48,.22);color:var(--bad);}
      .btn.ghost{background:transparent;}
      .btn:disabled{opacity:.5;cursor:not-allowed;}

      details{margin-top:12px;}
      summary{cursor:pointer;font-weight:650;font-size:12px;color:var(--muted);list-style:none;}
      summary::-webkit-details-marker{display:none;}
      .pre{
        margin:10px 0 0;
        padding:10px;
        background: rgba(255,255,255,.70);
        border:1px solid var(--border);
        border-radius:14px;
        overflow:auto;
        max-height:220px;
        font-size:12px;
        line-height:1.5;
        white-space:pre-wrap;
      }

      .modal{position:fixed;inset:0;display:none;align-items:flex-start;justify-content:center;padding:18px;z-index:50;}
      .mask{position:absolute;inset:0;background:rgba(0,0,0,.35);}
      .dialog{
        position:relative;
        width:min(980px, calc(100vw - 36px));
        margin-top:48px;
        background:rgba(255,255,255,.92);
        border:1px solid var(--border);
        border-radius:18px;
        box-shadow: 0 24px 70px rgba(0,0,0,.20);
        backdrop-filter: blur(10px);
        overflow:hidden;
        max-height: calc(100vh - 96px);
        display:flex;
        flex-direction:column;
      }
      .dialogHead{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 12px 0;}
      .dialogHeadBtns{display:flex;align-items:center;gap:8px;}
      .dialogTitle{font-weight:700;font-size:13px;}
      .dialogBody{padding:10px 12px 14px;overflow:auto;-webkit-overflow-scrolling: touch;}
      .log{margin:0;padding:10px;background:rgba(60,60,67,.06);border:1px solid var(--border);border-radius:14px;max-height:62vh;overflow:auto;font-size:12px;line-height:1.5;}
      .resultMsg{font-size:13px;font-weight:750;letter-spacing:.1px;margin:2px 0 10px;line-height:1.35;}
      .resultDesc{font-size:12px;color:var(--muted);margin:0 0 10px 0;line-height:1.45;white-space:pre-wrap;}
      .resultDetails{margin-top:10px;}
      .resultTools{display:flex;gap:8px;align-items:center;margin:8px 0;}

      /* TODO list (iOS-like, actionable) */
      .todoIntro{font-size:12px;color:var(--muted);line-height:1.45;margin:0 0 10px 0;}
      .todoList{border:1px solid var(--border);border-radius:14px;overflow:hidden;background:rgba(60,60,67,.06);}
      .todoItem{display:flex;gap:12px;align-items:flex-start;justify-content:space-between;padding:12px;background:rgba(255,255,255,.72);}
      .todoItem + .todoItem{border-top:1px solid var(--separator);}
      .todoNo{width:22px;height:22px;border-radius:999px;background:rgba(60,60,67,.12);color:rgba(60,60,67,.70);display:flex;align-items:center;justify-content:center;font-weight:750;font-size:12px;flex-shrink:0;margin-top:1px;}
      .todoNo.ok{background:rgba(52,199,89,.18);color:var(--ok);}
      .todoNo.warn{background:rgba(255,149,0,.18);color:var(--warn);}
      .todoNo.bad{background:rgba(255,59,48,.18);color:var(--bad);}
      .todoText{flex:1;min-width:0;}
      .todoTitle{font-size:13px;font-weight:750;letter-spacing:.1px;}
      .todoDesc{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.35;white-space:pre-wrap;}
      .todoFields{
        margin-top:8px;
        border:1px solid var(--separator);
        border-radius:12px;
        overflow:hidden;
        background:rgba(255,255,255,.72);
      }
      .todoField{display:flex;align-items:center;gap:10px;padding:10px;}
      .todoField + .todoField{border-top:1px solid var(--separator);}
      .todoFieldKey{width:72px;flex-shrink:0;font-size:12px;color:var(--muted);font-weight:650;}
      .todoFieldVal{flex:1;min-width:0;font-size:12px;line-height:1.35;white-space:pre-wrap;word-break:break-word;}
      .todoFieldVal.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;}
      .todoActs{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;flex-shrink:0;}
      .miniBtn{height:32px;padding:0 10px;border-radius:10px;border:1px solid var(--border);background:rgba(255,255,255,.86);font-weight:750;font-size:12px;cursor:pointer;}
      .miniBtn.primary{background:rgba(0,122,255,.12);border-color:rgba(0,122,255,.22);color:var(--primary);}
      .miniBtn.danger{background:rgba(255,59,48,.10);border-color:rgba(255,59,48,.22);color:var(--bad);}

      /* Alert settings form (iOS-like) */
      .formSection{margin-top:12px;}
      .formTitle{font-size:12px;font-weight:750;color:rgba(60,60,67,.60);padding:0 2px 8px;}
      .formList{border:1px solid var(--border);border-radius:14px;overflow:hidden;background:rgba(255,255,255,.72);}
      .formRow{display:flex;gap:10px;align-items:center;justify-content:space-between;padding:10px;}
      .formRow + .formRow{border-top:1px solid var(--separator);}
      .formKey{width:112px;flex-shrink:0;font-size:12px;color:var(--muted);font-weight:650;}
      .formCtl{flex:1;min-width:0;display:flex;flex-direction:column;gap:6px;}
      .textInput,.selectInput{
        height:34px;
        padding:0 10px;
        border-radius:10px;
        border:1px solid var(--border);
        background:rgba(255,255,255,.86);
        font-size:12px;
        font-weight:650;
        color:var(--text);
        outline:none;
      }
      .hint{font-size:11px;color:var(--muted);line-height:1.35;white-space:pre-wrap;}
      .formActs{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;flex-shrink:0;}

      /* iOS-like Action Sheet */
      .sheet{position:fixed;inset:0;display:none;align-items:flex-end;justify-content:center;padding:18px;z-index:55;}
      .sheetMask{position:absolute;inset:0;background:rgba(0,0,0,.35);}
      .sheetBody{position:relative;width:min(520px, calc(100vw - 36px));}
      .sheetPanel{
        background:rgba(255,255,255,.92);
        border:1px solid var(--border);
        border-radius:18px;
        overflow:hidden;
        display:flex;
        flex-direction:column;
        max-height: calc(100vh - 160px);
        box-shadow: 0 24px 70px rgba(0,0,0,.20);
        backdrop-filter: blur(18px);
      }
      .sheetHead{padding:14px 14px 10px;text-align:center;}
      .sheetTitle{font-weight:750;font-size:15px;letter-spacing:.2px;}
      .sheetSub{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.4;word-break:break-word;}
      .sheetBtns{
        display:flex;
        flex-direction:column;
        overflow:auto;
        -webkit-overflow-scrolling: touch;
      }
      .sheetBtn{
        height:46px;
        border:0;
        background:transparent;
        font-weight:750;
        font-size:16px;
        cursor:pointer;
      }
      .sheetBtn + .sheetBtn{border-top:1px solid var(--separator);}
      .sheetBtn.primary{color:var(--primary);}
      .sheetBtn.danger{color:var(--bad);}
      .sheetCancel{
        margin-top:10px;
        width:100%;
        height:50px;
        border-radius:18px;
        border:1px solid var(--border);
        background:rgba(255,255,255,.92);
        font-weight:750;
        font-size:16px;
        cursor:pointer;
      }

      .toast{
        position:fixed;left:50%;bottom:18px;transform:translateX(-50%);
        padding:10px 14px;border-radius:999px;border:1px solid var(--border);
        background:rgba(255,255,255,.92);
        box-shadow: 0 16px 40px rgba(0,0,0,.12);
        font-weight:950;font-size:12px;
        display:none;
        z-index:60;
      }
      .toast.ok{color:var(--ok);border-color:rgba(31,138,91,.22);background:rgba(31,138,91,.10);}
      .toast.bad{color:var(--bad);border-color:rgba(226,74,59,.22);background:rgba(226,74,59,.10);}
    </style>
  </head>
  <body>
    <div class="wrap">
	      <div class="top">
	        <div>
	          <div class="h1">奶宝 · 本机托管运营台</div>
	          <div class="sub">默认只显示需处理项；点一行即可操作。</div>
	        </div>
	        <div class="topRight">
	            <div class="pill ok" id="overallPill">—</div>
            <button class="iconBtn" onclick="openMenu()">设置</button>
	        </div>
	      </div>

	      <div class="section">
	        <div id="metrics" class="steps">
            <div class="step">
              <div class="stepHead">
                <div class="stepLeft">
                  <div class="stepTitle">正在检测…</div>
                  <div class="stepDesc">首次打开会检查 Docker / DNS / 外网通道，可能需要几秒。</div>
                </div>
                <div class="stepRight">
                  <div class="pill warn">加载中</div>
                </div>
              </div>
            </div>
          </div>
	      </div>

      <details>
        <summary>更多信息（路径/局域网/版本）</summary>
        <pre class="pre mono" id="foot">—</pre>
      </details>
    </div>

	    <div class="modal" id="modal">
	      <div class="mask" onclick="closeModal()"></div>
	      <div class="dialog">
	        <div class="dialogHead">
	          <div class="dialogTitle" id="modalTitle">—</div>
	          <div class="dialogHeadBtns">
	            <button class="btn ghost" id="modalCopyBtn" onclick="copyModal()" style="display:none;">复制</button>
	            <button class="btn ghost" onclick="closeModal()">关闭</button>
	          </div>
	        </div>
	        <div class="dialogBody" id="modalBody"></div>
	      </div>
	    </div>

	    <div class="sheet" id="sheet">
	      <div class="sheetMask" onclick="closeSheet()"></div>
	      <div class="sheetBody">
	        <div class="sheetPanel">
	          <div class="sheetHead">
	            <div class="sheetTitle" id="sheetTitle">—</div>
	            <div class="sheetSub" id="sheetSub">—</div>
	          </div>
	          <div class="sheetBtns" id="sheetBtns"></div>
	        </div>
	        <button class="sheetCancel" onclick="closeSheet()">取消</button>
	      </div>
	    </div>

	    <div class="toast" id="toast"></div>

    <script>
	      let auto = true;
	      let timer = null;
	      let toastTimer = null;
	      let issuesOnly = true;
	      let lastPreparedCards = [];
	      const collapsed = {};
	      let modalCopyText = '';
	      let lastCardId = '';
        let refreshInFlight = false;
        const LS_STATUS_KEY = 'naibao_ops_last_status_v1';

      const ACTION_LABELS = {
        docker_up: '启动/修复全部',
        docker_restart_all: '重启全部',
        docker_down: '停止全部',
        set_backend_port: '设置后端端口',
        tunnel_start: '启动外网通道',
        tunnel_restart: '重启外网通道',
        tunnel_stop: '停止外网通道',
        named_tunnel_init: '初始化固定外网（一次性）',
        git_publish_workflow: '提交部署工作流',
        git_publish_frontend: '发布前端更新',
        docker_prune: '清理 Docker 缓存',
        open_docker: '打开 Docker',
        alerts_open_config: '打开告警配置',
        alerts_test: '发送测试消息',
        alerts_enable: '开启告警',
        alerts_disable: '关闭告警',
        mobile_preview_start: '启动手机外网验收',
        mobile_preview_restart: '重启手机外网验收',
        mobile_preview_stop: '停止手机外网验收',
        ops_shutdown: '关闭运营台',
      };

      function openMenu(){
        openSheet({
          title:'设置',
          value:'',
          sub:'显示偏好 / 高级操作',
          actions:[
            {type:'refresh', label:'刷新'},
            {type:'toggle', label:'只看需处理：' + (issuesOnly ? '开' : '关'), key:'issuesOnly'},
            {type:'toggle', label:'自动刷新：' + (auto ? '开' : '关'), key:'auto'},
            {type:'api', label:'停止全部服务', action:'docker_down', kind:'danger', confirm:'确认停止全部服务？停止后外网/本机 API 都将不可用。'},
            {type:'api', label:'关闭运营台', action:'ops_shutdown', kind:'danger', confirm:'确认关闭运营台？关闭后将无法打开本页。'},
          ]
        });
      }

      function actionLabel(action, service){
        const a = String(action || '').trim();
        const s = String(service || '').trim();
        if(a === 'docker_restart' && s){ return '重启' + prettySvcName(s); }
        if(a === 'docker_stop_container' && s){ return '停止：' + prettyContainerName(s); }
        if(ACTION_LABELS[a]){ return ACTION_LABELS[a]; }
        return a || '操作';
      }

      function fmtBytes(n){
        if(typeof n !== 'number' || !isFinite(n)){ return '—'; }
        const units = ['B','KB','MB','GB','TB'];
        let v = n;
        let i = 0;
        while(v >= 1024 && i < units.length - 1){ v = v / 1024; i++; }
        const dp = (i > 0 && v < 10) ? 1 : 0;
        return v.toFixed(dp) + ' ' + units[i];
      }

      function fmtPct(p){
        if(typeof p !== 'number' || !isFinite(p)){ return '—'; }
        return Math.round(p * 100) + '%';
      }

      function fmtUptime(sec){
        if(typeof sec !== 'number' || !isFinite(sec) || sec <= 0){ return '—'; }
        let s = Math.floor(sec);
        const d = Math.floor(s / 86400); s %= 86400;
        const h = Math.floor(s / 3600); s %= 3600;
        const m = Math.floor(s / 60);
        if(d > 0){ return `${d}天${h}小时`; }
        if(h > 0){ return `${h}小时${m}分钟`; }
        return `${m}分钟`;
      }

      function toast(text, kind){
        const el = document.getElementById('toast');
        el.classList.remove('ok','bad');
        if(kind){ el.classList.add(kind); }
        el.textContent = text;
        el.style.display = 'block';
        if(toastTimer){ clearTimeout(toastTimer); }
        toastTimer = setTimeout(() => { el.style.display = 'none'; }, 2400);
      }

      async function copyText(txt){
        const s = String(txt || '').trim();
        if(!s){
          toast('无可复制内容', 'bad');
          return;
        }
        try{
          if(navigator.clipboard && navigator.clipboard.writeText){
            await navigator.clipboard.writeText(s);
            toast('已复制', 'ok');
            return;
          }
        }catch(e){
          // ignore and fallback
        }
        try{
          const ta = document.createElement('textarea');
          ta.value = s;
          ta.style.position = 'fixed';
          ta.style.left = '-9999px';
          ta.style.top = '-9999px';
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          toast('已复制', 'ok');
        }catch(e){
          toast('复制失败', 'bad');
        }
      }

      function setModalCopy(txt){
        modalCopyText = String(txt || '');
        const b = document.getElementById('modalCopyBtn');
        if(!b){ return; }
        b.style.display = modalCopyText.trim() ? 'inline-flex' : 'none';
      }

      function copyModal(){
        return copyText(modalCopyText);
      }

      function setAuto(on){
        auto = !!on;
        const b = document.getElementById('autoBtn');
        if(b){ b.textContent = '自动刷新：' + (auto ? '开' : '关'); }
        if(timer){ clearInterval(timer); timer = null; }
        if(auto){ timer = setInterval(refresh, 5000); }
      }

      function toggleAuto(){
        setAuto(!auto);
      }

      function setIssuesOnly(on){
        issuesOnly = !!on;
        const b = document.getElementById('issuesBtn');
        if(b){ b.textContent = '只看需处理：' + (issuesOnly ? '开' : '关'); }
      }

      function toggleIssues(){
        setIssuesOnly(!issuesOnly);
        refresh();
      }

      function sev(s){
        const x = String(s || '').toLowerCase();
        if(x === 'bad'){ return 0; }
        if(x === 'warn'){ return 1; }
        return 2;
      }

      const GROUPS = [
        {
          id: 'run',
          order: 0,
          title: '① 本机',
          desc: ''
        },
        {
          id: 'mobile',
          order: 1,
          title: '② 手机验收',
          desc: ''
        },
        {
          id: 'setup',
          order: 2,
          title: '③ 固定域名上线',
          desc: ''
        },
        {
          id: 'host',
          order: 3,
          title: '④ 资源与版本',
          desc: ''
        },
      ];
      const GROUP_MAP = {};
      GROUPS.forEach(g => { GROUP_MAP[g.id] = g; });

      function groupOrder(g){
        const k = String(g || '').trim();
        return (GROUP_MAP[k] && Number.isFinite(GROUP_MAP[k].order)) ? GROUP_MAP[k].order : 99;
      }

        function prepareCards(cards){
          const src = Array.isArray(cards) ? cards : [];
          let out = src.map((c, i) => Object.assign({_i:i}, c));
          if(issuesOnly){
          out = out.filter(c => {
            const st = String((c && c.status) || 'ok');
            if(st === 'ok'){ return !!(c && c.always); }
            // Default to "product-like": hide host warnings (noise) unless it's a real red alert.
            const gid = String((c && c.group) || '').trim();
            if(gid === 'host' && st === 'warn'){ return false; }
            return true;
          });
          }
        out.sort((a, b) => {
          const ga = groupOrder(a.group);
          const gb = groupOrder(b.group);
          if(ga !== gb){ return ga - gb; }
          const oa = Number(a.order || 0);
          const ob = Number(b.order || 0);
          if(oa !== ob){ return oa - ob; }
          const da = sev(a.status);
          const db = sev(b.status);
          if(da !== db){ return da - db; }
          return (a._i || 0) - (b._i || 0);
        });
        return out.map(c => {
          const x = Object.assign({}, c);
          delete x._i;
          return x;
        });
      }

      function normalizeServiceItem(x){
        return {
          svc: String((x && (x.Service || x.Name)) || '').trim(),
          state: String((x && x.State) || '').trim(),
          status: String((x && x.Status) || '').trim(),
          health: String((x && x.Health) || '').trim(),
        };
      }

      function prettySvcName(s){
        const k = String(s || '').trim().toLowerCase();
        if(k === 'backend'){ return '后端'; }
        if(k === 'db'){ return '数据库'; }
        if(k === 'redis'){ return 'Redis'; }
        return String(s || '').trim() || '服务';
      }

      function prettyContainerName(n){
        const s = String(n || '').trim();
        if(!s){ return ''; }
        if(s.includes('deploy-backend')){ return '奶宝后端'; }
        if(s.includes('deploy-db')){ return '奶宝数据库'; }
        if(s.includes('deploy-redis')){ return '奶宝 Redis'; }
        return s;
      }

      function classifyService(item){
        if(!item || !item.svc){
          return { status:'bad', value:'未检测到', sub:'请先点击「启动/修复全部」让服务跑起来' };
        }
        const state = (item.state || '').toLowerCase();
        const st = (item.status || '').toLowerCase();
        const health = (item.health || '').toLowerCase();
        if(state !== 'running'){
          return { status:'bad', value:'未运行', sub:'服务未运行（可尝试重启/修复全部）' };
        }
        if(health === 'unhealthy' || st.includes('unhealthy')){
          return { status:'bad', value:'不健康', sub:'健康检查未通过（请查看日志）' };
        }
        if(st.includes('starting') || (health && health !== 'healthy')){
          return { status:'warn', value:'启动中', sub:'服务正在启动（稍等片刻）' };
        }
        return { status:'ok', value:'运行中', sub:'健康' };
      }

      function buildCards(data){
        const cards = [];
        const list = Array.isArray(data && data.containers) ? data.containers.map(normalizeServiceItem) : [];
        const getSvc = (name) => list.find(i => (i.svc || '').toLowerCase() === name);

        const dockerOk = !!(data && data.docker && data.docker.daemon && data.docker.daemon.ok);
        const dockerMsg = (data && data.docker && data.docker.daemon && data.docker.daemon.msg) ||
          (data && data.docker && data.docker.cli && data.docker.cli.msg) || '';
        // Step 1 primary action (always visible): novices should only need to click once.
        const localApiOk = !!(data && data.api && data.api.local && data.api.local.ok);
        const backendSt = classifyService(getSvc('backend'));
        const dbSt = classifyService(getSvc('db'));
        const redisSt = classifyService(getSvc('redis'));
        const coreOk = dockerOk && localApiOk && backendSt.status === 'ok' && dbSt.status === 'ok' && redisSt.status === 'ok';
        let oneStatus = 'ok';
        if(!dockerOk){ oneStatus = 'bad'; }
        else if(!coreOk){ oneStatus = 'warn'; }
        cards.push({
          id:'oneclick',
          group:'run',
          order:0,
          always:true,
          title:'一键启动/修复',
          status: oneStatus,
          value: coreOk ? '已就绪' : (dockerOk ? '建议执行' : '需要 Docker'),
          sub: coreOk ? '已启动。需要重启/修复时点这里' : (dockerOk ? '点一次即可自动修复端口并启动后端' : '先安装并启动 Docker / OrbStack'),
          actions:[
            {type:'api', label:'启动/修复全部', action:'docker_up', kind:'primary'},
            {type:'api', label:'重启全部', action:'docker_restart_all'},
            {type:'guide', label:'说明', title:'一键启动/修复', text:
              '适合零技术同学：遇到任何“端口占用/服务没起来/后端不通”，优先点它。\\n\\n' +
              '它会做：\\n' +
              '- 自动选择可用后端端口（避免 8080/18080 被占用）\\n' +
              '- 启动/修复后端、数据库、Redis\\n\\n' +
              '点完后返回本页，看到「API 本机」变绿即可。'
            },
          ]
        });

        const al = (data && data.alerts) ? data.alerts : null;
        const alEnabled = !!(al && al.enabled);
        const alSilenceNow = !!(al && al.silence && al.silence.active_now);
        const alChannels = (al && al.channels) ? al.channels : {};
        const chWecom = !!alChannels.wecom;
        const chTg = !!alChannels.telegram;
        const chBark = !!alChannels.bark;
        const chCount = (chWecom?1:0) + (chTg?1:0) + (chBark?1:0);
        const last = (al && al.last) ? al.last : {};
        const lastSendOk = !!(last && last.send_ok);
        const lastSentTs = Number((last && last.sent_ts) || 0) || 0;
        const lastSentText = lastSentTs ? new Date(lastSentTs * 1000).toLocaleString() : '';
        const lastMsg = (last && last.send_msg) ? String(last.send_msg) : '';

        let alStatus = 'warn';
        let alValue = alEnabled ? '已开启' : '未开启';
        let alSub = '';
        if(chCount === 0){
          alStatus = alEnabled ? 'bad' : 'warn';
          alValue = alEnabled ? '未配置渠道' : '待配置';
          alSub = '先配置微信/Telegram/Bark，再开启告警';
        }else if(alEnabled && alSilenceNow){
          alStatus = 'warn';
          alValue = '静默中';
          alSub = '当前在静默时段内（不会推送）';
        }else if(alEnabled){
          alStatus = lastSendOk ? 'ok' : 'warn';
          alValue = '已开启';
          alSub = '渠道：' + [chWecom?'微信':'', chTg?'Telegram':'', chBark?'Bark':''].filter(Boolean).join('、');
        }else{
          alStatus = 'warn';
          alValue = '未开启';
          alSub = '开启后：异常会第一时间推送到手机';
        }
        if(lastSentText){
          alSub += (alSub ? ' · ' : '') + ('上次发送：' + lastSentText + (lastSendOk ? '' : '（失败）'));
        }
        const alActions = [
          {type:'alerts_settings', label:'告警设置', kind:'primary'},
          {type:'api', label:'发送测试消息', action:'alerts_test', kind:'primary', confirm:'将向你已配置的渠道发送一条测试消息。继续？'},
          alEnabled
            ? {type:'api', label:'关闭告警', action:'alerts_disable', kind:'danger', confirm:'确认关闭告警？关闭后异常将不再推送。'}
            : {type:'api', label:'开启告警', action:'alerts_enable', kind:'primary'},
          {type:'log', label:'告警日志', target:'alerts'},
          {type:'api', label:'打开配置文件', action:'alerts_open_config'},
          {type:'guide', label:'说明', title:'告警策略', text:
            '默认只在“运行异常”时推送（Docker/API/Tunnel/外网/前端）。\\n' +
            '为了避免刷屏：\\n' +
            '- 仅在状态变化（异常/恢复）时推送\\n' +
            '- 异常持续时按「重复提醒」间隔再提醒\\n' +
            '- 支持静默时段（夜间不打扰）\\n\\n' +
            '建议：先配置渠道 -> 发送测试 -> 再开启告警。'
          },
        ];
        cards.push({
          id:'alerts',
          group:'run',
          order:5,
          always:true,
          title:'告警',
          status: alStatus,
          value: alValue,
          sub: alSub,
          actions: alActions
        });

        const dockerActions = dockerOk ? [] : [
          {type:'todo', label:'待办清单', title:'Docker 引擎不可用', intro:'Docker 未启动会导致后端/数据库无法启动。按顺序做：', steps:[
            {title:'打开 Docker（或 OrbStack）', desc:'优先用下方一键打开；若未安装可先下载。', actions:[
              {type:'api', label:'打开 Docker', action:'open_docker', kind:'primary'},
              {type:'link', label:'下载 Docker', href:'https://www.docker.com/products/docker-desktop/'},
              {type:'link', label:'OrbStack', href:'https://orbstack.dev/'},
            ]},
            {title:'等待引擎就绪', desc:'通常 10-60 秒。看到「Docker 引擎」变绿即可。', actions:[{type:'refresh', label:'刷新', kind:'primary'}]},
            {title:'一键启动/修复', desc:'让后端/数据库/Redis 自动拉起。', actions:[{type:'api', label:'一键启动/修复', action:'docker_up', kind:'primary'}]},
          ]}
        ];
        cards.push({
          id:'docker',
          group:'run',
          order:10,
          title:'Docker 引擎',
          status: dockerOk ? 'ok' : 'bad',
          value: dockerOk ? '可用' : '不可用',
          sub: dockerMsg || (dockerOk ? '正常' : ''),
          actions: dockerActions
        });

        const portInfo = data && data.ports && data.ports.backend;
        const portNum = Number((portInfo && portInfo.port) || (data && data.api && data.api.local && data.api.local.port) || 0) || 18080;
        const pDocker = portInfo && portInfo.docker;
        const pHost = portInfo && portInfo.host;
        const dockerOwners = (pDocker && pDocker.ok && Array.isArray(pDocker.owners)) ? pDocker.owners.map(x => String(x || '')).filter(Boolean) : [];
        const hostListeners = (pHost && pHost.ok && Array.isArray(pHost.listeners)) ? pHost.listeners : [];
        const hostText = hostListeners.map(x => {
          const cmd = String((x && x.cmd) || '').trim() || '未知进程';
          const pid = Number((x && x.pid) || 0) || 0;
          return pid ? (cmd + '(' + pid + ')') : cmd;
        }).filter(Boolean).join(', ');

        const homeOwners = dockerOwners.filter(n => n.includes('deploy-backend'));
        const otherOwners = dockerOwners.filter(n => !homeOwners.includes(n));
        let portStatus = 'ok';
        let portValue = '正常';
        let portSub = '';
        if(!portInfo || !pDocker){
          portStatus = 'warn';
          portValue = '未知';
          portSub = '无法获取端口占用情况';
        }else if(hostListeners.length > 0 && dockerOwners.length === 0){
          portStatus = 'bad';
          portValue = '被占用';
          portSub = '占用：' + (hostText || '本机进程');
        }else if(!pDocker.ok){
          portStatus = 'warn';
          portValue = '未知';
          portSub = (pDocker && pDocker.msg) ? String(pDocker.msg) : '无法获取端口占用情况';
        }else if(dockerOwners.length === 0){
          portStatus = 'warn';
          portValue = '空闲';
          portSub = portNum + ' 无监听（后端可能未启动）';
        }else if(otherOwners.length === 0){
          portStatus = 'ok';
          portValue = '正常';
          // Always 卡片在 OK 状态下尽量安静（避免噪音）。
          portSub = '';
        }else{
          portStatus = 'bad';
          portValue = '被占用';
          portSub = '占用：' + dockerOwners.map(prettyContainerName).filter(Boolean).join('、');
        }
        const defaultBackendPort = 18080;
        // 交互收敛：有问题就只给「待办清单」一个入口；正常时仅保留最少的“改端口”入口。
        let portActions = [];
        if(portStatus !== 'ok'){
          const lsofCmd = 'lsof -nP -iTCP:' + portNum + ' -sTCP:LISTEN';
          const releaseActs = otherOwners.map(n => ({
            type:'api',
            label:'停止 ' + prettyContainerName(n),
            action:'docker_stop_container',
            service:n,
            kind:'danger',
            confirm:'将停止容器 ' + n + ' 以释放端口 ' + portNum + '（不删除数据）。继续？'
          }));
          if(releaseActs.length){
            releaseActs.push({type:'api', label:'重试启动/修复', action:'docker_up', kind:'primary'});
          }
          const steps = [
            {title:'先试一键修复（推荐）', desc:'会自动避让端口冲突并启动后端/数据库/Redis。', actions:[
              {type:'api', label:'启动/修复全部', action:'docker_up', kind:'primary'},
            ]},
          ];
          if(hostListeners.length > 0 && dockerOwners.length === 0){
            steps.push({title:'查看是谁占用了端口', desc:
              (hostText ? ('当前占用：' + hostText + '\\n\\n') : '') +
              '端口被本机进程占用，需要你手动关闭对应应用。\\n' +
              '检查指令：' + lsofCmd,
              actions:[
                {type:'copy', label:'复制检查指令', text:lsofCmd, kind:'primary'},
              ]
            });
          }
          if(releaseActs.length){
            steps.push({title:'释放端口（停止占用容器）', desc:'仅在你确定这些容器不是你需要的服务时再停止。', actions: releaseActs});
          }
          steps.push({title:'如需改端口（可选）', desc:'建议用 18080/18081/18082（不要用 80/443）。验证通过将立即生效（会重启后端）。', actions:[
            {type:'prompt', label:'设置后端端口…', action:'set_backend_port', prompt:'请输入后端端口（1024-65535）。验证通过将立即生效（会重启后端）。', def:String(portNum), kind:'primary'},
            {type:'api', label:'恢复默认（' + defaultBackendPort + '）', action:'set_backend_port', service:String(defaultBackendPort)},
          ]});
          steps.push({title:'确认恢复', desc:'看到「API 本机」变绿（200）即可。', actions:[{type:'refresh', label:'刷新', kind:'primary'}]});
          portActions = [{
            type:'todo',
            label:'待办清单',
            title:'后端端口异常',
            intro:'端口异常会导致后端启动失败/外网不可用。按顺序做：',
            steps
          }];
        }else{
          portActions = [
            {type:'prompt', label:'设置后端端口…', action:'set_backend_port', prompt:'请输入后端端口（1024-65535）。验证通过将立即生效（会重启后端）。', def:String(portNum), kind:'primary'},
          ];
          if(portNum !== defaultBackendPort){
            portActions.push({type:'api', label:'恢复默认（' + defaultBackendPort + '）', action:'set_backend_port', service:String(defaultBackendPort), confirm:'将恢复默认端口并重启后端。继续？'});
          }
        }
        cards.push({
          id:'port_backend',
          group:'run',
          order:20,
          always:true,
          title:'后端端口 ' + portNum,
          status: portStatus,
          value: portValue,
          sub: portSub,
          actions: portActions
        });

        const cfOk = !!(data && data.cloudflared && data.cloudflared.ok);
        const cfVer = (data && data.cloudflared && data.cloudflared.version) ? String(data.cloudflared.version) : '';
        const cfActions = cfOk ? [] : [
          {type:'todo', label:'待办清单', title:'Cloudflare 工具未就绪', intro:'外网通道依赖 cloudflared。按顺序做：', steps:[
            {title:'下载并启动', desc:'会下载到本项目 scripts/bin，不污染系统环境。', actions:[{type:'api', label:'下载并启动', action:'tunnel_start', kind:'primary'}]},
            {title:'确认已安装', desc:'回到本页刷新，本卡片变绿即可。', actions:[{type:'refresh', label:'刷新', kind:'primary'}]},
          ]}
        ];
        cards.push({
          id:'cloudflared',
          group:'setup',
          order:5,
          title:'Cloudflare 工具（外网所需）',
          status: cfOk ? 'ok' : 'warn',
          value: cfOk ? '已安装' : '未安装',
          sub: cfOk ? (cfVer || '—') : '缺少工具（会自动下载）',
          actions: cfActions
        });

        const tunnelAlive = !!(data && data.tunnel && data.tunnel.alive);
        const tunMode = (data && data.tunnel && data.tunnel.mode) ? String(data.tunnel.mode) : '-';
        const tunHost = (data && data.tunnel && data.tunnel.hostname) ? String(data.tunnel.hostname) : '';
        const tunUrl = (data && data.tunnel && data.tunnel.url) ? String(data.tunnel.url) : '';
        const tunCfg = (data && data.tunnel && data.tunnel.config) ? String(data.tunnel.config) : '';

        const tunIsQuick = (String(tunMode || '').toLowerCase() === 'quick');
        const tunCurl = 'curl -fsSL https://' + (tunHost || 'api.naibao.me') + '/api/health';
        let tunTodoSteps = tunIsQuick ? [
          {title:'更适合临时验收：用「手机外网验收」', desc:'会生成 trycloudflare 临时链接（链接会变化）。', actions:[
            {type:'api', label:'启动手机验收', action:'mobile_preview_start', kind:'primary'},
            {type:'log', label:'手机验收日志', target:'mobile_preview'},
          ]},
          {title:'想要长期稳定：改用固定域名（named）', desc:'完成「③ 固定域名」的待办后再启动外网通道。', actions:[{type:'refresh', label:'刷新', kind:'primary'}]},
        ] : [
          {title:'先确保「API 本机」变绿', desc:'本机 health 200 后再处理外网。', actions:[{type:'refresh', label:'刷新', kind:'primary'}]},
          {title: (tunCfg ? '确认已初始化固定外网' : '一键初始化固定外网（一次性）'), desc:'会打开浏览器完成 Cloudflare 授权，并生成配置文件。', actions:[
            {type:'api', label:'一键初始化', action:'named_tunnel_init', kind:'primary'},
            {type:'log', label:'初始化日志', target:'named_init'},
            {type:'link', label:'Cloudflare', href:'https://dash.cloudflare.com/'},
          ]},
          {title:'启动外网通道', desc:'启动后建议先看日志是否报错。', actions:[
            {type:'api', label:'启动', action:'tunnel_start', kind:'primary'},
            {type:'api', label:'重启', action:'tunnel_restart'},
            {type:'log', label:'通道日志', target:'tunnel'},
          ]},
          {title:'验证外网健康检查', desc:tunCurl, actions:[
            {type:'copy', label:'复制 curl', text:tunCurl, kind:'primary'},
            {type:'link', label:'打开 API', href:'https://' + (tunHost || 'api.naibao.me') + '/api/health'},
          ]},
        ];
        if(tunnelAlive){
          tunTodoSteps = tunTodoSteps.concat([
            {title:'停止外网通道（可选）', desc:'不需要外网时才停止。停止后外网 API 将不可用。', actions:[
              {type:'api', label:'停止外网通道', action:'tunnel_stop', kind:'danger', confirm:'确认停止外网通道？停止后外网 API 将不可用。'}
            ]}
          ]);
        }
        const tunTodo = {type:'todo', label:'待办清单', title:(tunIsQuick ? '临时外网（quick）' : '固定外网（named）'), intro:(tunIsQuick ? '临时外网链接会变且偶发不稳定。' : '固定外网适合长期线上访问。按顺序做：'), steps:tunTodoSteps};
        const tunModeZh = (String(tunMode || '').toLowerCase() === 'quick') ? '临时' : '固定';
        const tunCfgZh = tunCfg ? '已就绪' : '缺失';
        const tunWhere = (tunHost || '').trim() || (tunUrl ? String(tunUrl).replace(/^https?:\\/\\//,'') : '') || 'api.naibao.me';
        cards.push({
          id:'tunnel',
          group:'setup',
          order:50,
          title:'5. 外网通道',
          status: tunnelAlive ? 'ok' : 'bad',
          value: tunnelAlive ? '运行中' : '未运行',
          sub: `${tunModeZh} · ${tunWhere} · 配置${tunCfgZh}`,
          actions: [tunTodo]
        });

        const apiLocalOk = !!(data && data.api && data.api.local && data.api.local.ok);
        const apiLocalMsg = (data && data.api && data.api.local && data.api.local.msg) ? String(data.api.local.msg) : '';
        const apiLocalUrl = (data && data.api && data.api.local && data.api.local.url)
          ? String(data.api.local.url)
          : ('http://127.0.0.1:' + portNum + '/health');
        const apiLocalTodo = {type:'todo', label:'待办清单', title:'API 本机不可用', intro:'目标：让 ' + apiLocalUrl + ' 返回 200。按顺序做：', steps:[
          {title:'一键启动/修复', desc:'会自动处理端口冲突并拉起后端/数据库/Redis。', actions:[
            {type:'api', label:'启动/修复全部', action:'docker_up', kind:'primary'},
          ]},
          {title:'仍失败：重启后端', desc:'优先重启后端再观察。', actions:[
            {type:'api', label:'重启后端', action:'docker_restart', service:'backend', kind:'primary'},
          ]},
          {title:'查看后端日志', desc:'把报错内容复制给开发/AI 排查。', actions:[
            {type:'log', label:'后端日志', target:'docker', service:'backend', kind:'primary'},
            {type:'copy', label:'复制健康检查', text:'curl -fsSL ' + apiLocalUrl, kind:'primary'},
          ]},
          {title:'确认恢复', desc:'看到本卡片变绿（200）即可。', actions:[{type:'refresh', label:'刷新', kind:'primary'}]},
        ]};
        const apiLocalActions = apiLocalOk ? [
          {type:'log', label:'后端日志', target:'docker', service:'backend'}
        ] : [apiLocalTodo];
        cards.push({
          id:'api_local',
          group:'run',
          order:60,
          title:'API 本机',
          status: apiLocalOk ? 'ok' : 'bad',
          value: apiLocalOk ? '200 正常' : '不可用',
          sub: apiLocalOk ? apiLocalUrl : (apiLocalMsg || apiLocalUrl),
          actions: apiLocalActions
        });

        const pubUrl = (data && data.api && data.api.public && data.api.public.url) ? String(data.api.public.url) : '';
        const pubHealthUrl = pubUrl ? (pubUrl.replace(/\\/$/,'') + '/api/health') : '';
        const apiPublicOk = !!(data && data.api && data.api.public && data.api.public.ok);
        const apiPublicMsg = (data && data.api && data.api.public && data.api.public.msg) ? String(data.api.public.msg) : '';
        const apiPublicTodo = {type:'todo', label:'待办清单', title:'API 外网不可用', intro:'目标：让 ' + (pubUrl || 'https://api.naibao.me') + '/api/health 返回 200。按顺序做：', steps:[
          {title:'先确保「API 本机」变绿', desc:'外网问题前先把本机 health 跑通。', actions:[{type:'refresh', label:'刷新', kind:'primary'}]},
          {title:'重启外网通道', desc:'最常见的恢复方式。', actions:[
            {type:'api', label:'重启外网通道', action:'tunnel_restart', kind:'primary'},
            {type:'log', label:'通道日志', target:'tunnel'},
          ]},
          {title:'仍失败：一键修复后端', desc:'确保后端/端口无异常。', actions:[{type:'api', label:'启动/修复全部', action:'docker_up', kind:'primary'}]},
          {title:'验证外网健康检查', desc:'curl -fsSL ' + (pubUrl || 'https://api.naibao.me') + '/api/health', actions:[
            {type:'copy', label:'复制 curl', text:'curl -fsSL ' + (pubUrl || 'https://api.naibao.me') + '/api/health', kind:'primary'},
            {type:'link', label:'打开', href:(pubUrl ? (pubUrl + '/api/health') : '#')},
          ]},
        ]};
        const apiPublicActions = apiPublicOk ? [
          {type:'link', label:'打开健康检查', href: pubHealthUrl || '#', kind:'primary'},
          {type:'copy', label:'复制健康检查', text:'curl -fsSL ' + (pubUrl || 'https://api.naibao.me') + '/api/health'}
        ] : [apiPublicTodo];
        cards.push({
          id:'api_public',
          group:'setup',
          order:60,
          title:'6. API 外网',
          status: apiPublicOk ? 'ok' : 'bad',
          value: apiPublicOk ? '可访问' : '不可用',
          sub: apiPublicOk
            ? (pubUrl || '')
            : ((apiPublicMsg || '不可用') + (pubUrl ? (' · ' + pubUrl) : '')),
          actions: apiPublicActions
        });

        const zone = (data && data.dns && data.dns.zone) ? data.dns.zone : null;
        const zoneDomain = zone && zone.domain ? String(zone.domain) : '';
        const zoneNs = zone && zone.ns ? zone.ns : null;
        const nsOk = !!(zone && zone.cloudflare);
        const nsAnswers = (zoneNs && Array.isArray(zoneNs.answers)) ? zoneNs.answers.map(x => String(x||'').trim()).filter(Boolean) : [];
        const nsMsg = (zoneNs && zoneNs.msg) ? String(zoneNs.msg) : '';

        const git = (data && data.git) ? data.git : null;
        const ghRepo = (git && git.github) ? git.github : null;
        const ghRepoName = (ghRepo && ghRepo.owner && ghRepo.repo) ? (String(ghRepo.owner) + '/' + String(ghRepo.repo)) : '';
        const ghRepoUrl = (ghRepo && ghRepo.repo_url) ? String(ghRepo.repo_url) : '';
        const ghPagesUrl = (ghRepo && ghRepo.pages_settings_url) ? String(ghRepo.pages_settings_url) : 'https://github.com/settings/pages';
        const ghActionsUrl = (ghRepo && ghRepo.actions_url) ? String(ghRepo.actions_url) : (ghRepoUrl ? (ghRepoUrl + '/actions') : '');
        const ghPagesWfUrl = (ghRepo && ghRepo.pages_workflow_url) ? String(ghRepo.pages_workflow_url) : (ghRepoUrl ? (ghRepoUrl + '/actions/workflows/pages.yml') : '');
        const ghVerifiedUrl = zoneDomain ? ('https://github.com/settings/pages_verified_domains/' + zoneDomain) : 'https://github.com/settings/pages_verified_domains';

        // GitHub publish (commit + push) to trigger Pages auto-deploy.
        const gitBranch = (git && git.branch) ? String(git.branch) : '';
        const gitAhead = Number((git && git.ahead) || 0) || 0;
        const gitBehind = Number((git && git.behind) || 0) || 0;
        const scopes = (git && git.scopes) ? git.scopes : null;
        const wfScope = (scopes && scopes.workflow) ? scopes.workflow : null;
        const feScope = (scopes && scopes.frontend) ? scopes.frontend : null;
        const wfOnOrigin = !!(wfScope && wfScope.on_origin);
        const wfCnt = Number((wfScope && wfScope.count) || 0) || 0;
        const feCnt = Number((feScope && feScope.count) || 0) || 0;
        const wfFiles = (wfScope && Array.isArray(wfScope.files)) ? wfScope.files.map(x => String(x||'').trim()).filter(Boolean) : [];
        const feFiles = (feScope && Array.isArray(feScope.files)) ? feScope.files.map(x => String(x||'').trim()).filter(Boolean) : [];

        const hasRepo = !!ghRepoUrl;
        let pubStatus = 'warn';
        let pubValue = '可发布';
        let pubNote = '';
        if(!hasRepo){
          pubStatus = 'warn';
          pubValue = '未识别仓库';
          pubNote = '未检测到 GitHub 仓库 origin（请确认 git remote origin 已配置）';
        }else if(gitBranch && gitBranch !== 'main'){
          pubStatus = 'warn';
          pubValue = '需切回 main';
          pubNote = '当前分支：' + gitBranch;
        }else if(!wfOnOrigin){
          pubStatus = 'bad';
          pubValue = '自动部署未启用';
          pubNote = '需要先提交部署工作流（否则不会自动部署）';
        }else if(gitBehind > 0){
          pubStatus = 'warn';
          pubValue = '远端有更新';
          pubNote = '本机落后 ' + gitBehind + ' 个提交，推送可能失败（需先拉取/处理冲突）';
        }else if(wfCnt > 0 || feCnt > 0 || gitAhead > 0){
          pubStatus = 'warn';
          pubValue = '有更新待发布';
          pubNote = '前端改动 ' + feCnt + ' · 工作流改动 ' + wfCnt + ' · ahead ' + gitAhead;
        }else{
          pubStatus = 'ok';
          pubValue = '已同步';
          pubNote = '已开启自动部署';
        }

        const pad2 = (n) => String(n).padStart(2, '0');
        const now = new Date();
        const ts = now.getFullYear() + '-' + pad2(now.getMonth()+1) + '-' + pad2(now.getDate()) + ' ' + pad2(now.getHours()) + ':' + pad2(now.getMinutes());
        const wfState = wfOnOrigin ? '已完成' : '未完成';
        const syncLine = '同步：ahead ' + gitAhead + ' / behind ' + gitBehind;
        const changeLine = '待发布：前端 ' + feCnt + ' · 工作流 ' + wfCnt;
        const wfDesc = '部署工作流文件：.github/workflows/pages.yml';
        const feDesc = '会提交：frontend/src + 关键配置文件（不会提交 dist/.env/node_modules）';

        const gitSnapshot = [
          '仓库：' + (ghRepoName || '—'),
          '分支：' + (gitBranch || '—'),
          syncLine,
          '自动部署工作流：' + wfState,
          changeLine,
          '时间：' + ts,
        ].join('\\n');

        const stateFields = [
          {label:'仓库', value:(ghRepoName || '—'), mono:true},
          {label:'分支', value:(gitBranch || '—'), mono:true},
          {label:'同步', value:('ahead ' + gitAhead + ' / behind ' + gitBehind), mono:true},
          {label:'自动部署', value: wfState, mono:true},
          {label:'待发布', value: ('前端 ' + feCnt + ' · 工作流 ' + wfCnt), mono:true},
        ];
        if(wfFiles.length){ stateFields.push({label:'工作流改动(摘要)', value: wfFiles.join('\\n'), mono:true}); }
        if(feFiles.length){ stateFields.push({label:'前端改动(摘要)', value: feFiles.join('\\n'), mono:true}); }

        const pubSteps = [];

        pubSteps.push({
          title:'当前 Git 状态',
          pin:true,
          status:'ok',
          desc:'这是运营台将要用来发布的范围摘要（避免误提交）。',
          fields: stateFields,
          actions:[
            {type:'copy', label:'一键复制状态', text: gitSnapshot, kind:'primary'},
            {type:'log', label:'查看完整 Git 状态', target:'git', service:''},
          ]
        });

        if(gitBranch && gitBranch !== 'main'){
          pubSteps.push({
            title:'切回 main 分支',
            status:'warn',
            desc:'发布动作只允许在 main 上执行（避免把部署发到错误分支）。',
            actions:[
              {type:'copy', label:'复制指令', text:'git checkout main', kind:'primary'},
            ]
          });
        }

        if(gitBehind > 0){
          pubSteps.push({
            title:'先同步远端更新',
            status:'warn',
            desc:'远端有更新，推送可能会被拒绝（non-fast-forward）。',
            actions:[
              {type:'copy', label:'复制指令', text:'git pull --rebase origin main', kind:'primary'},
            ]
          });
        }

        const wfStepStatus = (!hasRepo) ? 'warn' : (wfOnOrigin ? (wfCnt > 0 ? 'warn' : 'ok') : 'bad');
        const wfStepTitle = wfOnOrigin ? '部署工作流（一次性）已完成' : '部署工作流（一次性）';
        const wfStepDesc = (!wfOnOrigin)
          ? ('未完成（阻塞自动部署）。\\n完成后：你每次“发布前端更新”，GitHub Pages 会自动上线 https://' + ghDomain)
          : (wfCnt > 0 ? ('检测到部署工作流有改动，建议发布一次。\\n' + wfDesc) : ('已完成，无需再操作。\\n' + wfDesc));
        const wfStepActs = [];
        if(!wfOnOrigin || wfCnt > 0){
          wfStepActs.push({
            type:'api', label:'提交部署工作流', action:'git_publish_workflow', kind:'primary',
            confirm:'将提交并推送：.github/workflows/pages.yml\\n\\n提交说明会自动生成（含完整修改日志）。\\n\\n继续？'
          });
        }
        wfStepActs.push({type:'link', label:'打开部署工作流', href:(ghPagesWfUrl || ghActionsUrl || ghRepoUrl || 'https://github.com/'), kind:'primary'});
        wfStepActs.push({type:'log', label:'查看工作流改动', target:'git', service:'workflow'});
        pubSteps.push({title:wfStepTitle, status:wfStepStatus, desc:wfStepDesc, actions:wfStepActs});

        // Frontend publish step
        let feStepStatus = 'ok';
        let feStepDesc = '当前无前端改动，无需发布。';
        const feStepActs = [];
        if(!wfOnOrigin){
          feStepStatus = 'warn';
          feStepDesc = '请先完成「部署工作流（一次性）」，否则推送前端不会自动部署到 Pages。';
        }else if(gitBehind > 0){
          feStepStatus = 'warn';
          feStepDesc = '请先同步远端更新，再发布前端（避免推送失败）。';
        }else if(feCnt > 0 || gitAhead > 0){
          feStepStatus = 'warn';
          feStepDesc = feDesc + (feFiles.length ? ('\\n\\n检测到改动（摘要）：\\n' + feFiles.join('\\n')) : '');
          feStepActs.push({
            type:'api', label:'发布前端更新', action:'git_publish_frontend', kind:'primary',
            confirm:'将提交并推送前端更新到 GitHub（触发 Pages 自动部署）。\\n\\n提交说明会自动生成（含完整修改日志）。\\n\\n继续？'
          });
          feStepActs.push({type:'log', label:'查看前端改动', target:'git', service:'frontend'});
        }
        pubSteps.push({title: (feStepStatus === 'ok' ? '发布前端更新（已完成）' : '发布前端更新'), status:feStepStatus, desc:feStepDesc, actions:feStepActs});

        pubSteps.push({title:'查看部署进度', status:'ok', desc:'推送后 1-3 分钟通常能看到构建/发布结果。', actions:[
          {type:'link', label:'打开 Actions', href:(ghActionsUrl || 'https://github.com/'), kind:'primary'},
          {type:'link', label:'打开 Pages 设置', href: ghPagesUrl},
        ]});

        const pubTodo = {type:'todo', label:'待办清单', title:'发布到 GitHub（自动部署前端）', intro:'目标：把本机改动推送到 GitHub，并触发 Pages 自动部署。按顺序做：', steps: pubSteps};
        const pubSub = (ghRepoName ? (ghRepoName + ' · ') : '') + ('自动部署：' + wfState + ' · ' + changeLine + ' · ' + syncLine);
        cards.push({
          id:'gh_publish',
          group:'setup',
          order:17,
          always:true,
          title:'GitHub：发布更新',
          status: pubStatus,
          value: pubValue,
          sub: pubSub,
          actions: [pubTodo]
        });

        const needCf = String(tunMode || 'named').toLowerCase() !== 'quick';
        const nsStatus = nsOk ? 'ok' : (needCf ? 'bad' : 'warn');
        const nsValue = nsOk
          ? '已完成'
          : (needCf ? '未接入（阻塞固定域名）' : (nsAnswers.length ? '当前非 Cloudflare' : '未知'));
        const nsProvider = (() => {
          const s = (nsAnswers || []).join(" ").toLowerCase();
          if(!s){ return '未知'; }
          if(s.includes('cloudflare')){ return 'Cloudflare'; }
          if(s.includes('spaceship') || s.includes('launch')){ return 'Spaceship'; }
          return '其它';
        })();
        const nsTodo = {type:'todo', label:'待办清单', title:'域名托管未接入 Cloudflare', intro:'这一步只做一次：把域名 DNS 托管交给 Cloudflare。按顺序做：', steps:[
          {title:'在 Cloudflare 添加站点', desc:'域名：' + (zoneDomain || '—') + '\\n（Add site -> 输入域名）', actions:[
            {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/', kind:'primary'},
            {type:'copy', label:'复制域名', text: zoneDomain},
          ]},
          {title:'复制 Cloudflare 提供的两条 Nameserver(NS)', desc:
            '添加完成后会显示两条 NS（类似 xxx.ns.cloudflare.com）。先复制备用。\\n' +
            '注意：Cloudflare 给的 NS 一定是 *.ns.cloudflare.com；如果你看到 launch1/launch2.spaceship.net，说明你还在 Spaceship 页面（不要把它们填回 Cloudflare）。',
            actions:[]},
          {title:'到 Spaceship 修改 Nameservers', desc:'路径：Domains -> ' + (zoneDomain || '') + ' -> Nameservers -> Custom\\n把上一步两条 NS 填进去并保存。', actions:[
            {type:'link', label:'打开 Spaceship', href:'https://www.spaceship.com/', kind:'primary'},
          ]},
          {title:'等待生效并刷新', desc:'通常 5-30 分钟。本卡片变绿即完成。\\n当前 NS：' + (nsAnswers.length ? nsAnswers.join('\\n') : (nsMsg || '—')), actions:[
            {type:'refresh', label:'刷新', kind:'primary'},
            {type:'copy', label:'复制检查指令', text: zoneDomain ? ('dig +short NS ' + zoneDomain) : ''},
          ]},
        ]};
        const nsActions = (!nsOk && needCf) ? [nsTodo] : [];
        cards.push({
          id:'dns_ns',
          group:'setup',
          order:10,
          title:'1. 域名托管（NS）',
          status: nsStatus,
          value: nsValue,
          sub: zoneDomain ? (zoneDomain + ' · 当前：' + nsProvider) : (nsMsg || '—'),
          actions: nsActions
        });

        const zoneA = zone && zone.a ? zone.a : null;
        const aAnswers = (zoneA && Array.isArray(zoneA.answers)) ? zoneA.answers.map(x => String(x||'').trim()).filter(Boolean) : [];
        const aMsg = (zoneA && zoneA.msg) ? String(zoneA.msg) : '';
        const ghA = ['185.199.108.153','185.199.109.153','185.199.110.153','185.199.111.153'];
        const matchA = ghA.filter(ip => aAnswers.includes(ip)).length;
        let aStatus = 'warn';
        let aValue = '待检查';
        if(matchA === ghA.length){
          aStatus = 'ok';
          aValue = '已指向 GitHub Pages';
        }else if(matchA > 0){
          aStatus = 'warn';
          aValue = '部分指向 GitHub Pages';
        }else if(aAnswers.length){
          aStatus = 'bad';
          aValue = '可能未指向 GitHub Pages';
        }

        // GitHub: one place to set everything (Pages / Custom domain / HTTPS / TXT verify).
        const feOkForGh = !!(data && data.frontend && data.frontend.ok);
        const ghDomain = zoneDomain || 'naibao.me';
        let ghBatchStatus = 'warn';
        let ghBatchValue = '待设置';
        let ghBatchSub = (ghRepoName ? (ghRepoName + ' · ') : '');
        if(!ghRepoUrl){
          ghBatchStatus = 'warn';
          ghBatchValue = '未识别仓库';
          ghBatchSub = '未识别到 GitHub 仓库 origin（请确保本仓库配置了 remote: origin）';
        }else if(feOkForGh){
          ghBatchStatus = 'ok';
          ghBatchValue = '已完成';
          ghBatchSub += 'Pages 已部署';
        }else if(matchA === ghA.length){
          ghBatchStatus = 'warn';
          ghBatchValue = '待生效';
          ghBatchSub += 'DNS 已指向，等待 Pages/HTTPS';
        }else{
          ghBatchStatus = 'warn';
          ghBatchValue = '可预设';
          ghBatchSub += '先配 Cloudflare DNS，再绑定域名';
        }
        const ghChecklist = [
          ('GitHub Pages 设置清单（' + (ghRepoName || '本仓库') + '）'),
          '',
          'Source: GitHub Actions',
          ('Custom domain: ' + ghDomain),
          'Enforce HTTPS: 打开',
          ('Pages 设置: ' + ghPagesUrl),
          ('部署工作流: ' + (ghPagesWfUrl || ghActionsUrl || ghRepoUrl || 'https://github.com/')),
        ].join('\\n');
        const ghSteps = [
          {title:'打开仓库 Pages 设置', desc:'路径：仓库 Settings -> Pages', actions:[
            {type:'link', label:'打开 Pages 设置', href: ghPagesUrl, kind:'primary'},
            {type:'link', label:'打开仓库', href: (ghRepoUrl || 'https://github.com/')}
          ]},
          {title:'配置 Pages（关键）', desc:
            'Source：GitHub Actions\\n' +
            'Custom domain：' + ghDomain + '\\n' +
            'DNS 生效后：打开 Enforce HTTPS',
            fields:[
              {label:'Source', value:'GitHub Actions', mono:true},
              {label:'Custom domain', value:ghDomain, mono:true},
              {label:'Enforce HTTPS', value:'打开', mono:true},
            ],
            actions:[
              {type:'copy', label:'复制域名', text: ghDomain, kind:'primary'},
              {type:'copy', label:'复制清单', text: ghChecklist},
            ]
          },
          {title:'若提示添加 DNS TXT 验证（常见）', desc:
            '这是 GitHub 的域名所有权验证（账号级/全局配置，合理）。\\n' +
            '按 GitHub 页面提示复制「记录名」和「值」，回 Cloudflare DNS 添加 TXT 即可。',
            fields:[
              {label:'类型', value:'TXT', mono:true},
              {label:'记录名', value:'_github-pages-challenge-<你的GitHub用户名>', mono:true},
              {label:'值', value:'从 GitHub 页面复制的一串校验码', mono:true},
            ],
            actions:[
              {type:'link', label:'打开 Verified domains', href: ghVerifiedUrl, kind:'primary'},
              {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/'},
            ]
          },
          {title:'部署一直不生效？先看日志（可选）', desc:'通常能看到 DNS/证书/构建失败的原因。', actions:[
            {type:'link', label:'打开部署工作流', href: (ghPagesWfUrl || ghActionsUrl || ghRepoUrl || 'https://github.com/'), kind:'primary'},
            {type:'link', label:'打开 Actions', href: (ghActionsUrl || ghRepoUrl || 'https://github.com/')},
          ]},
          {title:'回运营台刷新验证', desc:'看到「前端（H5）」变绿即可。', actions:[
            {type:'refresh', label:'刷新', kind:'primary'},
          ]},
        ];
        const ghBatchTodo = {type:'todo', label:'待办清单', title:'GitHub Pages（一次配完）', intro:'把需要在 GitHub 里设置的内容集中到一处：Pages 源/自定义域名/HTTPS/（可选）TXT 验证。', steps: ghSteps};
        cards.push({
          id:'gh_pages_batch',
          group:'setup',
          order:18,
          title:'3. GitHub Pages（一次配完）',
          status: ghBatchStatus,
          value: ghBatchValue,
          sub: ghBatchSub,
          actions: [ghBatchTodo]
        });

        const wwwRec = (data && data.dns && data.dns.www) ? data.dns.www : null;
        const wwwHost = wwwRec && wwwRec.hostname ? String(wwwRec.hostname) : (zoneDomain ? ('www.' + zoneDomain) : '');
        const wwwCn = wwwRec && wwwRec.cname ? wwwRec.cname : null;
        const wwwAnswers = (wwwCn && Array.isArray(wwwCn.answers)) ? wwwCn.answers.map(x => String(x||'').trim()).filter(Boolean) : [];
        const wwwOk = wwwAnswers.some(x => x.replace(/\\.$/,'') === zoneDomain) || wwwAnswers.some(x => x.toLowerCase().includes('.github.io'));

        const fe = (data && data.frontend) ? data.frontend : null;
        const feUrl = fe && fe.url ? String(fe.url) : '';
        const feOk = !!(fe && fe.ok);
        const feMsg = fe && fe.msg ? String(fe.msg) : '';
        const feTodo = {type:'todo', label:'待办清单', title:'前端不可访问', intro:'目标：让 ' + (feUrl || 'https://naibao.me') + ' 能正常打开。按顺序做：', steps:[
          {title:'先完成「2. Cloudflare DNS（一次配完）」', desc:'把 A / www /（可选）TXT 一次配齐。', actions:[
            {type:'refresh', label:'我已配置，刷新', kind:'primary'}
          ]},
          {title:'再完成「3. GitHub Pages（一次配完）」', desc:'在 GitHub Pages 绑定域名并打开 Enforce HTTPS。', actions:[
            {type:'refresh', label:'我已配置，刷新', kind:'primary'}
          ]},
          {title:'等待生效', desc:'DNS/证书通常需要 5-30 分钟。期间可反复刷新。', actions:[
            {type:'refresh', label:'刷新', kind:'primary'}
          ]},
        ]};
        const feActions = feOk ? [
          {type:'link', label:'打开', href: feUrl || '#', kind:'primary'},
          {type:'copy', label:'复制链接', text: feUrl}
        ] : [feTodo];
        cards.push({
          id:'frontend',
          group:'setup',
          order:70,
          title:'7. 前端（H5）',
          status: feOk ? 'ok' : 'warn',
          value: feOk ? '可访问' : '不可访问',
          sub: feUrl || (feMsg || ''),
          actions: feActions
        });

        const mp = (data && data.mobile_preview) ? data.mobile_preview : null;
        const mpUrl = mp && mp.url ? String(mp.url) : '';
        const mpStarterAlive = !!(mp && mp.starter_alive);
        const mpTunAlive = !!(mp && mp.tunnel_alive);
        const mpOk = !!(mp && mp.ok) && !!mpUrl && mpTunAlive;
        const mpStale = !!(mp && mp.ok) && !!mpUrl && !mpTunAlive;
        const mpStatus = mpOk ? 'ok' : (mpStarterAlive ? 'warn' : (mpStale ? 'warn' : 'warn'));
        const mpValue = mpOk ? '已就绪' : (mpStarterAlive ? '启动中' : (mpStale ? '可能已过期' : '未启动'));
        const mpSub = mpUrl
          ? (mpUrl + (mpOk ? '' : (mpStale ? ' · 通道未在运行' : '')))
          : '用于手机外网验收（临时域名，可能不稳定）';
        const mpTodo = {type:'todo', label:'待办清单', title:'手机外网验收（临时域名）', intro:'用途：生成一个临时外网链接给手机验收（链接会变化）。按顺序做：', steps:[
          {title:'一键启动', desc:'会启动后端 + 前端 dev server + cloudflared 通道。', actions:[
            {type:'api', label:'一键启动', action:'mobile_preview_start', kind:'primary'},
            {type:'log', label:'日志', target:'mobile_preview'},
          ]},
          {title:'打开/复制链接', desc:(mpUrl ? ('当前链接：' + mpUrl + '\\n文件：frontend/mobile-preview.url') : '启动后会生成链接并写入 frontend/mobile-preview.url'), actions:(mpUrl ? [
            {type:'link', label:'打开', href: mpUrl, kind:'primary'},
            {type:'copy', label:'复制链接', text: mpUrl, kind:'primary'},
          ] : [{type:'refresh', label:'刷新', kind:'primary'}])},
          {title:'如果看到“NO tunnel here/空白页”', desc:'先重启通道；再看日志。', actions:[
            {type:'api', label:'一键重启', action:'mobile_preview_restart', kind:'primary'},
            {type:'log', label:'日志', target:'mobile_preview'},
          ]},
          {title:'停止验收（可选）', desc:'验收完成后建议停止，避免长时间占用资源。', actions:[
            {type:'api', label:'停止', action:'mobile_preview_stop', kind:'danger', confirm:'确认停止手机外网验收？停止后链接将不可用。'},
          ]},
        ]};
        cards.push({
          id:'mobile_preview',
          group:'mobile',
          order:10,
          always:true,
          title:'手机外网验收',
          status: mpStatus,
          value: mpValue,
          sub: mpSub,
          actions: [mpTodo]
        });

        const apiRec = (data && data.dns && data.dns.api_record) ? data.dns.api_record : null;
        const apiHost = apiRec && apiRec.hostname ? String(apiRec.hostname) : '';
        const apiDns = (data && data.dns && data.dns.api) ? data.dns.api : null;
        const apiIps = (apiDns && Array.isArray(apiDns.ips)) ? apiDns.ips.map(x => String(x||'').trim()).filter(Boolean) : [];
        const apiDnsMsg = (apiDns && apiDns.msg) ? String(apiDns.msg) : '';
        const apiDnsOk = !!(apiDns && apiDns.ok);

        const needNamed = String(tunMode || 'named').toLowerCase() !== 'quick';
        const named = (data && data.named_init) ? data.named_init : null;
	        const initAlive = !!(named && named.alive);
	        const initPid = Number((named && named.pid) || 0) || 0;
	        const cfgOk = !!(named && named.config_ok);
	        const credOk = !!(named && named.credentials_ok);
	        const certOk = !!(named && named.cert_ok);
	        const tunId = (named && named.tunnel_id) ? String(named.tunnel_id) : '';
	        const apiHas1014 = (!apiPublicOk) && String(apiPublicMsg || '').includes('1014');

        let apiCnStatus = 'ok';
        let apiCnValue = '已初始化';
        if(!needNamed){
          apiCnStatus = 'warn';
          apiCnValue = '可跳过（临时外网）';
        }else if(initAlive){
          apiCnStatus = 'warn';
          apiCnValue = '初始化中';
        }else if(cfgOk){
          apiCnStatus = apiHas1014 ? 'warn' : 'ok';
          apiCnValue = apiHas1014 ? '已初始化，但 Cloudflare 报 1014' : '已初始化';
	        }else{
	          apiCnStatus = 'bad';
	          apiCnValue = '未初始化（阻塞固定外网）';
	        }
	        const initLine = initAlive ? ('初始化中（pid=' + initPid + '），请完成浏览器授权') : '';
	        const dnsLine = 'DNS：' + (apiDnsOk ? '可解析' : '未解析');
	        const authLine = '授权：' + (certOk ? '已完成' : '未完成');
	        const cfgLine = '配置：' + (cfgOk ? '已生成' : '未生成') + (credOk || !cfgOk ? '' : ' · 凭据缺失');
	        const tidLine = tunId ? (' · tunnel：' + tunId.slice(0, 8) + '…') : '';
	        const cfLine = apiHas1014 ? ' · Cloudflare：1014' : '';
	        const subLine = (initLine ? (initLine + ' · ') : '') +
	          (apiHost ? (apiHost + ' · ') : '') +
	          (dnsLine + ' · ' + authLine + ' · ' + cfgLine + tidLine + cfLine);
	
	        const apiInitConfirm =
	          '将执行「固定外网初始化（一次性）」：\\n' +
	          '- 打开浏览器进行 Cloudflare 授权/登录\\n' +
	          '- 创建/复用 Tunnel，并可能修改 Cloudflare DNS（' + (apiHost || 'api.naibao.me') + '）\\n' +
	          '- 在本机生成配置文件（.naibao_runtime/cloudflared_named.yml）\\n\\n' +
	          '继续？';
	        const apiInitTodo = {type:'todo', label:'待办清单', title:'固定外网初始化（一次性）', intro:'目标：让 ' + (apiHost || 'api.naibao.me') + ' 绑定到 Cloudflare Tunnel，并生成配置文件。按顺序做：', steps:[
	          {title:'先让「1. 域名托管（NS）」变绿', desc:'否则 Cloudflare 可能无法写入 DNS 记录。', actions:[
	            {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/', kind:'primary'},
	            {type:'link', label:'打开 Spaceship', href:'https://www.spaceship.com/'},
	            {type:'refresh', label:'刷新', kind:'primary'},
	          ]},
	          {title:'点击「一键初始化」', desc:'会打开浏览器完成 Cloudflare 授权/登录，并在本机生成：.naibao_runtime/cloudflared_named.yml', actions:[
	            {type:'api', label:(cfgOk ? '重新初始化' : '一键初始化'), action:'named_tunnel_init', kind:'primary', confirm: apiInitConfirm},
	            {type:'log', label:'初始化日志', target:'named_init', kind:'primary'},
	          ]},
          {title:'如果看到 Cloudflare 1014', desc:
            '打开 https://' + (apiHost || 'api.naibao.me') + '/api/health 如果出现 1014，通常是 api 还没绑定到 Tunnel（route dns 未完成/账号不一致）。\\n\\n' +
            '处理方式：重新点一次「一键初始化」，并确保登录的是拥有 ' + (zoneDomain || 'naibao.me') + ' 的 Cloudflare 账号。\\n\\n' +
            '当前解析（A/AAAA，橙云会显示 Cloudflare IP，属正常）：\\n' + (apiIps.length ? apiIps.join('\\n') : (apiDnsMsg || '—')),
            actions:[
              {type:'link', label:'打开健康检查', href:'https://' + (apiHost || 'api.naibao.me') + '/api/health', kind:'primary'},
              {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/'},
            ]
          },
	          {title:'启动外网通道', desc:'初始化完成后到「5. 外网通道」点启动。', actions:[
	            {type:'api', label:'启动外网通道', action:'tunnel_start', kind:'primary'},
	            {type:'log', label:'通道日志', target:'tunnel'},
	          ]},
	          {title:'验证外网健康', desc:'curl -fsSL https://' + (apiHost || 'api.naibao.me') + '/api/health', actions:[
	            {type:'copy', label:'复制 curl', text:'curl -fsSL https://' + (apiHost || 'api.naibao.me') + '/api/health', kind:'primary'},
	            {type:'link', label:'打开', href:'https://' + (apiHost || 'api.naibao.me') + '/api/health'},
	          ]},
	        ]};
	        const apiInitActions = (needNamed && apiCnStatus !== 'ok') ? [apiInitTodo] : [];
	
		        cards.push({
		          id:'dns_api_record',
		          group:'setup',
		          order:40,
		          title:'4. 固定外网初始化（一次性）',
		          status: apiCnStatus,
		          value: apiCnValue,
		          sub: subLine,
		          actions: apiInitActions
		        });

            // Cloudflare DNS: one place to set everything (A / www / TXT / api).
            const ghOk2 = (matchA === ghA.length);
            const wwwOk2 = !!wwwOk;
            const apiNeed2 = !!needNamed;
            // api 记录通常由第 4 步（route dns）自动创建；当出现 1014 或解析不到时才提示“需要处理”。
            const apiNeedFix2 = apiNeed2 && !!tunId && (!apiDnsOk || apiHas1014);
            const missingCf = [];
            if(!ghOk2){ missingCf.push('A'); }
            if(!wwwOk2){ missingCf.push('www'); }
            if(apiNeedFix2){ missingCf.push('api'); }

            let cfBatchStatus = missingCf.length ? 'warn' : 'ok';
            let cfBatchValue = missingCf.length ? '待设置' : '已完成';
            let cfBatchSub = (zoneDomain || '') ? (zoneDomain + ' · ') : '';
            if(needCf && !nsOk){
              cfBatchStatus = 'warn';
              cfBatchValue = missingCf.length ? '可预设' : '已设置，待激活';
              cfBatchSub += 'NS 未切到 Cloudflare';
            }else if(missingCf.length){
              cfBatchSub += ('缺：' + missingCf.join('、'));
            }else{
              cfBatchSub += '一次配置即可';
            }
            if(apiNeed2 && !tunId){
              cfBatchSub += ' · api 由第 4 步生成';
            }

            const ghRoot = zoneDomain || 'naibao.me';
            const apiTargetForCopy = tunId ? (tunId + '.cfargotunnel.com') : '';
            const cfChecklistLines = [
              ('Cloudflare DNS 清单（' + ghRoot + '）'),
              '',
              ('A ' + ghRoot + ' -> ' + ghA.join(', ')),
              ('CNAME www -> ' + ghRoot),
              ('TXT（若 GitHub 提示）_github-pages-challenge-<username> -> <code>'),
            ];
            if(apiNeed2){
              if(apiTargetForCopy){
                cfChecklistLines.push('CNAME api -> ' + apiTargetForCopy + '（代理：橙云）');
              }else{
                cfChecklistLines.push('CNAME api -> （先完成第 4 步「固定外网初始化」后自动生成）');
              }
            }
            const cfChecklist = cfChecklistLines.join('\\n');
            const cfTodoSteps = [
              {title:'打开 Cloudflare DNS', desc:'把下面的记录一次填完（建议用 DNS only/灰云）。', actions:[
                {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/', kind:'primary'},
                {type:'copy', label:'复制清单', text: cfChecklist},
              ]},
              {title:'前端：根域 A（GitHub Pages）', desc:'删除其它 A/AAAA，只保留这 4 条 A（DNS only/灰云）。这 4 个 IP 是 GitHub Pages 固定值，不是你的电脑 IP。', fields:[
                {label:'记录名', value:ghRoot, mono:true},
                {label:'类型', value:'A（4 条）', mono:true},
                {label:'代理', value:'DNS only（灰云）', mono:true},
                {label:'值', value:ghA.join('\\n'), mono:true},
              ], actions:[
                {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/', kind:'primary'},
              ]},
              {title:'前端：www CNAME', desc:'让用户输入 www.naibao.me 也能打开（DNS only/灰云）。', fields:[
                {label:'记录名', value:'www', mono:true},
                {label:'类型', value:'CNAME', mono:true},
                {label:'代理', value:'DNS only（灰云）', mono:true},
                {label:'目标', value:ghRoot, mono:true},
              ], actions:[
                {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/', kind:'primary'},
              ]},
              {title:'GitHub 验证 TXT（若提示）', desc:'只有当 GitHub Pages 提示验证域名时才需要添加。', fields:[
                {label:'类型', value:'TXT', mono:true},
                {label:'记录名', value:'_github-pages-challenge-<你的GitHub用户名>', mono:true},
                {label:'值', value:'从 GitHub 页面复制的一串校验码', mono:true},
              ], actions:[
                {type:'link', label:'打开 GitHub Pages 设置', href: ghPagesUrl, kind:'primary'},
                {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/', kind:'primary'},
              ]},
            ];
            if(apiNeed2){
              const apiTarget = tunId ? (tunId + '.cfargotunnel.com') : '（先完成第 4 步「固定外网初始化」后自动生成）';
              const apiHost2 = apiHost || (zoneDomain ? ('api.' + zoneDomain) : 'api.naibao.me');
              cfTodoSteps.push({title:'后端：api CNAME（Cloudflare Tunnel）', desc:
                '用于固定域名访问后端。通常第 4 步「固定外网初始化」会自动创建；若仍未生效再手动补。\\n' +
                (tunId ? '' : '\\n注意：还未生成 tunnel id，请先完成第 4 步，否则不要在 Cloudflare 手填占位符。'),
                fields:[
                  {label:'记录名', value:'api', mono:true},
                  {label:'类型', value:'CNAME', mono:true},
                  {label:'代理', value:'已代理（橙云）', mono:true},
                  {label:'目标', value:apiTarget, mono:true},
                  {label:'验证', value:('curl -fsSL https://' + apiHost2 + '/api/health'), mono:true},
                  {label:'DNS 检查', value:('dig +short A ' + apiHost2), mono:true},
                ],
                actions:[
                  {type:'link', label:'打开 Cloudflare', href:'https://dash.cloudflare.com/', kind:'primary'},
                  {type:'link', label:'打开健康检查', href:('https://' + apiHost2 + '/api/health')},
                  {type:'copy', label:'复制验证指令', text:('curl -fsSL https://' + apiHost2 + '/api/health')},
                ]
              });
            }
            cfTodoSteps.push({title:'回运营台刷新验证', desc:'下面各卡片变绿即完成。', actions:[
              {type:'refresh', label:'刷新', kind:'primary'},
            ]});
            const cfBatchTodo = {type:'todo', label:'待办清单', title:'Cloudflare DNS（一次配完）', intro:'把需要在 Cloudflare DNS 里设置的内容集中到一处：A / www /（可选）TXT / api。', steps: cfTodoSteps};
            cards.push({
              id:'cf_dns_batch',
              group:'setup',
              order:15,
              title:'2. Cloudflare DNS（一次配完）',
              status: cfBatchStatus,
              value: cfBatchValue,
              sub: cfBatchSub,
              actions: [cfBatchTodo]
            });

	        const SVC_META = {
	          backend: {title:'核心服务 · 后端(API)', order:30},
	          db: {title:'核心服务 · 数据库', order:40},
	          redis: {title:'核心服务 · 缓存', order:50},
	        };
        ['backend','db','redis'].forEach(name => {
          const item = getSvc(name);
          const cls = classifyService(item);
          const acts = [];
          if(cls.status !== 'ok'){
            acts.push({type:'api', label:'重启', action:'docker_restart', service:name, kind:'primary'});
            acts.push({type:'api', label:'修复全部', action:'docker_up'});
          }else{
            acts.push({type:'api', label:'重启', action:'docker_restart', service:name});
          }
          acts.push({type:'log', label:'日志', target:'docker', service:name});
          const meta = SVC_META[name] || {title:('服务 · ' + name), order:30};
          cards.push({
            id:'svc_' + name,
            group:'run',
            order: meta.order,
            title: meta.title,
            status: cls.status,
            value: cls.value,
            sub: cls.sub || '',
            actions: acts
          });
        });

        const disk = data && data.host && data.host.disk;
        if(disk && disk.ok){
          const freePct = Number(disk.free_pct || 0);
          let st = 'ok';
          if(freePct < 0.05){ st = 'bad'; }
          else if(freePct < 0.15){ st = 'warn'; }
          const acts = (st === 'ok') ? [] : [
            {type:'api', label:'清理 Docker 缓存', action:'docker_prune', kind:'primary', confirm:'将清理无用容器/网络/构建缓存（不会删除数据库 volume）。可能需要重新拉取镜像。继续？'}
          ];
          cards.push({
            id:'disk',
            group:'host',
            order:10,
            title:'磁盘',
            status: st,
            value: `剩余 ${fmtBytes(disk.free)} (${fmtPct(freePct)})`,
            sub: `${fmtBytes(disk.used)} / ${fmtBytes(disk.total)}`,
            actions: acts
          });
        }else{
          cards.push({id:'disk', group:'host', order:10, title:'磁盘', status:'warn', value:'—', sub:(disk && disk.msg) ? disk.msg : '无法获取', actions:[]});
        }

        const mem = data && data.host && data.host.mem;
        if(mem && mem.ok){
          const availPct = Number(mem.avail_pct || 0);
          let st = 'ok';
          if(availPct < 0.08){ st = 'bad'; }
          else if(availPct < 0.15){ st = 'warn'; }
          const acts = (st === 'ok') ? [] : [
            {type:'api', label:'重启全部', action:'docker_restart_all', kind:'primary', confirm:'内存紧张时建议先重启服务释放资源。继续重启全部？'}
          ];
          cards.push({
            id:'mem',
            group:'host',
            order:20,
            title:'内存',
            status: st,
            value: `可用 ${fmtBytes(mem.avail)} (${fmtPct(availPct)})`,
            sub: `总计 ${fmtBytes(mem.total)}${mem.note ? (' · ' + mem.note) : ''}`,
            actions: acts
          });
        }else{
          cards.push({id:'mem', group:'host', order:20, title:'内存', status:'warn', value:'—', sub:(mem && mem.msg) ? mem.msg : '无法获取', actions:[]});
        }

        const cpu = data && data.host && data.host.cpu;
        const cpuCount = Number((data && data.host && data.host.cpu_count) || 0) || (navigator.hardwareConcurrency || 0);
        if(cpu && cpu.ok){
          const load1 = Number(cpu.load1 || 0);
          let st = 'ok';
          if(cpuCount > 0){
            if(load1 > cpuCount * 2){ st = 'bad'; }
            else if(load1 > cpuCount * 1.2){ st = 'warn'; }
          }else{
            if(load1 > 8){ st = 'bad'; }
            else if(load1 > 4){ st = 'warn'; }
          }
          const acts = (st === 'ok') ? [] : [
            {type:'api', label:'重启后端', action:'docker_restart', service:'backend', kind:'primary', confirm:'负载过高时先重启后端观察是否恢复。继续？'}
          ];
          cards.push({
            id:'cpu',
            group:'host',
            order:30,
            title:'负载',
            status: st,
            value: `1分钟 ${load1.toFixed(2)} · 5分钟 ${(Number(cpu.load5 || 0)).toFixed(2)}`,
            sub: cpuCount ? ('CPU 核心 ' + cpuCount) : '',
            actions: acts
          });
        }else{
          cards.push({id:'cpu', group:'host', order:30, title:'负载', status:'warn', value:'—', sub:(cpu && cpu.msg) ? cpu.msg : '无法获取', actions:[]});
        }

        const up = data && data.host && data.host.uptime;
        if(up && up.ok){
          cards.push({
            id:'uptime',
            group:'host',
            order:40,
            title:'主机运行',
            status:'ok',
            value: fmtUptime(Number(up.uptime_s || 0)),
            sub: (data && data.host && data.host.platform) ? String(data.host.platform) : '',
            actions: []
          });
        }else{
          cards.push({id:'uptime', group:'host', order:40, title:'主机运行', status:'warn', value:'—', sub:(up && up.msg) ? up.msg : '', actions:[]});
        }

        const commit = (data && data.git && data.git.commit) ? String(data.git.commit) : '';
        const py = (data && data.host && data.host.python) ? String(data.host.python) : '';
        cards.push({id:'git', group:'host', order:50, title:'当前版本', status:'ok', value:(commit || '—'), sub:(py ? ('python ' + py) : ''), actions:[]});

        return cards;
      }

	      function updateOverall(cards){
	        let worst = 'ok';
	        let badCount = 0;
	        let warnCount = 0;
	        (cards || []).forEach(c => {
	          if(c.status === 'bad'){ badCount++; worst = 'bad'; }
	          else if(c.status === 'warn'){ warnCount++; if(worst !== 'bad'){ worst = 'warn'; } }
	        });
	        const pill = document.getElementById('overallPill');
	        pill.classList.remove('ok','warn','bad');
	        pill.classList.add(worst);
	        const todo = badCount + warnCount;
	        pill.textContent = todo > 0 ? ('待办 ' + todo) : '全部正常';
	      }

	      function closeSheet(){
	        document.getElementById('sheet').style.display = 'none';
	      }

	      function openSheet(card){
	        const sheet = document.getElementById('sheet');
	        const title = document.getElementById('sheetTitle');
	        const sub = document.getElementById('sheetSub');
	        const btns = document.getElementById('sheetBtns');
	        title.textContent = card && card.title ? String(card.title) : '—';
	        const v = (card && card.value) ? String(card.value).trim() : '';
	        const s = (card && card.sub) ? String(card.sub).trim() : '';
	        sub.textContent = [v, s].filter(Boolean).join(' · ') || '—';
	        btns.innerHTML = '';

	        const acts = Array.isArray(card && card.actions) ? card.actions : [];
	        if(acts.length === 0){
	          const b = document.createElement('button');
	          b.className = 'sheetBtn primary';
	          b.textContent = '知道了';
	          b.onclick = () => closeSheet();
	          btns.appendChild(b);
	        }else{
	          const primary = acts.filter(x => x && x.kind === 'primary');
	          const danger = acts.filter(x => x && x.kind === 'danger');
	          const rest = acts.filter(x => x && x.kind !== 'primary' && x.kind !== 'danger');
	          const ordered = primary.concat(rest).concat(danger);
	          ordered.forEach(x => {
	            const b = document.createElement('button');
	            b.className = 'sheetBtn ' + (x.kind || '');
	            b.textContent = x.label || '操作';
	            b.onclick = async () => {
	              // Copy doesn't need to close the sheet.
	              if(x.type === 'copy'){
	                await copyText(x.text || '');
	                return;
	              }
	              closeSheet();
	              handleAction(x);
	            };
	            btns.appendChild(b);
	          });
	        }
	        sheet.style.display = 'flex';
	      }

	      function cellEl(card){
	        const el = document.createElement('div');
	        el.className = 'cell ' + (card.status || 'ok');
	        el.onclick = () => {
	          lastCardId = String((card && card.id) || '').trim();
	          const acts = Array.isArray(card && card.actions) ? card.actions : [];
	          const todo = acts.find(x => x && x.type === 'todo');
	          if(todo){
	            handleAction(todo);
	            return;
	          }
	          openSheet(card);
	        };

	        const main = document.createElement('div');
	        main.className = 'cellMain';
	        const t = document.createElement('div');
	        t.className = 'cellTitle';
	        t.textContent = card.title || '—';
	        main.appendChild(t);

	        // Show sub text when:
	        // - not OK (need attention), OR
	        // - explicitly marked always, OR
	        // - user turned off "issues only" (wants full context)
	        const showSub = !!(card.sub && (String(card.status || 'ok') !== 'ok' || !!card.always || !issuesOnly));
	        if(showSub){
	          const s = document.createElement('div');
	          s.className = 'cellSub';
	          s.textContent = card.sub;
	          main.appendChild(s);
	        }

	        const right = document.createElement('div');
	        right.className = 'cellRight';
	        const dot = document.createElement('div');
	        dot.className = 'dot';
	        const v = document.createElement('div');
	        v.className = 'cellValue';
	        v.textContent = card.value || '—';
	        const chev = document.createElement('div');
	        chev.className = 'chev';
	        right.appendChild(dot);
	        right.appendChild(v);
	        right.appendChild(chev);

	        el.appendChild(main);
	        el.appendChild(right);
	        return el;
	      }

	      function groupStats(cardsIn){
	        const bad = (cardsIn || []).filter(x => x && x.status === 'bad').length;
	        const warn = (cardsIn || []).filter(x => x && x.status === 'warn').length;
	        const worst = bad ? 'bad' : (warn ? 'warn' : 'ok');
	        return {bad, warn, worst};
	      }

	      function groupPill(stats){
	        const s = stats || {bad:0, warn:0, worst:'ok'};
	        const pill = document.createElement('div');
	        pill.className = 'pill ' + (s.worst || 'ok');
	        pill.textContent = (s.bad || s.warn) ? ('待办 ' + ((s.bad || 0) + (s.warn || 0))) : '全部正常';
	        return pill;
	      }

	      function isCollapsed(groupId, stats){
	        if(Object.prototype.hasOwnProperty.call(collapsed, groupId)){
	          return !!collapsed[groupId];
	        }
	        // Default: keep only "run" open (avoid overwhelming novices with a wall of cards).
	        let c = true;
	        if(String(groupId) === 'run'){ c = false; }
	        collapsed[groupId] = c;
	        return c;
	      }

	      function toggleGroup(groupId){
	        collapsed[groupId] = !collapsed[groupId];
	        render(lastPreparedCards);
	      }

	      function render(cards){
	        const box = document.getElementById('metrics');
	        box.innerHTML = '';
	        const list = Array.isArray(cards) ? cards : [];
	        if(list.length === 0){
	          const empty = document.createElement('div');
	          empty.className = 'stepCard';
	          empty.appendChild(cellEl({status:'ok', title:'全部正常', value:'无需处理', sub:'当前没有红/橙指标。', actions:[]}));
	          box.appendChild(empty);
	          return;
	        }

	        // Group cards; user can follow ①→②→③ step-by-step.
	        const byGroup = {};
	        list.forEach(c => {
	          const gid = String((c && c.group) || '').trim() || 'other';
	          if(!byGroup[gid]){ byGroup[gid] = []; }
	          byGroup[gid].push(c);
	        });

          // Keep UI calm: don't auto-expand other groups even if they have issues.

	        const knownIds = new Set(GROUPS.map(g => g.id));

	        function renderGroup(g){
	          const cardsIn = byGroup[g.id] || [];
	          if(cardsIn.length === 0){ return; }
	          const stats = groupStats(cardsIn);
	          const collapsedNow = isCollapsed(g.id, stats);

	          const wrap = document.createElement('div');
	          wrap.className = 'step';

	          const head = document.createElement('div');
	          head.className = 'stepHead';
	          head.onclick = () => toggleGroup(g.id);

	          const left = document.createElement('div');
	          left.className = 'stepLeft';
	          const t = document.createElement('div');
	          t.className = 'stepTitle';
	          t.textContent = g.title || g.id || '—';
	          left.appendChild(t);

	          const d = String(g.desc || '').trim();
	          if(d){
	            const dd = document.createElement('div');
	            dd.className = 'stepDesc';
	            dd.textContent = d;
	            left.appendChild(dd);
	          }

	          const right = document.createElement('div');
	          right.className = 'stepRight';
	          right.appendChild(groupPill(stats));
	          const exp = document.createElement('div');
	          exp.className = 'expander';
	          exp.textContent = collapsedNow ? '展开' : '收起';
	          right.appendChild(exp);

	          head.appendChild(left);
	          head.appendChild(right);
	          wrap.appendChild(head);

	          const card = document.createElement('div');
	          card.className = 'stepCard' + (collapsedNow ? ' hidden' : '');
	          cardsIn.forEach(c => card.appendChild(cellEl(c)));
	          wrap.appendChild(card);

	          box.appendChild(wrap);
	        }

	        GROUPS.slice().sort((a,b) => (a.order||0) - (b.order||0)).forEach(renderGroup);

	        const leftovers = Object.keys(byGroup).filter(id => !knownIds.has(id));
	        leftovers.sort().forEach(id => renderGroup({id, title:'其它', desc:'未分类指标'}));
	      }

      function confirmAct(action, msg){
        if(!confirm(msg || '确认执行？')){ return; }
        act(action);
      }

      async function act(action, service){
        const lbl = actionLabel(action, service);
        try{
          const r = await fetch('/api/action', {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({action, service})
          });
          const data = await r.json();
          const ok = !!(data && data.ok);
          const msg = String((data && data.message) || '').trim();
          const detail = String((data && data.detail) || '').trim();
          if(ok){
            toast(msg || ('已完成：' + lbl), 'ok');
            openResult('已完成：' + lbl, (msg || '已完成'), detail);
          }else{
            toast(msg || '操作失败', 'bad');
            openResult('未完成：' + lbl, (msg || '操作失败'), detail || msg);
          }
        }catch(e){
          const m = '请求失败：' + (e && e.message ? e.message : String(e));
          toast('请求失败', 'bad');
          openResult('未完成：' + lbl, '请求失败', m);
        }
        if(action === 'ops_shutdown'){
          setAuto(false);
          return;
        }
        await refresh();
      }

      function openResult(titleText, msgText, detailText){
        const modal = document.getElementById('modal');
        const title = document.getElementById('modalTitle');
        const body = document.getElementById('modalBody');
        modal.style.display = 'flex';
        title.textContent = titleText || '结果';
        setModalCopy('');

        body.innerHTML = '';
        const msg = document.createElement('div');
        msg.className = 'resultMsg';
        msg.textContent = String(msgText || '').trim() || '—';
        body.appendChild(msg);

        const backId = String(lastCardId || '').trim();
        if(backId){
          const row = document.createElement('div');
          row.className = 'resultTools';
          const backBtn = document.createElement('button');
          backBtn.className = 'miniBtn';
          backBtn.textContent = '继续下一步';
          backBtn.onclick = () => { closeModal(); openCardById(backId); };
          row.appendChild(backBtn);
          body.appendChild(row);
        }

        const det = String(detailText || '').trim();
        const msg0 = String(msgText || '').trim();
        if(det && det !== msg0){
          const details = document.createElement('details');
          details.className = 'resultDetails';
          const sum = document.createElement('summary');
          sum.textContent = '详细信息（可复制）';
          details.appendChild(sum);

          const tools = document.createElement('div');
          tools.className = 'resultTools';
          const copyBtn = document.createElement('button');
          copyBtn.className = 'miniBtn primary';
          copyBtn.textContent = '一键复制';
          copyBtn.onclick = () => copyText(det);
          tools.appendChild(copyBtn);
          details.appendChild(tools);

          const pre = document.createElement('pre');
          pre.className = 'log mono';
          pre.textContent = det;
          details.appendChild(pre);
          body.appendChild(details);
        }
      }

      function openText(titleText, bodyText){
        const modal = document.getElementById('modal');
        const title = document.getElementById('modalTitle');
        const body = document.getElementById('modalBody');
        modal.style.display = 'flex';
        title.textContent = titleText || '—';
        body.innerHTML = '';
        const pre = document.createElement('pre');
        pre.className = 'log mono';
        pre.textContent = bodyText || '';
        body.appendChild(pre);
        setModalCopy(bodyText || '');
      }

      async function openAlertsSettings(){
        lastCardId = 'alerts';
        openText('告警设置', '加载中...');
        let cfg = null;
        try{
          const r = await fetch('/api/alerts/config', {cache:'no-store'});
          cfg = await r.json();
        }catch(e){
          openText('告警设置', '加载失败：' + (e && e.message ? e.message : String(e)));
          return;
        }
        if(!cfg || cfg.ok !== true){
          openText('告警设置', '加载失败（配置不可用）');
          return;
        }

        const values = (cfg && cfg.values) ? cfg.values : {};
        const conf = (cfg && cfg.configured) ? cfg.configured : {};
        const masked = (cfg && cfg.masked) ? cfg.masked : {};
        const links = (cfg && cfg.links) ? cfg.links : {};
        const clearFlags = {};
        const dirtyFlags = {};

        const modal = document.getElementById('modal');
        const title = document.getElementById('modalTitle');
        const body = document.getElementById('modalBody');
        modal.style.display = 'flex';
        title.textContent = '告警设置';
        setModalCopy('');
        body.innerHTML = '';

        const note = document.createElement('div');
        note.className = 'todoIntro';
        note.textContent = '渠道三选一即可：微信 / Telegram / Bark 任填一项即可（也可以同时填多个做备用）。';
        body.appendChild(note);

        function sec(titleText){
          const box = document.createElement('div');
          box.className = 'formSection';
          const t = document.createElement('div');
          t.className = 'formTitle';
          t.textContent = titleText;
          box.appendChild(t);
          const list = document.createElement('div');
          list.className = 'formList';
          box.appendChild(list);
          body.appendChild(box);
          return list;
        }

        function openLink(href){
          const url = String(href || '').trim();
          if(!url){ toast('链接不可用', 'bad'); return; }
          window.open(url, '_blank');
          toast('已打开', 'ok');
        }

        function rowInput(list, label, key, opt){
          const o = opt || {};
          const r = document.createElement('div');
          r.className = 'formRow';

          const k = document.createElement('div');
          k.className = 'formKey';
          k.textContent = label;
          r.appendChild(k);

          const ctl = document.createElement('div');
          ctl.className = 'formCtl';

          const input = document.createElement('input');
          input.className = 'textInput';
          input.type = o.type || 'text';
          if(o.inputMode){ input.inputMode = o.inputMode; }
          input.placeholder = o.placeholder || '';
          input.value = (o.value !== undefined && o.value !== null) ? String(o.value) : '';
          const inputId = 'alerts_' + String(key || '').replace(/[^A-Za-z0-9_]/g, '_');
          input.id = inputId;
          input.name = inputId;

          const ac = (o.autocomplete !== undefined && o.autocomplete !== null) ? String(o.autocomplete) : 'off';
          input.autocomplete = ac;
          input.setAttribute('autocomplete', ac);
          input.setAttribute('autocapitalize', 'none');
          input.setAttribute('autocorrect', 'off');
          // Try best-effort to prevent password managers from auto-filling secrets into wrong fields.
          input.setAttribute('data-1p-ignore', 'true');
          input.setAttribute('data-lpignore', 'true');
          input.setAttribute('data-bwignore', 'true');
          input.spellcheck = false;
          const markDirty = () => {
            clearFlags[key] = false;
            // Avoid saving browser auto-filled values unless user really interacted.
            if(document.activeElement === input){
              dirtyFlags[key] = true;
            }
          };
          input.addEventListener('input', markDirty);
          input.addEventListener('paste', () => { dirtyFlags[key] = true; clearFlags[key] = false; });
          input.addEventListener('keydown', () => { dirtyFlags[key] = true; clearFlags[key] = false; });
          ctl.appendChild(input);

          const hint = String(o.hint || '').trim();
          if(hint){
            const h = document.createElement('div');
            h.className = 'hint';
            h.textContent = hint;
            ctl.appendChild(h);
          }

          r.appendChild(ctl);

          const acts = document.createElement('div');
          acts.className = 'formActs';
          const linksArr = Array.isArray(o.links) ? o.links : [];
          linksArr.forEach(x => {
            const b = document.createElement('button');
            b.className = 'miniBtn primary';
            b.textContent = String(x.label || '打开');
            b.onclick = () => openLink(x.href);
            acts.appendChild(b);
          });
          if(o.clearable){
            const c = document.createElement('button');
            c.className = 'miniBtn danger';
            c.textContent = '清除';
            c.onclick = () => {
              input.value = '';
              clearFlags[key] = true;
              dirtyFlags[key] = false;
              toast('已标记清除', 'ok');
            };
            acts.appendChild(c);
          }
          if(acts.childNodes.length){
            r.appendChild(acts);
          }

          list.appendChild(r);
          return input;
        }

        function rowSelect(list, label, key, opt){
          const o = opt || {};
          const r = document.createElement('div');
          r.className = 'formRow';

          const k = document.createElement('div');
          k.className = 'formKey';
          k.textContent = label;
          r.appendChild(k);

          const ctl = document.createElement('div');
          ctl.className = 'formCtl';

          const sel = document.createElement('select');
          sel.className = 'selectInput';
          const items = Array.isArray(o.items) ? o.items : [];
          items.forEach(it => {
            const op = document.createElement('option');
            op.value = String(it.value);
            op.textContent = String(it.label);
            sel.appendChild(op);
          });
          sel.value = (o.value !== undefined && o.value !== null) ? String(o.value) : '';
          ctl.appendChild(sel);

          const hint = String(o.hint || '').trim();
          if(hint){
            const h = document.createElement('div');
            h.className = 'hint';
            h.textContent = hint;
            ctl.appendChild(h);
          }

          r.appendChild(ctl);
          list.appendChild(r);
          return sel;
        }

        const basic = sec('基本');
        const ipEnabled = rowSelect(basic, '开启告警', 'ALERT_ENABLED', {
          value: String(values.ALERT_ENABLED || '0'),
          items:[{label:'关', value:'0'},{label:'开', value:'1'}],
          hint:'开启后：异常/恢复会自动推送。'
        });
        const ipInclude = rowSelect(basic, '包含上线配置', 'ALERT_INCLUDE_SETUP', {
          value: String(values.ALERT_INCLUDE_SETUP || '0'),
          items:[{label:'否', value:'0'},{label:'是', value:'1'}],
          hint:'默认只告警“运行异常”；如果你希望 DNS/Pages 未完成也提醒，可开启。'
        });
        const ipInterval = rowInput(basic, '轮询间隔(秒)', 'ALERT_INTERVAL_S', {
          type:'number',
          inputMode:'numeric',
          value: String(values.ALERT_INTERVAL_S || '30'),
          hint:'范围：10-600。越小越及时，但更容易刷屏。'
        });
        const ipRepeat = rowInput(basic, '重复提醒(分钟)', 'ALERT_REPEAT_MINUTES', {
          type:'number',
          inputMode:'numeric',
          value: String(values.ALERT_REPEAT_MINUTES || '30'),
          hint:'异常持续时的重复提醒间隔（防止漏看）。范围：5-1440。'
        });
        const ipRecovery = rowSelect(basic, '推送恢复通知', 'ALERT_SEND_RECOVERY', {
          value: String(values.ALERT_SEND_RECOVERY || '1'),
          items:[{label:'开', value:'1'},{label:'关', value:'0'}],
          hint:'建议开启：一眼知道是否恢复。'
        });

        const silence = sec('静默时段（可选）');
        const ipSilStart = rowInput(silence, '开始', 'ALERT_SILENCE_START', {
          value: String(values.ALERT_SILENCE_START || ''),
          placeholder:'例如 23:00',
          hint:'留空=不静默。支持跨天（如 23:00-07:00）。'
        });
        const ipSilEnd = rowInput(silence, '结束', 'ALERT_SILENCE_END', {
          value: String(values.ALERT_SILENCE_END || ''),
          placeholder:'例如 07:00',
        });

        const wecom = sec('微信（可选，国内推荐）');
        const wecomCur = String((masked && masked.ALERT_WECOM_WEBHOOK) || '').trim();
        const wecomPlaceholder = conf.ALERT_WECOM_WEBHOOK ? '粘贴新的 Webhook（留空=不改）' : '未配置';
        const wecomHint = (conf.ALERT_WECOM_WEBHOOK ? '已设置（脱敏显示），无需重复填写。\\n要更换：直接粘贴新的 Webhook 覆盖即可。\\n\\n' : '') + '企业微信：群聊 -> 添加群机器人 -> 复制 Webhook。';
        const ipWecom = rowInput(wecom, 'Webhook', 'ALERT_WECOM_WEBHOOK', {
          type:'url',
          value: wecomCur,
          placeholder: wecomPlaceholder,
          hint: wecomHint,
          clearable:true,
          links:[{label:'申请/教程', href:String(links.wecom_bot || '')}]
        });

        const tg = sec('Telegram（可选）');
        const tgTokCur = String((masked && masked.ALERT_TG_BOT_TOKEN) || '').trim();
        const tgTokPlaceholder = conf.ALERT_TG_BOT_TOKEN ? '粘贴新的 Token（留空=不改）' : '未配置';
        const tgTokHint = (conf.ALERT_TG_BOT_TOKEN ? '已设置（脱敏显示），无需重复填写。\\n要更换：直接粘贴新的 Token 覆盖即可。\\n\\n' : '') + '在 Telegram 里用 BotFather 创建机器人并获取 token。';
        const ipTgTok = rowInput(tg, 'Bot Token', 'ALERT_TG_BOT_TOKEN', {
          type:'text',
          value: tgTokCur,
          placeholder: tgTokPlaceholder,
          hint: tgTokHint,
          clearable:true,
          links:[{label:'打开 BotFather', href:String(links.telegram_botfather || '')}]
        });
        const tgChatCur = String((masked && masked.ALERT_TG_CHAT_ID) || '').trim();
        const tgChatPlaceholder = conf.ALERT_TG_CHAT_ID ? '填写新的 Chat ID（留空=不改）' : '未配置';
        const tgChatHint = (conf.ALERT_TG_CHAT_ID ? '已设置（脱敏显示），无需重复填写。\\n要更换：直接填写新的 Chat ID 覆盖即可。\\n\\n' : '') + '把 bot 拉进你的聊天/群后可获得 chat_id（详见 API 文档）。';
        const ipTgChat = rowInput(tg, 'Chat ID', 'ALERT_TG_CHAT_ID', {
          type:'text',
          inputMode:'numeric',
          value: tgChatCur,
          placeholder: tgChatPlaceholder,
          hint: tgChatHint,
          clearable:true,
          links:[{label:'API 文档', href:String(links.telegram_api || '')}]
        });

        const bark = sec('iOS 推送（Bark，可选）');
        const barkCur = String((masked && masked.ALERT_BARK_URL) || '').trim();
        const barkPlaceholder = conf.ALERT_BARK_URL ? '粘贴新的 Bark URL（留空=不改）' : '未配置';
        const barkHint = (conf.ALERT_BARK_URL ? '已设置（脱敏显示），无需重复填写。\\n要更换：直接粘贴新 URL 覆盖即可。\\n\\n' : '') + '只填前缀（形如 https://api.day.app/<Key>）。如果你粘贴了长链接，保存时会自动截断为前缀。';
        const ipBark = rowInput(bark, 'Bark URL', 'ALERT_BARK_URL', {
          // Use text+inputMode=url so masked display (contains "…") won't be blanked by browsers'
          // URL input sanitization/validation behaviors (observed in Safari).
          type:'text',
          inputMode:'url',
          value: barkCur,
          placeholder: barkPlaceholder,
          hint: barkHint,
          clearable:true,
          links:[{label:'Bark', href:String(links.bark || '')}]
        });

        // Tools
        const tools = document.createElement('div');
        tools.className = 'resultTools';
        tools.style.marginTop = '14px';

        const saveBtn = document.createElement('button');
        saveBtn.className = 'miniBtn primary';
        saveBtn.textContent = '保存';
        saveBtn.onclick = async () => {
          const outValues = {
            ALERT_ENABLED: String(ipEnabled.value || '0'),
            ALERT_INCLUDE_SETUP: String(ipInclude.value || '0'),
            ALERT_INTERVAL_S: String(ipInterval.value || '').trim(),
            ALERT_REPEAT_MINUTES: String(ipRepeat.value || '').trim(),
            ALERT_SEND_RECOVERY: String(ipRecovery.value || '1'),
            ALERT_SILENCE_START: String(ipSilStart.value || '').trim(),
            ALERT_SILENCE_END: String(ipSilEnd.value || '').trim(),
          };

          function maybeSecret(key, inputEl){
            if(!!clearFlags[key]){ return; }
            if(!dirtyFlags[key]){ return; }
            const v = String((inputEl && inputEl.value) || '').trim();
            const mv = String((masked && masked[key]) || '').trim();
            // If user only touched the field but kept the masked display value, treat as unchanged.
            if(mv && v === mv){ return; }
            if(v){
              outValues[key] = v;
            }else if(conf && conf[key]){
              // Allow clearing by deleting the content then saving.
              clearFlags[key] = true;
            }
          }

          maybeSecret('ALERT_WECOM_WEBHOOK', ipWecom);
          maybeSecret('ALERT_TG_BOT_TOKEN', ipTgTok);
          maybeSecret('ALERT_TG_CHAT_ID', ipTgChat);
          maybeSecret('ALERT_BARK_URL', ipBark);

          const payload = { values: outValues, clear: clearFlags };
          try{
            const r = await fetch('/api/alerts/config', {
              method:'POST',
              headers:{'Content-Type':'application/json'},
              body: JSON.stringify(payload),
            });
            const res = await r.json();
            const ok = !!(res && res.ok);
            const msg = String((res && res.message) || '').trim();
            const detail = String((res && res.detail) || '').trim();
            if(ok){
              toast(msg || '已保存', 'ok');
              openResult('已完成：告警设置', msg || '已保存', detail);
            }else{
              toast(msg || '保存失败', 'bad');
              openResult('未完成：告警设置', msg || '保存失败', detail || msg);
            }
            await refresh();
          }catch(e){
            const m = '请求失败：' + (e && e.message ? e.message : String(e));
            toast('保存失败', 'bad');
            openResult('未完成：告警设置', '保存失败', m);
          }
        };
        tools.appendChild(saveBtn);

        const testBtn = document.createElement('button');
        testBtn.className = 'miniBtn';
        testBtn.textContent = '发送测试消息';
        testBtn.onclick = () => confirmAct('alerts_test', '将向你已配置的渠道发送一条测试消息。继续？');
        tools.appendChild(testBtn);

        const openFileBtn = document.createElement('button');
        openFileBtn.className = 'miniBtn';
        openFileBtn.textContent = '打开配置文件';
        openFileBtn.onclick = () => act('alerts_open_config', '');
        tools.appendChild(openFileBtn);

        body.appendChild(tools);
      }

      function openTodo(titleText, introText, steps){
        const modal = document.getElementById('modal');
        const title = document.getElementById('modalTitle');
        const body = document.getElementById('modalBody');
        modal.style.display = 'flex';
        title.textContent = titleText || '待办清单';
        setModalCopy('');

        body.innerHTML = '';
        const intro = String(introText || '').trim();
        if(intro){
          const p = document.createElement('div');
          p.className = 'todoIntro';
          p.textContent = intro;
          body.appendChild(p);
        }

        function renderSteps(container, stepsIn, emptyTitle){
          const arr = Array.isArray(stepsIn) ? stepsIn : [];
          if(arr.length === 0){
            const item = document.createElement('div');
            item.className = 'todoItem';
            const no = document.createElement('div');
            no.className = 'todoNo ok';
            no.textContent = '✓';
            const txt = document.createElement('div');
            txt.className = 'todoText';
            const tt = document.createElement('div');
            tt.className = 'todoTitle';
            tt.textContent = emptyTitle || '暂无待办';
            txt.appendChild(tt);
            item.appendChild(no);
            item.appendChild(txt);
            container.appendChild(item);
            return;
          }

          let todoIdx = 0;
          arr.forEach((st) => {
            const item = document.createElement('div');
            item.className = 'todoItem';

            const no = document.createElement('div');
            no.className = 'todoNo';
            const stStatus = String((st && st.status) || '').toLowerCase();
            if(stStatus === 'ok'){
              no.classList.add('ok');
              no.textContent = '✓';
            }else{
              todoIdx += 1;
              if(stStatus === 'warn' || stStatus === 'bad'){
                no.classList.add(stStatus);
              }
              no.textContent = String(todoIdx);
            }

            const txt = document.createElement('div');
            txt.className = 'todoText';
            const tt = document.createElement('div');
            tt.className = 'todoTitle';
            tt.textContent = String((st && (st.title || st.text)) || '—');
            txt.appendChild(tt);
            const fields = Array.isArray(st && st.fields) ? st.fields : [];
            if(fields.length){
              const box = document.createElement('div');
              box.className = 'todoFields';
              fields.forEach(f => {
                const row = document.createElement('div');
                row.className = 'todoField';

                const k = document.createElement('div');
                k.className = 'todoFieldKey';
                k.textContent = String((f && (f.label || f.key)) || '—');
                row.appendChild(k);

                const raw = (f && f.value !== undefined && f.value !== null) ? f.value : '';
                let text = '';
                if(Array.isArray(raw)){
                  text = raw.map(x => String(x ?? '')).join('\\n');
                }else{
                  text = String(raw);
                }
                text = text.trim();

                const valEl = document.createElement('div');
                valEl.className = 'todoFieldVal' + ((f && f.mono) ? ' mono' : '');
                valEl.textContent = text || '—';
                row.appendChild(valEl);

                const copyOk = !(f && f.copy === false);
                if(copyOk && text){
                  const cb = document.createElement('button');
                  cb.className = 'miniBtn';
                  cb.textContent = String((f && f.copyLabel) || '复制');
                  cb.onclick = () => copyText(text);
                  row.appendChild(cb);
                }

                box.appendChild(row);
              });
              txt.appendChild(box);
            }
            const desc = (st && st.desc) ? String(st.desc) : '';
            if(desc.trim()){
              const dd = document.createElement('div');
              dd.className = 'todoDesc';
              dd.textContent = desc;
              txt.appendChild(dd);
            }

            const actsWrap = document.createElement('div');
            actsWrap.className = 'todoActs';
            const acts = Array.isArray(st && st.actions) ? st.actions : [];
            acts.forEach(a => {
              const b = document.createElement('button');
              b.className = 'miniBtn ' + (a && a.kind ? a.kind : '');
              b.textContent = (a && a.label) ? String(a.label) : '操作';
              b.onclick = () => handleAction(a);
              actsWrap.appendChild(b);
            });

            item.appendChild(no);
            item.appendChild(txt);
            if(acts.length){ item.appendChild(actsWrap); }
            container.appendChild(item);
          });
        }

        const arrAll = Array.isArray(steps) ? steps : [];
        const stepsShow = [];
        const stepsDone = [];
        arrAll.forEach(st => {
          const stStatus = String((st && st.status) || '').toLowerCase();
          const t = String((st && (st.title || st.text)) || '').trim();
          const pin = !!(st && st.pin);
          const fold = (!pin) && stStatus === 'ok' && (!!(st && st.fold) || t.includes('已完成'));
          if(fold){
            stepsDone.push(st);
          }else{
            stepsShow.push(st);
          }
        });

        const list = document.createElement('div');
        list.className = 'todoList';
        const emptyTitle = (stepsShow.length === 0 && stepsDone.length > 0) ? '全部已完成' : '暂无待办';
        renderSteps(list, stepsShow, emptyTitle);
        body.appendChild(list);

        if(stepsDone.length){
          const det = document.createElement('details');
          det.className = 'resultDetails';
          const sum = document.createElement('summary');
          sum.textContent = '已完成 ' + stepsDone.length + ' 项';
          det.appendChild(sum);
          const doneList = document.createElement('div');
          doneList.className = 'todoList';
          renderSteps(doneList, stepsDone, '');
          det.appendChild(doneList);
          body.appendChild(det);
        }
      }

      async function openLog(target, service){
        const t = (target === 'tunnel')
          ? '外网通道日志'
          : (target === 'named_init'
            ? '固定外网初始化 · 日志'
            : (target === 'mobile_preview'
              ? '手机外网验收 · 日志'
              : (target === 'alerts'
                ? '告警日志'
                : (target === 'git'
                  ? ('Git 状态' + (service ? (' · ' + service) : ''))
                : ('服务日志 · ' + (service || '—'))))));
        openText(t, '加载中...');
        let url = '/api/logs?target=' + encodeURIComponent(target || '');
        if(target === 'docker' || target === 'git'){ url += '&service=' + encodeURIComponent(service || ''); }
        try{
          const r = await fetch(url, {cache:'no-store'});
          openText(t, await r.text());
        }catch(e){
          openText(t, '加载失败：' + (e && e.message ? e.message : String(e)));
        }
      }

      function closeModal(){
        document.getElementById('modal').style.display = 'none';
        setModalCopy('');
      }

      function openCardById(cardId){
        const id = String(cardId || '').trim();
        if(!id){ return; }
        const list = Array.isArray(lastPreparedCards) ? lastPreparedCards : [];
        const card = list.find(c => c && String(c.id || '').trim() === id);
        if(!card){
          toast('未找到目标卡片（可能已更新/被隐藏）', 'bad');
          return;
        }
        const acts = Array.isArray(card && card.actions) ? card.actions : [];
        const todo = acts.find(x => x && x.type === 'todo');
        if(todo){
          handleAction(todo);
          return;
        }
        openSheet(card);
      }

      function handleAction(x){
        if(!x || !x.type){ return; }
        if(x.type === 'refresh'){
          closeSheet();
          return refresh();
        }
        if(x.type === 'alerts_settings'){
          closeSheet();
          return openAlertsSettings();
        }
        if(x.type === 'todo'){
          return openTodo(x.title || x.label || '待办清单', x.intro || '', x.steps || []);
        }
        if(x.type === 'prompt'){
          const tip = x.prompt || '请输入内容';
          const def = (x.def !== undefined && x.def !== null) ? String(x.def) : '';
          const v = prompt(tip, def);
          if(v === null){ return; }
          const s = String(v || '').trim();
          if(!s){
            toast('未填写', 'bad');
            return;
          }
          if(x.confirm && !confirm(x.confirm)){ return; }
          closeSheet();
          return act(x.action, s);
        }
        if(x.type === 'toggle'){
          if(x.key === 'issuesOnly'){
            setIssuesOnly(!issuesOnly);
            toast('只看需处理：' + (issuesOnly ? '开' : '关'), 'ok');
            return refresh();
          }
          if(x.key === 'auto'){
            setAuto(!auto);
            toast('自动刷新：' + (auto ? '开' : '关'), 'ok');
            return;
          }
          return;
        }
        if(x.type === 'api'){
          if(x.confirm && !confirm(x.confirm)){ return; }
          return act(x.action, x.service || '');
        }
        if(x.type === 'log'){
          return openLog(x.target, x.service || '');
        }
        if(x.type === 'guide'){
          return openText(x.title || '处理方法', x.text || '');
        }
        if(x.type === 'link'){
          const href = String(x.href || '').trim();
          if(href && href !== '#'){
            window.open(href, '_blank');
            toast('已打开', 'ok');
          }else{
            toast('链接不可用', 'bad');
          }
          return;
        }
        if(x.type === 'copy'){
          return copyText(x.text || '');
        }
      }

      function updateFoot(data){
        const ip = (data && data.lan && data.lan.ip) ? data.lan.ip : '—';
        const tun = (data && data.tunnel && data.tunnel.url) ? String(data.tunnel.url) : '-';
        const fe = (data && data.frontend && data.frontend.url) ? String(data.frontend.url) : ((data && data.links && data.links.frontend) ? String(data.links.frontend) : 'https://naibao.me');
        const root = (data && data.root_dir) ? String(data.root_dir) : '';
        const compose = (data && data.compose_file) ? String(data.compose_file) : '';
        const env = (data && data.env_file) ? String(data.env_file) : '';
        const commit = (data && data.git && data.git.commit) ? String(data.git.commit) : '';
        const ts = (data && typeof data.ts === 'number' && isFinite(data.ts)) ? new Date(data.ts * 1000).toLocaleString() : '';
        const lines = [
          root ? ('仓库：' + root) : '',
          compose ? ('编排：' + compose) : '',
          env ? ('配置：' + env) : '',
          '局域网：' + ip,
          '外网通道：' + tun,
          '前端：' + fe,
          commit ? ('版本：' + commit) : '',
          ts ? ('更新时间：' + ts) : '',
        ].filter(Boolean);
        document.getElementById('foot').textContent = lines.join('\\n');
      }

      function renderOneCard(card){
        const cards = [card];
        updateOverall(cards);
        lastPreparedCards = prepareCards(cards);
        render(lastPreparedCards);
      }

      function showLoading(meta){
        const m = meta || {};
        const sub = String(m.last_error || '').trim()
          ? ('上次错误：' + String(m.last_error || '').trim())
          : '首次打开需要几秒；稍后会自动刷新。';
        renderOneCard({
          id:'loading',
          group:'run',
          order:0,
          title:'正在检测',
          status:'warn',
          value:'加载中…',
          sub,
          actions:[{type:'refresh', label:'刷新', kind:'primary'}]
        });
      }

      function showError(msg){
        const m = String(msg || '').trim() || '加载失败';
        renderOneCard({
          id:'load_err',
          group:'run',
          order:0,
          title:'加载失败',
          status:'bad',
          value:m,
          sub:'点击「刷新」重试。',
          actions:[{type:'refresh', label:'刷新', kind:'primary'}]
        });
      }

      function tryRenderCached(){
        try{
          const raw = localStorage.getItem(LS_STATUS_KEY);
          if(!raw){ return false; }
          const data = JSON.parse(raw);
          if(!data || typeof data !== 'object'){ return false; }
          const cards = buildCards(data);
          updateOverall(cards);
          lastPreparedCards = prepareCards(cards);
          render(lastPreparedCards);
          updateFoot(data);
          return true;
        }catch(e){
          return false;
        }
      }

      async function refresh(){
        if(refreshInFlight){ return; }
        refreshInFlight = true;
        const ctrl = new AbortController();
        const to = setTimeout(() => ctrl.abort(), 8000);
        try{
          const r = await fetch('/api/status', {cache:'no-store', signal: ctrl.signal});
          const data = await r.json();

          const meta = (data && data._meta) ? data._meta : null;
          if(meta && meta.has_data === false){
            showLoading(meta);
            return;
          }
          // Only persist a usable snapshot. (When status is still warming up, server returns a placeholder.)
          try{ localStorage.setItem(LS_STATUS_KEY, JSON.stringify(data)); }catch(e){}

          const cards = buildCards(data);
          updateOverall(cards);
          lastPreparedCards = prepareCards(cards);
          render(lastPreparedCards);
          updateFoot(data);
        }catch(e){
          const isAbort = !!(e && e.name === 'AbortError');
          const msg = isAbort ? '加载超时（请稍后重试）' : ('加载失败：' + (e && e.message ? e.message : String(e)));
          toast(isAbort ? '加载超时' : '加载失败', 'bad');
          if(!lastPreparedCards || lastPreparedCards.length === 0){
            showError(msg);
          }
        }finally{
          clearTimeout(to);
          refreshInFlight = false;
        }
      }

      // Instant render with last snapshot, then refresh in background.
      tryRenderCached();
      setAuto(true);
      refresh();
    </script>
  </body>
</html>
"""


def pretty_svc_name(svc: str) -> str:
    s = (svc or "").strip()
    if not s:
        return ""
    m = {
        "backend": "后端(API)",
        "db": "数据库",
        "redis": "缓存(Redis)",
    }
    return m.get(s, s)


def normalize_action_result(action: str, service: str, ok: bool, message: str, detail: str) -> Tuple[bool, str, str]:
    """
    Make action responses "product-like":
    - message: short, clear, user-facing (shown immediately)
    - detail: long, raw output (hidden behind details, copyable)
    """
    a = (action or "").strip()
    svc = (service or "").strip()

    msg_raw = (message or "").strip()
    det_raw = (detail or "").strip()

    # Always keep raw detail for debugging/copying.
    det = det_raw or msg_raw

    if not ok:
        short = humanize_error(msg_raw)
        if not short or (short == msg_raw and (len(msg_raw) > 240 or "\n" in msg_raw)):
            short = "操作失败（请展开详情查看原因）"
        return False, short, det

    # OK messages: prefer explicit labels per action.
    if a == "docker_up":
        port = ""
        m = re.search(r"已自动选择可用端口：(\d+)", det)
        if m:
            port = m.group(1)
        return True, ("已启动/修复完成" + (f"（端口 {port}）" if port else "")), det
    if a == "docker_down":
        return True, "已停止全部服务", det
    if a == "docker_restart_all":
        return True, "已重启全部服务", det
    if a == "docker_restart":
        return True, ("已重启" + (pretty_svc_name(svc) or "服务")), det
    if a == "docker_prune":
        return True, "已清理 Docker 缓存", det
    if a == "docker_stop_container":
        return True, ("已停止占用容器" + (f"：{svc}" if svc else "")), det

    if a == "mobile_preview_start":
        return True, "手机外网验收已启动", det
    if a == "mobile_preview_stop":
        return True, "手机外网验收已停止", det
    if a == "mobile_preview_restart":
        return True, "手机外网验收已重启", det

    if a == "tunnel_start":
        return True, "外网通道已启动", det
    if a == "tunnel_restart":
        return True, "外网通道已重启", det
    if a == "tunnel_stop":
        return True, "外网通道已停止", det
    if a == "named_tunnel_init":
        # message already human-friendly (browser login etc)
        return True, (msg_raw or "固定外网初始化已开始"), det

    if a == "open_docker":
        return True, (msg_raw or "已打开 Docker"), det
    if a == "set_backend_port":
        return True, (msg_raw or "已生效"), det

    if a.startswith("git_"):
        return True, (msg_raw or "已推送到 GitHub"), det

    # fallback: use raw if it's short; otherwise show a generic completion.
    if msg_raw and len(msg_raw) <= 80 and "\n" not in msg_raw:
        return True, msg_raw, det
    return True, "操作已完成", det


class OpsHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    # Python 标准库 http.server.HTTPServer 会在 bind 时做一次 `socket.getfqdn(host)`，
    # 某些 DNS/反向解析配置下可能卡住，导致服务“永远起不来”（尤其在新版本 Python 上更明显）。
    # 运营台不需要反向解析，直接跳过即可。
    def server_bind(self) -> None:  # noqa: D401
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = str(host)
        self.server_port = int(port)


class Handler(BaseHTTPRequestHandler):
    server_version = "naibao-ops/1.0"

    def _json(self, code: int, data: Any) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _text(self, code: int, txt: str) -> None:
        raw = (txt or "").encode("utf-8", errors="ignore")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path.startswith("/?"):
            raw = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if self.path.startswith("/api/status"):
            self._json(200, status_payload_cached())
            return

        if self.path.startswith("/api/alerts/config"):
            self._json(200, alerts_config_payload())
            return

        if self.path.startswith("/api/logs"):
            from urllib.parse import parse_qs, urlparse

            q = parse_qs(urlparse(self.path).query)
            target = (q.get("target", [""])[0] or "").strip()
            if target == "tunnel":
                self._text(200, tail_file(TUN_LOG, 200))
                return
            if target == "named_init":
                self._text(200, tail_file(NAMED_INIT_LOG, 200))
                return
            if target == "mobile_preview":
                self._text(200, mobile_preview_logs())
                return
            if target == "alerts":
                self._text(200, tail_file(ALERTS_LOG, 200) or "暂无日志")
                return
            if target == "docker":
                svc = (q.get("service", [""])[0] or "").strip()
                self._text(200, docker_logs(svc, tail=200))
                return
            if target == "git":
                svc = (q.get("service", [""])[0] or "").strip()
                self._text(200, git_status_text(svc))
                return
            self._text(400, "未知日志目标")
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/alerts/config"):
            try:
                n = int(self.headers.get("Content-Length") or "0")
            except Exception:
                n = 0
            body = self.rfile.read(max(0, n)) if n > 0 else b""
            try:
                payload = json.loads(body.decode("utf-8", errors="ignore") or "{}")
            except Exception:
                payload = {}
            ok, msg, detail = alerts_config_save(payload if isinstance(payload, dict) else {})
            self._json(200, {"ok": bool(ok), "message": str(msg or ""), "detail": str(detail or "")})
            return

        if not self.path.startswith("/api/action"):
            self.send_response(404)
            self.end_headers()
            return

        try:
            n = int(self.headers.get("Content-Length") or "0")
        except Exception:
            n = 0
        body = self.rfile.read(max(0, n)) if n > 0 else b""
        try:
            payload = json.loads(body.decode("utf-8", errors="ignore") or "{}")
        except Exception:
            payload = {}

        action = str(payload.get("action") or "").strip()
        service = str(payload.get("service") or "").strip()

        if action == "ops_shutdown":
            self._json(200, {"ok": True, "message": "正在关闭运营台", "detail": ""})

            def _shutdown() -> None:
                try:
                    self.server.shutdown()
                except Exception:
                    pass

            threading.Thread(target=_shutdown, daemon=True).start()
            return

        ensure_home_env_file()
        env = read_env_file(HOME_ENV_FILE)

        res: Any
        if action == "docker_up":
            res = docker_up()
        elif action == "docker_down":
            res = docker_down()
        elif action == "docker_restart":
            res = docker_restart(service)
        elif action == "docker_restart_all":
            res = docker_restart_all()
        elif action == "docker_prune":
            res = docker_prune()
        elif action == "docker_stop_container":
            res = docker_stop_container(service)
        elif action == "mobile_preview_start":
            res = mobile_preview_start()
        elif action == "mobile_preview_stop":
            res = mobile_preview_stop()
        elif action == "mobile_preview_restart":
            ok1, out1 = mobile_preview_stop()
            ok2, out2 = mobile_preview_start()
            res = (bool(ok1 and ok2), (out1 + "\n\n" + out2).strip())
        elif action == "tunnel_start":
            res = start_tunnel(env)
        elif action == "tunnel_restart":
            ok1, out1 = stop_tunnel()
            ok2, out2 = start_tunnel(env)
            res = (bool(ok1 and ok2), (out1 + "\n\n" + out2).strip())
        elif action == "tunnel_stop":
            res = stop_tunnel()
        elif action == "named_tunnel_init":
            res = named_tunnel_init()
        elif action == "git_publish_workflow":
            res = git_publish([".github/workflows/pages.yml"], service, kind="workflow")
        elif action == "git_publish_frontend":
            res = git_publish(
                [
                    "frontend/src",
                    "frontend/index.html",
                    "frontend/package.json",
                    "frontend/package-lock.json",
                    "frontend/vite.config.js",
                    "frontend/.npmrc",
                    ".github/workflows/pages.yml",
                ],
                service,
                kind="frontend",
            )
        elif action == "alerts_open_config":
            ensure_alerts_env_file()
            res = open_text_file(ALERTS_ENV_FILE)
        elif action == "alerts_enable":
            ensure_alerts_env_file()
            changed = set_env_kv(ALERTS_ENV_FILE, "ALERT_ENABLED", "1")
            res = (True, "告警已开启" if changed else "告警已开启（无需修改）")
        elif action == "alerts_disable":
            ensure_alerts_env_file()
            changed = set_env_kv(ALERTS_ENV_FILE, "ALERT_ENABLED", "0")
            res = (True, "告警已关闭" if changed else "告警已关闭（无需修改）")
        elif action == "alerts_test":
            ensure_alerts_env_file()
            aenv = read_env_file(ALERTS_ENV_FILE)
            st0 = alerts_state()
            # Build a friendly test message, not tied to current health.
            env2 = read_env_file(HOME_ENV_FILE) if HOME_ENV_FILE.exists() else {}
            public_domain = (env2.get("NB_PUBLIC_DOMAIN") or "naibao.me").strip()
            api_public = (env2.get("NB_TUNNEL_HOSTNAME") or "api.naibao.me").strip()
            title = "奶宝：告警测试"
            body = "\n".join(
                [
                    f"时间：{time.strftime('%Y-%m-%d %H:%M')}",
                    "说明：这是一条测试消息，用于确认告警渠道可用。",
                    "",
                    f"前端：https://{public_domain}",
                    f"API：https://{api_public}/api/health",
                ]
            ).strip()
            ok, report = alerts_send_all(aenv, title, body)
            st0["last_sent_ts"] = int(time.time())
            st0["last_send_ok"] = bool(ok)
            st0["last_send_msg"] = str(report or "")
            _save_json(ALERTS_STATE_FILE, st0)
            detail = "\n".join(
                [
                    "== 发送结果 ==",
                    report or "",
                    "",
                    "== 消息内容 ==",
                    title,
                    "",
                    body,
                ]
            ).strip()
            msg = "已发送测试消息" if ok else (report or "测试发送失败")
            res = (bool(ok), msg, detail)
        elif action == "open_docker":
            res = open_docker_desktop()
        elif action == "set_backend_port":
            res = set_backend_host_port(service)
        else:
            res = (False, f"未知操作：{action}", f"未知操作：{action}")

        ok = False
        message = ""
        detail = ""
        if isinstance(res, tuple):
            if len(res) == 3:
                ok, message, detail = bool(res[0]), str(res[1] or ""), str(res[2] or "")
            elif len(res) == 2:
                ok, message = bool(res[0]), str(res[1] or "")
                detail = message
            else:
                ok, message, detail = False, "操作失败（返回格式异常）", str(res)
        else:
            ok, message, detail = False, "操作失败（返回值异常）", str(res)

        ok, message, detail = normalize_action_result(action, service, ok, message, detail)
        self._json(200, {"ok": bool(ok), "message": str(message or ""), "detail": str(detail or "")})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=17623, help="port (default: 17623)")
    parser.add_argument("--open", action="store_true", help="open browser automatically")
    args = parser.parse_args()

    if not HOME_COMPOSE_FILE.exists():
        print(f"ERROR: missing {HOME_COMPOSE_FILE}", file=sys.stderr)
        return 2

    ensure_runtime_dir()
    ensure_home_env_file()

    bind = str(args.bind)
    port = int(args.port)
    addr = (bind, port)
    url = f"http://{bind}:{port}/"

    try:
        httpd = OpsHTTPServer(addr, Handler)
    except OSError as e:
        # 端口被占用：1) 已有运营台在跑则直接打开；2) 否则自动选一个空闲端口。
        if getattr(e, "errno", None) in (48, 98) and is_ops_console_running(bind, port):
            print(f"[ops] already running: {url}")
            if args.open:
                try:
                    webbrowser.open(url)
                except Exception:
                    pass
            return 0

        if getattr(e, "errno", None) in (48, 98):
            free_port = pick_free_port(bind)
            addr = (bind, free_port)
            url = f"http://{bind}:{free_port}/"
            httpd = OpsHTTPServer(addr, Handler)
            print(f"[ops] port {port} in use, switched to {free_port}")
        else:
            raise

    print(f"[ops] running: {url}")
    write_ops_runtime_files(int(addr[1]))
    # Warm-up status snapshot so the first page load is never a blank screen.
    ensure_status_update(force=True)
    if args.open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    stop_event = threading.Event()
    # Start alerts watchdog in-process. It only sends when enabled in alerts.env.
    try:
        threading.Thread(target=alerts_worker, args=(stop_event,), daemon=True).start()
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            stop_event.set()
        except Exception:
            pass
        cleanup_ops_runtime_files()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
