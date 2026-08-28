#!/usr/bin/env python3
"""从卷纲长出章级设定与信息调度，把《万界概率战争》扩到 200 章规模。

这条链路是系统现在缺的那块：`s3_plan_chapter_accounts` 只拼审批话术、不调 LLM
（`mcp/tools_write.py:1168-1181`），所以「把 10 章扩成 200 章」现在只能人手写。
3000 章的书这么走不可能。

和产正文的区别：这里交的是**账**，不是文笔。每章要回答的是「谁知道了什么、
谁在瞒谁、埋了哪条线、收了哪条线」——人脑记不住第 200 章谁知道什么，这是系统
唯一不可替代的地方；而句子写得好不好，作者自己比模型强。

分批生成，每批带三样上下文：卷纲、前文近窗、**当前的伏笔台账与主角限知状态**。
后者从库里实时查（不是模型现编），这正是上一轮草稿实验没验到的一层。

用法：
    scribe3/.venv/bin/python -m scribe3.tools.expand_wanjie_chapters \
        --db wanjie_scale --from 11 --to 20 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from weakref import WeakKeyDictionary

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scribe3.knowledge import project_frame  # noqa: E402
from scribe3.ontology import Fact, KnowledgeEdge, canon_oid  # noqa: E402
from scribe3.store import SurrealStore  # noqa: E402

FOCALIZER = "role:柳岸青"


# ---------- 上下文组装 ----------

def _bible(st) -> str:
    """世界观常量。压到能塞进提示词，但不许压成标签——压成标签模型就只会贴标签。"""
    out = []
    chars = st.characters() or []
    if chars:
        lines = []
        for c in chars:
            t = c.traits or {}
            lines.append(
                f"- {c.name}（{t.get('importance', '')}）要的是：{t.get('surface_goal') or '—'}"
                f"｜真正缺的：{t.get('deep_need') or '—'}｜怕：{t.get('fear') or '—'}")
        out.append("【人】\n" + "\n".join(lines))

    rules = st.list_world_rules() or []
    if rules:
        out.append("【规矩·谁破谁付钱】\n" + "\n".join(
            f"- {r.get('name')}：{r.get('cost') or '—'}" for r in rules))

    fac = st.list_factions() or []
    if fac:
        out.append("【势力】\n" + "\n".join(
            f"- {f.get('name')}：{(f.get('ideology') or '')[:60]}" for f in fac))

    items = st.list_items() or []
    if items:
        out.append("【物件】\n" + "\n".join(
            f"- {i.get('name')}（在 {i.get('current_owner') or '?'} 手里）："
            f"{(i.get('description') or '')[:60]}" for i in items))

    terms = st.list_terms() or []
    if terms:
        out.append("【术语】" + "；".join(
            f"{t.get('name')}={t.get('definition') or ''}" for t in terms))

    motifs = st.list_motifs() or []
    if motifs:
        out.append("【母题】" + "；".join(
            f"{m.get('name')}（{m.get('theme') or ''}）" for m in motifs))
    return "\n\n".join(out)


def _recent(st, upto: int, keep: int = 12) -> str:
    rows = [c for c in (st.chapters_lite() or []) if int(c.get("seq") or 0) < upto]
    rows = sorted(rows, key=lambda r: int(r.get("seq") or 0))[-keep:]
    if not rows:
        return "（还没有前文）"
    return "\n".join(f"第{r['seq']}章《{r.get('title') or ''}》：{r.get('synopsis') or ''}"
                     for r in rows)


def _open_promises(st) -> list[dict]:
    return [p for p in (st.list_promises() or [])
            if (p.get("status") or "open") == "open"]


def promise_ref(p: dict) -> str:
    """给未收的线一个短编号，模型收线时引用它。

    此前收线是把原话抄一半回来做模糊匹配，认不出就整条丢。给了编号就是精确引用，
    不依赖模型复述得准不准。
    """
    pid = str(p.get("id") or "")
    return "L" + (pid.split(":")[-1] if ":" in pid else pid)


def _promise_ledger(st, at: int) -> str:
    """开着的伏笔 + 到期提醒。千万字连载最容易崩的就是埋了没收。"""
    open_rows = _open_promises(st)
    if not open_rows:
        return "（暂无未收的线）"
    out = []
    for p in open_rows:
        pmax = p.get("payoff_max")
        due = ""
        if pmax and at > int(pmax):
            due = "  ← 已过期，必须收或明确改判"
        elif pmax and at > int(pmax) - 10:
            due = "  ← 快到期了"
        out.append(f"- {promise_ref(p)}｜[{p.get('tier', '?')}] "
                   f"第{p.get('setup_chapter')}章埋：{p.get('text')}{due}")
    return "\n".join(out)


def reserved_ahead(st, seq: int) -> list[str]:
    """后面几卷契约点名、这一章还不能用的实体。

    一次性立完全书时，模型给卷 2 预留了兰因，铺卷 1 时又把她提前引入。
    章级提示已经发「已经登场过的」，没发「后面预留的」。重名检查拦不住
    「契约没点名、生成时自己提前用」——必须把预留名单发下去。
    """
    from scribe3.charter import normalize_charter

    out: list[str] = []
    seen: set[str] = set()
    for v in st.list_volumes() or []:
        c = normalize_charter(v.get("charter"))
        rng = c["chapter_range"]
        if not rng or int(rng[0]) <= seq:
            continue
        for item in c["introduces"]:
            oid = item["oid"]
            if oid and oid not in seen:
                seen.add(oid)
                out.append(oid)
    return out


def _reserved_block(st, seq: int) -> str:
    oids = reserved_ahead(st, seq)
    if not oids:
        return "（后面几卷没有预留）"
    return "、".join(oids)


def _entities_in_play(st, before: int) -> str:
    """这一章之前已经登场的实体。

    新鲜度按「这一卷之前没出现过的实体」算，模型把老实体当新的引入不算数。
    不把这张表交给它，它没法知道哪些名字已经用过。
    """
    from scribe3.charter import story_entities

    try:
        oids = story_entities(st.facts_at(before - 1) or []) if before > 1 else set()
    except Exception as e:
        return f"（查询失败：{e}）"
    if not oids:
        return "（还没有）"
    return "、".join(sorted(oids))


def rank_known_facts(facts, *, keys=(), oids=(), cap: int = 25):
    """按卷契约 key 和本批实体排序。不要 facts[:25] 任意切片。"""
    keys = {str(k) for k in (keys or ()) if k}
    oids = {str(o) for o in (oids or ()) if o}

    def score(f) -> tuple:
        attr = str(getattr(f, "attribute", "") or "")
        eid = str(getattr(f, "entity_id", "") or "")
        val = str(getattr(f, "value", "") or "")
        hit_key = 2 if attr in keys else (1 if any(k in attr or k in val for k in keys) else 0)
        hit_oid = 1 if eid in oids else 0
        recency = int(getattr(f, "valid_from", 0) or 0)
        return (hit_key, hit_oid, recency)

    return sorted(facts, key=score, reverse=True)[:cap]


def _hero_knows(st, at: int, cap: int = 25) -> str:
    """主角此刻知道什么——从库里查，不是让模型现编。

    千万字规模下这张表人脑记不住，是系统唯一不可替代的东西。
    167 之前查一次要 30 秒以上，现在毫秒级，才敢放进每批生成的上下文里。
    """
    try:
        frame = project_frame(st, FOCALIZER, at)
    except Exception as e:
        return f"（限知帧查询失败：{e}）"
    facts = list(getattr(frame, "facts", []) or [])
    if not facts:
        return "（库里还没有他的知情记录）"
    keys, oids = set(), set()
    try:
        from scribe3.charter import normalize_charter
        vol = volume_for_chapter(st, at)
        c = normalize_charter((vol or {}).get("charter"))
        ke = c.get("knowledge_end") or {}
        for slot in ("must_know", "must_not_know"):
            for item in ke.get(slot) or []:
                if item.get("key"):
                    keys.add(item["key"])
        for item in (c.get("introduces") or []) + (c.get("thickens") or []):
            if item.get("oid"):
                oids.add(item["oid"])
    except Exception:
        pass
    head = rank_known_facts(facts, keys=keys, oids=oids, cap=cap)
    tail = f"\n（另有 {len(facts) - cap} 条略）" if len(facts) > cap else ""
    return "\n".join(f"- {f.entity_id}·{f.attribute}：{f.value}" for f in head) + tail


# ---------- 提示词 ----------

def pending_introduces(st, charter: dict, before: int) -> list[dict]:
    """契约点名、这一章之前还没首次出场的。"""
    from scribe3.charter import story_entities

    prior = story_entities(st.facts_at(before - 1) or []) if before > 1 else set()
    out: list[dict] = []
    for item in charter.get("introduces") or []:
        if isinstance(item, dict):
            oid, why = item.get("oid") or "", item.get("why") or ""
        else:
            oid, why = str(item), ""
        if oid and oid not in prior:
            out.append({"oid": oid, "why": why})
    return out


def remaining_batches(vol_hi: int, lo: int, batch: int) -> int:
    if batch <= 0 or lo > vol_hi:
        return 0
    return (vol_hi - lo + 1 + batch - 1) // batch


def introduce_quota(pending: int, n_batches: int) -> int:
    """本批该引入几个。剩余点名 ÷ 剩余批数，最后一批收干净。

    卷级点名可以全塞进前半批，判据看卷级就发现不了。11 个、两批：5 然后 6。
    """
    if pending <= 0 or n_batches <= 0:
        return 0
    if n_batches == 1:
        return pending
    return max(1, pending // n_batches)


def volume_for_chapter(st, seq: int) -> dict | None:
    """按契约的章号范围找这一章属于哪一卷。没有契约就回退到最后一卷。"""
    from scribe3.charter import normalize_charter

    vols = st.list_volumes() or []
    for v in vols:
        rng = normalize_charter(v.get("charter"))["chapter_range"]
        if rng and rng[0] <= seq <= rng[1]:
            return v
    return vols[-1] if vols else None


def _charter_block(st, lo: int, hi: int) -> str:
    """卷契约注入章级生成——这是「下一卷有新起点」的落地点。

    没有这一段时实测过：拿同一份卷纲生成 200 章，第 14 章起每章新增实体恒为 0。
    模型不是不会长新东西，是没人告诉它这一卷该长出什么。

    引入按批切：点名可以全塞进前半批，卷级新鲜度仍然达标、后半十章 0。
    本批只强制「剩余 ÷ 剩余批数」那么多个，其余留给后面几批。
    """
    from scribe3.charter import normalize_charter

    vol = volume_for_chapter(st, lo)
    if not vol:
        return "（这一卷还没有契约）"
    c = normalize_charter(vol.get("charter"))
    if not c["duty"]:
        return "（这一卷还没有契约）"

    out = [f"这一卷要办的那一件事：{c['duty']}", ""]
    pending = pending_introduces(st, c, lo)
    rng = c["chapter_range"] or [lo, hi]
    n_left = remaining_batches(int(rng[1]), lo, max(1, hi - lo + 1))
    quota = introduce_quota(len(pending), n_left)
    must, later = pending[:quota], pending[quota:]
    if must:
        out.append(f"**本批必须引入这 {len(must)} 个**（硬要求，用契约给的 oid 立事实；"
                   f"本卷还剩 {len(pending)} 个没出场，后面还有 {n_left} 批，"
                   "不许把后面几批的提前用光）：")
        for i in must:
            out.append(f"  - {i['oid']}：{i['why']}")
        out.append("")
    if later:
        out.append("**本卷还欠着、留给后面几批**（现在别用）：")
        for i in later:
            out.append(f"  - {i['oid']}")
        out.append("")
    if c["thickens"]:
        out.append("**这一卷必须把下面这些已有实体写厚**（他要什么、他让人付出什么；"
                   "引入完撂着不管，世界就是空的）：")
        for i in c["thickens"]:
            out.append(f"  - {i['oid']}：{i['why']}")
        out.append("")
    if c["pays"]:
        out.append("这一卷要收的旧线：")
        out += [f"  - {p}" for p in c["pays"]]
        out.append("")
    ke = c["knowledge_end"]
    if ke["must_know"]:
        out.append("卷末柳岸青必须已经知道（在这一卷里安排他怎么知道的）。"
                   "**立这条事实时，`attribute` 就用下面给的属性名**，核对时按它精确比对：")
        out += [f"  - 属性名「{k['key'] or '（未给）'}」：{k['what']}" for k in ke["must_know"]]
        out.append("")
    if ke["must_not_know"]:
        out.append("卷末柳岸青仍然不许知道（**红线，写进去就是写坏了**）。"
                   "这些属性名底下的事实，不许给他挂知识边：")
        out += [f"  - 属性名「{k['key'] or '（未给）'}」：{k['what']}"
                for k in ke["must_not_know"]]
    return "\n".join(out)


def build_prompt(st, vol_title: str, vol_intro: str, lo: int, hi: int,
                 total: int) -> str:
    return f"""你在给一本长篇立账，不是写正文。

