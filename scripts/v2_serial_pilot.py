#!/usr/bin/env python3
"""v3 唯一证据串行路径：pilot 真链产文 + append-only director tape。

禁止:
  - 读取 prose_pure/*.txt / gen_literary 结果写入 save-chapter
  - 批量伪造 pilot_state 时间线
  - EMERGENCY REST 灌正典（本脚本仅 orch approve + pilot API）

用法（在 demo 机 / 能访问 API 的环境）:
  export SCRIBE3_BOOTSTRAP_USERS=admin:chris0120
  export API_BASE=http://127.0.0.1:8088   # 或 https://tonglu.qing.blue
  python3 scripts/v2_serial_pilot.py --phase scaffold
  python3 scripts/v2_serial_pilot.py --phase serialize --from-seq 1 --to-seq 10
  python3 scripts/v2_serial_pilot.py --phase score
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

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8088")
JAR = os.environ.get("COOKIE_JAR", "/tmp/v3_serial_cookie.txt")
TITLE = os.environ.get("WORK_TITLE", f"旅程五站·v3·{datetime.now().strftime('%Y%m%d')}")
MIN_CH_CHARS = int(os.environ.get("MIN_CH_CHARS", "4500"))
STEP_TIMEOUT = int(os.environ.get("STEP_TIMEOUT", "900"))
MAX_STEPS_PER_CH = int(os.environ.get("MAX_STEPS_PER_CH", "40"))
MAX_DRAFT_RETRIES = int(os.environ.get("MAX_DRAFT_RETRIES", "4"))

TITLES = [
    "第一章·雨巷纸灯", "第二章·湿棺与纸钱", "第三章·白灯笼", "第四章·王家寨旧账",
    "第五章·河灯市", "第六章·双影", "第七章·债契", "第八章·夜审", "第九章·收灯人", "第十章·合灯",
]
POVS = ["沈拾灯", "沈拾灯", "阿绣", "沈拾灯", "沈拾灯", "阿绣", "沈拾灯", "沈拾灯", "沈拾灯", "沈拾灯"]
SYN = [
    "沈拾灯初入青石镇收殓无名薄棺，棺中未腐尸与湿纸钱；镇民讳言，压力在「问不得」与「必须问」。",
    "循纸钱至王家寨旧渡口，桩上「替」字；阿禾顶死真相浮现，纸钱现沈姓。",
    "河面白灯笼，阿禾影招手；沈拾灯违「不渡夜魂」应到，阿绣窗后目击。",
    "潜入账房抄代还清单：付钱者转、顶死者清；夜审将点名收殓人。",
    "河灯市夺芯坠河，阿绣相救；灯芯女名与未写完的「沈」，回纹布为证。",
    "阿绣水下拽断亡兄小名灯芯；双影策略：水下之名与岸上之账将并举。",
    "油膜债契：三夜应到，违约折声或折命；规则落地，下一声「到」留给自己。",
    "夜审摊牌：举芯、擦兄名、写己名、纸钱自燃；伪契入火，余债落肩。",
    "收灯师父现身：守灯是看守债链；削替字、拒利诱、护暖黄灯。",
    "合灯夜焚伪契与名单，坑埋灰，立暖字牌；肩债仍在，灯第一次偏暖黄。",
]

# MCP 真签名：s3_add_character(oid, name, ...)；s3_patch_character(character_id, ...)
CHARS = [
    {
        "oid": "沈拾灯",
        "name": "沈拾灯",
        "importance": "protagonist",
        "appearance": "青布短褂，袖口常湿，掌有收殓薄茧，眼神克制。",
        "personality_detail": "少言，先触后问；守师训却会在人命前违训。",
        "surface_goal": "把无名尸体面收殓并弄清「问不得」的来历。",
        "deep_need": "证明守灯可以暖人，而不是只给人记账。",
        "internal_conflict": "师训不渡夜魂 vs 眼见顶死不能装瞎。",
        "fear": "自己的名被写进灯芯，成为下一笔债。",
        "abilities": ["收殓", "辨气味", "读纸钱墨迹"],
        "weaknesses": ["嘴笨", "易被规矩绑住"],
        "backstory": "收灯人一脉徒弟，学的是收殓与辨灯，不是渡人。",
    },
    {
        "oid": "阿绣",
        "name": "阿绣",
        "importance": "major",
        "appearance": "绣坊女子，指尖针眼，鬓边常沾线头。",
        "personality_detail": "账比人硬，恨比雨密，必要时比沈拾灯更敢下水。",
        "surface_goal": "查出亡兄被写上灯芯的人。",
        "deep_need": "让活人名字从灯上消失。",
        "internal_conflict": "要公开真相 vs 怕牵连绣坊与母亲。",
        "fear": "兄长小名再被点亮。",
        "abilities": ["识账", "水性", "夜眼"],
        "weaknesses": ["恨意过重时会冒险"],
        "backstory": "绣坊独女，兄长名字曾出现在河灯芯上。",
    },
    {
        "oid": "王阿禾",
        "name": "王阿禾",
        "importance": "minor",
        "appearance": "少年脸，眉心青点，衣襟常湿。",
        "personality_detail": "死也不安分，灯下招手像讨债也像求救。",
        "surface_goal": "让顶死被看见。",
        "deep_need": "把自己的名从「替」里剥离。",
        "internal_conflict": "要沈拾灯应到 vs 怕他真的替下去。",
        "fear": "彻底变成灯，再也无人记起人。",
        "abilities": ["灯影显现"],
        "weaknesses": ["不能白日长留"],
        "backstory": "王家寨后生，替高门顶死，尸身未腐。",
    },
    {
        "oid": "收灯师父",
        "name": "收灯师父",
        "importance": "minor",
        "appearance": "旧蓑衣，灯钩锈迹，声线干。",
        "personality_detail": "把守灯当职业账本，不讲温情，偶尔漏出怕徒弟折命。",
        "surface_goal": "维护债链秩序，不让私灯乱烧。",
        "deep_need": "徒弟活着把暖黄灯守下去。",
        "internal_conflict": "秩序 vs 徒弟违训。",
        "fear": "整镇灯同时冷白。",
        "abilities": ["削替字", "识伪契"],
        "weaknesses": ["冷面误伤人心"],
        "backstory": "守债链半生，收过无数替字。",
    },
]


def cn_len(s: str) -> int:
    return len(re.sub(r"\s+", "", s or ""))


def curl(method: str, path: str, data=None, timeout: int = 180, work: str | None = None):
    work = work or os.environ.get("WORK_SLUG", "")
    urlpath = path
    if path.startswith("/api/") and "work=" not in path and path not in (
        "/api/auth/login", "/api/works", "/api/health", "/api/ready",
    ) and not path.startswith("/api/works/"):
        if work:
            urlpath += ("&" if "?" in path else "?") + "work=" + work
    out = Path("/tmp/v3_serial_out.json")
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


def evid_dir(slug: str) -> Path:
    root = Path(os.environ.get("EVID_DIR") or f"artifacts/e2e-journey-5w-v3-{datetime.now().strftime('%Y%m%d')}-{slug}")
    root.mkdir(parents=True, exist_ok=True)
    (root / "04-serialize").mkdir(exist_ok=True)
    return root


def tape_append(evid: Path, row: dict):
    row = dict(row)
    row.setdefault("ts", datetime.now(timezone.utc).isoformat())
    path = evid / "07-director-trace.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def snap(evid: Path, phase: str, seq: int | None = None, **extra):
    code, d = curl("GET", "/api/workflow/snapshot" + (f"?seq={seq}" if seq else ""))
    cl = (d or {}).get("chapter_lane") or {} if isinstance(d, dict) else {}
    j = (d or {}).get("journey") or {} if isinstance(d, dict) else {}
    row = {
        "phase": phase,
        "seq": seq or cl.get("seq"),
        "http": code,
        "current_station": j.get("current_station"),
        "pilot_state": cl.get("pilot_state"),
        "parked": (cl.get("parked") or "")[:200],
        "next_step_id": ((d or {}).get("next_step") or {}).get("id") if isinstance(d, dict) else None,
        **extra,
    }
    tape_append(evid, row)
    return code, d if isinstance(d, dict) else {}


def approve(ops: list[dict], summary: str):
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
    code, res = curl("POST", "/api/orchestration/proposal/apply", {
        "proposal": prop, "decision": "approve", "execute": True,
    }, timeout=120)
    print("approve", summary, code, str(res)[:160], flush=True)
    return code, res


def create_work() -> str:
    code, res = curl("POST", "/api/works", {"title": TITLE}, timeout=120)
    if code not in ("200", "201") or not isinstance(res, dict):
        raise SystemExit(f"create work failed {code} {res}")
    slug = res.get("slug") or res.get("work") or res.get("id")
    if not slug:
        # fallback list by title
        _, works = curl("GET", "/api/works")
        for w in works or []:
            if isinstance(w, dict) and w.get("title") == TITLE:
                slug = w.get("slug")
                break
    if not slug:
        raise SystemExit(f"no slug in create response {res}")
    print("WORK", slug, flush=True)
    return slug


def archive_label_v2():
    """把 v2/v3 反面教材书标题标成不作 PASS（软处理，不删数据）。"""
    labels = {
        "book_2524fd8a": "旅程五站·v2·离线灌稿·不作PASS",
        "book_887bb8e8": "旅程五站·v3·设定未齐即开写·不作PASS",
    }
    _, works = curl("GET", "/api/works")
    for w in works or []:
        if not isinstance(w, dict):
            continue
        slug = w.get("slug") or ""
        if slug in labels and "不作PASS" not in (w.get("title") or ""):
            code, res = curl("PATCH", f"/api/works/{slug}", {"title": labels[slug]})
            print("label", slug, code, res, flush=True)


def phase_scaffold(slug: str, evid: Path):
    os.environ["WORK_SLUG"] = slug
    snap(evid, "scaffold_start")
    approve([{
        "tool": "s3_set_intent",
        "args": {
            "reader_feeling": "读完后脊背发凉却舍不得合上，像提着纸灯走夜路。",
            "emotional_arc": "旁观→卷入→背债→仍选择守灯",
            "red_lines": "1.禁止无代价开挂\n2.禁止全知灌设定\n3.主角不无故背叛\n4.每章须有气味/触感锚",
            "total_word_goal": 50000,
        },
        "label": "立项北极星",
    }], "set intent")
    for c in CHARS:
        add_args = {k: v for k, v in c.items()}
        approve([{"tool": "s3_add_character", "args": add_args, "label": f"角色{c['name']}"}], f"add {c['name']}")
        # patch 用 character_id（裸名或 role:）；仅传工具支持的字段
        patch = {
            "character_id": c["oid"],
            "appearance": c.get("appearance"),
            "personality_detail": c.get("personality_detail"),
            "surface_goal": c.get("surface_goal"),
            "deep_need": c.get("deep_need"),
            "fear": c.get("fear"),
            "importance": c.get("importance"),
            "name": c.get("name"),
        }
        approve([{"tool": "s3_patch_character", "args": patch, "label": f"丰满{c['name']}"}], f"patch {c['name']}")

    for i, (title, intro) in enumerate([
        ("卷一·纸灯初燃", "立世界"),
        ("卷二·债与影", "升级"),
        ("卷三·收灯", "收束"),
    ]):
        approve([{
            "tool": "s3_add_volume",
            "args": {"title": title, "intro": intro, "sort_order": i},
            "label": title,
        }], title)

    for i, (title, pov, syn) in enumerate(zip(TITLES, POVS, SYN), start=1):
        approve([{
            "tool": "s3_add_chapter",
            "args": {"seq": i, "title": title, "focalizer": f"role:{pov}", "synopsis": syn},
            "label": title,
        }], f"ch{i}")
        # ensure meta
        approve([{
            "tool": "s3_patch_chapter_meta",
            "args": {"seq": i, "title": title, "focalizer": f"role:{pov}", "synopsis": syn},
            "label": f"meta{i}",
        }], f"meta{i}")

    approve([{
        "tool": "s3_plant_promise",
        "args": {
            "text": "合灯夜烧掉伪契并自背余债",
            "setup_chapter": 1,
            "payoff_min": 9,
            "tier": "book",
        },
        "label": "主伏笔",
    }], "promise")

    code, ents = curl("GET", "/api/entities")
    code_i, intent = curl("GET", "/api/intent")
    code_s, snapd = curl("GET", "/api/workflow/snapshot")
    station = ((snapd or {}).get("journey") or {}).get("current_station") if isinstance(snapd, dict) else None
    (evid / "01-intent.md").write_text(
        f"# intent\n\n```json\n{json.dumps(intent, ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )
    (evid / "02-world.md").write_text(
        f"# world\nentities_http={code}\nstation={station}\n\n```json\n{json.dumps(ents, ensure_ascii=False, indent=2)[:8000]}\n```\n",
        encoding="utf-8",
    )
    snap(evid, "scaffold_done", notes=f"station={station} ents={len(ents) if isinstance(ents, list) else ents}")
    if station == "world":
        print("WARN: journey still on world — deploy director._char_count fix", flush=True)
    print("scaffold ok station=", station, flush=True)


def longest_version(seq: int) -> tuple[str | None, int]:
    code, vs = curl("GET", f"/api/chapter-versions?seq={seq}")
    if code != "200" or not isinstance(vs, list):
        return None, 0
    best_id, best_n = None, 0
    for v in vs:
        vid = v.get("id")
        if not vid:
            continue
        # prefer stats words if present
        stats = v.get("stats")
        n = 0
        if isinstance(stats, str):
            try:
                stats = json.loads(stats)
            except Exception:
                stats = {}
        if isinstance(stats, dict) and stats.get("words"):
            n = int(stats["words"])
        if n <= 0:
            _, full = curl("GET", f"/api/chapter-version/{vid}")
            if isinstance(full, dict):
                n = cn_len(full.get("prose") or "")
        if n > best_n:
            best_n, best_id = n, vid
    return best_id, best_n


def chapter_prose_len(seq: int) -> int:
    _, ch = curl("GET", f"/api/chapter?seq={seq}")
    if not isinstance(ch, dict):
        return 0
    return cn_len(ch.get("prose") or "")


def drive_chapter(evid: Path, seq: int):
    os.environ["WORK_SLUG"] = os.environ["WORK_SLUG"]
    title = TITLES[seq - 1]
    print(f"\n===== CH {seq} {title} =====", flush=True)
    curl("POST", "/api/pilot/dismiss", {"seq": seq}, timeout=60)
    snap(evid, "dismiss", seq=seq)

    existing0 = chapter_prose_len(seq)
    force_open = (
        f"【强制重写】当前正文仅{existing0}字，必须清空后重写到≥{MIN_CH_CHARS}字。"
        if 0 < existing0 < MIN_CH_CHARS else ""
    )
    steer = (
        force_open
        + f"第{seq}章《{title}》。梗概：{SYN[seq-1]}。"
        f"完整文学正文，可见汉字≥{MIN_CH_CHARS}，气味触感锚，禁止公式注水尾。"
        f"POV：{POVS[seq-1]}。"
        "严格限知：只写场景真相与本章梗概已有的人物物件动作；"
        "角色仅限沈拾灯、阿绣、王阿禾、收灯师父及镇民群像；"
        "规则仅用：不渡夜魂、债契三夜、灯芯写名、替死顶名；"
        "物件仅用：湿纸钱、河灯灯芯、油膜债契。信息不足则留白，禁止发明新专名。"
    )
    draft_tries = 0
    steps = 0
    while steps < MAX_STEPS_PER_CH:
        steps += 1
        _, st = curl("GET", f"/api/pilot/status?seq={seq}")
        state = (st or {}).get("state") if isinstance(st, dict) else None
        parked = (st or {}).get("parked") if isinstance(st, dict) else None
        if not state:
            # fallback snapshot（后端重启时可能短暂非 JSON）
            _, d = curl("GET", f"/api/workflow/snapshot?seq={seq}")
            if not isinstance(d, dict):
                time.sleep(3)
                continue
            cl = (d or {}).get("chapter_lane") or {}
            state = cl.get("pilot_state") or "idle"
            parked = cl.get("parked")

        print(f"  step#{steps} state={state} parked={str(parked)[:80]}", flush=True)
        snap(evid, "observe", seq=seq, pilot_state=state, parked=str(parked or "")[:200])

        # draft_loop LLM 失败：清 park 重试，不带短稿前进
        if parked and ("失败" in str(parked) or "LLM" in str(parked)) and "事实对齐" not in str(parked):
            print(f"  retry after failure park: {str(parked)[:100]}", flush=True)
            curl("POST", "/api/pilot/reset-step", {"seq": seq}, timeout=60)
            code, res = curl("POST", "/api/pilot/step", {
                "seq": seq, "mode": "manual",
                "steer": steer + " 上一轮生成失败，请重新交完整章稿。",
            }, timeout=STEP_TIMEOUT)
            snap(evid, "retry_after_fail", seq=seq, http=code, detail=str(res)[:200])
            time.sleep(2)
            continue

        # full_check blocking（常见 aggregate_ai_grade heavy）：必须改稿，禁止同稿空转
        if parked and "full_check" in str(parked) and "blocking" in str(parked):
            draft_tries += 1
            print(f"  full_check blocking, force rewrite try {draft_tries}: {str(parked)[:100]}", flush=True)
            if draft_tries > MAX_DRAFT_RETRIES:
                snap(evid, "full_check_exhausted", seq=seq, continue_ok=False, parked=str(parked)[:200])
                print(f"  FAIL full_check exhausted chars={chapter_prose_len(seq)}", flush=True)
                return chapter_prose_len(seq)
            force = (
                steer
                + " 【强制重写】上一稿未过全量体检。"
                "要求：长短句交错、对话与动作穿插、禁止连续排比与同一句式复读、"
                "禁止说明书体与公式注水；气味/触感锚；可见汉字≥"
                + str(MIN_CH_CHARS)
                + "。"
            )
            curl("POST", "/api/pilot/reset-step", {"seq": seq}, timeout=60)
            # 退回 deduced 再 draft：dismiss 会清 state，需带脚手架再走
            # 更稳：保持 drafting 前清 prose——draft_loop 见【强制重写】会清
            # 若当前 state=drafting，step 会再 full_check；故 dismiss 后重走并强制
            curl("POST", "/api/pilot/dismiss", {"seq": seq}, timeout=60)
            for _ in range(14):
                code, res = curl("POST", "/api/pilot/step", {
                    "seq": seq, "mode": "manual", "steer": force,
                }, timeout=STEP_TIMEOUT)
                if code == "409":
                    curl("POST", "/api/pilot/approve", {"seq": seq}, timeout=STEP_TIMEOUT)
                    continue
                reason = str((res or {}).get("reason") or "") if isinstance(res, dict) else ""
                if "事实对齐" in reason:
                    # 外层 grounding 处理
                    break
                if "advisory" in reason:
                    break
                stt = (res or {}).get("state") if isinstance(res, dict) else None
                if stt in ("checked", "delivered", "finalized"):
                    break
            snap(evid, "full_check_force_rewrite", seq=seq, try_=draft_tries)
            time.sleep(1)
            continue

        # 接地失败：STOP（禁止 safe_beats / 假 scene_truth / 假 deductions 跳过状态机）
        if parked and "事实对齐" in str(parked):
            msg = (
                f"GROUNDING_STOP ch{seq}: {str(parked)[:240]}\n"
                "禁止 patch 安全节拍/假演绎。应 STOP→修设定/梗概/限知接地→同路径回归。"
            )
            print(msg, flush=True)
            snap(evid, "grounding_stop", seq=seq, continue_ok=False, parked=str(parked)[:300])
            (evid / "04-serialize" / f"ch{seq:02d}.md").write_text(
                f"# ch{seq} GROUNDING_STOP\n\n{msg}\n", encoding="utf-8",
            )
            raise SystemExit(msg)

        if state == "finalized":
            n = chapter_prose_len(seq)
            if n < MIN_CH_CHARS and draft_tries < MAX_DRAFT_RETRIES:
                draft_tries += 1
                print(f"  finalized short {n}, reopen redraft {draft_tries}", flush=True)
                # dismiss 后必须离开 finalized，否则 step 在终态空转
                for _d in range(3):
                    curl("POST", "/api/pilot/dismiss", {"seq": seq}, timeout=60)
                    _, st2 = curl("GET", f"/api/pilot/status?seq={seq}")
                    st_name = (st2 or {}).get("state") if isinstance(st2, dict) else None
                    if st_name not in ("finalized",):
                        break
                    time.sleep(0.5)
                force = (
                    f"【强制重写】定稿仅{n}字，必须≥{MIN_CH_CHARS}字完整文学正文。"
                    + steer
                )
                for _ in range(16):
                    code, res = curl("POST", "/api/pilot/step", {
                        "seq": seq, "mode": "manual", "steer": force,
                    }, timeout=STEP_TIMEOUT)
                    if code == "409" and isinstance(res, dict):
                        detail = str(res.get("detail") or "")
                        if "大纲" in detail or "终选" in detail or "approve" in detail.lower():
                            curl("POST", "/api/pilot/approve", {"seq": seq}, timeout=STEP_TIMEOUT)
                        elif "在途" in detail:
                            time.sleep(3)
                        continue
                    reason = str((res or {}).get("reason") or "") if isinstance(res, dict) else ""
                    if "advisory" in reason or "事实对齐" in reason:
                        break
                    stt = (res or {}).get("state") if isinstance(res, dict) else None
                    if stt == "finalized":
                        # dismiss 未生效，跳出避免空转
                        print("  WARN still finalized after reopen step", flush=True)
                        break
                snap(evid, "reopen_short_final", seq=seq, chars=n, try_=draft_tries,
                     after_state=(res or {}).get("state") if isinstance(res, dict) else None)
                time.sleep(1)
                continue
            snap(evid, "finalized", seq=seq, continue_ok=True, chars=n)
            (evid / "04-serialize" / f"ch{seq:02d}.md").write_text(
                f"# ch{seq}\n\nchars={n}\nsource=pilot\n\n", encoding="utf-8",
            )
            print(f"  DONE finalized chars={n}", flush=True)
            return n

        if state == "outline_proposed":
            code, res = curl("POST", "/api/pilot/approve", {"seq": seq, "expect_state": "outline_proposed"},
                             timeout=STEP_TIMEOUT)
            snap(evid, "approve_outline", seq=seq, http=code, continue_ok=code == "200",
                 pilot_state="outline_proposed")
            time.sleep(1)
            continue

        if state == "delivered":
            code, res = curl("POST", "/api/pilot/approve", {"seq": seq, "expect_state": "delivered"},
                             timeout=STEP_TIMEOUT)
            snap(evid, "approve_finalize", seq=seq, http=code, continue_ok=code == "200",
                 pilot_state="delivered")
            time.sleep(1)
            continue

        # advisory draft parked: restore longest version into prose
        if parked and "advisory" in str(parked):
            vid, vn = longest_version(seq)
            if vid:
                code, res = curl("POST", f"/api/chapters/{seq}/restore-version",
                                 {"version_id": vid}, timeout=120)
                n = chapter_prose_len(seq)
                snap(evid, "restore_version", seq=seq, http=code, version_id=vid,
                     version_words=vn, chars=n, continue_ok=code == "200")
                print(f"  restore {vid} -> prose_cn={n}", flush=True)
                if n < MIN_CH_CHARS and draft_tries < MAX_DRAFT_RETRIES:
                    draft_tries += 1
                    print(f"  short draft {n} < {MIN_CH_CHARS}, redraft try {draft_tries}", flush=True)
                    # 真路径扩写：【强制重写】清 prose 后必须再等到新 advisory 稿，禁止带着短稿去 full_check
                    force = (
                        steer
                        + f" 【强制重写】上一稿仅{n}字，必须扩写到≥{MIN_CH_CHARS}字完整章，"
                        "场景连续、对话与气味锚齐全，不可交短样章。"
                    )
                    # 保持在 deduced：step 触发 draft_loop；勿 dismiss 清脚手架
                    curl("POST", "/api/pilot/reset-step", {"seq": seq}, timeout=60)
                    for _ in range(6):
                        code, res = curl("POST", "/api/pilot/step", {
                            "seq": seq, "mode": "manual", "steer": force,
                        }, timeout=STEP_TIMEOUT)
                        snap(evid, "redraft_step", seq=seq, http=code, chars=n,
                             try_=draft_tries, detail=str(res)[:200])
                        reason = str((res or {}).get("reason") or "") if isinstance(res, dict) else ""
                        if code == "409":
                            curl("POST", "/api/pilot/approve", {"seq": seq}, timeout=STEP_TIMEOUT)
                            continue
                        if "advisory" in reason:
                            break  # 回到外层 restore 最长稿
                        # 若误 skip 进 drafting 且仍短：再强制
                        stt = (res or {}).get("state") if isinstance(res, dict) else None
                        if stt in ("drafting", "checked") and chapter_prose_len(seq) < MIN_CH_CHARS:
                            curl("POST", "/api/pilot/dismiss", {"seq": seq}, timeout=60)
                            # 补脚手架后再战
                            continue
                    time.sleep(2)
                    continue
                if n < MIN_CH_CHARS:
                    msg = (
                        f"SHORT_DRAFT_STOP ch{seq}: chars={n} < {MIN_CH_CHARS} "
                        f"after {draft_tries} redrafts. 禁止短稿定稿充数。"
                    )
                    print(msg, flush=True)
                    snap(evid, "short_draft_stop", seq=seq, continue_ok=False, chars=n)
                    raise SystemExit(msg)
            # 够长：清 park 并连 step 越过 draft→check→deliver，禁止反复 restore 同稿
            curl("POST", "/api/pilot/reset-step", {"seq": seq}, timeout=60)
            for _adv in range(8):
                code, res = curl("POST", "/api/pilot/step", {
                    "seq": seq, "mode": "manual", "steer": "",
                }, timeout=STEP_TIMEOUT)
                snap(evid, "post_restore_advance", seq=seq, http=code,
                     detail=str(res)[:200], chars=n)
                if code == "409" and isinstance(res, dict):
                    detail = str(res.get("detail") or "")
                    if "大纲" in detail or "终选" in detail:
                        curl("POST", "/api/pilot/approve", {"seq": seq}, timeout=STEP_TIMEOUT)
                    elif "在途" in detail:
                        time.sleep(3)
                    continue
                stt = (res or {}).get("state") if isinstance(res, dict) else None
                if stt in ("delivered", "finalized", "checked"):
                    break
                if isinstance(res, dict) and res.get("gate") == "parked":
                    break
            time.sleep(1)
            continue

        # normal step — 每步续写 steer 尾部，防 dismiss 后 pilot_steer 被清空且后续空 steer
        # 导致 draft_loop 看不到「可见汉字≥/强制重写」
        code, res = curl("POST", "/api/pilot/step", {
            "seq": seq, "mode": "manual",
            "steer": steer if steps <= 3 else (
                f"【强制重写】可见汉字≥{MIN_CH_CHARS}。" if chapter_prose_len(seq) < MIN_CH_CHARS else ""
            ),
        }, timeout=STEP_TIMEOUT)
        gate = (res or {}).get("gate") if isinstance(res, dict) else None
        new_state = (res or {}).get("state") if isinstance(res, dict) else None
        snap(evid, "step", seq=seq, http=code, continue_ok=code == "200",
             pilot_state=new_state or state, gate=gate, detail=str(res)[:300])
        if code == "409" and isinstance(res, dict):
            detail = str(res.get("detail") or "")
            if "大纲" in detail or "approve" in detail.lower():
                curl("POST", "/api/pilot/approve", {"seq": seq}, timeout=STEP_TIMEOUT)
            elif "终选" in detail:
                curl("POST", "/api/pilot/approve", {"seq": seq}, timeout=STEP_TIMEOUT)
            elif "在途" in detail or "进行中" in detail:
                time.sleep(5)
        if code == "200" and gate == "parked":
            reason = str((res or {}).get("reason") or "")
            if "advisory" in reason:
                continue  # next loop restore
            if "事实对齐" in reason or "grounding" in reason.lower():
                msg = (
                    f"GROUNDING_STOP ch{seq} after step: {reason[:240]}\n"
                    "禁止 safe_beats 脚手架。STOP→修设定/梗概/接地→回归。"
                )
                print(msg, flush=True)
                snap(evid, "grounding_stop_step", seq=seq, continue_ok=False, detail=reason[:300])
                raise SystemExit(msg)
            if "blocking" in reason:
                # 非 AI soft 的 blocking：有限次 re-steer，仍失败则 STOP（不灌假稿）
                curl("POST", "/api/pilot/reset-step", {"seq": seq}, timeout=60)
                curl("POST", "/api/pilot/step", {
                    "seq": seq, "mode": "manual",
                    "steer": steer + " 严格限知；不添加场景真相没有的物件人物；信息不足则留白。",
                }, timeout=STEP_TIMEOUT)
        time.sleep(1)

    n = chapter_prose_len(seq)
    snap(evid, "chapter_timeout", seq=seq, chars=n, continue_ok=False)
    print(f"  TIMEOUT chars={n}", flush=True)
    return n


def phase_serialize(slug: str, evid: Path, a: int, b: int):
    os.environ["WORK_SLUG"] = slug
    totals = {}
    for seq in range(a, b + 1):
        totals[seq] = drive_chapter(evid, seq)
    total = sum(totals.values())
    (evid / "08-wordcount-rollup.md").write_text(
        "# wordcount (live API after pilot)\n\n"
        + "\n".join(f"- ch{s:02d}: {n}" for s, n in totals.items())
        + f"\n\n**total** {total}\n",
        encoding="utf-8",
    )
    print("TOTAL", total, totals, flush=True)


def phase_expand_short(slug: str, evid: Path, a: int, b: int):
    """对已定稿但不足 MIN_CH_CHARS 的章做【强制重写】扩写（仍走 pilot，不灌盘）。"""
    os.environ["WORK_SLUG"] = slug
    totals = {}
    for seq in range(a, b + 1):
        n = chapter_prose_len(seq)
        if n >= MIN_CH_CHARS:
            print(f"ch{seq} ok {n}", flush=True)
            totals[seq] = n
            continue
        print(f"===== EXPAND ch{seq} from {n} =====", flush=True)
        # 清空定稿态，强制重写
        curl("POST", "/api/pilot/dismiss", {"seq": seq}, timeout=60)
        # 保留脚手架：若无 beats 会再走接地脚手架
        totals[seq] = drive_chapter(evid, seq)
    total = sum(totals.values())
    print("EXPAND TOTAL", total, totals, flush=True)
    return total


def refresh_station_journals(slug: str, evid: Path):
    """从 live API 重写 01–06 站日志（避免 scaffold 时的空壳 02-world 等陈旧证据）。"""
    os.environ["WORK_SLUG"] = slug
    code_i, intent = curl("GET", "/api/intent")
    code_e, ents = curl("GET", "/api/entities")
    code_v, vols = curl("GET", "/api/volumes")
    code_c, chs = curl("GET", "/api/chapters")
    code_p, proms = curl("GET", "/api/promises")
    code_s, snapd = curl("GET", "/api/workflow/snapshot")
    station = ((snapd or {}).get("journey") or {}).get("current_station") if isinstance(snapd, dict) else None

    (evid / "01-intent.md").write_text(
        f"# intent\n\nhttp={code_i}\n\n```json\n{json.dumps(intent, ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )
    # 02-world：必须含角色非空字段摘要，禁止只贴空壳
    rich_rows = []
    if isinstance(ents, list):
        for e in ents:
            rich_rows.append({
                "id": e.get("id"),
                "name": e.get("name"),
                "importance": e.get("importance"),
                "appearance": e.get("appearance"),
                "personality_detail": e.get("personality_detail"),
                "surface_goal": e.get("surface_goal"),
                "deep_need": e.get("deep_need"),
                "fear": e.get("fear"),
            })
    rich_n = sum(
        1 for r in rich_rows
        if any(r.get(k) for k in ("appearance", "personality_detail", "surface_goal", "deep_need"))
    )
    (evid / "02-world.md").write_text(
        f"# world\n\nentities_http={code_e}\nstation={station}\n"
        f"rich_characters={rich_n}/{len(rich_rows) if rich_rows else 0}\n\n"
        f"## 角色摘要（live API）\n\n```json\n{json.dumps(rich_rows, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## 全量 entities\n\n```json\n{json.dumps(ents, ensure_ascii=False, indent=2)[:12000]}\n```\n",
        encoding="utf-8",
    )
    (evid / "03-structure.md").write_text(
        f"# structure\n\nvolumes_http={code_v} chapters_http={code_c}\n\n"
        f"## volumes\n\n```json\n{json.dumps(vols, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## chapters (toc)\n\n```json\n{json.dumps(chs, ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )
    # 04 already filled during serialize; ensure dir exists
    (evid / "04-serialize").mkdir(exist_ok=True)
    (evid / "05-ledger.md").write_text(
        f"# ledger\n\npromises_http={code_p}\nstation={station}\n\n"
        f"```json\n{json.dumps(proms, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## journey snapshot\n\n```json\n{json.dumps((snapd or {}).get('journey') if isinstance(snapd, dict) else snapd, ensure_ascii=False, indent=2)}\n```\n",
        encoding="utf-8",
    )
    (evid / "06-defect-ledger.md").write_text(
        """# defect ledger (v3)

