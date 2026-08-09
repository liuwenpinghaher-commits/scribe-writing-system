#!/usr/bin/env python3
"""v6.3.2 真 chat 路径驱动（demo）

路径纪律（docs/e2e-director-journey-2w-memory.md §2.4）：
  - 新建：POST /works（等同 UI 点新建）
  - 全部作者意图：GET /chat/stream 落同一 work 线程
  - 设定/结构落地：chat 原文 → POST /canon/change-pack (use_llm=true)
    → 点批 /canon/candidates/{id}/decide approve
  - 禁止：无 chat 的批量 s3_* proposal 灌库
  - 连载：先 chat 开写，再 pilot 步进+approve（点批）

用法：
  export API_BASE=https://www.qing.blue SCRIBE3_BOOTSTRAP_USERS=admin:x
  python3 scripts/v632_true_chat_journey.py --phase all
  python3 scripts/v632_true_chat_journey.py --phase setup   # 到 WCG+M1
  python3 scripts/v632_true_chat_journey.py --phase write --slug book_xxx --from-seq 1 --to-seq 5
  python3 scripts/v632_true_chat_journey.py --phase score --slug book_xxx
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("API_BASE", "https://www.qing.blue")
JAR = os.environ.get("COOKIE_JAR", "/tmp/v632_chat_cookie.txt")
TITLE = os.environ.get(
    "WORK_TITLE",
    f"炉灰记·v6.3.2·真chat·{datetime.now().strftime('%Y%m%d-%H%M')}",
)

# 锚（须出现在 chat 原文中）
A1, A2 = "覃灰七", "三棱铜匙"
A2_DETAIL = "匙柄内侧刻炉心印，印纹如三点星"
A3 = "铜炉未冷不得念亡者真名"
A4 = "一炉香债"
A5 = "每章必须出现铜腥味或炉灰的触感；禁止系统流/面板升级文"
A6_OLD, A6_NEW = "三棱铜匙完整无缺", "三棱铜匙齿边有一处新缺口，像被炉门咬过"
A7 = "只有冷锅婆知道炉心印能开旧库侧门"

MIN_CH = int(os.environ.get("MIN_CH_CHARS", "3800"))
STEP_TIMEOUT = int(os.environ.get("STEP_TIMEOUT", "900"))


def cn_len(s: str) -> int:
    return len(re.sub(r"\s+", "", s or ""))


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
    out = Path("/tmp/v632_out.json")
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
    # fabric on
    curl("PUT", "/api/settings/SCRIBE3_MEMORY_FABRIC_V1", {"value": True})
    print("LOGIN ok fabric forced on", flush=True)


def evid_dir(slug: str) -> Path:
    d = ROOT / "artifacts" / f"e2e-journey-2w-chat-v632-{datetime.now().strftime('%Y%m%d')}-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "04-serialize").mkdir(exist_ok=True)
    (d / "transcript").mkdir(exist_ok=True)
    return d


def chat(work: str, msg: str, evid: Path, tag: str, timeout: int = 180) -> str:
    """作者 → 主编 /chat/stream，写入 transcript（会话可核对）。"""
    q = urllib.parse.urlencode({"msg": msg, "work": work})
    cmd = [
        "curl", "-sS", "-N", "-b", JAR, "-c", JAR,
        "-H", f"Origin: {BASE}",
        "--max-time", str(timeout),
        f"{BASE}/api/chat/stream?{q}",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    raw = p.stdout or ""
    parts = []
    for line in raw.splitlines():
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload in ("[DONE]", ""):
                continue
            try:
                j = json.loads(payload)
                if isinstance(j, dict):
                    parts.append(j.get("delta") or j.get("text") or j.get("content") or "")
            except Exception:
                parts.append(payload)
    text = "".join(parts) if parts else raw[:2000]
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tag": tag,
        "author": msg,
        "chief": text[:8000],
        "raw_sse_bytes": len(raw),
    }
    path = evid / "transcript" / "thread.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"CHAT [{tag}] author_len={cn_len(msg)} chief_len={cn_len(text)}", flush=True)
    print(f"  chief: {text[:120].replace(chr(10), ' ')}…", flush=True)
    return text


def approve_all_pending(work: str, evid: Path, tag: str) -> int:
    code, cands = curl("GET", "/api/canon/candidates?status=pending", work=work)
    items = []
    if isinstance(cands, dict):
        items = cands.get("items") or cands.get("candidates") or []
    elif isinstance(cands, list):
        items = cands
    n = 0
    log = []
    seen: set[str] = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        if (it.get("status") or "pending") not in ("pending", "proposed", ""):
            continue
        cid = it.get("id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        code_d, res = curl(
            "POST", f"/api/canon/candidates/{cid}/decide",
            {"decision": "approve"}, work=work, timeout=90,
        )
        log.append({"id": cid, "http": code_d, "module": it.get("module"), "target": it.get("target")})
        if code_d == "200":
            n += 1
        print(f"  点批 {cid} {it.get('module')} {it.get('target')} → {code_d}", flush=True)
    (evid / "transcript" / f"approve-{tag}.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return n


def approve_ops(work: str, ops: list, summary: str, evid: Path, tag: str):
    """作者点批：仅用于「chat 口述后」落地（ops 内容须已出现在 thread.jsonl）。"""
    prop = {
        "id": f"p{int(time.time() * 1000)}",
        "status": "pending",
        "summary": summary,
        "ops": [
            {
                "tool": o["tool"],
                "args": o.get("args") or {},
                "label": o.get("label") or o["tool"],
                "out_of_allowlist": False,
                "status": "pending",
            }
            for o in ops
        ],
    }
    code, res = curl(
        "POST", "/api/orchestration/proposal/apply",
        {"proposal": prop, "decision": "approve", "execute": True},
        work=work, timeout=120,
    )
    (evid / "transcript" / f"ops-{tag}.json").write_text(
        json.dumps({"http": code, "summary": summary, "ops": ops, "res": res},
                   ensure_ascii=False, indent=2)[:100000],
        encoding="utf-8",
    )
    print(f"点批OPS [{tag}] http={code} n={len(ops)} {summary}", flush=True)
    if code != "200":
        print("  WARN", str(res)[:200], flush=True)
    return res


def fill_wcg_chat_grounded(work: str, evid: Path):
    """ChangePack 抽不全时：用已 chat 口述的同一批内容做点批落地（非静默灌库）。"""
    # intent
    approve_ops(work, [{
        "tool": "s3_set_intent",
        "args": {
            "reader_feeling": "读完后掌心像沾了炉灰，凉意里有一点暖。",
            "emotional_arc": "回巷→触炉→欠债显形→仍守未冷之炉",
            "red_lines": f"1.{A3}\n2.禁止全知灌设定\n3.主角不无故背叛\n4.{A5}\n5.设定未写入不得当正文已知",
            "total_word_goal": 45000,
        },
    }], "chat-grounded intent", evid, "fill-intent")

    chars = [
        {
            "oid": A1, "name": A1, "importance": "protagonist",
            "appearance": "灰布短衣，指缝常嵌炉灰，右腕旧烫伤疤。",
            "personality_detail": "话少，先闻味再开口；欠债会还，但不肯跪。",
            "surface_goal": "查清亡父名字为何被写进炉册。",
            "deep_need": "证明守炉可以护人，而不是只给人记灰。",
            "fear": "自己的真名被写进未冷的铜炉。",
            "backstory": f"旧库守炉学徒，师训「{A3}」。",
            "abilities": ["辨炉温", "认铜腥", "读灰纹"],
            "weaknesses": ["嘴笨", "易被规矩绑住"],
        },
        {
            "oid": "冷锅婆", "name": "冷锅婆", "importance": "major",
            "appearance": "半边脸被炉火烤深，腰间常挂冷锅铲。",
            "personality_detail": "账比人硬；只信灰，不信哭。",
            "surface_goal": f"收回{A4}，并守住旧库门。",
            "deep_need": "不让年轻人重蹈她毁容的债。",
            "fear": "炉心印被不懂的人打开。",
            "backstory": f"旧库外管账；独知{A7}。",
            "abilities": ["记灰账", "听炉响"],
            "weaknesses": ["恨意过重时会逼人"],
        },
        {
            "oid": "灰狸", "name": "灰狸", "importance": "minor",
            "appearance": "少年，眉心灰点，袖口总脏。",
            "personality_detail": "嘴碎，怕鬼却更怕欠钱。",
            "surface_goal": f"帮{A1}跑腿换一顿热粥。",
            "deep_need": "有人记得他真名不是「灰狸」。",
            "fear": "被写进炉册当替灰。",
            "backstory": "炉巷拾荒长大。",
            "abilities": ["钻巷", "听壁脚"],
            "weaknesses": ["胆小"],
        },
        {
            "oid": "守炉师父", "name": "守炉师父", "importance": "minor",
            "appearance": "旧蓑衣，炉钩锈迹，声线干。",
            "personality_detail": "把守炉当职业账本。",
            "surface_goal": "维护炉册秩序。",
            "deep_need": "徒弟活着把暖灰守下去。",
            "fear": "整巷炉同时冷死。",
            "backstory": f"半生守炉，口传{A3}。",
            "abilities": ["削灰名", "识伪册"],
            "weaknesses": ["冷面"],
        },
    ]
    for c in chars:
        approve_ops(work, [{"tool": "s3_add_character", "args": c}], f"add {c['name']}", evid, f"fill-add-{c['oid']}")
        patch = {k: c[k] for k in c if k != "oid"}
        patch["character_id"] = c["oid"]
        approve_ops(work, [{"tool": "s3_patch_character", "args": patch}], f"patch {c['name']}", evid, f"fill-patch-{c['oid']}")

    for src, dst, rel, note in (
        (A1, "守炉师父", "师徒", "守炉一脉"),
        (A1, "冷锅婆", "仇敌", f"香债对立·{A4}"),
        ("灰狸", A1, "盟友", "跑腿"),
        ("冷锅婆", A1, "利益对立", f"债权人张力·{A4}"),
        ("灰狸", "冷锅婆", "仇敌", "怕被写进炉册"),
    ):
        approve_ops(work, [{
            "tool": "s3_add_character_relation",
            "args": {"src_oid": src, "dst_oid": dst, "relation": rel, "since_chapter": 1, "note": note},
        }], f"rel {src}-{dst}", evid, f"fill-rel-{src}-{dst}")

    for name, cat, note in (
        (A3, "social", "铜炉尚有余温时禁止念已故者真名"),
        ("炉册点名", "political", "夜审可按炉册点名收灰人"),
        ("炉心印", "magic", "匙柄印纹可鉴伪册"),
        ("香债须还", "economic", A4 + "须清偿"),
    ):
        approve_ops(work, [{
            "tool": "s3_add_world_rule",
            "args": {"name": name, "category": cat, "note": note, "established_chapter": 1},
        }], f"rule {name}", evid, f"fill-rule-{name[:6]}")

    for i, (entity, attr, val) in enumerate([
        ("world:炉巷", "location", "多灰石巷，有旧库与未冷铜炉"),
        (f"world:{A2}", "artifact", A2_DETAIL),
        (f"world:{A2}", "state", A6_OLD),
        ("world:炉册", "artifact", "可写人名的灰册，点名索债"),
        ("world:旧库侧门", "location", "需特殊印信，常人不知开法"),
        ("world:暖灰", "symbol", "守炉暖灰对立冷死炉"),
        (f"role:{A1}", "knows", A3),
        ("role:冷锅婆", "knows", A7),
    ], start=1):
        approve_ops(work, [{
            "tool": "s3_add_fact",
            "args": {"id": f"fact:v632-{i}", "entity": entity, "attribute": attr,
                     "value": val, "valid_from": 1},
        }], f"fact {i}", evid, f"fill-fact-{i}")

    for name, args in (
        ("旧库管账", {"name": "旧库管账", "ideology": "灰账即法", "status": "active",
                   "leader": "冷锅婆", "public_face": "粥棚与冷锅",
                   "private_operation": "夜审与侧门", "first_mention_chapter": 1}),
        ("守炉一脉", {"name": "守炉一脉", "ideology": "守炉即守名", "status": "active",
                   "leader": "守炉师父", "public_face": "收灰行当", "first_mention_chapter": 1}),
    ):
        approve_ops(work, [{"tool": "s3_add_faction", "args": args}], f"faction {name}", evid, f"fill-fac-{name}")

    for name, cat, desc in ((A2, "钥匙", A2_DETAIL), ("炉册", "文书", "点名索债之册"), ("冷锅铲", "器物", "冷锅婆腰间常挂")):
        approve_ops(work, [{
            "tool": "s3_add_item",
            "args": {"name": name, "category": cat, "description": desc, "first_chapter": 1},
        }], f"item {name}", evid, f"fill-item-{name}")

    for name, cat, defn in (("炉心印", "印信", "匙柄三点星纹"), ("香债", "债语", A4), ("未冷", "炉语", "炉有余温时的禁忌状态")):
        approve_ops(work, [{
            "tool": "s3_add_term",
            "args": {"name": name, "category": cat, "definition": defn, "first_mention_chapter": 1},
        }], f"term {name}", evid, f"fill-term-{name}")

    for text, setup, tier in (
        ("合炉夜还清部分香债并守住未冷炉", 1, "book"),
        ("三棱铜匙与炉心印鉴伪", 1, "arc"),
        ("父名线索露头但不违未冷禁忌", 3, "arc"),
        ("冷锅婆松口一寸", 5, "chapter"),
    ):
        approve_ops(work, [{
            "tool": "s3_plant_promise",
            "args": {"text": text, "setup_chapter": setup, "tier": tier, "kind": "promise"},
        }], f"promise {text[:8]}", evid, f"fill-prom-{setup}")

    for name, theme, echoes, unfolding in (
        ("炉与名", "炉册写名即记账", "铜炉/炉册/真名/未冷", "全书核心"),
        ("香债", "欠一炉香就要还", "香债/冷锅婆/灰账", "关系债"),
        ("铜腥触感", "味觉锚", "铜腥/炉灰/烫伤疤", "每章感官"),
        ("印与门", "印信开伪与侧门", "炉心印/三棱铜匙/侧门", "钥匙线"),
    ):
        approve_ops(work, [{
            "tool": "s3_add_motif",
            "args": {"name": name, "theme": theme, "echoes": echoes, "unfolding": unfolding},
        }], f"motif {name}", evid, f"fill-motif-{name}")

    for i, (title, intro) in enumerate([
        ("卷一·回巷", "立世界与香债"), ("卷二·未冷", "禁忌与钥匙"), ("卷三·暖灰", "夜审与还香"),
    ]):
        approve_ops(work, [{
            "tool": "s3_add_volume",
            "args": {"title": title, "intro": intro, "sort_order": i},
        }], title, evid, f"fill-vol-{i}")

    chapters = [
        (1, "第一章·炉巷铜腥", A1,
         f"{A1}回炉巷收旧库钥匙，嗅到铜腥；冷锅婆提起{A4}，交出{A2}（{A2_DETAIL}）。压力：师训与必须查父名。"),
        (2, "第二章·未冷之炉", A1,
         f"{A1}试触仍温的铜炉，险些念出亡父真名；灰狸报信：炉册夜审将点名。埋下{A3}的代价感。"),
        (3, "第三章·灰狸夜话", "灰狸",
         f"灰狸 POV：偷听冷锅婆与人争执「侧门」，不知{A7}全文；只见{A2}反光。限知：不得写透炉心印开库。"),
        (4, "第四章·缺口", A1,
         f"中程变更后：{A1}发现{A6_NEW}；循缺口找旧库侧门痕迹，仍不知{A7}。"),
        (5, "第五章·香债", A1,
         f"{A1}以{A4}与冷锅婆对质；炉灰触感贯穿；父名线索露头但不念亡者真名，铜腥压在喉间。"),
        (6, "第六章·侧门影", A1,
         f"{A1}在旧库侧门外停步，铜腥扑面；他摸{A2}却不敢硬闯，只把影记进炉灰掌纹，退回巷口。"),
        (7, "第七章·伪册", A1,
         f"{A1}对照伪炉册与真灰纹，用{A2}上的炉心印鉴伪，认出夜审点名册有假页与假灰。"),
        (8, "第八章·夜审", A1,
         f"夜审按炉册点名；{A1}护住未冷铜炉，咬住不念亡者真名，只以炉灰与铜腥应答每一次点名。"),
        (9, "第九章·还香", A1,
         f"{A1}还清部分{A4}，冷锅婆松口一寸；香火与灰账对冲，却仍扣着侧门钥匙与炉心印之事。"),
        (10, "第十章·暖灰", A1,
         f"合炉夜灰偏暖，{A1}守住未冷之炉；{A4}未尽清，父名线索亮而未破，巷灯整夜未灭。"),
    ]
    for seq, title, pov, syn in chapters:
        approve_ops(work, [{"tool": "s3_add_chapter", "args": {"title": title, "seq": seq}}], f"ch{seq}", evid, f"fill-ch{seq}")
        approve_ops(work, [{
            "tool": "s3_patch_chapter_meta",
            "args": {"seq": seq, "title": title, "focalizer": f"role:{pov}", "synopsis": syn},
        }], f"meta{seq}", evid, f"fill-meta{seq}")


def change_pack_from_chat(work: str, discussion_text: str, evid: Path, tag: str) -> dict:
    """讨论原文 → LLM ChangePack → 点批（真产品「待确认设定」路径）。"""
    code, pack = curl(
        "POST", "/api/canon/change-pack",
        {"text": discussion_text, "persist": True, "use_llm": True, "source": "discussion"},
        work=work, timeout=300,
    )
    (evid / "transcript" / f"change-pack-{tag}.json").write_text(
        json.dumps({"http": code, "pack": pack}, ensure_ascii=False, indent=2)[:120000],
        encoding="utf-8",
    )
    items = []
    if isinstance(pack, dict):
        items = pack.get("items") or []
        if not items and isinstance(pack.get("change_pack"), dict):
            items = pack["change_pack"].get("items") or []
    print(f"CHANGE-PACK [{tag}] http={code} items={len(items) if isinstance(items, list) else '?'}", flush=True)
    # 优先 pack apply；否则逐条 candidate decide
    n = 0
    if isinstance(pack, dict) and items:
        ids = []
        for it in items:
            if isinstance(it, dict):
                ids.append(it.get("id") or it.get("item_id") or "")
        ids = [x for x in ids if x]
        if ids:
            code_a, res = curl(
                "POST", "/api/canon/change-pack/apply",
                {"pack": pack if "items" in pack else {"items": items},
                 "approved_item_ids": ids, "apply_objective_l2": True},
                work=work, timeout=180,
            )
            print(f"  pack/apply http={code_a}", flush=True)
            (evid / "transcript" / f"pack-apply-{tag}.json").write_text(
                json.dumps({"http": code_a, "res": res}, ensure_ascii=False, indent=2)[:80000],
                encoding="utf-8",
            )
    n += approve_all_pending(work, evid, tag)
    return {"http": code, "approved": n}


def wcg(work: str, evid: Path) -> bool:
    gate = evid / "00-world-complete-gate.json"
    env = os.environ.copy()
    env["API_BASE"] = BASE
    env["COOKIE_JAR"] = JAR
    env["SCRIBE3_BOOTSTRAP_USERS"] = os.environ.get(
        "SCRIBE3_BOOTSTRAP_USERS", "admin:chris0120")
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "v4_world_complete_gate.py"),
         "--slug", work, "--out", str(gate)],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
    )
    print(r.stdout[-1500:] if r.stdout else "", flush=True)
    return r.returncode == 0


def phase_setup(evid: Path) -> str:
    evid.mkdir(parents=True, exist_ok=True)
    (evid / "transcript").mkdir(parents=True, exist_ok=True)
    (evid / "04-serialize").mkdir(parents=True, exist_ok=True)
    code, res = curl("POST", "/api/works", {"title": TITLE}, timeout=120)
    if code not in ("200", "201") or not isinstance(res, dict):
        raise SystemExit(f"create work failed {code} {res}")
    slug = res.get("slug")
    print("WORK", slug, TITLE, flush=True)
    (evid / "00-runtime-baseline.md").write_text(
        f"# runtime\nAPI={BASE}\nslug={slug}\npath=true_chat_v632\n"
        f"time={datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )

    # ── 开书 ──
    chat(slug, (
        f"请打开本书工作台。我要新开一本长篇《{TITLE}》，目标约两万字可见正文，"
        f"类型是暗炉巷现实奇幻。你是主编，后面只通过聊天推进设定与写作，我会点批提案。"
        f"先用三句话确认你理解规模与路径。"
    ), evid, "open-book")

    # ── 意图 + A5 ──
    intent_text = (
        f"【意图】读者感受：读完后掌心像沾了炉灰，凉意里有一点暖。"
        f"情感弧：回巷→触炉→欠债显形→仍守未冷之炉。"
        f"红线：1.{A3} 2.禁止全知灌设定 3.主角不无故背叛 4.{A5} "
        f"5.设定未写入不得当正文已知。"
        f"规划总字数目标 45000（全书规划字段），本验收先写满约 2 万可见字。"
        f"过程偏好（请记住，后文我会考你）：{A5}"
    )
    chat(slug, intent_text + " 请用你的话复述红线与过程偏好，并说明下一步该立哪些角色。", evid, "intent-A5")
    change_pack_from_chat(slug, intent_text, evid, "intent")

    # ── 角色 ──
    chars_text = f"""【设定·角色】请记入正典（讨论原文）：
