#!/usr/bin/env python3
"""预算头寸采样（本地 config 表 或 demo budget-probe）。

用法::

  PYTHONPATH=. python -m scribe3.tools.sample_budget_report --out /tmp/b.json

  PYTHONPATH=. python -m scribe3.tools.sample_budget_report \\
    --url https://tonglu.qing.blue --mode config \\
    --cookie-jar /tmp/smoke.cookies --out /tmp/budget_demo.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from http.cookiejar import MozillaCookieJar
from pathlib import Path


def sample_local(*, beat_type: str | None = "dialogue") -> dict:
    """从 context_budget 采样 L0/L1/L2 头寸（不连库）。"""
    os.environ.setdefault("SCRIBE3_ENVELOPE_V2_ENABLE", "1")
    os.environ.setdefault("SCRIBE3_ENVELOPE_NOVEL", "1")
    os.environ.setdefault("SCRIBE3_ADAPTIVE_BUDGET", "1")

    from scribe3.context_budget import (
        BLOCK_BUDGETS_NOVEL,
        NOVEL_ENVELOPE_TOKEN_BUDGET,
        NOVEL_PROMPT_HARD,
        build_budget_report,
        context_fidelity,
        get_block_budgets,
        get_envelope_token_budget,
        get_prompt_hard,
        get_total_prompt_budget,
    )

    bb = get_block_budgets(beat_type=beat_type)
    rep = build_budget_report(beat_type=beat_type)
    env = get_envelope_token_budget()
    hard = get_prompt_hard()
    total = get_total_prompt_budget()
    l1 = env
    l2_room = max(0, hard - env)
    conclusion = (
        "48k 头寸够用（novel 22k envelope + L2 余量）"
        if hard >= NOVEL_PROMPT_HARD and env >= NOVEL_ENVELOPE_TOKEN_BUDGET * 0.95
        else "头寸偏紧或 fidelity 非 novel，请查 env"
    )
    return {
        "source": "local",
        "fidelity": context_fidelity(),
        "beat_type": beat_type,
        "block_budgets": bb,
        "block_sum": sum(bb.values()),
        "novel_base_sum": sum(BLOCK_BUDGETS_NOVEL.values()),
        "L0_note": "redline/L0 永不整段丢（见 L0_NEVER_CUT）",
        "L1_envelope": l1,
        "L2_room_est": l2_room,
        "effective_L2_est": l2_room,
        "prompt_hard": hard,
        "total_prompt_budget": total,
        "budget_report_keys": sorted(rep.keys()),
        "registry_mode": rep.get("registry_mode"),
        "adaptive_profile": rep.get("adaptive_profile"),
        "event_graph_k": (rep.get("event_graph") or {}).get("k"),
        "conclusion": conclusion,
        "primary_metric": "signal_density_for_drama",
        "not_a_kpi": "tokens_saved",
    }


def sample_remote(
    *,
    url: str,
    mode: str = "config",
    work: str = "main",
    seq: int = 1,
    cookie_jar: str = "",
    user: str = "",
    password: str = "",
    beat_type: str | None = "dialogue",
) -> dict:
    """打已部署 POST /api/debug/budget-probe（需登录 cookie 或 USER/PASS）。"""
    base = url.rstrip("/")
    jar_path = cookie_jar or ""
    cj = MozillaCookieJar()
    if jar_path and Path(jar_path).is_file():
        try:
            cj.load(jar_path, ignore_discard=True, ignore_expires=True)
        except Exception:
            pass
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def _req(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        r = urllib.request.Request(base + path, data=data, headers=headers, method=method)
        try:
            with opener.open(r, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                code = getattr(resp, "status", 200) or 200
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            code = e.code
        try:
            return code, json.loads(raw)
        except Exception:
            return code, raw

    if user and password:
        code, _ = _req("POST", "/api/auth/login", {"username": user, "password": password})
        if code not in (200, 204) and code != 401:
            pass  # soft
        if jar_path:
            try:
                Path(jar_path).parent.mkdir(parents=True, exist_ok=True)
                cj.save(jar_path, ignore_discard=True, ignore_expires=True)
            except Exception:
                pass

    body = {"mode": mode or "config", "work": work, "seq": int(seq), "beat_type": beat_type}
    code, data = _req("POST", "/api/debug/budget-probe", body)
    if isinstance(data, dict):
        data = dict(data)
        data["http_status"] = code
        data["source"] = "remote"
        data["url"] = base
        if code == 200:
            hard = int(data.get("prompt_hard") or 0)
            env = int(data.get("L1_envelope") or 0)
            data["conclusion"] = (
                "48k 头寸够用（remote config）"
                if hard >= 48000 and env >= 20000
                else data.get("note") or "见 prompt_hard / L1_envelope"
            )
        else:
            data["conclusion"] = f"remote HTTP {code}"
        return data
    return {
        "source": "remote",
        "http_status": code,
        "error": str(data)[:500],
        "conclusion": f"remote fail {code}",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="sample budget report headroom")
    ap.add_argument("--out", default="", help="write JSON path")
    ap.add_argument("--beat-type", default="dialogue")
    ap.add_argument("--url", default="", help="demo base e.g. https://tonglu.qing.blue")
    ap.add_argument("--mode", default="config", choices=("config", "assemble"))
    ap.add_argument("--work", default="main")
    ap.add_argument("--seq", type=int, default=1)
    ap.add_argument("--cookie-jar", default="", help="cookie jar path for auth")
    ap.add_argument("--user", default=os.environ.get("SMOKE_USER") or os.environ.get("USER") or "")
    ap.add_argument("--password", default=os.environ.get("SMOKE_PASS") or os.environ.get("PASS") or "")
    args = ap.parse_args(argv)

    if args.url:
        data = sample_remote(
            url=args.url,
            mode=args.mode,
            work=args.work,
            seq=args.seq,
            cookie_jar=args.cookie_jar,
            user=args.user,
            password=args.password,
            beat_type=args.beat_type or None,
        )
    else:
        data = sample_local(beat_type=args.beat_type or None)

    text = json.dumps(data, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(f"# wrote {p}", file=sys.stderr)
    print(f"# conclusion: {data.get('conclusion')}", file=sys.stderr)
    return 0 if (not args.url or data.get("http_status") in (200, 401)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