这本书要写 {total} 章。现在立第 {lo} 到 {hi} 章的账。

判据只有一条：作者拿着这份账能直接往下写，不用回头补。
所以每一条都要具体到能查证——不许出现「某人」「某种力量」「一些线索」这种词。

## 北极星
{st.get_intent().get('north_star') or ''}

## 红线（越过就是写坏了，不许碰）
{st.get_intent().get('red_lines') or ''}

## 这本书的常量
{_bible(st)}

## 这一卷的契约（必须兑现，会被逐条核对）
{_charter_block(st, lo, hi)}

## 这一卷
《{vol_title}》：{vol_intro}

## 已经登场过的实体（这些不算新的，别拿它们充数）
{_entities_in_play(st, lo)}

## 后面几卷预留的实体（现在别用，用了后一卷就长不出新东西）
{_reserved_block(st, lo)}

## 前面已经发生的
{_recent(st, lo)}

## 还欠着的线（从库里查的，不是我编的）
{_promise_ledger(st, lo)}

## 柳岸青此刻知道什么（从库里查的）
{_hero_knows(st, lo)}

---

交一个 JSON 数组，{hi - lo + 1} 个元素，对应第 {lo} 到 {hi} 章。不要代码块标记，
不要任何解释文字，第一个字符就是 `[`。