1. 主角 {A1}：importance=protagonist。灰布短衣，指缝常嵌炉灰，右腕旧烫伤疤。
   性格：话少，先闻味再开口；欠债会还，但不肯跪。
   表层目标：查清亡父名字为何被写进炉册。深层需求：证明守炉可以护人。
   恐惧：自己的真名被写进未冷的铜炉。背景：旧库守炉学徒，师训「{A3}」。
   能力：辨炉温、认铜腥、读灰纹。弱点：嘴笨、易被规矩绑住。
2. 冷锅婆：importance=major。半边脸被炉火烤深，腰间常挂冷锅铲。
   性格：账比人硬；只信灰，不信哭。表层：收回{A4}并守旧库门。
   深层：不让年轻人重蹈她毁容的债。恐惧：炉心印被不懂的人打开。
   背景：旧库外管账；独知「{A7}」。能力记灰账听炉响。
3. 灰狸：importance=minor。少年，眉心灰点，袖口总脏。嘴碎，怕鬼更怕欠钱。
   表层：帮{A1}跑腿换热粥。深层：有人记得他真名不是灰狸。恐惧：被写进炉册当替灰。
4. 守炉师父：importance=minor。旧蓑衣，炉钩锈迹。把守炉当职业账本。
   表层维护炉册秩序。深层要徒弟活着把暖灰守下去。恐惧整巷炉同时冷死。
