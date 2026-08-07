#!/usr/bin/env python3
"""v5 Phase A–C: 建书 + 完整世界设定 + 结构对齐（orch approve，EMERGENCY=0）。

不做正文。通过后应 `v4_world_complete_gate.py` exit 0。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8088")
JAR = os.environ.get("COOKIE_JAR", "/tmp/v5_bible_cookie.txt")
TITLE = os.environ.get("WORK_TITLE", f"旅程五站·v5·{time.strftime('%Y%m%d')}")


def curl(method, path, data=None, timeout=120, work=""):
    urlpath = path
    if (
        path.startswith("/api/")
        and "work=" not in path
        and path not in ("/api/auth/login", "/api/works", "/api/health", "/api/ready")
        and not path.startswith("/api/works/")
        and work
    ):
        urlpath += ("&" if "?" in path else "?") + "work=" + work
    out = Path("/tmp/v5_bible_out.json")
    cmd = [
        "curl", "-sS", "-o", str(out), "-w", "%{http_code}",
        "-b", JAR, "-c", JAR, "-X", method,
        "-H", f"Origin: {BASE}", "--max-time", str(timeout),
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
    assert code == "200", code


def approve(work, ops, summary):
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
        "POST",
        "/api/orchestration/proposal/apply",
        {"proposal": prop, "decision": "approve", "execute": True},
        work=work,
        timeout=120,
    )
    print("approve", summary, code, str(res)[:160], flush=True)
    if code != "200":
        raise SystemExit(f"approve failed {summary} {code} {res}")
    return res


def create_work():
    code, res = curl("POST", "/api/works", {"title": TITLE}, timeout=120)
    if code not in ("200", "201") or not isinstance(res, dict):
        raise SystemExit(f"create work failed {code} {res}")
    slug = res.get("slug") or res.get("work")
    if not slug:
        _, works = curl("GET", "/api/works")
        for w in works or []:
            if isinstance(w, dict) and w.get("title") == TITLE:
                slug = w.get("slug")
                break
    assert slug, res
    print("WORK", slug, flush=True)
    return slug


def main():
    login()
    slug = os.environ.get("WORK_SLUG") or create_work()
    w = slug

    # labels for old books
    for s, t in (
        ("book_2524fd8a", "旅程五站·v2·离线灌稿·不作PASS"),
        ("book_887bb8e8", "旅程五站·v3·设定未齐即开写·不作PASS"),
    ):
        curl("PATCH", f"/api/works/{s}", {"title": t})

    approve(w, [{
        "tool": "s3_set_intent",
        "args": {
            "reader_feeling": "读完后脊背发凉却舍不得合上，像提着纸灯走夜路。",
            "emotional_arc": "旁观→卷入→背债→仍选择守灯",
            "red_lines": "1.禁止无代价开挂\n2.禁止全知灌设定\n3.主角不无故背叛\n4.每章须有气味/触感锚\n5.设定未写入不得当作正文已知",
            "total_word_goal": 50000,
        },
    }], "intent")

    chars = [
        {
            "oid": "沈拾灯", "name": "沈拾灯", "importance": "protagonist",
            "appearance": "青布短褂，袖口常湿，掌有收殓薄茧，眼神克制。",
            "personality_detail": "少言，先触后问；守师训却会在人命前违训。",
            "surface_goal": "收殓无名尸并弄清「问不得」的来历。",
            "deep_need": "证明守灯可以暖人，而不是只给人记账。",
            "fear": "自己的名被写进灯芯，成为下一笔债。",
            "backstory": "收灯人一脉徒弟，学收殓与辨灯，不学渡人；师训「不渡夜魂」。",
            "abilities": ["收殓", "辨气味", "读纸钱墨迹"],
            "weaknesses": ["嘴笨", "易被规矩绑住"],
        },
        {
            "oid": "阿绣", "name": "阿绣", "importance": "major",
            "appearance": "绣坊女子，指尖针眼，鬓边常沾线头。",
            "personality_detail": "账比人硬，恨比雨密，必要时比沈拾灯更敢下水。",
            "surface_goal": "查出亡兄被写上灯芯的人。",
            "deep_need": "让活人名字从灯上消失。",
            "fear": "兄长小名再被点亮。",
            "backstory": "青石镇绣坊独女；兄长名字曾出现在河灯芯上后失踪。",
            "abilities": ["识账", "水性", "夜眼"],
            "weaknesses": ["恨意过重时会冒险"],
        },
        {
            "oid": "王阿禾", "name": "王阿禾", "importance": "minor",
            "appearance": "少年脸，眉心青点，衣襟常湿。",
            "personality_detail": "死也不安分，灯下招手像讨债也像求救。",
            "surface_goal": "让顶死被看见。",
            "deep_need": "把自己的名从「替」里剥离。",
            "fear": "彻底变成灯，再也无人记起人。",
            "backstory": "王家寨后生，替高门少爷顶死，尸身未腐。",
            "abilities": ["灯影显现"],
            "weaknesses": ["不能白日长留"],
        },
        {
            "oid": "收灯师父", "name": "收灯师父", "importance": "minor",
            "appearance": "旧蓑衣，灯钩锈迹，声线干。",
            "personality_detail": "把守灯当职业账本，不讲温情。",
            "surface_goal": "维护债链秩序，不让私灯乱烧。",
            "deep_need": "徒弟活着把暖黄灯守下去。",
            "fear": "整镇灯同时冷白。",
            "backstory": "守债链半生，收过无数替字，口传非法条款。",
            "abilities": ["削替字", "识伪契"],
            "weaknesses": ["冷面误伤人心"],
        },
    ]
    for c in chars:
        approve(w, [{"tool": "s3_add_character", "args": c}], f"add {c['name']}")
        patch = {k: c[k] for k in (
            "appearance", "personality_detail", "surface_goal", "deep_need", "fear",
            "importance", "backstory", "abilities", "weaknesses", "name",
        ) if k in c}
        patch["character_id"] = c["oid"]
        approve(w, [{"tool": "s3_patch_character", "args": patch}], f"patch {c['name']}")

    # relation 须符合 schema 词表；category 须为 magic/technology/social/physical/economic/political
    for src, dst, rel, note in (
        ("沈拾灯", "收灯师父", "师徒", "收灯一脉"),
        ("沈拾灯", "阿绣", "盟友", "共查灯债"),
        ("王阿禾", "沈拾灯", "恩人", "灯影招手"),
        ("阿绣", "王阿禾", "知己", "灯芯与兄名"),
    ):
        approve(w, [{
            "tool": "s3_add_character_relation",
            "args": {"src_oid": src, "dst_oid": dst, "relation": rel, "since_chapter": 1, "note": note},
        }], f"rel {src}-{dst}")

    for name, cat, note in (
        ("不渡夜魂", "social", "收灯人不得应夜魂「到」；违者折声或折命"),
        ("债契三夜", "social", "油膜债契展开后三夜内须应到，违约折声或折命"),
        ("灯芯写名", "magic", "灯芯上写的人名即债链节点，可被点亮索债"),
        ("替死顶名", "political", "付钱者「转」，顶死者「清」，纸钱与替字为证"),
    ):
        approve(w, [{
            "tool": "s3_add_world_rule",
            "args": {"name": name, "category": cat, "note": note, "established_chapter": 1},
        }], f"rule {name}")

    for i, (entity, attr, val) in enumerate([
        ("world:青石镇", "location", "多雨青石巷，有河灯市与王家寨旧渡口"),
        ("world:纸钱", "artifact", "湿透纸钱可辨墨迹与「替」字"),
        ("world:灯芯", "artifact", "河灯灯芯可写人名，点亮即索债"),
        ("world:伪契", "artifact", "高门代还清单与油膜债契"),
        ("world:暖黄灯", "symbol", "守债链的暖黄灯对立冷白索债灯"),
        ("role:沈拾灯", "knows", "师训不渡夜魂"),
        ("role:阿绣", "knows", "兄名曾在灯芯上"),
    ], start=1):
        approve(w, [{
            "tool": "s3_add_fact",
            "args": {
                "id": f"fact:v5-{i}",
                "entity": entity,
                "attribute": attr,
                "value": val,
                "valid_from": 1,
            },
        }], f"fact {i}")

    approve(w, [{
        "tool": "s3_add_faction",
        "args": {
            "name": "高门代还",
            "ideology": "用纸灯转债，活人替死人顶名",
            "status": "active",
            "public_face": "义仓与账房",
            "private_operation": "夜审点名收殓人与债名",
            "first_mention_chapter": 1,
        },
    }], "faction 高门")
    approve(w, [{
        "tool": "s3_add_faction",
        "args": {
            "name": "收灯一脉",
            "ideology": "守灯即守债链",
            "status": "active",
            "leader": "收灯师父",
            "public_face": "收殓行当",
            "first_mention_chapter": 1,
        },
    }], "faction 收灯")

    for name, cat, desc in (
        ("湿纸钱", "祭器", "棺中人衣襟湿透纸钱，可辨替字与姓"),
        ("河灯灯芯", "祭器", "可写人名的灯芯，点亮索债"),
        ("油膜债契", "契约", "三夜应到的油膜契文"),
    ):
        approve(w, [{
            "tool": "s3_add_item",
            "args": {"name": name, "category": cat, "description": desc, "first_chapter": 1},
        }], f"item {name}")

    for name, cat, defn in (
        ("到", "债语", "应债之声；灯下应到即入债链"),
        ("替", "债语", "替死顶名之字，桩与纸钱可见"),
        ("收灯", "行当", "守债链、收殓、削替字之业"),
    ):
        approve(w, [{
            "tool": "s3_add_term",
            "args": {"name": name, "category": cat, "definition": defn, "first_mention_chapter": 1},
        }], f"term {name}")

    for text, setup, tier in (
        ("合灯夜烧掉伪契并自背余债", 1, "book"),
        ("纸钱与替字揭露王阿禾顶死真相", 1, "arc"),
        ("灯芯上的沈姓与阿绣兄名被当众点破", 3, "arc"),
        ("收灯师父现身削替字并拒高门利诱", 8, "chapter"),
    ):
        approve(w, [{
            "tool": "s3_plant_promise",
            "args": {"text": text, "setup_chapter": setup, "tier": tier, "kind": "promise"},
        }], f"promise {text[:12]}")

    for i, (title, intro) in enumerate([
        ("卷一·纸灯初燃", "立世界与问不得"),
        ("卷二·债与影", "规则落地与双影"),
        ("卷三·收灯", "夜审与合灯收束"),
    ]):
        approve(w, [{
            "tool": "s3_add_volume",
            "args": {"title": title, "intro": intro, "sort_order": i},
        }], title)

    chapters = [
        (1, "第一章·雨巷纸灯", "沈拾灯",
         "沈拾灯初入青石镇，受雇收殓无名薄棺；棺中未腐尸与湿纸钱，镇民讳言问不得。压力在师训与必须问之间。"),
        (2, "第二章·湿棺与纸钱", "沈拾灯",
         "沈拾灯循湿纸钱至王家寨旧渡口，桩上「替」字；得知王阿禾顶死，纸钱现沈姓。"),
        (3, "第三章·白灯笼", "沈拾灯",
         "河面白灯笼，王阿禾影招手；沈拾灯违不渡夜魂应到，阿绣窗后目击。"),
        (4, "第四章·王家寨旧账", "沈拾灯",
         "沈拾灯与阿绣潜入账房，抄得高门代还清单：付钱者转、顶死者清；夜审将点名收殓人。"),
        (5, "第五章·河灯市", "沈拾灯",
         "河灯市上沈拾灯夺芯坠河，阿绣相救；灯芯女名与未写完的沈字，回纹布为证。"),
        (6, "第六章·双影", "阿绣",
         "阿绣水下拽断写有亡兄小名的灯芯；双影策略：水下之名与岸上之账将并举。限知：她不知他已应到。"),
        (7, "第七章·债契", "沈拾灯",
         "油膜债契全文展开：三夜应到，违约折声或折命；规则落地，下一声到留给自己。"),
        (8, "第八章·夜审", "沈拾灯",
         "夜审摊牌：举芯、擦兄名、写己名、纸钱自燃；伪契入火，余债落肩，收灯师父现身。"),
        (9, "第九章·收灯人", "沈拾灯",
         "收灯师父削替字、口传非法条款、拒高门利诱；沈拾灯护暖黄灯。"),
        (10, "第十章·合灯", "沈拾灯",
         "合灯夜焚伪契与名单，坑埋灰，立暖字牌；肩债仍在，灯第一次偏暖黄。"),
    ]
    for seq, title, pov, syn in chapters:
        approve(w, [{
            "tool": "s3_add_chapter",
            "args": {"title": title, "seq": seq},
        }], f"ch{seq}")
        # create_chapter may ignore seq — patch meta on actual max; re-list
        approve(w, [{
            "tool": "s3_patch_chapter_meta",
            "args": {
                "seq": seq,
                "title": title,
                "focalizer": f"role:{pov}",
                "synopsis": syn,
            },
        }], f"meta{seq}")

    # If create_chapter ignored seq, chapters may be 1..10 in order anyway after 10 creates
    code, chs = curl("GET", "/api/chapters", work=w)
    print("chapters", code, chs, flush=True)
    # re-patch all by list order if needed
    if isinstance(chs, list) and len(chs) >= 10:
        for i, (seq, title, pov, syn) in enumerate(chapters):
            real_seq = int(chs[i].get("seq") or seq)
            approve(w, [{
                "tool": "s3_patch_chapter_meta",
                "args": {
                    "seq": real_seq,
                    "title": title,
                    "focalizer": f"role:{pov}",
                    "synopsis": syn,
                },
            }], f"align{real_seq}")

    print("BIBLE_DONE", w, flush=True)
    print(w)


if __name__ == "__main__":
    main()
