#!/usr/bin/env python3

"""
为“手机外网验收”准备可用演示数据（无需手动注册/建档）：
- 创建/复用固定演示账号（手机号/密码稳定）
- 创建/复用一个宝宝档案
- 设置喂奶间隔、绑定奶粉（可选）
- 生成当天 3 条喂奶记录，方便看到 24h 时间轴与建议

仅使用标准库，适合本地/CI。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http_json(method: str, url: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, method=method.upper(), headers=headers, data=data)
    try:
        with _OPENER.open(req, timeout=10) as resp:
            status = resp.getcode()
            raw = resp.read() or b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                payload = {"_raw": raw.decode("utf-8", errors="ignore")}
            return status, payload
    except urllib.error.HTTPError as e:
        raw = e.read() or b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {"_raw": raw.decode("utf-8", errors="ignore")}
        return e.code, payload


def wait_health(base: str, timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    url = f"{base}/health"
    last = None
    while time.time() < deadline:
        try:
            status, payload = http_json("GET", url)
            last = (status, payload)
            if status == 200 and payload.get("status") == "ok":
                return
        except Exception as e:
            last = e
        time.sleep(1)
    raise SystemExit(f"backend not ready: {url}\nlast={last}")


def cn_now() -> datetime:
    tz = timezone(timedelta(hours=8))
    return datetime.now(timezone.utc).astimezone(tz)


def pick_today_times(n: int = 3) -> list[datetime]:
    now = cn_now()
    tz = now.tzinfo or timezone(timedelta(hours=8))
    day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 优先用固定“白天节奏”时间点（更像真实家庭）
    candidates = [
        day0 + timedelta(hours=9, minutes=10),
        day0 + timedelta(hours=13, minutes=20),
        day0 + timedelta(hours=17, minutes=30),
    ]
    safe_now = now - timedelta(minutes=1)
    usable = [t for t in candidates if t <= safe_now]

    if len(usable) >= n:
        return usable[-n:]

    # 兜底：用相对 now 的过去时间，确保落在当天
    rel = [
        safe_now - timedelta(hours=3),
        safe_now - timedelta(hours=2),
        safe_now - timedelta(hours=1),
    ]
    out: list[datetime] = []
    for t in rel:
        if t < day0:
            t = day0 + timedelta(minutes=30)
        out.append(t.astimezone(tz))
    return out[-n:]


def main() -> None:
    base = os.environ.get("API_BASE", "http://localhost:18080").rstrip("/")

    demo_phone = os.environ.get("DEMO_PHONE", "13800138000")
    demo_password = os.environ.get("DEMO_PASSWORD", "naibao123")

    print(f"[demo] API_BASE={base}")
    wait_health(base)
    print("[demo] /health ok")

    # register (idempotent) -> login
    status, reg = http_json(
        "POST",
        f"{base}/api/public/register",
        body={
            "phone": demo_phone,
            "password": demo_password,
            "nickname": "验收账号",
            "avatar_url": "/static/avatars/avatar_1.png",
        },
    )
    if status == 200 and reg.get("token"):
        token = reg["token"]
        print("[demo] register ok")
    else:
        status, login = http_json(
            "POST",
            f"{base}/api/public/login",
            body={"phone": demo_phone, "password": demo_password},
        )
        if status != 200 or not login.get("token"):
            raise SystemExit(f"[demo] login failed status={status} payload={login}")
        token = login["token"]
        print("[demo] login ok (user already exists)")

    # baby
    status, babies = http_json("GET", f"{base}/api/babies", token=token)
    if status != 200:
        raise SystemExit(f"[demo] list babies failed status={status} payload={babies}")
    first = (babies.get("babies") or [{}])[0] if isinstance(babies.get("babies"), list) else None
    baby_id = first.get("id") if isinstance(first, dict) else None

    if not baby_id:
        status, created = http_json(
            "POST",
            f"{base}/api/babies",
            token=token,
            body={
                "nickname": "元宝",
                "avatar_url": "/static/avatars/avatar_2.png",
                "birth_date": "2025-01-01",
                "birth_time": "12:00:00",
                "gender": "male",
                "current_weight": 4.6,
                "current_height": 55,
            },
        )
        if status != 200 or not created.get("baby", {}).get("id"):
            raise SystemExit(f"[demo] create baby failed status={status} payload={created}")
        baby_id = created["baby"]["id"]
        print(f"[demo] create baby baby_id={baby_id}")
    else:
        print(f"[demo] reuse baby baby_id={baby_id}")

    # feeding settings (best-effort)
    _ = http_json(
        "PUT",
        f"{base}/api/babies/{baby_id}/settings",
        token=token,
        body={"day_interval": 3, "night_interval": 5, "day_start_hour": 6, "day_end_hour": 18, "advance_minutes": 15, "reminder_enabled": True},
    )

    # formula selection (best-effort)
    status, brands = http_json("GET", f"{base}/api/formula/brands", token=token)
    if status == 200 and isinstance(brands.get("brands"), list) and brands["brands"]:
        brand_id = brands["brands"][0].get("id")
        if brand_id:
            _ = http_json(
                "POST",
                f"{base}/api/babies/{baby_id}/formula",
                token=token,
                body={"brand_id": brand_id},
            )

    # feedings (avoid duplicating too many)
    qs = urllib.parse.urlencode({"baby_id": str(baby_id)})
    status, feedings = http_json("GET", f"{base}/api/feedings?{qs}", token=token)
    existing = feedings.get("feedings") if status == 200 else []
    existing = existing if isinstance(existing, list) else []

    # 只要当天已有 >=2 条记录，就不再强行灌入
    if len(existing) >= 2:
        print(f"[demo] feedings already exist: {len(existing)}")
    else:
        times = pick_today_times(3)
        amounts = [120, 110, 100]
        for t, amt in zip(times, amounts):
            # RFC3339 with +08 offset
            feeding_time = t.isoformat(timespec="seconds")
            status, res = http_json(
                "POST",
                f"{base}/api/feedings",
                token=token,
                body={
                    "baby_id": int(baby_id),
                    "amount": int(amt),
                    "feeding_time": feeding_time,
                    "input_method": "manual",
                },
            )
            if status != 200:
                print(f"[demo] create feeding failed status={status} payload={res}")
        print("[demo] seeded feedings ok")

    print("")
    print("[demo] ✅ 验收账号已准备好：")
    print(f"[demo] 手机号: {demo_phone}")
    print(f"[demo] 密码:  {demo_password}")


if __name__ == "__main__":
    main()
