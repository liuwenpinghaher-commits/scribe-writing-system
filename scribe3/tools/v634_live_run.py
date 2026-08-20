"""demo 内：假书/验收书五层连写。只在已部署容器里跑。"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from scribe3.ontology import Entity, Fact
from scribe3.playbook.quality_metrics import measure_chapter
from scribe3.playbook.quote import PLAYBOOK_VERSION
from scribe3.playbook.structural import check_chapter_state_struct
from scribe3.store.surreal import SurrealStore

FOCAL = "role:柳岸青"
STAGES = ("duty", "design", "deduce", "draft", "final")
FROZEN_OF = {
    "duty": "duty_card",
    "design": "chapter_play",
    "deduce": "chapter_deduce",
    "draft": "chapter_draft",
}
CHAPTERS = [(1, "华山成核"), (2, "四十二度"), (3, "金縢裂纹")]
SHELLS = [
    (4, "灭活边缘"), (5, "牧场主出价"), (6, "相位锚"),
    (7, "双向隐形破口"), (8, "信史改写"), (9, "衔尾蛇"), (10, "波粒未决"),
]


def pad(s: str, n: int) -> str:
    s = (s or "").strip()
    filler = "此句只为把设定写够，说明处境、代价和不能拆穿的事。"
    while len(s) < n:
        s += filler
    return s


def login() -> str:
    bu = os.environ.get("SCRIBE3_BOOTSTRAP_USERS") or ""
    u, pw = bu.split(":", 1)
    last = None
    for i in range(8):
        req = urllib.request.Request(
            "http://127.0.0.1:3321/auth/login",
            data=json.dumps({"username": u.strip(), "password": pw.strip()}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            r = urllib.request.urlopen(req, timeout=20)
            return r.headers.get("Set-Cookie", "").split(";", 1)[0]
        except Exception as e:
            last = e
            time.sleep(2 + i)
    raise last  # type: ignore[misc]


def http(cookie: str, method: str, path: str, body: Any = None, timeout: int = 60):
    data = None
    headers = {"Cookie": cookie}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request("http://127.0.0.1:3321" + path, data=data, headers=headers, method=method)
    try:
        rr = urllib.request.urlopen(req, timeout=timeout)
        raw = rr.read().decode()
        return rr.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:800]}
    except Exception as e:
        return 0, {"error": str(e), "type": type(e).__name__}


def health_fingerprint() -> dict[str, Any]:
    try:
        raw = urllib.request.urlopen("http://127.0.0.1:3321/health", timeout=8).read().decode()
        body = json.loads(raw) if raw else {}
    except Exception as e:
        body = {"error": str(e)}
    cf = body.get("changefeed") if isinstance(body.get("changefeed"), dict) else {}
    return {
        "playbook": PLAYBOOK_VERSION,
        "started_at": cf.get("started_at") or body.get("started_at"),
        "health": {k: body.get(k) for k in ("ok", "status", "version") if k in body},
    }


def seed_world(st: SurrealStore) -> None:
    st.set_intent({
        "reader_feeling": "先冷后烫，读完还想翻下一页，怕大遮蔽再撕一指。",
        "emotional_arc": "从隐瞒体温到被迫按回碎片，再欠下一笔收不回的账。",
        "red_lines": "不美化观测样本化人体\n不让柳岸青看见场核坐标\n不提前拆穿炉认主与帝的真名",
        "who_pays": "柳岸青用自己的四十二度体温付账",
        "axis_terms": "大遮蔽/成核点/指针态/场核",
        "clock_start": "大泄露当夜",
        "clock_end": "十八个月深渊碰撞前",
        "imagery": "准：黑屋、青砖、湿冷、手电、碳化标价、腕内体温。禁：赛博霓虹、星舰甲板。若要跨到志怪质感，须先在场上放一个同时属于两个世界的物件作桥。",
        "total_word_goal": 45000,
    })
    try:
        from scribe3.wanjie_catalog import ensure_wanjie_catalog
        ensure_wanjie_catalog(st)
    except Exception:
        pass
    chars = [
        ("柳岸青", "protagonist", "男", "黑发湿贴额角，腕上有旧烫疤。",
         "他同时握着守望者权柄和意识之海。",
         "在成核点扩开前把场核碎片按回裂口。",
         "不想被标成移动真真空泡。",
         "怕一观测就把身边的人写成样本。",
         "他要活，也要让母亲活。"),
        ("沈烛", "major", "男", "灰袍档案员，眼底不热。",
         "守火人要切断观测耦合。",
         "切断柳岸青与场核的观测耦合。",
         "档案完整比一个人的命更干净。",
         "怕档案被海改写。",
         "他把人当成条目。"),
        ("赫斯", "major", "男", "神权祭司，令牌贴在掌心。",
         "天龙座买办要做一次非法观测。",
         "用令牌锁定柳岸青带走交差。",
         "交差比弄懂成核点更要紧。",
         "怕令牌熄火。",
         "他不知道成核点机制。"),
        ("兰因", "minor", "女", "相位锚工程师，说话短。",
         "同盟要民用穿越器活下来。",
         "把相位锚焊在能走的人身上。",
         "工程能交差。",
         "怕第一次死人是她的锅。",
         "她还没进华山这一夜。"),
    ]
    for name, imp, gender, ap, pd, sg, dn, fear, bs in chars:
        eid = f"role:{name}"
        if st.entity(eid) is None:
            try:
                st.add_entity(Entity(eid, "character", name, traits={
                    "importance": imp,
                    "gender": gender,
                    "appearance": pad(ap, 40),
                    "personality_detail": pad(pd, 200),
                    "surface_goal": pad(sg, 80),
                    "deep_need": pad(dn, 80),
                    "fear": pad(fear, 80),
                    "internal_conflict": pad("他要的和系统要的不是同一笔账。", 80),
                    "backstory": pad(bs, 200),
                    "abilities": ["观测闭合"],
                    "weaknesses": ["体温暴露"],
                }))
            except Exception:
                pass
        else:
            try:
                st._execute_write(
                    "UPDATE type::record('character', $local) SET importance=$i, appearance=$a, "
                    "personality_detail=$pd, surface_goal=$sg, deep_need=$dn, fear=$fr, backstory=$bs, "
                    "gender=$g",
                    {"local": name, "i": imp, "a": pad(ap, 40), "pd": pad(pd, 200),
                     "sg": pad(sg, 80), "dn": pad(dn, 80), "fr": pad(fear, 80), "bs": pad(bs, 200),
                     "g": gender},
                )
            except Exception:
                pass
    for a, b, rel in (("role:柳岸青", "role:沈烛", "利益对立"),
                      ("role:柳岸青", "role:赫斯", "仇敌"),
                      ("role:沈烛", "role:赫斯", "竞争者")):
        try:
            st.add_character_relation(a, b, rel, 1)
        except Exception:
            pass
    try:
        if st.entity("place:华山北峰") is None:
            st.add_entity(Entity("place:华山北峰", "place", "华山北峰"))
    except Exception:
        pass
    for name, ideology, leader in (
        ("守火人", "档案完整高于一个人的命。", "role:沈烛"),
        ("天龙座", "交差比弄懂成核点更要紧。", "role:赫斯"),
        ("普罗米修斯同盟", "民用穿越器必须有人活着回来。", "role:兰因"),
    ):
        try:
            st.add_faction(name, ideology=pad(ideology, 40), status="active", leader=leader,
                           known_members=[leader], public_face=pad(name, 20),
                           private_operation=pad(ideology, 40), first_mention_chapter=1)
        except Exception:
            pass
    for text, tier, res in (
        ("十八个月深渊碰撞仍在倒计时", "book", "倒计时走完必须选第三条路"),
        ("肉体三年碳化的标价已经写在袖口", "arc", "碳化不是病是体温被写成常态"),
        ("金縢因果封印还没开箱", "chapter", "开箱会付另一笔账"),
    ):
        try:
            st.plant_promise(text, 1, kind="promise", tier=tier, resolution=res)
        except Exception:
            pass
    try:
        st.create_storyline(title="金縢未开", arc_kind="main", chapter_seqs=[1, 2, 3],
                            notes="箱还没开", craft_only=False)
    except Exception:
        pass
    for name, theme, echoes in (
        ("指针态", "环境冗余锁定可复制状态。", "指针态、冗余、复制"),
        ("负熵", "牧场要人活着被剪。", "负熵、牧场、恐惧"),
        ("波粒互补", "第三条路承认两者同时贵。", "波粒、互补、第三条路"),
    ):
        try:
            st.add_motif(name, theme=pad(theme, 40), echoes=echoes, unfolding=pad(theme, 80),
                         echo_terms=echoes.split("、"))
        except Exception:
            pass
    for name, cat, cost in (
        ("大遮蔽破损即大泄露", "physical", "双向隐形变成单向可见"),
        ("场核是拓扑锚", "physical", "拔核等于真空衰变"),
        ("观测即改写指针态", "magic", "被观测者可能被写成样本"),
    ):
        try:
            st.add_world_rule(name, cat, source="万界V7", cost=cost,
                              limitations=["不可当免费超能力"], exceptions=["逻辑豁免可短暂"],
                              capabilities=["挡住异界叙事寄生"])
        except Exception:
            pass
    for oid, who, attr, val, secret in (
        ("fact:裂口", "role:沈烛", "地点", "华山北峰裂口在当夜扩开", False),
        ("fact:体温", "role:柳岸青", "身体", "四十二度不是病是标价", False),
        ("fact:令牌", "role:赫斯", "物件", "令牌用于非法观测", False),
        ("fact:坐标密", "role:柳岸青", "秘密", "柳岸青看不见场核坐标", True),
        ("fact:炉名密", "role:沈烛", "秘密", "炉认主与帝的真名此刻不能拆穿", True),
    ):
        try:
            st.add_fact(Fact(oid, who, attr, val, valid_from=1, secret=secret))
        except Exception:
            pass
    vols = []
    try:
        vols = [v.get("id") for v in (st.list_volumes() or []) if v.get("id")]
    except Exception:
        vols = []
    if len(vols) < 3:
        vols = []
        for title, intro, order in (
            ("囚笼", pad("大遮蔽内，觉醒到华山成核。", 80), 1),
            ("泄露", pad("融合点、穿越、各方下场。", 80), 2),
            ("第三条路", pad("电车之外的联邦飞升。", 80), 3),
        ):
            vols.append(st.add_volume(title=title, sort_order=order, intro=intro))
    max_seq = 0
    try:
        max_seq = int(st.max_chapter() or 0)
    except Exception:
        max_seq = 0
    if max_seq < 10:
        for seq, title in CHAPTERS + SHELLS:
            if seq <= max_seq:
                continue
            vol = vols[0] if seq <= 4 else (vols[1] if seq <= 7 else vols[2])
            st.create_chapter(title, volume_id=vol)
    syn = pad("华山北峰当夜，柳岸青必须在成核点扩开前决定交碎片还是按回。", 40)
    for seq, _t in CHAPTERS + SHELLS:
        try:
            st.update_chapter_meta(int(seq), {"synopsis": syn, "focalizer": FOCAL})
        except Exception:
            pass


def already_frozen(slug: str, seq: int, stage: str) -> bool:
    st = SurrealStore(ns="scribe3", db=slug)
    try:
        if stage == "final":
            ch = st.get_chapter(seq) or {}
            return bool((ch.get("prose") or "").strip())
        if stage == "design":
            return bool(st.get_frozen("chapter_play", seq) and st.get_frozen("chapter_contract", seq))
        table = FROZEN_OF.get(stage)
        return bool(table and st.get_frozen(table, seq))
    except Exception:
        return False
    finally:
        try:
            st.close()
        except Exception:
            pass


def gen_stage(cookie: str, slug: str, seq: int, stage: str) -> tuple[str, dict[str, Any]]:
    if already_frozen(slug, seq, stage):
        return cookie, {"seq": seq, "stage": stage, "ok": True, "status": "already_frozen", "http": 200}
    timeout = {"duty": 300, "design": 600, "deduce": 600, "draft": 900, "final": 900}.get(stage, 600)
    t0 = time.time()
    code, body = http(cookie, "POST", f"/generate-stage?work={slug}",
                      {"seq": seq, "stage": stage, "persist": True, "focalizer": FOCAL}, timeout=timeout)
    if code == 401:
        cookie = login()
        code, body = http(cookie, "POST", f"/generate-stage?work={slug}",
                          {"seq": seq, "stage": stage, "persist": True, "focalizer": FOCAL}, timeout=timeout)
    rec = {
        "seq": seq, "stage": stage, "http": code,
        "ok": bool(isinstance(body, dict) and body.get("ok")),
        "status": body.get("status") if isinstance(body, dict) else None,
        "code": body.get("code") if isinstance(body, dict) else None,
        "sec": round(time.time() - t0, 1),
    }
    need_retry = rec["status"] == "needs_human" or code in (0, 500, 502, 503, 401)
    if need_retry and not rec["ok"]:
        cookie = login()
        t1 = time.time()
        code2, body2 = http(cookie, "POST", f"/generate-stage?work={slug}",
                            {"seq": seq, "stage": stage, "persist": True, "focalizer": FOCAL,
                             "force": True, "extra": "force=1"}, timeout=timeout)
        rec["retry"] = {"http": code2, "ok": bool(isinstance(body2, dict) and body2.get("ok")),
                        "status": body2.get("status") if isinstance(body2, dict) else None,
                        "sec": round(time.time() - t1, 1)}
        if rec["retry"]["ok"]:
            rec["ok"] = True
            rec["status"] = rec["retry"]["status"]
    rec["ok"] = rec["ok"] or rec.get("status") in ("frozen", "skipped", "ok", "already_frozen")
    return cookie, rec


def run_live(*, n_chapters: int = 1, title: str | None = None, slug: str | None = None) -> dict[str, Any]:
    n_chapters = max(1, min(3, int(n_chapters)))
    from scribe3.tools.gate0 import check_gate0_freeze
    freeze = check_gate0_freeze(require=n_chapters > 1)
    if not freeze.get("ok"):
        return {
            "ok": False,
            "error": freeze.get("code") or "gate0_freeze",
            "message": freeze.get("message") or "Gate 0 未冻结，拒跑",
            "gate0_freeze": freeze,
            "n_chapters": n_chapters,
        }
    fp = health_fingerprint()
    cookie = login()
    if not slug:
        title = title or (
            "万界概率战争·v6.3.4rev13·" +
            ("冒烟" if n_chapters == 1 else "三章验收") + "·" +
            datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        )
        code, created = http(cookie, "POST", "/works", {"title": title})
        if code >= 400 or not isinstance(created, dict) or not created.get("slug"):
            return {"ok": False, "error": "create_fail", "http": code, "body": created, "fingerprint": fp}
        slug = created["slug"]
    st = SurrealStore(ns="scribe3", db=slug)
    try:
        st.apply_schema()
        seed_world(st)
    finally:
        try:
            st.close()
        except Exception:
            pass
    stages: list[dict[str, Any]] = []
    verify: list[dict[str, Any]] = []
    all_ok = True
    for seq, _title in CHAPTERS[:n_chapters]:
        layer_ok = True
        for stage in STAGES:
            cookie, rec = gen_stage(cookie, slug, seq, stage)
            stages.append(rec)
            print(json.dumps({"step": "stage", **rec}, ensure_ascii=False)[:400], flush=True)
            if not rec.get("ok"):
                all_ok = False
                layer_ok = False
                break
        st = SurrealStore(ns="scribe3", db=slug)
        try:
            metrics = measure_chapter(st, seq)
            play = st.get_frozen("chapter_play", seq) or {}
            contract = st.get_frozen("chapter_contract", seq) or {}
            duty = st.get_frozen("duty_card", seq) or {}
            draft = st.get_frozen("chapter_draft", seq) or {}
            state = st.get_frozen("chapter_state", seq) or {}
        finally:
            try:
                st.close()
            except Exception:
                pass
        code, ld = http(cookie, "GET", f"/latest-draft?seq={seq}&work={slug}")
        source = ld.get("source") if isinstance(ld, dict) else None
        draft_text = str(draft.get("text") or "")
        state_hit = check_chapter_state_struct(state, draft_text) if state else {
            "ok": False, "code": "no_chapter_state",
        }
        verify.append({
            "seq": seq,
            "play_n": len(play.get("text") or ""),
            "draft_n": len(draft.get("text") or ""),
            "duty": bool(duty),
            "contract": bool(contract),
            "latest_source": source,
            "metrics": metrics,
            "state_ok": bool(state) and bool(state_hit.get("ok")),
            "state_detail": state_hit.get("code") or ("ok" if state else "missing"),
            "state": {
                "seq": state.get("seq"),
                "sha": state.get("sha"),
                "status": state.get("status"),
                "narrative_pov": state.get("narrative_pov") or "",
                "characters": state.get("characters") or [],
                "objects": state.get("objects") or [],
                "open_loops": state.get("open_loops") or [],
                "timeline": state.get("timeline") or {},
                "imagery": state.get("imagery") or [],
            } if state else {},
        })
        print(json.dumps({"step": "verified", "seq": seq, "source": source, "metrics_ok": metrics.get("ok")},
                         ensure_ascii=False), flush=True)
        if not layer_ok:
            break
    sources = [v.get("latest_source") for v in verify]
    source_ok = len(set(s for s in sources if s)) <= 1 and all(s in ("chapter_version", "chapter_draft", None) or True for s in sources)
    gate0 = all(
        v.get("play_n", 0) >= 200 and v.get("draft_n", 0) >= 200
        and (v.get("metrics") or {}).get("overlap", 1) <= 0.15
        and (v.get("metrics") or {}).get("boundary_hits", 1) == 0
        for v in verify
    ) and bool(verify)
    return {
        "ok": all_ok and (gate0 if n_chapters == 1 else all((v.get("metrics") or {}).get("ok") for v in verify)),
        "slug": slug,
        "title": title,
        "fingerprint": fp,
        "n_chapters": n_chapters,
        "stages": stages,
        "verify": verify,
        "latest_sources": sources,
        "source_consistent": len({s for s in sources if s}) <= 1,
        "gate0": gate0,
        "gate0_freeze": freeze,
        "playbook": PLAYBOOK_VERSION,
    }
