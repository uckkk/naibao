#!/usr/bin/env python3

"""
API 功能冒烟测试（本地 / CI 友好，无第三方依赖）

覆盖核心链路：
- 注册 / 登录 / 获取用户信息 / 更新头像
- 宝宝创建 / 查询 / 家庭成员
- 奶粉品牌 / 选择奶粉 / 查询当前奶粉
- 喂奶设置 / 下次喂奶时间
- 创建喂养记录 / 查询列表 / 统计 / 每日记录
"""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request


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


def must(status: int, ok: bool, msg: str, payload: dict) -> None:
    if not ok:
        raise SystemExit(f"❌ {msg}\nstatus={status}\npayload={json.dumps(payload, ensure_ascii=False, indent=2)}")


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
    raise SystemExit(f"❌ 后端健康检查超时: {url}\nlast={last}")


def main() -> None:
    base = os.environ.get("API_BASE", "http://localhost:8080").rstrip("/")
    print(f"[smoke] API_BASE={base}")

    wait_health(base)
    print("[smoke] ✅ /health ok")

    # Register/Login
    phone = "13" + "".join(str(random.randint(0, 9)) for _ in range(9))
    password = "test123456"

    status, reg = http_json(
        "POST",
        f"{base}/api/public/register",
        body={
            "phone": phone,
            "password": password,
            "nickname": "SmokeTest",
            "avatar_url": "/static/avatars/avatar_1.png",
        },
    )
    must(status, status == 200 and "token" in reg and "user" in reg, "注册失败", reg)
    token = reg["token"]
    user_id = reg["user"]["id"]
    print(f"[smoke] ✅ register user_id={user_id}")

    status, login = http_json(
        "POST",
        f"{base}/api/public/login",
        body={"phone": phone, "password": password},
    )
    must(status, status == 200 and "token" in login, "登录失败", login)
    token = login["token"]
    print("[smoke] ✅ login")

    # Profile + avatar update
    status, profile = http_json("GET", f"{base}/api/user/profile", token=token)
    must(status, status == 200 and profile.get("user", {}).get("id") == user_id, "获取用户信息失败", profile)
    print("[smoke] ✅ profile")

    status, upd = http_json(
        "PUT",
        f"{base}/api/user/avatar",
        token=token,
        body={"avatar_url": "/static/avatars/avatar_2.png"},
    )
    must(status, status == 200 and upd.get("user", {}).get("avatar_url") == "/static/avatars/avatar_2.png", "更新头像失败", upd)
    print("[smoke] ✅ update avatar")

    # Create baby
    status, created = http_json(
        "POST",
        f"{base}/api/babies",
        token=token,
        body={
            "nickname": "宝宝A",
            "avatar_url": "/static/avatars/avatar_3.png",
            "birth_date": "2025-01-01",
            "birth_time": "12:00:00",
            "gender": "male",
        },
    )
    must(status, status == 200 and "baby" in created and "id" in created["baby"], "创建宝宝失败", created)
    baby_id = created["baby"]["id"]
    print(f"[smoke] ✅ create baby baby_id={baby_id}")

    status, babies = http_json("GET", f"{base}/api/babies", token=token)
    must(status, status == 200 and any(b.get("id") == baby_id for b in babies.get("babies", [])), "查询宝宝列表失败", babies)
    print("[smoke] ✅ list babies")

    status, baby = http_json("GET", f"{base}/api/babies/{baby_id}", token=token)
    must(status, status == 200 and baby.get("baby", {}).get("id") == baby_id, "查询宝宝详情失败", baby)
    print("[smoke] ✅ get baby")

    status, members = http_json("GET", f"{base}/api/babies/{baby_id}/family-members", token=token)
    must(status, status == 200 and len(members.get("members", [])) >= 1, "查询家庭成员失败", members)
    print("[smoke] ✅ family members")

    # Formula brands & selection
    status, brands = http_json("GET", f"{base}/api/formula/brands", token=token)
    must(status, status == 200 and len(brands.get("brands", [])) >= 1, "获取奶粉品牌失败", brands)
    brand_id = brands["brands"][0]["id"]
    print(f"[smoke] ✅ formula brands brand_id={brand_id}")

    status, sel = http_json(
        "POST",
        f"{base}/api/babies/{baby_id}/formula",
        token=token,
        body={"brand_id": brand_id, "series_name": "测试系列", "age_range": "0-6"},
    )
    must(status, status == 200, "选择奶粉失败", sel)
    print("[smoke] ✅ select formula")

    status, cur = http_json("GET", f"{base}/api/babies/{baby_id}/formula", token=token)
    must(status, status == 200 and cur.get("selection", {}).get("brand_id") == brand_id, "获取当前奶粉失败", cur)
    print("[smoke] ✅ current formula")

    # Feeding settings + next time
    status, settings = http_json("GET", f"{base}/api/babies/{baby_id}/settings", token=token)
    must(status, status == 200 and "settings" in settings, "获取喂奶设置失败", settings)
    print("[smoke] ✅ get settings")

    status, settings2 = http_json(
        "PUT",
        f"{base}/api/babies/{baby_id}/settings",
        token=token,
        body={"day_interval": 3, "night_interval": 5, "day_start_hour": 6, "day_end_hour": 18},
    )
    must(status, status == 200 and settings2.get("settings", {}).get("day_interval") == 3, "更新喂奶设置失败", settings2)
    print("[smoke] ✅ update settings")

    status, next_time = http_json("GET", f"{base}/api/babies/{baby_id}/next-feeding-time", token=token)
    must(status, status == 200 and "next_feeding_timestamp" in next_time, "获取下次喂奶时间失败", next_time)
    print("[smoke] ✅ next feeding time")

    # Create feeding + list + stats + daily records
    status, feeding = http_json(
        "POST",
        f"{base}/api/feedings",
        token=token,
        body={
            "baby_id": baby_id,
            "amount": 120,
            "formula_brand_id": brand_id,
            "formula_series_name": "测试系列",
            "scoops": 4,
        },
    )
    must(status, status == 200 and "feeding" in feeding and "id" in feeding["feeding"], "创建喂养记录失败", feeding)
    feeding_id = feeding["feeding"]["id"]
    print(f"[smoke] ✅ create feeding feeding_id={feeding_id}")

    qs = urllib.parse.urlencode({"baby_id": str(baby_id)})
    status, feedings = http_json("GET", f"{base}/api/feedings?{qs}", token=token)
    must(status, status == 200 and len(feedings.get("feedings", [])) >= 1, "查询喂养记录列表失败", feedings)
    print("[smoke] ✅ list feedings")

    status, stats = http_json("GET", f"{base}/api/feedings/stats?{qs}", token=token)
    must(status, status == 200 and "stats" in stats and "recommended" in stats, "获取喂养统计失败", stats)
    print("[smoke] ✅ feeding stats")

    month = time.strftime("%Y-%m")
    status, daily = http_json("GET", f"{base}/api/babies/{baby_id}/daily-records?{urllib.parse.urlencode({'month': month})}", token=token)
    must(status, status == 200 and isinstance(daily.get("records"), list), "获取每日记录失败", daily)
    print("[smoke] ✅ daily records")

    # Update feeding (basic)
    status, upd_feed = http_json(
        "PUT",
        f"{base}/api/feedings/{feeding_id}",
        token=token,
        body={"amount": 130},
    )
    must(status, status == 200 and upd_feed.get("feeding", {}).get("amount") == 130, "更新喂养记录失败", upd_feed)
    print("[smoke] ✅ update feeding")

    print("[smoke] 🎉 ALL PASSED")


if __name__ == "__main__":
    main()
