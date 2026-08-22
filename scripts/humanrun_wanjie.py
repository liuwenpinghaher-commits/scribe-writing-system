#!/usr/bin/env python3
"""真人建书 workflow 执行器（N 可指定，默认 1）。

通道纪律：
- 建书：POST /api/works（与 UI 新建同一条）
- 设定：POST /orchestration/resolve + POST /ai/runs + 点批审批卡
- 禁止 curl s3_add_*，禁止 pad，禁止续写旧书
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.humanrun_wanjie_seed import (  # noqa: E402
    CHAPTERS,
    CHARS,
    FOCALIZER,
    INTENT_SPEECH,
    N_DEFAULT,
    NORTH_STAR,
    cn_len,
    speech_chars,
    speech_chapters,
    speech_facts,
    speech_fit,
    speech_motifs,
    speech_promises,
    speech_relations,
    speech_rules,
    speech_stage,
    speech_synopses,
    speech_volumes,
)

BASE = os.environ.get("API_BASE", "https://tonglu.qing.blue")
JAR = os.environ.get("COOKIE_JAR", "/tmp/humanrun_cookie.txt")
WW_INSTRUCTIONS = (
    "这是 scribe3 会改世界状态的主编任务。"
    "作者点名的 s3_* 工具必须调用并等待审批，禁止只口头答应。"
    "按作者原文写入，禁止 s3_generate_codex 另写一套，禁止凑字，禁止改成空话。"
    "未获批准不得声称已落库。剧情事实只进本书库。"
)
TERMINAL = {
    "completed", "completed_unverified", "failed", "stopped", "cancelled",
    "canceled", "approval_expired",
}


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def curl(method: str, path: str, data=None, timeout: int = 180, work: str | None = None):
    urlpath = path
    if (
        work
        and path.startswith("/api/")
        and "work=" not in path
        and path not in ("/api/auth/login", "/api/works", "/api/health", "/api/ready", "/api/capabilities")
        and not path.startswith("/api/works/")
    ):
        urlpath += ("&" if "?" in path else "?") + "work=" + work
    out = Path("/tmp/humanrun_out.json")
    cmd = [
        "curl", "-sS", "-o", str(out), "-w", "%{http_code}",
        "-b", JAR, "-c", JAR, "-X", method,
        "-H", f"Origin: {BASE}", "--max-time", str(timeout),
    ]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json",
                "-d", json.dumps(data, ensure_ascii=False)]
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
    u, pw = bu.split(":", 1)
    subprocess.run(["rm", "-f", JAR], check=False)
    code, res = curl("POST", "/api/auth/login", {"username": u, "password": pw})
    if code != "200":
        raise SystemExit(f"login failed {code} {res}")
    print("LOGIN ok", flush=True)


def getj(path: str, work: str | None = None, timeout: int = 60):
    code, res = curl("GET", path, work=work, timeout=timeout)
    return code, res


class Runner:
    def __init__(self, n: int, evid: Path, slug: str | None):
        self.n = n
        self.evid = evid
        self.slug = slug
        self.state_path = evid / "state.json"
        self.state = {}
        if self.state_path.exists():
            self.state = json.loads(self.state_path.read_text())
            self.slug = self.state.get("slug") or slug

    def save_state(self, **kw):
        self.state.update(kw)
        self.state["slug"] = self.slug
        self.state["updated"] = datetime.now().isoformat()
        dump(self.state_path, self.state)

    def resolve(self, msg: str, chapter: int | None = None):
        body = {
            "message": msg,
            "chapter": chapter,
            "phase": None,
            "action": "auto",
            "activate": True,
        }
        code, res = curl("POST", "/api/orchestration/resolve", body, work=self.slug, timeout=60)
        return code, res if isinstance(res, dict) else {}

    def create_run(self, msg: str, instructions: str, chapter: int | None = None, phase: str = ""):
        code, pkg = self.resolve(msg, chapter=chapter)
        dump(self.evid / "resolve-last.json", {"code": code, "pkg": pkg, "msg_head": msg[:200]})
        ins = instructions
        suf = ""
        if isinstance(pkg, dict):
            suf = str((pkg.get("instruction_suffix") or (pkg.get("package") or {}).get("instruction_suffix") or "")).strip()
            if not suf and isinstance(pkg.get("package"), dict):
                suf = str(pkg["package"].get("instruction_duty") or "").strip()
        if suf:
            ins = ins + "\n\n## 本域纪律\n" + suf
        body = {"input": msg, "instructions": ins}
        if chapter and phase:
            body["run_scope"] = f"chapter:{chapter}:{phase}"
        code, res = curl("POST", "/api/ai/runs", body, work=self.slug, timeout=60)
        if code not in ("200", "201") or not isinstance(res, dict):
            raise RuntimeError(f"ai/runs failed {code} {res}")
        run_id = res.get("run_id") or res.get("id")
        if not run_id:
            raise RuntimeError(f"no run_id {res}")
        print(f"  RUN {run_id} created", flush=True)
        return run_id, pkg

    def pending(self, chapter: int | None = None, phase: str | None = None):
        q = "/api/ai/runs/pending-approvals"
        if chapter and phase:
            q += f"?chapter={chapter}&phase={phase}"
        code, res = getj(q, work=self.slug)
        runs = (res or {}).get("runs") if isinstance(res, dict) else []
        return runs or []

    def approve(self, run_id: str, approval_id: str | None):
        payload = {"decision": "approve"}
        if approval_id:
            payload["approval_id"] = approval_id
        code, res = curl("POST", f"/api/ai/runs/{run_id}/approval", payload, work=self.slug, timeout=60)
        print(f"  APPROVE {run_id} {approval_id} -> {code} {str(res)[:400]}", flush=True)
        return code, res

    def run_status(self, run_id: str):
        code, res = getj(f"/api/ai/runs/{run_id}", work=self.slug)
        return (res or {}) if isinstance(res, dict) else {}

    def wait_run(self, run_id: str, timeout: int = 1200, chapter: int | None = None, phase: str | None = None):
        """等审批卡就点批，直到 Run 终态。"""
        t0 = time.time()
        seen = set()
        last = ""
        while time.time() - t0 < timeout:
            st = self.run_status(run_id)
            status = str(st.get("status") or "").lower()
            if status != last:
                print(f"  status={status}", flush=True)
                last = status
            if status in TERMINAL:
                return st
            cards = []
            cards.extend(self.pending())
            if chapter and phase:
                cards.extend(self.pending(chapter, phase))
            for c in cards:
                if not isinstance(c, dict):
                    continue
                rid = c.get("run_id")
                aid = c.get("approval_id")
                key = f"{rid}:{aid}"
                if rid == run_id and key not in seen:
                    seen.add(key)
                    self.approve(rid, aid)
            # 有时审批挂在 trace 里而 pending 列表空一拍
            code, tr = getj(f"/api/ai/runs/{run_id}/trace", work=self.slug)
            if isinstance(tr, dict):
                tstatus = str(tr.get("status") or "").lower()
                if tstatus in TERMINAL:
                    return tr
                for row in tr.get("approvals") or []:
                    if not isinstance(row, dict):
                        continue
                    aid = row.get("approval_id")
                    dec = row.get("decision")
                    stt = str(row.get("status") or "requested").lower()
                    key = f"{run_id}:{aid}"
                    if aid and key not in seen and dec is None and stt in {"requested", "pending"}:
                        seen.add(key)
                        self.approve(run_id, aid)
            time.sleep(4)
        raise TimeoutError(f"run {run_id} timeout after {timeout}s last={last}")

    def world_write(self, tag: str, msg: str, timeout: int = 1200, chapter: int | None = None, phase: str = ""):
        print(f"\n== {tag} ==", flush=True)
        (self.evid / "transcript").mkdir(exist_ok=True)
        (self.evid / "transcript" / f"{tag}.txt").write_text(msg, encoding="utf-8")
        extra = (
            "\n\n必须实际产生 MCP 函数调用事件，禁止只输出 XML/tool_search 文本。"
            "搜到工具后必须立刻 tool_call，不得把 Run 说成完成。"
        )
        last = None
        for attempt, text in enumerate((msg, msg + extra), start=1):
            run_id, pkg = self.create_run(text, WW_INSTRUCTIONS, chapter=chapter, phase=phase)
            st = self.wait_run(run_id, timeout=timeout, chapter=chapter, phase=phase or None)
            code, tr = getj(f"/api/ai/runs/{run_id}/trace", work=self.slug)
            calls = (tr or {}).get("tool_calls") if isinstance(tr, dict) else []
            effects = (tr or {}).get("write_effects") if isinstance(tr, dict) else []
            approvals = (tr or {}).get("approvals") if isinstance(tr, dict) else []
            outputs = (tr or {}).get("tool_outputs") if isinstance(tr, dict) else []
            ok_calls, bad_calls = _s3_call_split(calls, outputs)
            dump(self.evid / f"run-{tag}.json", {
                "run_id": run_id, "status": st, "pkg": pkg, "attempt": attempt,
                "n_tool_calls": len(calls or []), "n_approvals": len(approvals or []),
                "n_write_effects": len(effects or []),
                "n_s3_ok": len(ok_calls), "n_s3_bad": len(bad_calls),
            })
            last = (run_id, st)
            if approvals or effects or ok_calls:
                return run_id, st
            if bad_calls:
                print(f"  WARN {tag} attempt {attempt} 工具调用失败/超时 {len(bad_calls)} 次", flush=True)
            else:
                print(f"  WARN {tag} attempt {attempt} 无工具调用/审批卡，模型可能只写了假 XML", flush=True)
        raise RuntimeError(f"{tag} 两次主编 Run 都没有真正写入")

    # —— 只读回读 ——
    def intent(self):
        _, res = getj("/api/intent", work=self.slug)
        return res if isinstance(res, dict) else {}

    def entities(self):
        _, res = getj("/api/entities", work=self.slug)
        return res if isinstance(res, list) else []

    def chapters(self):
        _, res = getj("/api/chapters", work=self.slug)
        return res if isinstance(res, list) else []

    def volumes(self):
        _, res = getj("/api/volumes", work=self.slug)
        return res if isinstance(res, list) else []


def s0(r: Runner) -> None:
    print("\n==== S0 baseline ====", flush=True)
    code, health = getj("/api/health", timeout=30)
    started = None
    if isinstance(health, dict):
        started = (health.get("changefeed") or {}).get("started_at")
    git = subprocess.run(
        ["git", "log", "-1", "origin/main", "--format=%H %ci %s"],
        cwd=str(ROOT), capture_output=True, text=True,
    ).stdout.strip()
    pb = "playbook.3.2.3"
    started_iso = None
    if isinstance(started, (int, float)):
        started_iso = datetime.fromtimestamp(float(started)).isoformat()
    rec = {
        "health": health,
        "health_http": code,
        "origin_main": git,
        "playbook": pb,
        "started_at": started,
        "started_iso": started_iso,
        "note": "docs-only commit 不要求进程晚于方案文档；产品代码指纹以 playbook.3.2.3 + 已部署 pipeline 为准",
    }
    dump(r.evid / "00-baseline.json", rec)
    print("  health", code, "started", started_iso, "git", git[:80], flush=True)


def s1(r: Runner) -> None:
    print("\n==== S1 建书 ====", flush=True)
    if r.slug:
        print("  resume slug", r.slug, flush=True)
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    title = f"万界概率战争·真人建书·N{r.n}·{stamp}"
    code, res = curl("POST", "/api/works", {"title": title}, timeout=120)
    if code not in ("200", "201") or not isinstance(res, dict):
        raise SystemExit(f"create work failed {code} {res}")
    slug = res.get("slug") or res.get("id") or res.get("work")
    if not slug:
        _, works = getj("/api/works")
        if isinstance(works, list):
            hit = next((w for w in works if (w.get("title") or "") == title), None)
            slug = (hit or {}).get("slug") or (hit or {}).get("id")
    if not slug:
        raise SystemExit(f"no slug in {res}")
    r.slug = slug
    r.save_state(title=title, phase="s1")
    _, chs = getj("/api/chapters", work=slug)
    dump(r.evid / "01-work.json", {"title": title, "slug": slug, "create": res, "chapters": chs})
    print("  slug", slug, "chapters", chs if isinstance(chs, list) else type(chs), flush=True)


def s2(r: Runner) -> None:
    print("\n==== S2 意图 ====", flush=True)
    r.world_write("S2-intent", INTENT_SPEECH)
    intent = r.intent()
    dump(r.evid / "01-intent.json", intent)
    ns = (intent.get("north_star") or "").strip()
    rf = intent.get("reader_feeling") or ""
    ea = intent.get("emotional_arc") or ""
    rl = intent.get("red_lines") or ""
    twg = intent.get("total_word_goal")
    ok = bool(ns) and cn_len(rf) >= 10 and cn_len(ea) >= 4 and (
        str(rl).count("\n") + 1 >= 3 or cn_len(str(rl)) >= 20
    ) and isinstance(twg, int) and 40000 <= twg <= 60000
    generic = ("任何小说" in ns) or (ns and ns in ("写出好故事", "感动读者"))
    print("  north_star", ns[:80], "ok", ok, "generic", generic, flush=True)
    if not ok:
        print("  WARN intent 未齐，再催一枪", flush=True)
        r.world_write("S2-intent-retry", INTENT_SPEECH + "\n请把缺的字段补全，north_star 必须是这本书自己的方向。")
        intent = r.intent()
        dump(r.evid / "01-intent.json", intent)
    r.save_state(phase="s2")


def s3(r: Runner) -> None:
    print("\n==== S3 设定库 ====", flush=True)
    batches = [
        ("B1-chars", speech_chars(), lambda: len([e for e in r.entities() if (e.get("kind") or "character") == "character" or str(e.get("id") or "").startswith("role:")]) >= 4),
        ("B2-rel", speech_relations(), None),
        ("B3-rules", speech_rules(), None),
        ("B4-facts", speech_facts(), None),
        ("B5-fit", speech_fit(), None),
        ("B6-motifs", speech_motifs(), None),
        ("B7-promises", speech_promises(), None),
    ]
    done = set(r.state.get("s3_done") or [])
    for tag, msg, chk in batches:
        if tag in done:
            print(f"  skip {tag}", flush=True)
            continue
        r.world_write(tag, msg)
        code, snap = _codex_snapshot(r)
        dump(r.evid / f"02-codex-{tag}.json", snap)
        if chk and not chk():
            print(f"  WARN {tag} 回读未齐，再催一枪", flush=True)
            r.world_write(tag + "-retry", msg)
            _, snap = _codex_snapshot(r)
            dump(r.evid / f"02-codex-{tag}.json", snap)
        done.add(tag)
        r.save_state(phase="s3", s3_done=sorted(done))


def _codex_snapshot(r: Runner) -> tuple[str, dict]:
    snap = {}
    for path, key in (
        ("/api/entities", "entities"),
        ("/api/character-relations", "relations"),
        ("/api/world-rules", "rules"),
        ("/api/facts?chapter=1", "facts"),
        ("/api/factions", "factions"),
        ("/api/items", "items"),
        ("/api/terms", "terms"),
        ("/api/motifs", "motifs"),
        ("/api/promises", "promises"),
    ):
        code, res = getj(path, work=r.slug)
        snap[key] = {"http": code, "data": res}
    return "200", snap


def s4(r: Runner) -> None:
    print("\n==== S4 结构 ====", flush=True)
    if "B8-vol" not in (r.state.get("s4_done") or []):
        r.world_write("B8-vol", speech_volumes())
        r.save_state(s4_done=list(set(r.state.get("s4_done") or []) | {"B8-vol"}))
    vols = r.volumes()
    dump(r.evid / "03-volumes.json", vols)
    # 按 sort_order / 标题对齐
    ids = []
    by_title = { (v.get("title") or ""): v for v in vols if isinstance(v, dict) }
    for want in ("囚笼", "泄露", "第三条路"):
        hit = by_title.get(want) or {}
        vid = hit.get("id") or hit.get("volume_id") or ""
        if isinstance(vid, str) and ":" in vid:
            vid = vid.split(":")[-1]
        ids.append(str(vid))
    if "B8-ch" not in (r.state.get("s4_done") or []):
        r.world_write("B8-ch", speech_chapters(ids))
        r.save_state(s4_done=list(set(r.state.get("s4_done") or []) | {"B8-ch"}))
    chs = r.chapters()
    if "B8-syn" not in (r.state.get("s4_done") or []):
        r.world_write("B8-syn", speech_synopses())
        r.save_state(s4_done=list(set(r.state.get("s4_done") or []) | {"B8-syn"}))
    structure = {
        "volumes": r.volumes(),
        "chapters": r.chapters(),
        "synopses": [],
    }
    for spec in CHAPTERS:
        _, ch = getj(f"/api/chapter?seq={spec['seq']}", work=r.slug)
        syn = (ch or {}).get("synopsis") if isinstance(ch, dict) else ""
        structure["synopses"].append({
            "seq": spec["seq"],
            "title": (ch or {}).get("title") if isinstance(ch, dict) else "",
            "synopsis": syn,
            "len": cn_len(syn or ""),
        })
    dump(r.evid / "03-structure.json", structure)
    r.save_state(phase="s4")


def antipad(r: Runner) -> dict:
    syns = []
    for spec in CHAPTERS:
        _, ch = getj(f"/api/chapter?seq={spec['seq']}", work=r.slug)
        syn = ((ch or {}).get("synopsis") or "") if isinstance(ch, dict) else ""
        syns.append(re.sub(r"\s+", "", syn))
    similar = 0
    pairs = []
    for i in range(len(syns)):
        for j in range(i + 1, len(syns)):
            a, b = syns[i], syns[j]
            if not a or not b:
                continue
            if a == b or (len(a) > 20 and a[:20] == b[:20]):
                similar += 1
                pairs.append((i + 1, j + 1))
    ents = r.entities()
    chars = [e for e in ents if (e.get("kind") or "character") == "character" or str(e.get("id") or "").startswith("role:")]
    fields = []
    for e in chars:
        for k in ("personality_detail", "backstory", "surface_goal", "deep_need", "fear"):
            v = re.sub(r"\s+", "", (e.get(k) or "") if isinstance(e.get(k), str) else "")
            if v:
                fields.append((e.get("name"), k, v))
    dup = 0
    dup_hits = []
    for i in range(len(fields)):
        for j in range(i + 1, len(fields)):
            if fields[i][2] == fields[j][2]:
                dup += 1
                dup_hits.append((fields[i][0], fields[i][1], fields[j][0], fields[j][1]))
    report = {
        "synopsis_similar_pairs": similar,
        "synopsis_pairs": pairs,
        "character_duplicate_sentences": dup,
        "dup_hits": dup_hits,
        "pass": similar < 3 and dup < 2,
        "syn_lens": [len(s) for s in syns],
    }
    (r.evid / "04b-antipad-selfcheck.md").write_text(
        "# 反凑数自查\n\n" + json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def s5(r: Runner) -> None:
    print("\n==== S5 WCG ====", flush=True)
    env = os.environ.copy()
    env["API_BASE"] = BASE
    env["COOKIE_JAR"] = JAR
    outp = r.evid / "04-world-complete-gate.json"
    cmd = [
        sys.executable, str(ROOT / "scripts" / "v4_world_complete_gate.py"),
        "--slug", r.slug, "--out", str(outp),
    ]
    p = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True, text=True)
    print(p.stdout[-2000:] if p.stdout else "", flush=True)
    if p.returncode != 0:
        print("WCG STDERR", p.stderr[-1500:], flush=True)
    ap = antipad(r)
    print("  antipad", ap["pass"], ap, flush=True)
    if p.returncode != 0 or not ap["pass"]:
        raise SystemExit(f"S5 FAIL wcg={p.returncode} antipad={ap['pass']}")
    r.save_state(phase="s5")


def _s3_call_split(calls, outputs=None):
    errored = set()
    for o in outputs or []:
        if not isinstance(o, dict):
            continue
        if (o.get("completion") or {}).get("error"):
            errored.add(str(o.get("tool") or ""))
    ok, bad = [], []
    for c in calls or []:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or c.get("tool") or c.get("tool_name") or "")
        if "s3_" not in name:
            continue
        blob = json.dumps(c, ensure_ascii=False).lower()
        if (
            name in errored
            or c.get("error")
            or c.get("is_error")
            or "timed out" in blob
            or "closedresourceerror" in blob
            or '"status": "error"' in blob
            or '"status":"error"' in blob
        ):
            bad.append(c)
        else:
            ok.append(c)
    return ok, bad


def _missing_code(obj) -> str:
    if isinstance(obj, dict) and isinstance(obj.get("detail"), dict):
        return str(obj["detail"].get("code") or "")
    return ""


def _stage_live(r: "Runner", seq: int, stg: str) -> tuple[bool, object]:
    """书里这一层是不是真有东西（不是主编口头答应）。"""
    if stg == "duty":
        _, duty = getj(f"/api/chapters/{seq}/duty", work=r.slug)
        dump(r.evid / f"10-ch{seq}-duty.json", duty)
        live = isinstance(duty, dict) and not _missing_code(duty)
        return bool(live), duty
    if stg == "design":
        _, play = getj(f"/api/chapters/{seq}/play", work=r.slug)
        _, contract = getj(f"/api/chapters/{seq}/contract", work=r.slug)
        dump(r.evid / f"11-ch{seq}-play.json", play)
        dump(r.evid / f"12-ch{seq}-contract.json", contract)
        play_ok = isinstance(play, dict) and not _missing_code(play)
        con_ok = isinstance(contract, dict) and not _missing_code(contract)
        return bool(play_ok and con_ok), {"play": play, "contract": contract}
    if stg == "deduce":
        _, d = getj(f"/api/chapters/{seq}/deduce", work=r.slug)
        dump(r.evid / f"13-ch{seq}-deduce.json", d)
        return bool(isinstance(d, dict) and not _missing_code(d)), d
    if stg == "draft":
        _, d = getj(f"/api/latest-draft?seq={seq}", work=r.slug)
        dump(r.evid / f"14-ch{seq}-draft.json", d)
        text = ""
        if isinstance(d, dict):
            text = str(d.get("draft") or d.get("text") or d.get("prose") or "")
        return bool(text.strip()), d
    if stg == "final":
        _, ch = getj(f"/api/chapter?seq={seq}", work=r.slug)
        dump(r.evid / f"15-ch{seq}-final.json", ch)
        prose = (ch or {}).get("prose") if isinstance(ch, dict) else ""
        return bool(str(prose or "").strip()), ch
    return False, None


def s6(r: Runner) -> None:
    print("\n==== S6 五层 ×", r.n, "====", flush=True)
    stages = ["duty", "design", "deduce", "draft", "final"]
    for seq in range(1, r.n + 1):
        key = f"ch{seq}"
        done = set(r.state.get("s6_done") or [])
        for stg in stages:
            tag = f"{key}-{stg}"
            live, payload = _stage_live(r, seq, stg)
            if tag in done and live:
                print("  skip", tag, flush=True)
                continue
            if tag in done and not live:
                print(f"  redo {tag}（上次记完成但书里没有）", flush=True)
                done.discard(tag)
                r.save_state(s6_done=sorted(done))
            phase = "" if stg in ("duty", "design") else stg
            r.world_write(
                tag,
                speech_stage(seq, stg),
                timeout=1800,
                chapter=seq,
                phase=phase,
            )
            live, payload = _stage_live(r, seq, stg)
            if not live:
                raise RuntimeError(f"{tag} 主编跑完但书里没有这一层")
            if stg == "duty":
                _, arts = getj("/api/debug/pipeline-artifacts?kind=prompt&limit=20", work=r.slug)
                dump(r.evid / f"18-ch{seq}-prompt-in.json", arts)
                body = json.dumps(arts, ensure_ascii=False) if arts is not None else ""
                empty_cols = []
                for k in ("卷纲", "北极星", "本章责", "相关设定"):
                    for needle in (f"{k}：（无）", f"{k}:(无)", f"{k}（无）"):
                        if needle in body:
                            empty_cols.append(k)
                            break
                if empty_cols:
                    (r.evid / "21-defect-ledger.md").write_text(
                        f"# 缺陷\n\nduty.in 空栏: {empty_cols}\n立刻停批。\n",
                        encoding="utf-8",
                    )
                    raise SystemExit(f"M3 FAIL duty.in empty {empty_cols}")
            done.add(tag)
            r.save_state(s6_done=sorted(done))
        # save-chapter
        save_tag = f"{key}-save"
        if save_tag not in done:
            _, ch = getj(f"/api/chapter?seq={seq}", work=r.slug)
            prose = (ch or {}).get("prose") if isinstance(ch, dict) else ""
            title = (ch or {}).get("title") if isinstance(ch, dict) else ""
            if not prose:
                raise SystemExit(f"ch{seq} 定稿无正文，不 save")
            code, res = curl(
                "POST", "/api/save-chapter",
                {"seq": seq, "prose": prose, "title": title, "focalizer": FOCALIZER},
                work=r.slug, timeout=180,
            )
            dump(r.evid / f"16-ch{seq}-save.json", {"http": code, "res": res})
            _, ch2 = getj(f"/api/chapter?seq={seq}", work=r.slug)
            hook = ((ch2 or {}).get("narrative_drive") or {}).get("end_hook") if isinstance(ch2, dict) else None
            dump(r.evid / f"16-ch{seq}-state.json", ch2)
            print("  save", code, "end_hook", bool(hook), flush=True)
            if not hook:
                print("  WARN end_hook 空", flush=True)
            done.add(save_tag)
            r.save_state(s6_done=sorted(done), phase="s6")


def s7(r: Runner) -> None:
    print("\n==== S7 验收留证 ====", flush=True)
    acc = [
        "# 真人建书 N={} 验收\n".format(r.n),
        f"slug: `{r.slug}`\n",
        "盲读须在看机器数之前完成。本文件先留机器回读，人评表空着。\n",
    ]
    for seq in range(1, r.n + 1):
        _, ch = getj(f"/api/chapter?seq={seq}", work=r.slug)
        prose = ((ch or {}).get("prose") or "") if isinstance(ch, dict) else ""
        acc.append(f"\n## 第{seq}章 字数 {cn_len(prose)}\n")
        acc.append("1. 这一章推进了几件事？\n\n2. 有几个人说话？说了几句？\n\n3. 读完想不想翻下一页？\n")
    (r.evid / "20-acceptance.md").write_text("".join(acc), encoding="utf-8")
    ledger = r.evid / "21-defect-ledger.md"
    if not ledger.exists():
        ledger.write_text(
            "# 缺陷台账\n\n"
            "- 作者必须反常地说出内部层名才能触发核心管线；自然语言「写第N章」在旧代码会绕开五层。"
            "当前代码「写这一章」会进五层，但仍建议点名层名以免误入散文通道。\n",
            encoding="utf-8",
        )
    r.save_state(phase="s7")
    print("  evid", r.evid, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N_DEFAULT)
    ap.add_argument("--slug", default=os.environ.get("HUMANRUN_SLUG") or "")
    ap.add_argument("--stop-after", default="s7", help="s0..s7")
    ap.add_argument("--start-from", default="s0", help="s0..s7，跳过更早阶段")
    ap.add_argument("--evid", default="")
    args = ap.parse_args()
    if args.n < 1 or args.n > 10:
        raise SystemExit("N must be 1..10")
    stamp = datetime.now().strftime("%Y%m%d")
    evid = Path(args.evid) if args.evid else (ROOT / "artifacts" / f"humanrun-{stamp}-pending")
    evid.mkdir(parents=True, exist_ok=True)
    login()
    r = Runner(args.n, evid, args.slug or None)
    order = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7"]
    fns = {"s0": s0, "s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7}
    stop = args.stop_after
    start = args.start_from
    started = False
    for name in order:
        if not started:
            if name != start:
                print("  skip", name, "(start-from)", flush=True)
                continue
            started = True
        # 建书后把证据目录改成带 slug
        if name == "s1":
            fns[name](r)
            if r.slug and evid.name.endswith("pending"):
                dest = ROOT / "artifacts" / f"humanrun-{stamp}-{r.slug}"
                if evid.resolve() != dest.resolve():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dest.exists():
                        evid = dest
                    else:
                        evid.rename(dest)
                        evid = dest
                    r.evid = evid
                    r.state_path = evid / "state.json"
                    r.save_state(phase="s1")
                    print("  evid", evid, flush=True)
        else:
            fns[name](r)
        if name == stop:
            print("STOP after", name, flush=True)
            break
    print("DONE", r.slug, r.evid, flush=True)


if __name__ == "__main__":
    main()
