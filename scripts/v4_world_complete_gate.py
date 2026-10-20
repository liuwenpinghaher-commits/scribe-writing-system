#!/usr/bin/env python3
"""v4 设定完成门闩（World Complete Gate）。

未 exit 0 禁止任何验收向 draft_loop / 定稿。
用法：
  export SCRIBE3_BOOTSTRAP_USERS=admin:chris0120
  export API_BASE=http://127.0.0.1:8088   # 或 https://tonglu.example.com
  python3 scripts/v4_world_complete_gate.py --slug book_xxx
  # 可选 --out artifacts/.../00-world-complete-gate.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8088")
JAR = os.environ.get("COOKIE_JAR", "/tmp/v4_wcg_cookie.txt")


def cn_len(s: str) -> int:
    return len(re.sub(r"\s+", "", s or ""))


def curl(method: str, path: str, data=None, timeout: int = 120, work: str = ""):
    urlpath = path
    if (
        path.startswith("/api/")
        and "work=" not in path
        and path not in ("/api/auth/login", "/api/works", "/api/health", "/api/ready")
        and not path.startswith("/api/works/")
        and work
    ):
        urlpath += ("&" if "?" in path else "?") + "work=" + work
    out = Path("/tmp/v4_wcg_out.json")
    cmd = [
        "curl", "-sS", "-o", str(out), "-w", "%{http_code}",
        "-b", JAR, "-c", JAR, "-X", method,
        "-H", "Origin: " + BASE,
        "--max-time", str(timeout),
    ]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data, ensure_ascii=False)]
    cmd.append(BASE + urlpath)
    p = subprocess.run(cmd, capture_output=True, text=True)
    body = out.read_text() if out.exists() else ""
    try:
        j = json.loads(body) if body else None
    except Exception:
        j = body
    return p.stdout.strip(), j


def login():
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    u, p = bu.split(":", 1)
    subprocess.run(["rm", "-f", JAR], check=False)
    code, _ = curl("POST", "/api/auth/login", {"username": u, "password": p})
    if code != "200":
        raise SystemExit(f"login failed {code}")


def check(name: str, ok: bool, detail: str, fails: list, passes: list):
    row = {"check": name, "ok": ok, "detail": detail}
    (passes if ok else fails).append(row)
    mark = "OK" if ok else "FAIL"
    print(f"  [{mark}] {name}: {detail}", flush=True)


def run_gate(slug: str) -> dict:
    fails: list = []
    passes: list = []

    code, intent = curl("GET", "/api/intent", work=slug)
    intent = intent if isinstance(intent, dict) else {}
    rf = (intent.get("reader_feeling") or "").strip()
    ea = (intent.get("emotional_arc") or "").strip()
    rl = (intent.get("red_lines") or "").strip()
    twg = intent.get("total_word_goal")
    check("intent.reader_feeling", cn_len(rf) >= 10, f"len={cn_len(rf)}", fails, passes)
    check("intent.emotional_arc", cn_len(ea) >= 4, f"len={cn_len(ea)}", fails, passes)
    check("intent.red_lines", rl.count("\n") + 1 >= 3 or cn_len(rl) >= 20, f"preview={rl[:60]!r}", fails, passes)
    from scribe3.structure_budget import word_goal_accepted
    check(
        "intent.total_word_goal",
        word_goal_accepted(twg),
        f"goal={twg}",
        fails,
        passes,
    )

    code, ents = curl("GET", "/api/entities", work=slug)
    ents = ents if isinstance(ents, list) else []
    chars = [e for e in ents if (e.get("kind") or "character") == "character" or e.get("id", "").startswith("role:")]
    check("characters.count>=4", len(chars) >= 4, f"n={len(chars)}", fails, passes)

    required = ["appearance", "personality_detail", "surface_goal", "deep_need", "fear", "backstory"]
    full = 0
    for e in chars:
        if all((e.get(k) or "").strip() if isinstance(e.get(k), str) else e.get(k) for k in required):
            full += 1
    check(
        "characters.codex_full(backstory+5fields)",
        full >= 4,
        f"full={full}/{len(chars)} names={[e.get('name') for e in chars]}",
        fails,
        passes,
    )
    protag = any((e.get("importance") or "") == "protagonist" for e in chars)
    check("characters.has_protagonist", protag, f"importance values", fails, passes)

    # relations — try common endpoints
    rel_count = 0
    for path in (
        "/api/character-relations",
        "/api/relations",
        "/api/graph",
    ):
        code, data = curl("GET", path, work=slug)
        if code != "200":
            continue
        if isinstance(data, list):
            rel_count = max(rel_count, len(data))
        elif isinstance(data, dict):
            edges = data.get("edges") or data.get("links") or data.get("relations") or []
            if isinstance(edges, list):
                # count non-chapter edges if possible
                rel_count = max(rel_count, len(edges))
    check("relations.ge3_or_graph_edges", rel_count >= 3, f"rel_or_edges={rel_count}", fails, passes)

    # world rules / facts
    rules_n = 0
    facts_n = 0
    for path in ("/api/world-rules", "/api/rules", "/api/codex/world-rules"):
        code, data = curl("GET", path, work=slug)
        if code == "200" and isinstance(data, list):
            rules_n = max(rules_n, len(data))
    # facts often need chapter
    for ch in (1, 5, 10):
        code, data = curl("GET", f"/api/facts?chapter={ch}", work=slug)
        if code == "200" and isinstance(data, list):
            facts_n = max(facts_n, len(data))
        elif code == "200" and isinstance(data, dict):
            items = data.get("facts") or data.get("items") or []
            if isinstance(items, list):
                facts_n = max(facts_n, len(items))
    # graph nodes as weak fallback for facts
    code, graph = curl("GET", "/api/graph", work=slug)
    g_nodes = (graph or {}).get("nodes") if isinstance(graph, dict) else []
    fact_nodes = [n for n in (g_nodes or []) if (n.get("type") or "") in ("proposition", "fact", "world_rule")]
    if rules_n < 3 and len(fact_nodes) >= 3:
        rules_n = len(fact_nodes)  # soft: graph propositions stand in for rules audit
    check("world_rules_or_propositions.ge3", rules_n >= 3, f"rules={rules_n} fact_nodes={len(fact_nodes)}", fails, passes)
    check("facts.ge5_or_graph", facts_n >= 5 or len(fact_nodes) >= 5, f"facts={facts_n} prop_nodes={len(fact_nodes)}", fails, passes)

    # factions / items / terms via entities kinds or dedicated APIs
    kinds = {}
    for e in ents:
        k = e.get("kind") or "character"
        kinds[k] = kinds.get(k, 0) + 1
    for path, key in (
        ("/api/factions", "faction"),
        ("/api/items", "item"),
        ("/api/terms", "term"),
    ):
        code, data = curl("GET", path, work=slug)
        if code == "200" and isinstance(data, list):
            kinds[key] = max(kinds.get(key, 0), len(data))
    # at least 2 of 3 categories non-empty, or item+term counts
    cat_ok = sum(1 for k in ("faction", "item", "term") if kinds.get(k, 0) >= 1) >= 2
    if not cat_ok:
        # allow graph labels containing 门/契/灯 as weak signal — still fail clearly
        pass
    check(
        "faction_item_term.two_categories",
        cat_ok or (kinds.get("item", 0) + kinds.get("term", 0) + kinds.get("faction", 0) >= 3),
        f"kinds={kinds}",
        fails,
        passes,
    )

    code, proms = curl("GET", "/api/promises", work=slug)
    proms = proms if isinstance(proms, list) else []
    check("promises.ge3", len(proms) >= 3, f"n={len(proms)}", fails, passes)

    # 开书强制母题：与 bible_motifs.MIN_BIBLE_MOTIFS / craft GATE-A 对齐
    code, motifs = curl("GET", "/api/motifs", work=slug)
    motifs = motifs if isinstance(motifs, list) else []
    named_motifs = [m for m in motifs if isinstance(m, dict) and (m.get("name") or "").strip()]
    check(
        "motifs.ge3",
        len(named_motifs) >= 3,
        f"n={len(named_motifs)} names={[m.get('name') for m in named_motifs[:8]]}",
        fails,
        passes,
    )

    code, vols = curl("GET", "/api/volumes", work=slug)
    vols = vols if isinstance(vols, list) else []
    check("volumes.ge3", len(vols) >= 3, f"n={len(vols)}", fails, passes)
    intro_ok = 0
    for v in vols:
        if not isinstance(v, dict):
            continue
        intro = v.get("intro") or v.get("duty") or v.get("summary") or ""
        if cn_len(str(intro)) >= 40:
            intro_ok += 1
    if isinstance(twg, int) and twg >= 200_000:
        check("volume.intro.ge3", intro_ok >= 3, f"intro_ok={intro_ok}/{len(vols)}", fails, passes)

    code, chs = curl("GET", "/api/chapters", work=slug)
    chs = chs if isinstance(chs, list) else []
    check("chapters.ge10", len(chs) >= 10, f"n={len(chs)}", fails, passes)

    syn_ok = 0
    align_ok = 0
    char_names = [e.get("name") or "" for e in chars]
    for seq in range(1, 11):
        code, ch = curl("GET", f"/api/chapter?seq={seq}", work=slug)
        if not isinstance(ch, dict):
            continue
        syn = (ch.get("synopsis") or "").strip()
        if cn_len(syn) >= 40:
            syn_ok += 1
        if any(n and n in syn for n in char_names):
            align_ok += 1
        foc = (ch.get("focalizer") or "")
        if foc and any(n and n in foc for n in char_names):
            align_ok += 0  # already counted via names; focalizer presence separate
    check("synopsis.ge40chars.ge10", syn_ok >= 10, f"syn_ok={syn_ok}", fails, passes)
    check("synopsis.mentions_character.ge8", align_ok >= 8, f"align={align_ok}", fails, passes)

    report = {
        "slug": slug,
        "pass": len(fails) == 0,
        "fail_count": len(fails),
        "pass_count": len(passes),
        "fails": fails,
        "passes": passes,
        "policy": "WCG must pass before any acceptance draft_loop",
    }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    login()
    print(f"WCG audit work={args.slug}", flush=True)
    report = run_gate(args.slug)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("wrote", args.out, flush=True)
    print(json.dumps({"pass": report["pass"], "fail_count": report["fail_count"]}, ensure_ascii=False), flush=True)
    sys.exit(0 if report["pass"] else 2)


if __name__ == "__main__":
    main()
