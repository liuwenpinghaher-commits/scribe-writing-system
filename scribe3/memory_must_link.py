"""记忆质量 D3/D5：本章戏剧必需锚（must-link）与作者复述检测。

目标（质量向，不是通/绿）：
  · 组装时 **先锁** 与本章 synopsis / 开放伏笔 / 当章有效事实相关的正典，
    再填相似检索——避免预算把关键物件挤掉。
  · 检测作者消息是否 **粘贴大量设定锚**（验收时刷跨章记忆分 → 记分作废）。

纯逻辑可单测；store 鸭子类型：get_chapter / open_promises / facts_at / characters。
"""
from __future__ import annotations

from scribe3.feature_flags import get_flag
import os
import re
from typing import Any


def steer_mode() -> str:
    """minimal（产品默认 · rev.4）| full（作者粘贴设定模式）。"""
    try:
        from scribe3.settings import get_setting
        v = str(get_setting("SCRIBE3_MEMORY_STEER_MODE") or "").strip().lower()
        if v:
            return v
    except Exception:
        pass
    return (get_flag("SCRIBE3_MEMORY_STEER_MODE") or "minimal").strip().lower()


def is_minimal_steer() -> bool:
    return steer_mode() in {"minimal", "min", "ablation", "1", "true", "yes"}


def _setting_str(key: str, default: str = "") -> str:
    """优先热设置（demo PUT /api/settings），回落 env / 默认。"""
    try:
        from scribe3.settings import get_setting
        v = get_setting(key)
        if v is None:
            return default
        return str(v).strip()
    except Exception:
        return (os.environ.get(key) or default).strip()


def ablation_mode() -> str:
    """轨 2 消融：测量「记忆贡献」时关闭注入面（fabric 可仍开）。

    设置/环境 SCRIBE3_MEMORY_ABLATION（热切换）：
      · none / 空：正常产品（默认）
      · no_must：禁用 must-link 钉锚
      · no_must_facts：禁用 must-link + 正典 fact 类注入（轨 2 B 组）
    """
    raw = _setting_str("SCRIBE3_MEMORY_ABLATION", "none").lower()
    if raw in {"", "0", "false", "off", "no", "none", "normal"}:
        return "none"
    if raw in {"no_must", "must_off", "1"}:
        return "no_must"
    if raw in {"no_must_facts", "no_facts", "track2_b", "memory_contrib_b", "2"}:
        return "no_must_facts"
    return raw


def ablation_disables_must_link() -> bool:
    return ablation_mode() in {"no_must", "no_must_facts"}


def ablation_disables_fact_injection() -> bool:
    return ablation_mode() == "no_must_facts"


def must_link_limit(default: int = 10) -> int:
    """Canon 压力锚数量上限（防 50+ 源稀释；Wave-B / v4 S2.4）。"""
    try:
        from scribe3.settings import get_setting
        n = int(get_setting("SCRIBE3_MUST_LINK_LIMIT"))
    except Exception:
        try:
            n = int(get_flag("SCRIBE3_MUST_LINK_LIMIT") or default)
        except (TypeError, ValueError):
            n = default
    return max(3, min(n, 24))


def _cn_len(s: str) -> int:
    return len(re.sub(r"\s+", "", s or ""))


def _entity_short_name(eid: str) -> str:
    e = (eid or "").strip()
    if ":" in e:
        return e.split(":", 1)[-1]
    return e or "未知"


def format_fact_as_drama(eid: str, attr: str, val: str) -> str:
    """Wave-B：事实锚叙事化——推动情节/感官，避免 entity·attr=value 清单腔。"""
    name = _entity_short_name(eid)
    v = (val or "").strip()[:48]
    a = (attr or "").strip()
    if a in ("state", "condition", "status", "外观状态", "状态") or any(
        k in v for k in ("缺口", "残缺", "完整", "损坏", "未冷", "冷死")
    ):
        return f"物件「{name}」当前状态：{v}——须在情节中可感，勿当设定点名"
    if a in ("rule_text", "rule") or "铁律" in a or "rule" in a.lower():
        return f"场上铁律压着：{v}"
    if a in ("artifact", "description", "外观", "描述"):
        return f"与「{name}」相关的可感细节：{v}——写成触感/压力，禁止罗列"
    return f"既定事实·「{name}」：{v}（推动情节，禁止清单腔）"