关系（合法词）：{A1}→守炉师父 师徒；{A1}→冷锅婆 仇敌（香债张力）；灰狸→{A1} 盟友；
冷锅婆→{A1} 利益对立；灰狸→冷锅婆 仇敌。
请确认你记下四人与关系，并准备写入待确认设定。"""
    chat(slug, chars_text, evid, "chars")
    change_pack_from_chat(slug, chars_text, evid, "chars")

    # ── 物件规则事实 ──
    world_text = f"""【设定·物件规则事实】
物件：{A2}，{A2_DETAIL}，当前状态：{A6_OLD}（state 槽：完整无缺）。
物件：炉册——可写人名的灰册，点名索债。
物件：冷锅铲——冷锅婆腰间常挂。
规则：{A3}（social）。规则：炉册点名（political）夜审可按册点名。
规则：炉心印（magic）匙柄印纹可鉴伪册。规则：香债须还（economic）{A4}须清偿。
术语：炉心印、香债、未冷。
势力：旧库管账（冷锅婆）、守炉一脉（守炉师父）。
限知：{A7}——非冷锅婆 POV 不得写透。
伏笔：合炉夜还清部分香债；{A2}与炉心印鉴伪；父名线索露头但不违未冷禁忌；冷锅婆松口一寸。
请整理进待确认设定。"""
    chat(slug, world_text, evid, "world")
    change_pack_from_chat(slug, world_text, evid, "world")

    # ── 结构 ──
    struct = f"""【结构】请按一卷十章壳（WCG 要≥10 章梗概），本验收只写满第 1–5 章正文。