每个元素：

{{
  "seq": 章号,
  "title": "四到六字，不要副标题",
  "synopsis": "80-150字。这一章谁要干什么、被什么挡住、付了什么代价、结果偏到哪去。要有一件具体的事，不要写心境。",
  "new_facts": [
    {{"entity": "role:人名 / place:地名 / org:组织名，前缀只能用这三个",
      "attribute": "两到四字的属性名",
      "value": "这一章之后成立、以后不能推翻的事实，一句话说死",
      "secret": true 或 false}}
  ],
  "learns": [
    {{"who": "role:xx", "fact_index": 0, "how": "saw 或 told 或 inferred"}}
  ],
  "hides": [{{"who": "role:xx", "from": "role:xx", "what": "瞒的是哪件事"}}],
  "plant": [{{"text": "这一章埋下的线，要具体到能收", "tier": "chapter 或 arc 或 book"}}],
  "payoff": [{{"ref": "上面「还欠着的线」里那条的编号，照抄，比如 L7k2x9",
               "how": "怎么收的"}}]
}}

几条硬要求：

- **「本批必须引入」里的 oid，必须在这一批章里真的出场并立下事实**，
  用契约给的那个 oid 作 `entity`，不要改名。
  「本卷还欠着、留给后面几批」现在别用——实测卷 2 点名 11 个全塞进 21-26 章，
  31-40 章引入 0，卷级新鲜度 7.0 仍然达标，闸看不见。
