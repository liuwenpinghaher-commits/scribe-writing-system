"""记忆质量 D3/D5：本章戏剧必需锚（must-link）与作者复述检测。

目标（质量向，不是通/绿）：
  · 组装时 **先锁** 与本章 synopsis / 开放伏笔 / 当章有效事实相关的正典，
    再填相似检索——避免预算把关键物件挤掉。
  · 检测作者消息是否 **粘贴大量设定锚**（验收时刷跨章记忆分 → 记分作废）。

纯逻辑可单测；store 鸭子类型：get_chapter / open_promises / facts_at / characters。
"""
from __future__ import annotations

import os
import re
from typing import Any


def steer_mode() -> str:
    """full（默认）| minimal（质量验收：极简指令，禁止靠 steer 灌设定）。"""
    return (os.environ.get("SCRIBE3_MEMORY_STEER_MODE") or "full").strip().lower()


def is_minimal_steer() -> bool:
    return steer_mode() in {"minimal", "min", "ablation", "1", "true", "yes"}


def _cn_len(s: str) -> int:
    return len(re.sub(r"\s+", "", s or ""))


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
) -> list[dict[str, Any]]:
    """从本章大纲 + 开放伏笔 + 当章事实中抽取 must-link 锚点。

    chapter 为空（讨论态）：仍用开放伏笔 + 主角 + query 重叠事实 + 物件 condition 类，
    避免 must-link 整块空。

    返回 [{source_id, text, kind, score}]，score 越高越该优先入预算。
    """
    blob = _chapter_blob(store, chapter)
    q = (query or "").strip()
    if q:
        blob = (blob + "\n" + q).strip()
    no_chapter = not chapter
    anchors: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(source_id: str, text: str, kind: str, score: float):
        t = (text or "").strip()
        if not t or t in seen:
            return
        seen.add(t)
        anchors.append({
            "source_id": source_id,
            "text": t[:160],
            "kind": kind,
            "score": score,
        })

    # 1) 开放伏笔（戏剧压力；无章时仍全收，讨论态也有可钉锚）
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
            elif no_chapter:
                score = 2.5  # 讨论态：伏笔仍是全书戏剧压力
            else:
                score = 1.5
            # query 命中伏笔文本再抬
            if q and any(tok in txt for tok in re.findall(r"[\u4e00-\u9fff]{2,8}", q)[:6]):
                score += 1.0
            pid = str(p.get("id") or f"promise:{setup}")
            _add(pid, f"开放伏笔:第{setup}章埋 {txt[:48]}", "promise", score)
    except Exception:
        pass

    # 2) 当章有效事实：与 synopsis/query 有字面重叠的优先；无章时保物件 condition/artifact
    try:
        ch_n = int(chapter) if chapter else 99999
        facts = store.facts_at(ch_n) if hasattr(store, "facts_at") else []
        for f in facts or []:
            eid = getattr(f, "entity_id", "") or ""
            attr = getattr(f, "attribute", "") or ""
            val = getattr(f, "value", "") or ""
            fid = getattr(f, "id", "") or f"fact:{eid}:{attr}"
            line = f"{eid} {attr} {val}".strip()
            if not line:
                continue
            score = 1.0
            name_hint = eid.split(":")[-1] if ":" in eid else eid
            if name_hint and name_hint in blob:
                score += 2.5
            if val and len(val) >= 2 and val[:8] in blob:
                score += 1.5
            if attr in ("condition", "state", "artifact"):
                if name_hint in blob or no_chapter:
                    score += 1.2 if no_chapter else 1.0
            # 讨论态：主角相关 / 高分物件多保留几条
            if score >= 2.0 or (no_chapter and score >= 2.0):
                _add(str(fid), f"{eid}·{attr}={val[:60]}", "fact", score)
            elif no_chapter and attr in ("condition", "artifact") and score >= 1.5:
                _add(str(fid), f"{eid}·{attr}={val[:60]}", "fact", score)
    except Exception:
        pass

    # 3) 角色：有章看大纲；无章钉主角
    try:
        for c in (store.characters() or [])[:20]:
            name = getattr(c, "name", None) or (c.get("name") if isinstance(c, dict) else "")
            cid = getattr(c, "id", None) or (c.get("id") if isinstance(c, dict) else name)
            imp = getattr(c, "importance", None) or (
                c.get("importance") if isinstance(c, dict) else "")
            if name and name in blob:
                _add(str(cid), f"出场/相关角色:{name}", "character", 2.0)
            elif no_chapter and imp == "protagonist" and name:
                _add(str(cid), f"主角:{name}", "character", 2.2)
            elif no_chapter and name and q and name in q:
                _add(str(cid), f"相关角色:{name}", "character", 2.0)
    except Exception:
        pass

    anchors.sort(key=lambda a: -float(a.get("score") or 0))
    return anchors[:limit]


def format_must_link_items(anchors: list[dict[str, Any]], work: str = "") -> list[tuple[str, dict]]:
    """产出 (text, meta) 列表，供 assembler 插入 canonical 头部。"""
    if not anchors:
        return []
    lines = []
    header = (
        "- 【本章戏剧必需·记忆优先｜须推动情节或感官，禁止当设定清单点名】"
    )
    lines.append((header, {
        "source_id": "must_link:header",
        "kind": "must_link",
        "work": work,
    }))
    for a in anchors:
        lines.append((
            f"- 〔必需〕{a.get('text')}",
            {
                "source_id": str(a.get("source_id") or "must_link"),
                "kind": "must_link",
                "work": work,
                "score": a.get("score"),
            },
        ))
    return lines


def pin_must_first(canonical_texts: list[str], must_lines: list[str]) -> list[str]:
    """把 must 行置顶，并去掉与 must 正文高度重复的后续行（省预算）。"""
    if not must_lines:
        return list(canonical_texts or [])
    must_body = set()
    for m in must_lines:
        # 去掉前缀标记后的核心串
        core = re.sub(r"^[-•\s〕〔必需]*", "", m)
        if len(core) >= 6:
            must_body.add(core[:40])
    out = list(must_lines)
    for t in canonical_texts or []:
        skip = False
        for core in must_body:
            if core and core in (t or ""):
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