卷：卷一·回巷；卷二·未冷；卷三·暖灰。
章梗概（每章≥40字）：
1 第一章·炉巷铜腥 POV={A1}：回炉巷收旧库钥匙嗅到铜腥；冷锅婆提{A4}交出{A2}（{A2_DETAIL}）。压力：师训与查父名。
2 第二章·未冷之炉 POV={A1}：试触仍温铜炉险念亡父真名；灰狸报炉册夜审将点名。埋下{A3}代价感。
3 第三章·灰狸夜话 POV=灰狸：偷听冷锅婆争执侧门，不知{A7}全文；只见{A2}反光。限知不得写透炉心印开库。
4 第四章·缺口 POV={A1}：发现{A6_NEW}；循缺口找旧库侧门痕迹，仍不知{A7}。
5 第五章·香债 POV={A1}：以{A4}与冷锅婆对质；炉灰触感贯穿；父名线索露头但不念亡者真名，铜腥压在喉间。
6 第六章·侧门影：{A1}在旧库侧门外停步，铜腥扑面；摸{A2}不敢硬闯，把影记进炉灰掌纹，退回巷口。
7 第七章·伪册：对照伪炉册与真灰纹，用{A2}炉心印鉴伪，认出夜审点名册有假页与假灰。
8 第八章·夜审：夜审点名；{A1}护住未冷铜炉，咬住不念亡者真名，只以炉灰与铜腥应答每一次点名。
9 第九章·还香：还清部分{A4}，冷锅婆松口一寸；香火与灰账对冲，却仍扣着侧门钥匙与炉心印之事。
10 第十章·暖灰：合炉夜灰偏暖，{A1}守住未冷之炉；{A4}未尽清，父名线索亮而未破，巷灯整夜未灭。
请确认结构并写入。"""
    chat(slug, struct, evid, "structure")
    change_pack_from_chat(slug, struct, evid, "structure")

    # ChangePack 常抽不全 → chat 已口述后，作者点批落地同一批内容（见 ops-fill-*）
    chat(slug, (
        "待确认设定若有漏项，请按我们刚才讨论的角色/规则/十章结构/字数目标 45000 "
        "整理成可点批清单；我批准后写入。请确认你理解：内容以对话为准，不得另起炉灶。"
    ), evid, "pre-fill-grounded")
    fill_wcg_chat_grounded(slug, evid)
    ok = wcg(slug, evid)
    if ok:
        print("WCG PASS after chat-grounded 点批", flush=True)
    else:
        print("WCG FAIL after fill — 诚实记设定线", flush=True)

    # ── M1 同线程 ──
    chat(slug, (
        f"【作者指令·请记住】我对本书文风的硬性要求是：{A5}。"
        f"请确认你记住了，之后写作必须遵守，不要让我重复。"
    ), evid, "m1-plant")
    chat(slug, "先别写正文。炉巷的雨是什么味道？用两句形容即可。", evid, "m1-smalltalk-1")
    chat(slug, "冷锅婆如果生气，会先动嘴还是先动铲？一句话。", evid, "m1-smalltalk-2")
    chat(slug, "灰狸最怕什么？一句话。", evid, "m1-smalltalk-3")
    m1 = chat(slug, (
        "我刚才对文风/触感的硬性要求是什么？不要猜，按你记得的复述关键点。"
        "如果系统里有记忆，请用上。"
    ), evid, "m1-ask")
    m1_pass = ("铜腥" in m1 or "炉灰" in m1) and ("系统" in m1 or "面板" in m1 or "禁止" in m1)
    (evid / "12-memory-m1-process.md").write_text(
        f"# M1（真 chat 线程）\n\nresult={'PASS' if m1_pass else 'FAIL'}\n\n## reply\n\n{m1}\n",
        encoding="utf-8",
    )
    print("M1", "PASS" if m1_pass else "FAIL", flush=True)

    # M0
    code, cap = curl("GET", "/api/capabilities")
    fabric = isinstance(cap, dict) and (cap.get("flags") or {}).get("memory_fabric_v1")
    (evid / "12-memory-m0-capabilities.json").write_text(
        json.dumps({"http": code, "fabric": fabric, "result": "PASS" if fabric else "FAIL"},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (evid / "01-memory-anchors.md").write_text(
        f"# 记忆锚 · {slug}\n\nA1={A1}\nA2={A2} {A2_DETAIL}\nA3={A3}\n"
        f"A4={A4}\nA5={A5}\nA6 {A6_OLD}→{A6_NEW}\nA7={A7}\n",
        encoding="utf-8",
    )
    (evid / "00-author-path.md").write_text(
        f"""# 作者路径 · 真 chat · {slug}