- 「后面几卷预留的实体」现在别用。实测卷 2 预留了兰因，铺卷 1 时第 13 章就把她用了，
  卷 2 新鲜度掉到 4.5。
- `new_facts` 每章至少一条。这是这本书的账在长厚，没有新事实说明这章白写了。
- `learns` 里的 `fact_index` 指向本章 `new_facts` 的下标。**谁不在场就不许知道**。
- 上面「柳岸青此刻知道什么」里已经有的，不要重复立成新事实。
- `hides` 至少一处。全书的劲都在信息差上，没人瞒人就没有戏。
- 每三到四章要有一条 `payoff`，`ref` 必须照抄「还欠着的线」里某一条的编号，
  不要自己编号，也不要收一条那张表上没有的线。标了「已过期」的优先收。
- 标了 secret 的事实，要想清楚它泄露出去会伤到谁——伤不到人的秘密不是秘密。
- 不许让柳岸青看见场核坐标（红线）。
"""


# ---------- 解析与落库 ----------

def parse(raw: str) -> list[dict]:
    s = (raw or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s).strip()
    i, j = s.find("["), s.rfind("]")
    if i < 0 or j < 0:
        raise ValueError(f"没找到 JSON 数组，开头是：{s[:200]}")
    return json.loads(s[i:j + 1])


HIDE_PREFIX = "隐瞒·"


def hide_attr(what: str) -> str:
    """瞒某件事的属性名。同一件事共用一个键（该单真），不同的事互不覆盖。"""
    return HIDE_PREFIX + " ".join(str(what or "").split())[:24]


_faction_names: "WeakKeyDictionary[object, set[str]]" = WeakKeyDictionary()


def _ensure_entity(st, oid: str) -> None:
    """点名要引入的东西，第一次出场时得先有户口。

    实测 26-35 章：契约要求引入 role:纪棠，模型照办立了事实，但没人给她建实体，
    于是 `add_knowledge` 拒收悬挂边——那一卷的知识边直接丢了两条。

    传进来的 oid 必须已经过 `canon_oid`。势力走 faction 表、不进 entity。
    """
    from scribe3.ontology import Entity

    prefix, name = oid.split(":", 1)
    try:
        if prefix == "role":
            if not st.entity(oid):
                st.add_entity(Entity(oid, "character", name))
        elif prefix == "place":
            if not st.entity(oid):
                st.add_entity(Entity(oid, "place", name))
        elif prefix == "org":
            # 势力名缓存：不缓存的话每个 org 实体都要全表扫一次 faction，
            # 200 章下来上千次。新建的名字同步进缓存，进程内不会重复建。
            if _faction_names.get(st) is None:
                _faction_names[st] = {(f.get("name") or "") for f in (st.list_factions() or [])}
            if name not in _faction_names[st]:
                st.add_faction(name)
                _faction_names[st].add(name)
    except Exception as e:
        print(f"  ! 建档 {oid}: {e}")


def resolve_payoff(st, item: dict) -> str | None:
    """认出这条 payoff 收的是哪一条未收的线。

    先按提示词里发下去的编号精确认；模型没给编号时，才退回拿原话片段模糊匹配。
    """
    from scribe3.charter import _loose_match

    rows = _open_promises(st)
    ref = str(item.get("ref") or "").strip().upper()
    if ref:
        for p in rows:
            if promise_ref(p).upper() == ref:
                return _local_id(p)

    text = str(item.get("text") or "")
    best, best_len = None, 0
    for p in rows:
        ptext = str(p.get("text") or "")
        if (_loose_match(text, ptext) or _loose_match(ptext, text)) and len(ptext) > best_len:
            best, best_len = p, len(ptext)
    return _local_id(best) if best else None


def _local_id(p: dict) -> str:
    pid = str(p.get("id") or "")
    return pid.split(":")[-1] if ":" in pid else pid


def persist(st, chapters: list[dict], vol_id: str | None) -> dict:
    n_fact = n_know = n_plant = n_payoff = n_hide = 0
    for ch in chapters:
        seq = int(ch["seq"])
        st.save_chapter(seq, "", title=ch.get("title") or f"第{seq}章",
                        focalizer=FOCALIZER)
        meta = {"synopsis": ch.get("synopsis") or ""}
        if vol_id:
            meta["volume"] = vol_id
        st.update_chapter_meta(seq, meta)

        fact_ids: list[str] = []
        for k, f in enumerate(ch.get("new_facts") or []):
            oid = canon_oid(f.get("entity") or "")
            if not oid:
                print(f"  ! 第{seq}章事实的实体 {f.get('entity')!r} 认不出，整条不落库")
                continue
            fid = f"fact:c{seq}-{k}"
            _ensure_entity(st, oid)
            # supersede_open=True：同 (实体, 属性) 的旧值在本章关闭，时态历史仍查得到。
            # 用 False 会让同一属性的历次说法全挂成开区间「同时有效」，
            # 一致性扫描把它们当矛盾报（实测 36-100 章误报 11 条），而注入面本来也只认单真。
            st.add_fact(Fact(id=fid, entity_id=oid,
                             attribute=f.get("attribute") or "事", value=f.get("value") or "",
                             valid_from=seq, secret=bool(f.get("secret"))))
            fact_ids.append(fid)
            n_fact += 1

        for lr in ch.get("learns") or []:
            idx = lr.get("fact_index")
            if not isinstance(idx, int) or not (0 <= idx < len(fact_ids)):
                continue
            try:
                st.add_knowledge(KnowledgeEdge(
                    knower_id=lr.get("who") or FOCALIZER,
                    proposition_id=fact_ids[idx],
                    since_chapter=seq,
                    acquired_via=lr.get("how") or "told"))
                n_know += 1
            except Exception as e:
                print(f"  ! 第{seq}章知识边 {lr.get('who')}: {e}")

        # 「A 对 B 瞒 X」不另建表——限知模型本来就能说这件事：
        # 一条只有 A 有知识边的 secret 事实。模型多给的那点动机正好进 value。
        # 这样它自动落进泄密检查的射程：B 后来要是有了这条边，就是穿帮。
        #
        # attribute 必须带上瞒的是哪件事。`facts_at` 末尾要过 `resolve_injection_facts`
        # 做同键折叠（注入面单真），全写成 "隐瞒" 的话一个人瞒的所有事挤在同一个键上，
        # 读出来只剩最后一条——实测 36-100 章写了 71 条、读回来 7 条，每人一条。
        # 隐瞒不是互斥值，同时瞒十件事是常态；只有「同一件事」才该单真。
        for h in ch.get("hides") or []:
            who, frm, what = canon_oid(h.get("who") or ""), h.get("from"), h.get("what")
            if not (who and what):
                continue
            _ensure_entity(st, who)
            fid = f"fact:c{seq}-hide{n_hide}"
            try:
                st.add_fact(Fact(id=fid, entity_id=who, attribute=hide_attr(what),
                                 value=f"对{frm or '外人'}瞒：{what}",
                                 valid_from=seq, secret=True),
                            supersede_open=False)
                st.add_knowledge(KnowledgeEdge(knower_id=who, proposition_id=fid,
                                               since_chapter=seq, acquired_via="given"))
                n_hide += 1
            except Exception as e:
                print(f"  ! 第{seq}章隐瞒 {who}: {e}")

        # 同一条线不重复埋。模型跨批次会把同一句话再埋一遍（实测「岑枝腕内待核缺口」
        # 埋了三次），台账里就出现三条一模一样的欠账，收掉一条另两条还挂着。
        open_texts = {str(p.get("text") or "").strip() for p in _open_promises(st)}
        for p in ch.get("plant") or []:
            text = str(p.get("text") or "").strip()
            if not text or text in open_texts:
                continue
            try:
                st.plant_promise(text, seq, tier=p.get("tier") or "chapter",
                                 resolution=p.get("how") or "")
                open_texts.add(text)
                n_plant += 1
            except Exception as e:
                print(f"  ! 第{seq}章伏笔: {e}")

        for p in ch.get("payoff") or []:
            pid = resolve_payoff(st, p)
            if not pid:
                print(f"  ! 第{seq}章收线认不出：ref={p.get('ref')!r} "
                      f"{str(p.get('text'))[:40]}")
                continue
            try:
                st.advance_promise(pid, seq)
                n_payoff += 1
            except Exception as e:
                print(f"  ! 第{seq}章收线 {pid}: {e}")
    return {"facts": n_fact, "knows": n_know, "hides": n_hide,
            "plant": n_plant, "payoff": n_payoff}


_THICKEN_KIND = {"role": "character", "org": "faction"}


def thicken_named_entities(st, vol: dict, *, llm_fn, persist: bool = True) -> dict:
    """把这一卷点名的已有实体 + 新引入的角色/势力走 thicken_codex。

    不另发明字段。place 没有写厚合同，跳过。
    """
    from scribe3.charter import normalize_charter
    from scribe3.codex_generate import (
        apply_codex_persist_fields, load_codex_row, persist_codex_row, thicken_codex,
    )

    c = normalize_charter((vol or {}).get("charter"))
    oids: list[str] = []
    seen: set[str] = set()
    for item in c["thickens"] + c["introduces"]:
        oid = item["oid"]
        if oid and oid not in seen:
            seen.add(oid)
            oids.append(oid)
    items: list[dict] = []
    for oid in oids:
        prefix, _, name = oid.partition(":")
        kind = _THICKEN_KIND.get(prefix)
        if not kind or not name:
            continue
        row = load_codex_row(st, kind, name) or {"name": name}
        persist_fn = None
        if persist:
            def persist_fn(fields, _kind=kind, _name=name):
                packed = apply_codex_persist_fields(_kind, fields, {}, {})
                persist_codex_row(st, _kind, _name, packed)
        out = thicken_codex(
            kind, row, llm_fn=llm_fn, persist_fn=persist_fn, st=st, name=name,
        )
        items.append({
            "oid": oid, "kind": kind, "name": name,
            "ok": bool(out.get("ok")),
            "skipped": bool(out.get("skipped")),
            "status": ("skipped_ready" if out.get("skipped")
                       else ("ok" if out.get("ok") else out.get("code") or "fail")),
        })
    return {"items": items}


def plan_batches(st, lo: int, hi: int, batch: int) -> list[tuple[dict, int, int]]:
    """把 [lo,hi] 按卷契约的章号范围切成批，每批不跨卷且不超过 batch 章。

    不切分会出两个错：整段用起始章那一卷的契约（后面几卷的新实体永远不会被引入），
    以及所有章都挂到同一个 vol_id 上。一次请求塞太多章还会被 max_tokens 截断。
    """
    from scribe3.charter import normalize_charter

    out: list[tuple[dict, int, int]] = []
    seq = lo
    while seq <= hi:
        vol = volume_for_chapter(st, seq)
        if vol is None:
            raise SystemExit(f"第 {seq} 章找不到所属卷，先跑 plan_charter 立卷纲。")
        rng = normalize_charter(vol.get("charter"))["chapter_range"] or [seq, hi]
        vol_end = min(int(rng[1]), hi)
        while seq <= vol_end:
            end = min(seq + batch - 1, vol_end)
            out.append((vol, seq, end))
            seq = end + 1
    return out


def expand_volume_accounts(st, vol: dict, *, llm_fn, total: int = 200,
                           batch: int = 10, window: int | None = None) -> dict:
    """给一卷立章级账。产品路径和 CLI 共用。

    window 只铺从已有章之后的 N 章（眼前这一段）。不传则铺契约范围内还空的。
    """
    from scribe3.charter import normalize_charter

    c = normalize_charter((vol or {}).get("charter"))
    rng = c["chapter_range"] or [1, total]
    lo, hi = int(rng[0]), int(rng[1])
    have = [int(ch.get("seq") or 0) for ch in (st.chapters_lite() or [])]
    in_vol = [s for s in have if lo <= s <= hi]
    start = (max(in_vol) + 1) if in_vol else lo
    if window:
        hi = min(hi, start + int(window) - 1)
    lo = start
    if hi < lo:
        return {"chapters": 0, "note": "这一卷已经铺完"}
    n_ch = 0
    stats = []
    for v, a, b in plan_batches(st, lo, hi, batch):
        prompt = build_prompt(st, v.get("title") or "", v.get("intro") or "", a, b, total)
        try:
            raw = llm_fn(prompt, max_tokens=12288)
        except TypeError:
            raw = llm_fn(prompt)
        chapters = parse(raw)
        persisted = persist(st, chapters, v.get("id"))
        n_ch += len(chapters)
        stats.append({"lo": a, "hi": b, "persist": persisted})
    try:
        thick = thicken_named_entities(st, vol, llm_fn=llm_fn)
    except Exception as e:
        thick = {"error": str(e)}
    return {"chapters": n_ch, "batches": stats, "thicken": thick}


def run_batch(st, vol: dict, lo: int, hi: int, total: int, *,
              dry_run: bool = False, out: str | None = None) -> None:
    from scribe3.llm import hermes_complete

    vol_title = vol.get("title") or "未命名卷"
    prompt = build_prompt(st, vol_title, vol.get("intro") or "", lo, hi, total)
    print(f"卷《{vol_title}》 第 {lo}-{hi} 章｜提示词 {len(prompt)} 字")

    raw = hermes_complete(prompt, max_tokens=12288, temperature=0.6, timeout=900)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(raw)
    chapters = parse(raw)
    print(f"  解析出 {len(chapters)} 章")
    for ch in chapters:
        print(f"  第{ch.get('seq')}章《{ch.get('title')}》 {ch.get('synopsis')}")
        for f in ch.get("new_facts") or []:
            print(f"    + {'[密]' if f.get('secret') else ''}"
                  f"{f.get('entity')}·{f.get('attribute')} = {f.get('value')}")
        for h in ch.get("hides") or []:
            print(f"    瞒：{h.get('who')} 对 {h.get('from')} 瞒 {h.get('what')}")
        for p in ch.get("payoff") or []:
            print(f"    收：{p.get('text')}")
    if dry_run:
        print("  （dry-run，没落库）")
        return
    print("  落库：", persist(st, chapters, vol.get("id")))
    from scribe3.charter import freshness
    fr = freshness(st, lo, hi)
    print(f"  本批新鲜度 {fr['new_entities_per_10ch']:.1f}／10章　"
          f"新 {len(fr['new_entities'])}：{'、'.join(fr['new_entities'][:8]) or '无'}"
          f"{'…' if len(fr['new_entities']) > 8 else ''}（只报不拦）")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8123/rpc")
    ap.add_argument("--db", default="wanjie_scale")
    ap.add_argument("--from", dest="lo", type=int, required=True)
    ap.add_argument("--to", dest="hi", type=int, required=True)
    ap.add_argument("--total", type=int, default=200)
    ap.add_argument("--batch", type=int, default=10, help="每次请求最多几章")
    ap.add_argument("--volume", default=None, help="卷标题；缺省按契约自动分卷")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不落库")
    ap.add_argument("--prompt-only", action="store_true", help="只打提示词，不调模型")
    ap.add_argument("--out", default=None, help="把原始返回存到这个文件")
    args = ap.parse_args()

    st = SurrealStore(url=args.url, ns="scribe3", db=args.db)
    try:
        if args.volume:
            vols = st.list_volumes() or []
            vol = next((v for v in vols if v.get("title") == args.volume), None)
            if vol is None:
                raise SystemExit(f"没有叫《{args.volume}》的卷。")
            batches = [(vol, args.lo, args.hi)]
        else:
            batches = plan_batches(st, args.lo, args.hi, args.batch)

        if args.prompt_only:
            vol, lo, hi = batches[0]
            print(build_prompt(st, vol.get("title") or "", vol.get("intro") or "",
                               lo, hi, args.total))
            return

        print(f"共 {len(batches)} 批："
              + "、".join(f"《{v.get('title')}》{a}-{b}" for v, a, b in batches) + "\n")
        failed: list[tuple[int, int]] = []
        from scribe3.llm import hermes_complete
        for i, (vol, lo, hi) in enumerate(batches, 1):
            print(f"[{i}/{len(batches)}] ", end="")
            # 失败重试一次：一批就是十章，直接跳过等于书里空一段，
            # 而失败多是截断或超时这类重跑就好的事。
            for attempt in (1, 2):
                try:
                    run_batch(st, vol, lo, hi, args.total,
                              dry_run=args.dry_run, out=args.out)
                    break
                except Exception as e:
                    tag = "重试" if attempt == 1 else "仍失败，跳过"
                    print(f"  ✗ 第 {lo}-{hi} 章 {type(e).__name__}: {e}｜{tag}")
                    if attempt == 2:
                        failed.append((lo, hi))
            print()
            nxt = batches[i][0] if i < len(batches) else None
            vol_done = nxt is None or nxt.get("id") != vol.get("id")
            if vol_done and not args.dry_run:
                print(f"  写厚（整卷一次）：", thicken_named_entities(
                    st, vol, llm_fn=lambda p, max_tokens=4096: hermes_complete(
                        p, max_tokens=max_tokens, temperature=0.4, timeout=180)))
        if failed:
            print("这些章没铺成，补跑：" + "、".join(f"{a}-{b}" for a, b in failed))
    finally:
        st.close()


if __name__ == "__main__":
    main()