def format_promise_as_drama(setup: int, txt: str) -> str:
    t = (txt or "").strip()[:48]
    return f"未了戏剧债（第{setup}章埋下）：{t}——本章须回响或加压"


def format_character_as_drama(name: str, *, role_hint: str = "") -> str:
    n = (name or "").strip()
    if role_hint == "protagonist":
        return f"焦点人物：{n}——动机与关系由记忆推演，勿名单点卯"
    return f"在场压力人物：{n}——关系由记忆推演，勿名单点卯"


def _chapter_blob(store, chapter: int | None) -> str:
    if not chapter or not hasattr(store, "get_chapter"):
        return ""
    ch = store.get_chapter(int(chapter)) or {}
    if not isinstance(ch, dict):
        return ""
    parts = [
        ch.get("synopsis") or "",
        ch.get("title") or "",
        ch.get("scene_truth") or "",
    ]
    beats = ch.get("beats") or []
    for b in beats:
        if isinstance(b, dict):
            parts.append(b.get("text") or "")
        else:
            parts.append(str(b))
    return "\n".join(parts)


def collect_must_anchors(
    store,
    chapter: int | None,
    *,
    limit: int = 12,
    query: str = "",
    stats_out: dict | None = None,
) -> list[dict[str, Any]]:
    """从本章大纲 + 开放伏笔 + 当章事实中抽取 must-link 锚点。

    chapter 为空（讨论态）：仍用开放伏笔 + 主角 + query 重叠事实 + 物件 condition 类，
    避免 must-link 整块空。

    返回 [{source_id, text, kind, score}]，score 越高越该优先入预算。
    stats_out 可选写入 conflicts_dropped（注入面互斥裁掉条数）。
    """
    blob = _chapter_blob(store, chapter)
    q = (query or "").strip()
    if q:
        blob = (blob + "\n" + q).strip()
    no_chapter = not chapter
    anchors: list[dict[str, Any]] = []
    seen: set[str] = set()
    conflicts_dropped = 0

    def _add(source_id: str, text: str, kind: str, score: float, **extra):
        t = (text or "").strip()
        if not t or t in seen:
            return
        seen.add(t)
        row = {
            "source_id": source_id,
            "text": t[:160],
            "kind": kind,
            "score": score,
        }
        row.update(extra)
        anchors.append(row)

    # 1) 开放伏笔（戏剧压力；跨章回指强化：setup 越早且仍开放，本章越该加压）
    try:
        for p in (store.open_promises() or [])[:8]:
            if not isinstance(p, dict):
                continue
            setup = int(p.get("setup_chapter") or 0)
            txt = (p.get("text") or "").strip()
            if not txt:
                continue
            if chapter and setup and setup <= int(chapter):
                score = 3.0
                # Wave-B3：埋得更早的开放债，跨章回指权重更高
                age = int(chapter) - setup
                if age >= 1:
                    score += min(1.5, 0.4 * age)
            elif no_chapter:
                score = 2.5  # 讨论态：伏笔仍是全书戏剧压力
            else:
                score = 1.5
            # query 命中伏笔文本再抬
            if q and any(tok in txt for tok in re.findall(r"[\u4e00-\u9fff]{2,8}", q)[:6]):
                score += 1.0
            pid = str(p.get("id") or f"promise:{setup}")
            _add(pid, format_promise_as_drama(setup, txt), "promise", score)
    except Exception:
        pass

    # 2) 当章有效事实：投影单真后再叙事化；与 synopsis 重叠优先
    try:
        ch_n = int(chapter) if chapter else 99999
        facts = list(store.facts_at(ch_n) if hasattr(store, "facts_at") else [])
        # 再跑注入消解（FakeStore / 旧路径可能未折叠）；统计 conflicts_dropped
        try:
            from scribe3.fact_surface import resolve_injection_facts_with_stats
            facts, conflicts_dropped = resolve_injection_facts_with_stats(facts)
        except Exception:
            pass
        for f in facts or []:
            eid = getattr(f, "entity_id", None) or (
                f.get("entity_id") if isinstance(f, dict) else "") or ""
            attr = getattr(f, "attribute", None) or (
                f.get("attribute") if isinstance(f, dict) else "") or ""
            val = getattr(f, "value", None) or (
                f.get("value") if isinstance(f, dict) else "") or ""
            fid = getattr(f, "id", None) or (
                f.get("id") if isinstance(f, dict) else "") or f"fact:{eid}:{attr}"
            vf = getattr(f, "valid_from", None)
            if vf is None and isinstance(f, dict):
                vf = f.get("valid_from")
            try:
                vf_i = int(vf) if vf is not None else 0
            except (TypeError, ValueError):
                vf_i = 0
            line = f"{eid} {attr} {val}".strip()
            if not line:
                continue
            score = 1.0
            name_hint = _entity_short_name(str(eid))
            if name_hint and name_hint in blob:
                score += 2.5
            if val and len(val) >= 2 and val[:8] in blob:
                score += 1.5
            if attr in ("condition", "state", "artifact", "status"):
                if name_hint in blob or no_chapter:
                    score += 1.2 if no_chapter else 1.0
                # Wave-B3：上章已成立的物件态，跨章必须回指
                if chapter and vf_i and vf_i < int(chapter) and name_hint in blob:
                    score += 1.2
            drama = format_fact_as_drama(str(eid), str(attr), str(val))
            raw_key = f"{eid}·{attr}={str(val)[:60]}"
            if score >= 2.0 or (no_chapter and score >= 2.0):
                _add(str(fid), drama, "fact", score, raw_key=raw_key)
            elif no_chapter and attr in ("condition", "artifact", "state") and score >= 1.5:
                _add(str(fid), drama, "fact", score, raw_key=raw_key)
    except Exception:
        pass

    # 3) 角色：有章看大纲；无章钉主角；仅 protagonist/major 高分（降噪声）
    try:
        for c in (store.characters() or [])[:20]:
            name = getattr(c, "name", None) or (c.get("name") if isinstance(c, dict) else "")
            cid = getattr(c, "id", None) or (c.get("id") if isinstance(c, dict) else name)
            imp = getattr(c, "importance", None) or (
                c.get("importance") if isinstance(c, dict) else "")
            imp_s = str(imp or "")
            if name and name in blob:
                sc = 2.0 if imp_s in ("protagonist", "major", "") else 1.2
                _add(str(cid), format_character_as_drama(name, role_hint=imp_s),
                     "character", sc)
            elif no_chapter and imp_s == "protagonist" and name:
                _add(str(cid), format_character_as_drama(name, role_hint="protagonist"),
                     "character", 2.2)
            elif no_chapter and name and q and name in q:
                if imp_s in ("protagonist", "major", ""):
                    _add(str(cid), format_character_as_drama(name), "character", 2.0)
    except Exception:
        pass

    anchors.sort(key=lambda a: -float(a.get("score") or 0))
    before = len(anchors)
    anchors = _drop_conflicting_fact_anchors(anchors)
    conflicts_dropped += max(0, before - len(anchors))
    if stats_out is not None:
        stats_out["conflicts_dropped"] = int(conflicts_dropped)
    return anchors[:limit]