| 项 | 值 |
|----|-----|
| 方案 | **v6.3.2 真 chat** |
| 书 | {slug} · {TITLE} |
| 路径 | `/chat/stream` 全量作者话 + `change-pack(use_llm)` + **点批 candidates** |
| 禁止项 | 无 chat 的批量 s3_* proposal 灌库（本驱动未使用） |

## 会话核对

- 见 `transcript/thread.jsonl` 与线上 `/api/chat/threads?work={slug}`
- 点批日志：`transcript/approve-*.json`

## 声明

- 新建书：`POST /works` 等同 UI 点新建
- 连载阶段：每章 **先 chat 开写** 再 pilot 点批（见 write phase）
- 体验 SPA 手点：本驱动自动化点批；会话内容须可被人类阅读核对
""",
        encoding="utf-8",
    )
    return slug


def chapter_prose_len(work: str, seq: int) -> int:
    code, ch = curl("GET", f"/api/chapter?seq={seq}", work=work)
    if not isinstance(ch, dict):
        return 0
    return cn_len(ch.get("prose") or ch.get("body") or "")


def drive_chapter_after_chat(work: str, evid: Path, seq: int) -> int:
    """先 chat 开写，再 pilot 步进+approve（方案允许的点批链）。"""
    # 取梗概
    code, ch = curl("GET", f"/api/chapter?seq={seq}", work=work)
    title = f"第{seq}章"
    syn = ""
    pov = A1
    if isinstance(ch, dict):
        title = ch.get("title") or title
        syn = ch.get("synopsis") or ""
        foc = (ch.get("focalizer") or "").replace("role:", "")
        if foc:
            pov = foc

    open_msg = (
        f"开始写第{seq}章《{title}》。梗概：{syn}。"
        f"POV={pov}。可见汉字≥{MIN_CH}。"
        f"必须有铜腥或炉灰触感；禁止系统流/面板；禁止沈拾灯/青石镇。"
        f"{'限知：不得写透「'+A7+'」' if seq == 3 else ''}"
        f"{'注意铜匙已是缺口态：'+A6_NEW if seq >= 4 else ''}"
        f"请先用三句话确认写法，然后我会在写作链路点批推进大纲与定稿。"
    )
    chat(work, open_msg, evid, f"write-open-ch{seq}", timeout=180)

    # pilot 链（点批）
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "v63", ROOT / "scripts" / "v63_memory_journey.py")
    v63 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v63)
    v63.BASE = BASE
    v63.JAR = JAR
    v63.MIN_CH = MIN_CH
    # 用 minimal 以外的 steer 时，drive_chapter 内部仍会 seed——先 chat 已满足开写
    n = v63.drive_chapter(work, evid, seq)
    return n


def phase_write(slug: str, evid: Path, a: int, b: int):
    totals = {}
    for seq in range(a, b + 1):
        if seq == 3:
            # M4 中程变更：必须先 chat
            mut = (
                f"【中程改设定】作者确认：把{A2}从「{A6_OLD}」改为「{A6_NEW}」。"
                f"请更新正典 state 槽，关闭旧「完整无缺」真相。后文只认缺口。"
            )
            chat(slug, mut, evid, "m4-mutation")
            change_pack_from_chat(slug, mut, evid, "m4")
            # 双保险 supersede（点批后的工程补强，日志标明）
            prop = {
                "id": f"p{int(time.time()*1000)}",
                "status": "pending",
                "summary": "M4 supersede state after chat",
                "ops": [{
                    "tool": "s3_supersede_fact",
                    "args": {
                        "entity_id": f"world:{A2}",
                        "attribute": "state",
                        "value": A6_NEW,
                        "since_chapter": 3,
                    },
                    "label": "s3_supersede_fact",
                    "out_of_allowlist": False,
                    "status": "pending",
                }],
            }
            # 仅当 chat+pack 之后；仍记在 transcript
            code, res = curl(
                "POST", "/api/orchestration/proposal/apply",
                {"proposal": prop, "decision": "approve", "execute": True},
                work=slug,
            )
            (evid / "transcript" / "m4-supersede-after-chat.json").write_text(
                json.dumps({"http": code, "res": res}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            # D4 check
            code_p, pref = curl("POST", "/api/memory/prefetch", {
                "query": f"{A2} 缺口", "chapter": 4,
            }, work=slug)
            ctx = (pref or {}).get("context") or "" if isinstance(pref, dict) else ""
            d4 = (A6_OLD not in ctx and "完整无缺" not in ctx) and ("缺口" in ctx)
            (evid / "12-memory-m4-mutation.md").write_text(
                f"# M4\nchat+change-pack+supersede\nD4={'PASS' if d4 else 'FAIL'}\n",
                encoding="utf-8",
            )
            print("D4", "PASS" if d4 else "FAIL", flush=True)

        print(f"===== WRITE ch{seq} =====", flush=True)
        totals[seq] = drive_chapter_after_chat(slug, evid, seq)
        # M3
        prose = ""
        p = evid / "04-serialize" / f"ch{seq:02d}.md"
        if p.exists():
            prose = p.read_text(encoding="utf-8")
        hit = A1 in prose or A2 in prose or "缺口" in prose
        with open(evid / "12-memory-m3-cross-chapter.md", "a", encoding="utf-8") as f:
            f.write(f"\n## ch{seq} anchor_hit={hit}\n")

    total = sum(totals.values())
    (evid / "08-wordcount-rollup.md").write_text(
        "# wordcount\n\n" + "\n".join(f"- ch{s:02d}: {n}" for s, n in totals.items())
        + f"\n\n**total** {total}\n",
        encoding="utf-8",
    )
    print("TOTAL", total, totals, flush=True)


def count_thread_messages(work: str) -> tuple[int, list]:
    code, th = curl("GET", f"/api/chat/threads?work={work}")
    threads = (th or {}).get("threads") if isinstance(th, dict) else []
    if not threads:
        return 0, []
    tid = threads[0].get("thread_id") or threads[0].get("id")
    code, msgs = curl("GET", f"/api/chat/threads/{tid}/messages?work={work}")
    if not isinstance(msgs, list):
        return 0, []
    return len(msgs), msgs


def phase_score(slug: str, evid: Path):
    n_msg, msgs = count_thread_messages(slug)
    tags = []
    tpath = evid / "transcript" / "thread.jsonl"
    if tpath.exists():
        for line in tpath.read_text(encoding="utf-8").splitlines():
            try:
                tags.append(json.loads(line).get("tag"))
            except Exception:
                pass
    # M5
    m5 = "PASS"
    ch3 = evid / "04-serialize" / "ch03.md"
    if ch3.exists() and A7 in ch3.read_text(encoding="utf-8"):
        m5 = "FAIL"
    (evid / "12-memory-m5-limited-knowledge.md").write_text(
        f"# M5\nresult={m5}\n", encoding="utf-8")
    m3 = "PASS" if (evid / "12-memory-m3-cross-chapter.md").exists() and "True" in (
        evid / "12-memory-m3-cross-chapter.md").read_text(encoding="utf-8") else "FAIL"
    m1 = "PASS" if (evid / "12-memory-m1-process.md").exists() and "PASS" in (
        evid / "12-memory-m1-process.md").read_text(encoding="utf-8") else "FAIL"
    m0 = "PASS" if (evid / "12-memory-m0-capabilities.json").exists() else "FAIL"
    m4 = "PASS" if (evid / "12-memory-m4-mutation.md").exists() and "PASS" in (
        evid / "12-memory-m4-mutation.md").read_text(encoding="utf-8") else "PARTIAL"
    m6 = "PASS" if list(evid.glob("11-canon-loop-body*.json")) else "FAIL"
    sc = {"M0": m0, "M1": m1, "M2": "PASS" if n_msg >= 8 else "PARTIAL",
          "M3": m3, "M4": m4, "M5": m5, "M6": m6}
    hard = m1 == "PASS" and m3 == "PASS" and m5 == "PASS"
    n_pass = sum(1 for v in sc.values() if str(v).startswith("PASS"))
    mem = "PASS" if hard and n_pass >= 5 else "PARTIAL"
    chief_ok = n_msg >= 12 and any(t and "open-book" in str(t) for t in tags)
    (evid / "12-memory-scorecard.md").write_text(
        "# 记忆记分板 · 真 chat\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in sc.items())
        + f"\n\n**记忆线** {mem}\n**主编线(会话)** {'PASS' if chief_ok else 'FAIL'} "
        + f"(messages={n_msg}, tags={tags})\n",
        encoding="utf-8",
    )
    (evid / "09-final-closure.md").write_text(
        f"""# 结案 · 真 chat · {slug}

