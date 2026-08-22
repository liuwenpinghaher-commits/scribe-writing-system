#!/usr/bin/env python3
"""质量判定观测（板块一）：gate 触发率 / vcode 分布 / fail 原因 Top-5。

用法：
  python scripts/observability_quality_stats.py --book main --days 7
  python scripts/observability_quality_stats.py --book main --base-url http://127.0.0.1:8000

连不上接口时打印原因并退出 2，不甩 traceback。
机器数字只给人看运行是否健康，不得当作创作质量放行判据。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone


def _fail(msg: str, code: int = 2) -> int:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False), file=sys.stderr)
    return code


def _get_json(url: str, timeout: float = 8.0) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


def _event_time(ev: dict) -> datetime | None:
    for key in ("ended_at", "started_at", "ts", "created_at"):
        raw = ev.get(key) or (ev.get("payload") or {}).get(key)
        if not raw:
            continue
        text = str(raw).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            continue
    return None


def _vcode(ev: dict) -> str:
    payload = ev.get("payload") or {}
    for src in (
        payload.get("vcode"),
        payload.get("actual_reason"),
        ev.get("actual_reason"),
        payload.get("code"),
        ev.get("verdict"),
    ):
        text = str(src or "").strip()
        if text and text not in ("present", "ok", "green"):
            return text
    status = str(ev.get("status") or payload.get("status") or "")
    if status in ("ok", "failed"):
        return "pass" if status == "ok" else "fail"
    return ""


def _fail_reason(ev: dict) -> str:
    payload = ev.get("payload") or {}
    for src in (payload.get("message"), ev.get("message"), payload.get("actual_reason"), ev.get("actual_reason")):
        text = str(src or "").strip()
        if text:
            return text[:120]
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="质量判定观测统计")
    parser.add_argument("--book", default="main", help="书 id，对应 work")
    parser.add_argument("--days", type=int, default=7, help="回看天数")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SCRIBE3_BASE_URL", "http://127.0.0.1:8000"),
        help="后端根地址，默认本机或环境变量 SCRIBE3_BASE_URL",
    )
    args = parser.parse_args(argv)

    base = str(args.base_url).rstrip("/")
    query = urllib.parse.urlencode({
        "work": args.book,
        "step_key": "playbook.judge",
        "limit": 2048,
    })
    url = f"{base}/debug/pipeline-events?{query}"
    data = None
    try:
        data = _get_json(url)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            try:
                from scribe3.api import app_impl as core
                st = core._store_for(args.book)
                items = st.list_pipeline_events(
                    work=args.book, step_key="playbook.judge", limit=2048,
                ) or []
                data = {"ok": True, "items": items, "source": "store"}
                url = "store:list_pipeline_events"
            except Exception as store_exc:  # noqa: BLE001
                return _fail(
                    f"{url} 需要登录（HTTP {exc.code}），进程内读取也失败：{store_exc}"
                )
        else:
            return _fail(f"连不上 {url}：HTTP {exc.code}")
    except urllib.error.URLError as exc:
        return _fail(f"连不上 {url}：{exc.reason if getattr(exc, 'reason', None) else exc}")
    except TimeoutError:
        return _fail(f"连不上 {url}：超时")
    except json.JSONDecodeError:
        return _fail(f"{url} 返回的不是 JSON")
    except Exception as exc:  # noqa: BLE001 — 必须 graceful，禁止把栈甩给作者
        return _fail(f"读取失败：{type(exc).__name__}: {exc}")

    if data.get("ok") is False:
        return _fail(str(data.get("error") or "debug 接口报错"))

    items = list(data.get("items") or [])
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(args.days)))
    windowed = []
    for ev in items:
        when = _event_time(ev)
        if when is None or when.tzinfo is None:
            windowed.append(ev)
            continue
        if when >= cutoff:
            windowed.append(ev)

    vcodes = Counter()
    fail_reasons = Counter()
    judged = 0
    gated = 0
    for ev in windowed:
        judged += 1
        payload = ev.get("payload") or {}
        if ev.get("step_key") == "playbook.judge" or payload.get("gate") or payload.get("code"):
            gated += 1
        code = _vcode(ev)
        if code:
            vcodes[code] += 1
        if code and code != "pass":
            reason = _fail_reason(ev) or code
            fail_reasons[reason] += 1

    gate_rate = (gated / judged) if judged else 0.0
    out = {
        "ok": True,
        "book": args.book,
        "days": int(args.days),
        "source": url,
        "judged": judged,
        "gate_triggers": gated,
        "gate_rate": round(gate_rate, 4),
        "vcode": dict(vcodes.most_common()),
        "fail_reasons_top5": [
            {"reason": reason, "count": count}
            for reason, count in fail_reasons.most_common(5)
        ],
        "note": "只观测运行是否健康，不得当作创作质量放行判据。",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