def _parse_entity_value_key(raw: str) -> tuple[str, str]:
    """从 raw_key 或旧清单行解析 (entity, value)。失败则 ("", 原文)。"""
    t = (raw or "").strip()
    if "·" in t and "=" in t:
        left, val = t.split("=", 1)
        eid = left.split("·", 1)[0].strip()
        return eid, val.strip()
    return "", t


def _drop_conflicting_fact_anchors(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """同 entity 的 fact 锚若 value 互斥，只留 score 更高者（D4 注入面）。"""
    try:
        from scribe3.fact_surface import values_mutually_exclusive
    except Exception:
        return anchors
    fact_idxs = [i for i, a in enumerate(anchors) if a.get("kind") == "fact"]
    if len(fact_idxs) < 2:
        return anchors
    drop: set[int] = set()
    for ii, i in enumerate(fact_idxs):
        if i in drop:
            continue
        ti = str(anchors[i].get("text") or "")
        rk = str(anchors[i].get("raw_key") or "")
        ei, vi = _parse_entity_value_key(rk or ti)
        for j in fact_idxs[ii + 1:]:
            if j in drop:
                continue
            tj = str(anchors[j].get("text") or "")
            rkj = str(anchors[j].get("raw_key") or "")
            ej, vj = _parse_entity_value_key(rkj or tj)
            exclusive = (
                values_mutually_exclusive(vi, vj)
                or values_mutually_exclusive(ti, tj)
            )
            if not exclusive:
                continue
            # 能解析 entity 时要求同 entity；叙事句仅靠互斥短语
            if ei and ej and ei != ej:
                continue
            si = float(anchors[i].get("score") or 0)
            sj = float(anchors[j].get("score") or 0)
            if sj > si:
                drop.add(i)
            else:
                drop.add(j)
    if not drop:
        return anchors
    return [a for i, a in enumerate(anchors) if i not in drop]

def format_must_link_items(anchors: list[dict[str, Any]], work: str = "") -> list[tuple[str, dict]]:
    """产出 (text, meta) 列表，供 assembler 插入 canonical 头部。"""
    if not anchors:
        return []
    lines = []
    header = (
        "- 【戏剧压力·记忆优先｜写成可感冲突与触感，禁止设定表点名】"
    )
    lines.append((header, {
        "source_id": "must_link:header",
        "kind": "must_link",
        "work": work,
    }))
    for a in anchors:
        lines.append((
            f"- 〔压力〕{a.get('text')}",
            {
                "source_id": str(a.get("source_id") or "must_link"),
                "kind": "must_link",
                "work": work,
                "score": a.get("score"),
            },
        ))
    return lines


def inject_dedup_enabled() -> bool:
    """SCRIBE3_INJECT_DEDUP：1/true/空默认开；0/false 恢复 brief 与 envelope 双全文。"""
    raw = _setting_str("SCRIBE3_INJECT_DEDUP", "1").lower()
    if raw in {"0", "false", "off", "no", "dual", "legacy"}:
        return False
    return True


def is_must_link_pin_source(source: Any) -> bool:
    """现网 pin 真值：source_kind=canonical + reason=must_link_priority（或 source_id 前缀）。

    **禁止** 仅用 ``source_kind == "must_link"`` —— pin 从不写该 kind（恒假 → 双全文）。
    """
    if source is None:
        return False
    reason = ""
    sid = ""
    sk = ""
    if isinstance(source, dict):
        reason = str(source.get("reason") or "")
        sid = str(source.get("source_id") or "")
        sk = str(source.get("source_kind") or "")
    else:
        reason = str(getattr(source, "reason", None) or "")
        sid = str(getattr(source, "source_id", None) or "")
        sk = str(getattr(source, "source_kind", None) or "")
    if reason == "must_link_priority":
        return True
    if sid.startswith("must_link"):
        return True
    # 故意：不把 sk == "must_link" 当作充分条件
    _ = sk
    return False


def must_link_already_pinned_from_items(items: Any) -> bool:
    """从 envelope / canonical 列表检测是否已 pin must-link 全文。"""
    if not items:
        return False
    for it in items:
        src = None
        if isinstance(it, dict):
            src = it.get("source") or it
        else:
            src = getattr(it, "source", None) or it
        if is_must_link_pin_source(src):
            return True
    return False


def build_must_prefix(
    store,
    chapter: int | None,
    *,
    limit: int | None = None,
    query: str = "",
    focalizer: str = "",
    must_link_already_pinned: bool = False,
) -> str:
    """写路径 brief 用：与 assembler must 同源（format + limit + ablation）。

    ``must_link_already_pinned=True`` 且 ``inject_dedup_enabled()`` 时返回空串
    （权威全文已在 envelope pin，brief 短路防双份）。
    DEDUP=0 时忽略 pinned 标志，恢复双前缀兼容路径。
    """
    if must_link_already_pinned and inject_dedup_enabled():
        return ""
    if ablation_disables_must_link():
        return ""
    lim = limit if limit is not None else must_link_limit(8)
    anchors = collect_must_anchors(store, chapter, limit=lim, query=query)
    if not anchors:
        return ""
    # 限知：帧外 secret 源不进压力前缀
    if focalizer and chapter is not None:
        try:
            from scribe3.epistemic_guard import (
                collect_secret_surface_strings, frame_known_fact_ids,
            )
            known = frame_known_fact_ids(store, focalizer, int(chapter))
            off: list[str] = []
            for row in collect_secret_surface_strings(store, int(chapter)):
                fid = row.get("fact_id") or ""
                if fid and fid in known:
                    continue
                for s in row.get("strings") or []:
                    if s and len(s) >= 2:
                        off.append(s)
            if off:
                anchors = [
                    a for a in anchors
                    if not any(s in str(a.get("text") or "") for s in off)
                ]
        except Exception:
            pass
    if not anchors:
        return ""
    lines = "\n".join(f"- 〔压力〕{a.get('text')}" for a in anchors)
    return (
        "\n\n【戏剧压力·来自记忆/正典｜写成可感冲突与触感，禁止设定表点名】\n"
        + lines + "\n"
    )

def _normalize_ws(text: str) -> str:
    """去空白+小写，供 must/canonical 子串与指纹对齐。"""
    return re.sub(r"\s+", "", (text or "").lower())


def pin_must_first(canonical_texts: list[str], must_lines: list[str]) -> list[str]:
    """把 must 行置顶，并去掉与 must 正文高度重复的后续行（省预算）。

    O10：``SCRIBE3_INJECT_DEDUP`` 默认走内容指纹（``inject_dedup``）；
    子串/嵌入匹配一律在**空白归一化**后比较，使
    ``角色张三  拔刀。`` 能压掉 ``角色张三拔刀。后文``。
    """
    if not must_lines:
        return list(canonical_texts or [])
    use_fp = False
    content_fingerprint = None
    try:
        from scribe3.inject_dedup import content_fingerprint as _cfp, inject_dedup_fingerprint_enabled
        use_fp = inject_dedup_fingerprint_enabled()
        content_fingerprint = _cfp
    except Exception:
        use_fp = False
    # 归一化核心（全串）+ 短前缀（legacy 40 字归一化）
    must_cores_norm: list[str] = []
    must_fps: set[str] = set()
    for m in must_lines:
        # 去掉前缀标记后的核心串（兼容〔必需〕/〔压力〕）
        core = re.sub(r"^[-•\s〕〔]*(?:必需|压力)*[〕]*", "", m)
        if len(core.strip()) < 6:
            continue
        core_n = _normalize_ws(core)
        if len(core_n) >= 4:
            must_cores_norm.append(core_n)
        if use_fp and content_fingerprint is not None:
            must_fps.add(content_fingerprint(core))
    out = list(must_lines)
    for t in canonical_texts or []:
        t_raw = t or ""
        t_n = _normalize_ws(t_raw)
        skip = False
        if use_fp and must_fps and content_fingerprint is not None:
            if content_fingerprint(t_raw) in must_fps:
                skip = True
        if not skip:
            # 归一化嵌入：must 核心是 canonical 的前缀/子串
            for core_n in must_cores_norm:
                if core_n and core_n in t_n:
                    skip = True
                    break
        if not skip:
            out.append(t)
    return out

def detect_author_restated_canon(
    user_message: str,
    anchors: list[dict[str, Any]],
    *,
    threshold: float = 0.8,
) -> dict[str, Any]:
    """若作者消息覆盖 ≥ threshold 比例的 must 锚，视为粘贴圣经刷分。

    返回 {
      restated: bool,
      ratio: float,
      hit: [anchor texts],
      miss: [...],
    }
    """
    msg = user_message or ""
    if not anchors or _cn_len(msg) < 20:
        return {"restated": False, "ratio": 0.0, "hit": [], "miss": [],
                "reason": "too_few_anchors_or_short_msg"}
    hit, miss = [], []
    for a in anchors:
        t = (a.get("text") or "")
        # 用锚点中较长的专名片段
        tokens = re.findall(r"[\u4e00-\u9fff]{2,12}", t)
        tokens = [x for x in tokens if x not in (
            "开放伏笔", "出场", "相关角色", "本章", "必需",
        )]
        ok = False
        for tok in tokens[:4]:
            if tok and tok in msg:
                ok = True
                break
        # 也比 value 片段
        if not ok and "·" in t:
            val = t.split("·", 1)[-1][:12]
            if len(val) >= 2 and val in msg:
                ok = True
        (hit if ok else miss).append(t)
    ratio = len(hit) / max(len(anchors), 1)
    return {
        "restated": ratio >= threshold and len(hit) >= 3,
        "ratio": round(ratio, 3),
        "hit": hit,
        "miss": miss,
        "threshold": threshold,
    }


def minimal_chapter_steer(
    seq: int,
    title: str,
    pov: str,
    conflict_one_liner: str,
    *,
    min_chars: int = 3800,
) -> str:
    """质量验收用极简 steer：只给冲突与 POV，不塞完整设定圣经。"""
    return (
        f"第{seq}章《{title}》。POV={pov}。"
        f"核心冲突（一句）:{conflict_one_liner[:120]}。"
        f"可见汉字≥{min_chars}。"
        "【记忆验收·极简指令】禁止在指令中复述全书设定；"
        "人物关系、物件状态、规则与未了债须依赖系统记忆/正典注入；"
        "作者未粘贴的设定不得当作「本消息新提供的事实」编造。"
        "写文学正文，非设定清单。"
    )