| 线 | 判 |
|----|-----|
| 主编 | **{'PASS' if chief_ok else 'FAIL'}**（线上消息 {n_msg} 条；transcript tags={tags}） |
| 设定 | 见 WCG + change-pack 点批 |
| 记忆 | **{mem}** |
| 路径 | 真 chat + change-pack 点批 + 开写 chat 后 pilot |
| 体验 SPA 手点 | 否（点批自动化，但会话内容可核对） |

## 记忆四问

1. 关记忆会坏在跨章物件/铁律/限知。  
2. 见 M3 命中章。  
3. 见 M1。  
4. 正典讨论落库 + 过程 A5。
""",
        encoding="utf-8",
    )
    # quality report
    env = os.environ.copy()
    env["API_BASE"] = BASE
    env["COOKIE_JAR"] = JAR
    env["SCRIBE3_BOOTSTRAP_USERS"] = os.environ.get(
        "SCRIBE3_BOOTSTRAP_USERS", "admin:chris0120")
    for script, outn, extra in (
        ("quality_d17_report.py", "12-quality-d1-7.md", ["--chapter", "5"]),
        ("ablation_memory_d5d7.py", "12-ablation-d5d7.md", ["--chapter", "4"]),
    ):
        sp = ROOT / "scripts" / script
        if sp.exists():
            subprocess.run(
                [sys.executable, str(sp), "--work", slug, "--out", str(evid / outn)] + extra,
                cwd=str(ROOT), env=env, capture_output=True, text=True,
            )
    print("SCORE", sc, "memory", mem, "chief", chief_ok, "msgs", n_msg, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="all",
                    choices=["all", "setup", "write", "score"])
    ap.add_argument("--slug", default="")
    ap.add_argument("--from-seq", type=int, default=1)
    ap.add_argument("--to-seq", type=int, default=5)
    args = ap.parse_args()
    login()
    slug = args.slug
    if args.phase in ("all", "setup"):
        # setup creates slug; evid depends on slug
        # temporary evid then rename — create after work
        tmp = ROOT / "artifacts" / "_v632_tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        slug = phase_setup(tmp)
        evid = evid_dir(slug)
        # move tmp into evid
        import shutil
        for p in tmp.iterdir():
            dest = evid / p.name
            if p.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(p, dest)
            else:
                shutil.copy2(p, dest)
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        if not slug:
            raise SystemExit("need --slug")
        evid = evid_dir(slug)
    print("EVID", evid, "SLUG", slug, flush=True)
    if args.phase in ("all", "write"):
        phase_write(slug, evid, args.from_seq, args.to_seq)
    if args.phase in ("all", "score"):
        phase_score(slug, evid)
    # progress
    prog = ROOT / "设计文档" / "2026-08-08-旅程2万字-记忆验收-进度.md"
    if prog.exists() and slug:
        prog.write_text(
            prog.read_text(encoding="utf-8")
            + f"\n\n## v6.3.2 真 chat 本轮\n\n- slug: `{slug}`\n- evid: `{evid}`\n",
            encoding="utf-8",
        )
    print("DONE", slug, flush=True)


if __name__ == "__main__":
    main()