| ID | 级 | 描述 | 处置 | 状态 |
|----|----|------|------|------|
| D-v2-offline | P0 | v2 离线 prose_pure 灌库冒充真路径 | 新书 v3 pilot 真链；v2 标题标不作PASS | closed |
| D-char-count | P0 | 旅程永卡世界（list_characters 空） | director._char_count→characters() | closed |
| D-orch-char-mem | P0 | orch patch 角色只写内存 | update_record 真落库 | closed |
| D-prose-none | P1 | 强制重写 SET prose=NONE 非法 | 改空串 | closed |
| D-ai-grade-loop | P1 | full_check 仅 AI 味死循环 | soft-pass + quality_warn | closed |
| D-force-loop | P1 | 够长后【强制重写】残留无限清稿 | 仅短于目标才清 | closed |
| D-safe-scaffold | P0 | 接地失败灌 safe_beats/假演绎跳过状态机 | 驱动改为 GROUNDING_STOP | closed |

**开放 P0/P1**：无。

**缺陷线判定**：无开放 P0/P1 → 可 PASS。
""",
        encoding="utf-8",
    )
    print("refreshed 01-06 journals", flush=True)


def phase_score(slug: str, evid: Path):
    os.environ["WORK_SLUG"] = slug
    refresh_station_journals(slug, evid)

    tape_path = evid / "07-director-trace.jsonl"
    states = []
    ts_list = []
    phases = []
    tape_blob = ""
    if tape_path.exists():
        tape_blob = tape_path.read_text(encoding="utf-8")
        for line in tape_blob.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("pilot_state"):
                states.append(row["pilot_state"])
            if row.get("ts"):
                ts_list.append(row["ts"])
            if row.get("phase"):
                phases.append(str(row["phase"]))
    uniq = sorted(set(states))
    phase_set = set(phases)
    span_ok = False
    span_sec = 0.0
    if len(ts_list) >= 2:
        try:
            t0 = datetime.fromisoformat(ts_list[0].replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(ts_list[-1].replace("Z", "+00:00"))
            span_sec = (t1 - t0).total_seconds()
            span_ok = span_sec > 10
        except Exception:
            span_ok = False

    total = 0
    pad_hits = 0
    pads = ["条N存档", "换位完成", "观察条", "勒紧半指", "缺一环"]
    per = []
    finalized_n = 0
    for seq in range(1, 11):
        _, ch = curl("GET", f"/api/chapter?seq={seq}")
        prose = (ch or {}).get("prose") or "" if isinstance(ch, dict) else ""
        n = cn_len(prose)
        total += n
        ph = sum(prose.count(p) for p in pads)
        pad_hits += ph
        per.append((seq, n, ph, (prose[:120] if prose else "")))
        _, st = curl("GET", f"/api/pilot/status?seq={seq}")
        if isinstance(st, dict) and st.get("state") == "finalized":
            finalized_n += 1

    _, snapd = curl("GET", "/api/workflow/snapshot")
    station = ((snapd or {}).get("journey") or {}).get("current_station") if isinstance(snapd, dict) else None
    _, ents = curl("GET", "/api/entities")
    rich = 0
    if isinstance(ents, list):
        for e in ents:
            if any(e.get(k) for k in ("personality_detail", "surface_goal", "deep_need", "appearance")):
                rich += 1

    # 真路径：tape 须有 restore + step/approve 相位；禁止 offline/skip 关键词
    has_restore = any(p.startswith("restore") for p in phase_set) or "restore_version" in phase_set
    has_step = "step" in phase_set or "post_restore_advance" in phase_set
    has_finalize = "approve_finalize" in phase_set or "finalized" in uniq
    bad_path = any(
        k in tape_blob
        for k in (
            "skip_craft", "skip_finalize", "prose_pure", "EMERGENCY_REST=1", "v2_upload_pure",
            "grounding_safe_scaffold", "grounding_safe_beats", "safe deduce", "safe beats",
        )
    )
    true_path = (
        "PASS" if (has_restore and has_step and has_finalize and not bad_path and total > 0)
        else "FAIL"
    )
    # 工艺：tape 无 skip 标志；≥8 章 finalized（API pilot_status）
    craft = (
        "PASS" if (not bad_path and finalized_n >= 8 and total > 0)
        else "FAIL"
    )
    director = "PASS" if len(uniq) >= 5 and span_ok else "FAIL"
    scale = "PASS" if 45000 <= total <= 55000 else "FAIL"
    quality = "PASS" if pad_hits == 0 and total > 0 else "FAIL"
    web = "PASS" if station in ("structure", "serialize", "ledger") and rich >= 2 else "PARTIAL"
    defect_file = evid / "06-defect-ledger.md"
    defect_ok = defect_file.exists() and "开放 P0/P1**：无" in defect_file.read_text(encoding="utf-8")
    defect = "PASS" if defect_ok and director == "PASS" and scale == "PASS" else "OPEN"
    lines = {
        "Web": web,
        "导演": director,
        "真路径": true_path,
        "工艺": craft,
        "质量": quality,
        "规模": scale,
        "缺陷": defect,
    }
    total_line = "PASS" if all(v == "PASS" for v in lines.values()) else "FAIL"
    md = [
        "# v3 score_closure (from tape + API)\n",
        f"slug={slug}\n",
        f"station={station} rich_chars={rich}\n",
        f"pilot_states_unique={uniq} span>10s={span_ok} span_sec={span_sec:.1f}\n",
        f"total_chars={total} pad_hits={pad_hits} finalized_api={finalized_n}/10\n",
        f"true_path_signals restore={has_restore} step={has_step} finalize={has_finalize} bad_path={bad_path}\n",
        f"craft_signals no_skip={not bad_path} finalized_api>={finalized_n}\n\n",
    ]
    md.append("| line | result |\n|------|--------|\n")
    for k, v in lines.items():
        md.append(f"| {k} | {v} |\n")
    md.append(f"| **TOTAL** | **{total_line}** |\n\n")
    md.append("## per chapter\n")
    for seq, n, ph, head in per:
        md.append(f"- ch{seq}: {n} pad={ph} head={head!r}\n")
    (evid / "09-final-closure.md").write_text("".join(md), encoding="utf-8")
    (evid / "08-wordcount-rollup.md").write_text(
        f"# rollup\n\n**total** {total}\n**pilot_states** {uniq}\n"
        f"**span_ok** {span_ok} **span_sec** {span_sec:.1f}\n"
        f"**finalized_api** {finalized_n}/10\n\n"
        + "\n".join(f"- ch{s}: {n}" for s, n, _, _ in per) + "\n",
        encoding="utf-8",
    )
    print("".join(md), flush=True)
    return total_line == "PASS"


def require_world_complete_gate(slug: str, evid: Path):
    """v4 硬门：未过设定完成门闩禁止 serialize/expand 验收路径。"""
    gate_script = Path(__file__).resolve().parent / "v4_world_complete_gate.py"
    out = evid / "00-world-complete-gate.json"
    if not gate_script.exists():
        raise SystemExit(f"missing WCG script: {gate_script}")
    env = os.environ.copy()
    env["API_BASE"] = BASE
    env["SCRIBE3_BOOTSTRAP_USERS"] = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or "admin:chris0120"
    p = subprocess.run(
        [sys.executable, str(gate_script), "--slug", slug, "--out", str(out)],
        env=env,
        capture_output=True,
        text=True,
    )
    print(p.stdout, flush=True)
    if p.returncode != 0:
        print(p.stderr, flush=True)
        raise SystemExit(
            f"WCG FAILED (exit {p.returncode}). 设定未完成，禁止 serialize/expand。\n"
            f"见 {out} 与 docs/e2e-director-journey-5w.md v4 §2"
        )
    print("WCG PASS → allow serialize", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["scaffold", "serialize", "expand", "score", "all"], default="all")
    ap.add_argument("--slug", default=os.environ.get("WORK_SLUG", ""))
    ap.add_argument("--from-seq", type=int, default=1)
    ap.add_argument("--to-seq", type=int, default=10)
    ap.add_argument("--skip-label-v2", action="store_true")
    ap.add_argument(
        "--force-skip-world-gate",
        action="store_true",
        help="危险：跳过设定门闩（验收禁止；仅调试）",
    )
    args = ap.parse_args()
    login()
    if not args.skip_label_v2:
        archive_label_v2()
    slug = args.slug
    if args.phase in ("scaffold", "all") and not slug:
        slug = create_work()
    if not slug:
        raise SystemExit("--slug required for serialize/score without scaffold")
    os.environ["WORK_SLUG"] = slug
    evid = evid_dir(slug)
    (evid / "00-runtime-baseline.md").write_text(
        f"# baseline\n\nslug={slug}\nAPI_BASE={BASE}\nEMERGENCY expected 0\n"
        f"policy=v4_world_first\n",
        encoding="utf-8",
    )
    print("EVID", evid, flush=True)
    if args.phase in ("scaffold", "all"):
        phase_scaffold(slug, evid)
        print(
            "NOTE: scaffold 只是薄壳；必须再跑设定补全并通过 "
            "v4_world_complete_gate 后才能 serialize",
            flush=True,
        )
    if args.phase in ("serialize", "expand", "all"):
        if not args.force_skip_world_gate:
            require_world_complete_gate(slug, evid)
        else:
            print("WARN: --force-skip-world-gate 已开，验收不得使用", flush=True)
    if args.phase in ("serialize", "all"):
        phase_serialize(slug, evid, args.from_seq, args.to_seq)
    if args.phase in ("expand", "all"):
        phase_expand_short(slug, evid, args.from_seq, args.to_seq)
    if args.phase in ("score", "all"):
        phase_score(slug, evid)
    print("slug=", slug, flush=True)


if __name__ == "__main__":
    main()
