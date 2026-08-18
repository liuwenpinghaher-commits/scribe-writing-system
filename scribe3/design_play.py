"""章设计：先写戏，再审戏，再拆表。质量只问这篇戏。"""
from __future__ import annotations

from typing import Any, Callable, Mapping

LlmFn = Callable[..., str]

_PLAY_MAX = 3
_EXTRACT_MAX = 3

_DILEMMA_MARK = ("还是", " vs ", " VS ", "vs", "要么")
_FALSE_PREV = ("上章", "上一口", "余烬", "接上")

_TABLE_KEYS = (
    ("cast", "在场"),
    ("goal", "本章要"),
    ("choice", "选择"),
    ("decision", "决断"),
    ("cost", "代价"),
    ("bite", "咬上章"),
)

_META_CHOICE = ("选择", "做出", "决定", "选边", "两难", "还是")
_NO_DECISION = ("没选", "等于没选", "尚未选", "未选")
_WEAK_SIDE = ("他", "她", "它", "还", "就", "便")


def play_sha(play: str) -> str:
    import hashlib
    return hashlib.sha256((play or "").encode("utf-8")).hexdigest()[:16]


def _cn_content(text: str) -> str:
    from scribe3.narrative_contract import cn_strip
    t = cn_strip(text)
    for w in _WEAK_SIDE:
        t = t.replace(w, "")
    return t


def _side_has_substance(side: str) -> bool:
    from scribe3.narrative_contract import cn_len
    return cn_len(_cn_content(side)) >= 2


def _strip_meta_choice(text: str) -> str:
    from scribe3.narrative_contract import cn_strip
    t = cn_strip(text)
    for w in _META_CHOICE:
        t = t.replace(w, "")
    return t


def _meta_choice_only(text: str) -> bool:
    return not _side_has_substance(_strip_meta_choice(text))


def _same_event(slot: str, event: str) -> bool:
    """本章要是不是今晚那一件。去掉「做出选择」后若只剩人名，不算。"""
    from scribe3.narrative_contract import cn_len
    body = _strip_meta_choice(slot)
    ev = (event or "").strip()
    if not _side_has_substance(body) or not ev:
        return False
    if body in ev:
        rest = ev.replace(body, "", 1)
        if _side_has_substance(rest) and cn_len(body) < cn_len(rest):
            return False
        return True
    if ev in body:
        return True
    return _copied_clause(body, ev)


def _act_hits(sent: str, side: str) -> bool:
    """决断句是不是迈了这一边。短侧写（自按）要对上长决断句。"""
    from scribe3.clue_density import (
        _distinctive_overlap,
        _obj_residue,
        _side_same,
        _verb_stems,
    )
    if not (sent or "").strip() or not (side or "").strip():
        return False
    if side in sent or sent in side or _side_same(sent, side):
        return True
    if _distinctive_overlap(sent, side, None) and not _meta_choice_only(side):
        return True
    stems = _verb_stems(side)
    if not stems or not any(v in sent for v in stems):
        return False
    res = _obj_residue(side)
    if res:
        return res in sent or _copied_clause(res, sent)
    if any(c in side for c in "自己") and not any(c in sent for c in "自己"):
        return False
    return True


def _split_on_play_marks(sent: str) -> tuple[str, str] | None:
    import re
    text = (sent or "").strip()
    if not text:
        return None
    if "要么" in text or "要麼" in text:
        parts = [p.strip(" ，,：:") for p in re.split(r"要么|要麼", text) if p.strip(" ，,：:")]
        if len(parts) >= 2:
            a, b = parts[-2], parts[-1]
            if _side_has_substance(a) and _side_has_substance(b):
                return a, b
    for mark in ("还是", " vs ", " VS ", "vs"):
        if mark not in text:
            continue
        left, right = text.split(mark, 1)
        a, b = left.strip(" ，,：:"), right.strip(" ，,：:")
        if _side_has_substance(a) and _side_has_substance(b):
            return a, b
    return None


_AB_SKIP = ("都一样", "还是得选", "你还是得", "还是得先")


def _strip_speaker(side: str) -> str:
    import re
    t = (side or "").strip(" “”\"'「」『』，,：:")
    t = re.sub(r"^[\u4e00-\u9fff]{1,4}说[，,]?", "", t)
    t = re.sub(r"[，,]?[\u4e00-\u9fff]{1,4}说$", "", t)
    return t.strip(" “”\"'，,：:")


def play_choice_ab(play: str) -> tuple[str, str] | None:
    """从戏里取出那道还没选的两难。只认还是/vs/要么，不扫「对/或」。

    取最后一道像样的两难：前面常有旁人的「等还是等」，后面才是他要迈的那一步。
    引号把一句拆成两截、或左边只剩「某某说」时，拼上上一句再认一次。
    """
    from scribe3.clue_density import split_sents
    hits: list[tuple[str, str]] = []
    prev = ""
    for sent in split_sents(play or ""):
        if any(k in sent for k in _AB_SKIP):
            prev = sent
            continue
        hit = _split_on_play_marks(sent)
        need_join = bool(hit) and not _side_has_substance(_strip_speaker(hit[0]))
        if (not hit or need_join) and prev:
            if any(m in sent for m in ("还是", "要么")) or sent.lstrip("“”\"'「」 ").startswith("还是"):
                joined = _split_on_play_marks(prev + sent)
                if joined:
                    hit = (_strip_speaker(joined[0]), joined[1])
        if hit:
            a, b = _strip_speaker(hit[0]), hit[1]
            if _side_has_substance(a) and _side_has_substance(b):
                hits.append((a, b))
        prev = sent
    return hits[-1] if hits else None


def _copied_clause(slot: str, source: str) -> bool:
    from scribe3.clue_density import _distinctive_overlap, split_sents
    if not (slot or "").strip() or not (source or "").strip():
        return False
    if slot in source:
        return True
    for sent in split_sents(source):
        if _distinctive_overlap(slot, sent, None) and not _meta_choice_only(slot):
            return True
    return False


def play_event_sent(play: str, book) -> str:
    from scribe3.clue_density import split_sents
    event = ""
    if book is not None:
        event = str(getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "")
    if event:
        for sent in split_sents(play or ""):
            if _copied_clause(sent, event) or _copied_clause(event, sent):
                return sent
        return event
    before: list[str] = []
    for sent in split_sents(play or ""):
        if _split_on_play_marks(sent):
            return before[0] if before else sent
        if _side_has_substance(sent):
            before.append(sent)
    return before[0] if before else ""


def play_decision_sent(play: str) -> str:
    from scribe3.clue_density import _side_same, split_sents
    ab = play_choice_ab(play)
    if not ab:
        return ""
    after = False
    for sent in split_sents(play or ""):
        if _split_on_play_marks(sent):
            after = True
            continue
        if not after:
            continue
        like_a = _act_hits(sent, ab[0])
        like_b = _act_hits(sent, ab[1])
        if like_a ^ like_b:
            return sent
    return ""


def play_bill_sent(play: str, book) -> str:
    from scribe3.clue_density import split_sents
    ab = play_choice_ab(play)
    after = False
    dec = play_decision_sent(play)
    bill = ""
    if book is not None:
        bill = str(getattr(book, "duty_bill", "") or "")
    for sent in split_sents(play or ""):
        if dec and sent == dec:
            after = True
            continue
        if ab and _split_on_play_marks(sent):
            after = True
            continue
        if not after:
            continue
        if bill and (_copied_clause(sent, bill) or _copied_clause(bill, sent)):
            return sent
        if any(w in sent for w in ("变", "改", "裂", "账", "锁", "贵", "死", "开")):
            return sent
    if bill:
        return ""
    return ""


def table_same_play(play: str, parsed: Mapping[str, Any] | None, book) -> list[str]:
    """表上哪些行不是这篇戏。返回人话行名。"""
    from scribe3.chapter_spine import normalize_choice, parse_choice_ab, slot_text
    from scribe3.clue_density import _ab_same, invented_cast_names

    if not parsed:
        return ["整张表"]
    spine = parsed.get("chapter_spine") if isinstance(parsed.get("chapter_spine"), dict) else {}
    beats = parsed.get("beats") if isinstance(parsed.get("beats"), list) else []
    hits: list[str] = []
    event_sent = play_event_sent(play, book)
    duty_event = ""
    if book is not None:
        duty_event = str(getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "")
    goal = slot_text(spine.get("goal"))
    goal_ok = bool(goal) and (
        (event_sent and _same_event(goal, event_sent))
        or (duty_event and _same_event(goal, duty_event))
    )
    if not goal_ok:
        hits.append("本章要")
    want_ab = play_choice_ab(play)
    got_ab = parse_choice_ab(spine.get("choice"))
    if not want_ab or not got_ab or not _ab_same(want_ab, got_ab):
        hits.append("选择")
    decision = slot_text(spine.get("decision"))

    def _decides(side: str) -> bool:
        if not side:
            return False
        if _act_hits(decision, side):
            return True
        dec_sent = play_decision_sent(play)
        if dec_sent and (_act_hits(decision, dec_sent) or _copied_clause(decision, dec_sent)):
            return _act_hits(dec_sent, side)
        return False

    if (
        not decision
        or any(m in decision for m in _NO_DECISION)
        or not want_ab
    ):
        hits.append("决断")
    elif want_ab:
        like_a, like_b = _decides(want_ab[0]), _decides(want_ab[1])
        if like_a == like_b:
            hits.append("决断")
    staged = 0
    staged_ok = False
    for b in beats:
        if not isinstance(b, dict):
            continue
        bab = parse_choice_ab(b.get("choice"))
        if not bab:
            continue
        staged += 1
        if want_ab and _ab_same(bab, want_ab):
            staged_ok = True
    if staged == 0:
        hits.append("没有一场把两难搬上台")
    elif staged > 1:
        hits.append("只有一场搬上这道两难，其余选写无")
    elif want_ab and not staged_ok:
        hits.append("搬上台的不是戏里那道两难")
    cost = slot_text(spine.get("cost"))
    if cost:
        bill_sent = play_bill_sent(play, book)
        if not bill_sent or not _copied_clause(cost, bill_sent) or _meta_choice_only(cost):
            hits.append("代价")
    names = set(getattr(book, "character_names", None) or []) if book is not None else set()
    if names:
        invented = invented_cast_names(slot_text(spine.get("cast")), book)
        if invented:
            hits.append("在场（戏里多了个没立档的人）")
    lines_ok = bool(getattr(book, "bindable_lines", None)) if book is not None else False
    if lines_ok:
        bound = spine.get("lines") if isinstance(spine.get("lines"), list) else []
        for it in bound:
            if not isinstance(it, dict):
                continue
            delta = str(it.get("delta") or "").strip()
            if delta and not _copied_clause(delta, play or ""):
                hits.append("动哪条线")
                break
    del normalize_choice
    return hits


def staged_from_table(play: str, parsed: Mapping[str, Any] | None) -> tuple[str, int]:
    from scribe3.chapter_spine import parse_choice_ab
    from scribe3.clue_density import _ab_same
    ab = play_choice_ab(play)
    beats = (parsed or {}).get("beats") if isinstance((parsed or {}).get("beats"), list) else []
    n = 0
    for i, b in enumerate(beats or [], 1):
        if not isinstance(b, dict):
            continue
        bab = parse_choice_ab(b.get("choice"))
        if bab and ab and _ab_same(bab, ab):
            n = i
            break
    label = f"{ab[0]} 还是 {ab[1]}" if ab else ""
    return label, n


def play_system_prompt() -> str:
    return (
        "你在写这一章怎么发生，不是读者正文，不是填表。"
        "只写这场戏。不要输出表格、标签、拍头。"
    )


def play_has_dilemma(play: str) -> bool:
    text = play or ""
    return any(m in text for m in _DILEMMA_MARK)


def evaluate_play(play: str, book, *, seq: int | None = None) -> dict[str, Any]:
    """机器审这篇戏。意见只说戏，不报编号。"""
    from scribe3.clue_density import (
        _distinctive_overlap,
        duty_actor_names,
        topics_overlap,
    )

    text = (play or "").strip()
    errors: list[str] = []
    if not text:
        return {
            "ok": False,
            "errors": ["play_empty"],
            "opinion": "还没有这场戏。写成今晚谁在做事、办哪一件、他还没选时两头各要付出什么。",
        }
    if not play_has_dilemma(text):
        errors.append("no_dilemma")

    if book is not None:
        who = str(getattr(book, "duty_who", "") or "")
        event = str(getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "")
        bill = str(getattr(book, "duty_bill", "") or "")
        names = duty_actor_names(who, book)
        if names and any(n not in text for n in names):
            errors.append("who_unmet")
        if event and not _distinctive_overlap(text, event, book):
            errors.append("event_unmet")
        if bill and not _distinctive_overlap(text, bill, book):
            errors.append("bill_unmet")
        nseq = int(seq or getattr(book, "seq", 1) or 1)
        if nseq <= 1:
            if any(m in text for m in _FALSE_PREV):
                errors.append("bite_false_prev")
        else:
            hook = str(getattr(book, "prev_hook", "") or "")
            if hook and not topics_overlap(text, hook, book):
                errors.append("bite_off_hook")

    return {
        "ok": not errors,
        "errors": errors,
        "opinion": _play_opinion(errors, book),
    }


def _play_opinion(errors: list[str], book) -> str:
    who = str(getattr(book, "duty_who", "") or "") if book is not None else ""
    event = str(getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "") if book is not None else ""
    bill = str(getattr(book, "duty_bill", "") or "") if book is not None else ""
    hook = str(getattr(book, "prev_hook", "") or "") if book is not None else ""
    if "event_unmet" in errors and event:
        return f"你写成了另一件。这一章要办的是：{event}"
    if "who_unmet" in errors and who:
        return f"该做事的是：{who}。你现在没让他们在场做事。"
    if "bill_unmet" in errors and bill:
        return f"这一章的账是：{bill}。你现在写的代价是另一笔账。"
    if "cast_invented" in errors:
        return "不要编名单里没有的人。对手用已经有的人，或用物件、地点、机制。"
    if "bite_false_prev" in errors:
        return "这是第1章。只写章开始前还压在身上的状态，不要假装有上一章。"
    if "bite_off_hook" in errors and hook:
        return f"上一章没做完的是：{hook}。要接住这件事，不是另起一句。"
    if "no_dilemma" in errors:
        return "他还没选时两头各要付出什么，你没写出来。"
    return "这场戏还不像该发生的那一件。"


def build_play_prompt(book, *, seq: int | None, extra: str = "") -> str:
    bits = [
        play_system_prompt(),
        "写成一篇短戏。读完的人要能说出：谁在做事、今晚办哪一件、"
        "他还没选时两头各要付出什么、他选了哪边、世界因此怎么变、章末还没做完什么。",
        "不要编名单里没有的人。",
        "不要把今晚不该出场的东西拿来挡、拿来付账。",
        "不要把今晚还不该拆穿的事说破。",
    ]
    if book is not None:
        names = sorted(getattr(book, "character_names", None) or [])
        if names:
            bits.append("已有人名：" + "、".join(names[:24]))
        who = str(getattr(book, "duty_who", "") or "")
        event = str(getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "")
        bill = str(getattr(book, "duty_bill", "") or "")
        if who:
            bits.append("这一章该做事的人：" + who)
        if event:
            bits.append("这一章要办的一件事：" + event)
        if bill:
            bits.append("这一章的账：" + bill)
        hook = str(getattr(book, "prev_hook", "") or "")
        if hook:
            bits.append("上一章没做完的：" + hook)
        elif int(seq or 0) <= 1:
            bits.append("这是第1章。只写章开始前还压在身上的状态，不要假装有上一章。")
    blob = (extra or "").lower()
    if extra and "force=1" not in blob and "rewrite_play=1" not in blob:
        bits.append(extra.strip())
    if seq:
        bits.append(f"这是第{seq}章。")
    bits.append("只输出这篇戏，不要标签。")
    return "\n".join(bits)


def build_play_retry_prompt(play: str, opinion: str, book, *, seq: int | None) -> str:
    del book, seq
    return "\n".join([
        "下面这篇戏没有过审。按意见改戏，不要填表，不要输出标签。",
        "【戏】",
        (play or "").strip(),
        "【意见】",
        (opinion or "").strip(),
        "只输出改过的戏。",
    ])


def build_review_prompt(play: str, book, *, seq: int | None) -> str:
    del seq
    bits = [
        "下面是一场已经过机器这一关的戏。只判断这场戏像不像，不要填表。",
        "只问这两件：",
        "有没有把下一章的东西提前拿来挡、拿来付账？",
        "还不该拆穿的事有没有提前说破？",
    ]
    if book is not None:
        event = str(getattr(book, "duty_event", "") or getattr(book, "must_happen", "") or "")
        if event:
            bits.append("今晚该办的是：" + event)
    bits.append("【戏】\n" + (play or "").strip())
    bits.append(
        "第一行只能写「过」或「不过」三个字里选一个，不要写别的。"
        "不过则第二段写改戏意见，只说戏，不说表格，不要点名某几个字当交卷条件。"
    )
    return "\n".join(bits)


def parse_review(raw: str) -> dict[str, Any]:
    """首行必须是整词「过」或「不过」。「过程写歪了」不算过。"""
    text = (raw or "").strip()
    first = text.splitlines()[0] if text else ""
    head = first.replace("：", ":").strip().rstrip("。．.")
    if ":" in head:
        head = head.split(":", 1)[0].strip()
    low = head.lower()
    if head == "过" or low == "pass":
        ok = True
    elif head == "不过" or low == "fail" or head.startswith("不过"):
        ok = False
    else:
        ok = False
    opinion = ""
    if not ok:
        rest = "\n".join(text.splitlines()[1:]).strip()
        opinion = rest or text
    return {"ok": ok, "opinion": opinion, "raw": text[:800]}


def build_extract_prompt(play: str, book, *, missing: str = "") -> str:
    bits = [
        "下面这篇戏已经过审。只从这篇戏里抽出标签行，不要另编一场戏。",
        "戏里没有的人、物、线，不要补。",
        "「本章要」抄今晚办的那一件，不要写成「做出选择」。",
        "「选择」抄他还没选时的两难，中间用「还是」。",
        "「决断」抄他选了哪边。",
        "「代价」抄世界因此怎么变；戏里没有就不要编。",
        "三场里只有一场的选抄这道两难，其余场选写「无」。",
        "冒号后面只写戏里有的句子。",
    ]
    if missing:
        bits.append("上一轮这些还没从戏里抽清，只补这些，别的按戏原样：\n" + missing)
    else:
        bits.append(
            "需要从戏里抄出的行名：时空、在场、咬上章、本章要、挡、触发、升级、"
            "选择、决断、代价、信息差、动哪条线、钩、禁令、时长、增量、地点、地点增量、世界事实。"
            "再拆三场上台的压力，拍头写成 ## 拍1 / ## 拍2 / ## 拍3。"
            "不要丢一张空白表格逼自己编。戏里没有的行不要写。"
        )
    if book is not None:
        names = sorted(getattr(book, "character_names", None) or [])
        if names:
            bits.append("已有人名：" + "、".join(names[:24]))
        lines = list(getattr(book, "bindable_lines", None) or [])
        if lines:
            shown = []
            for ln in lines[:8]:
                shown.append(
                    f"{getattr(ln, 'kind', '')}:{getattr(ln, 'id', '')} {getattr(ln, 'text', '')}".strip()
                )
            bits.append("可绑的线（戏里真动到才写）：\n" + "\n".join(shown))
    bits.append("【戏】\n" + (play or "").strip())
    bits.append("只输出从这篇戏里抄出来的标签行。")
    return "\n".join(bits)


def extract_missing(parsed: Mapping[str, Any] | None, play: str = "", book=None) -> str:
    bits = []
    if play:
        bits.extend(table_same_play(play, parsed, book))
    if not parsed or not parsed.get("ok"):
        bits.append("【章】和三场还没抽全。从戏里把在场、本章要、选择、决断、代价、三场抄出来。")
        return "；".join(bits)
    spine = parsed.get("chapter_spine") if isinstance(parsed.get("chapter_spine"), dict) else {}
    from scribe3.chapter_spine import slot_text, parse_choice_ab
    if not parse_choice_ab(spine.get("choice")):
        bits.append("选择：戏里他还没选时的两难")
    if not slot_text(spine.get("decision")):
        bits.append("决断：他选了哪边")
    beats = parsed.get("beats") if isinstance(parsed.get("beats"), list) else []
    if len(beats) < 3:
        bits.append("三场上台的压力")
    clock = parsed.get("clock") if isinstance(parsed.get("clock"), dict) else {}
    place = parsed.get("place") if isinstance(parsed.get("place"), dict) else {}
    if not str((clock or {}).get("span") or "").strip():
        bits.append("时长：这一场多重")
    if not str((place or {}).get("name") or "").strip():
        bits.append("地点：人还在哪")
    # 去重保序
    seen: set[str] = set()
    out: list[str] = []
    for b in bits:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return "；".join(out)


def table_ungrounded(play: str, parsed: Mapping[str, Any] | None, book) -> list[str]:
    """表上哪些行不是这篇戏。"""
    return table_same_play(play, parsed, book)


def play_design_ready(ch: Mapping[str, Any] | None) -> bool:
    """戏过了、表是这篇戏的抄本：设计层算齐。"""
    src = ch if isinstance(ch, dict) else {}
    meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
    play = str(meta.get("play") or "").strip()
    if not play:
        return False
    if str(meta.get("schema_design") or "") != "chapter_design.v1":
        return False
    from scribe3.chapter_spine import is_v1, parse_choice_ab
    spine = src.get("chapter_spine")
    if not is_v1(spine):
        return False
    if not parse_choice_ab((spine or {}).get("choice")):
        return False
    beats = [b for b in (src.get("beats") or []) if b]
    if len(beats) < 3:
        return False
    return not table_same_play(play, {"chapter_spine": spine, "beats": beats}, None)


def persist_play_design_blocked(
    fields: Mapping[str, Any] | None,
    *,
    book=None,
    store=None,
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """戏过之后：半稿 / 编人 / 换地 / 表不是这篇戏。play-only 放行。"""
    from scribe3.chapter_spine import is_v1, slot_text
    from scribe3.clue_density import invented_cast_names, same_landmark

    if store is not None and book is None:
        return {
            "code": "iceberg_thin_persist",
            "message": "有书却没带上户口，禁止只考表格",
            "missing": [{"id": "design_book_missing", "detail": "store_without_book"}],
        }
    src = dict(fields or {})
    writing_design = (
        src.get("chapter_spine") not in (None, {},) and "chapter_spine" in src
    ) or ("beats" in src and src.get("beats") not in (None, []))
    if not writing_design:
        return None
    spine = src.get("chapter_spine") if src.get("chapter_spine") else (existing or {}).get("chapter_spine")
    beats = src.get("beats") if src.get("beats") else (existing or {}).get("beats")
    if not is_v1(spine) or not isinstance(beats, list) or not beats:
        return {
            "code": "design_half",
            "message": "戏过了，大纲和几场要一起进书",
            "missing": [{"id": "design_half", "detail": "half"}],
        }
    if book is not None and set(getattr(book, "character_names", None) or []):
        invented = invented_cast_names(slot_text((spine or {}).get("cast")), book)
        if invented:
            return {
                "code": "iceberg_thin_persist",
                "message": "戏里多了个没立档的人，不能自动建档",
                "missing": [{"id": "cast_invented", "detail": "、".join(invented[:4])}],
            }
        meta = src.get("beats_meta") if isinstance(src.get("beats_meta"), dict) else {}
        place = meta.get("place") if isinstance(meta.get("place"), dict) else {}
        pname = str(place.get("name") or "")
        prev = str(getattr(book, "prev_place_name", "") or "")
        setting = slot_text((spine or {}).get("setting"))
        if prev and pname and not same_landmark(pname, prev):
            if not setting:
                return {
                    "code": "iceberg_thin_persist",
                    "message": "换了地方，要让人看得出他怎么到的",
                    "missing": [{"id": "place_travel_unsaid", "detail": pname}],
                }
        try:
            pdelta = int(place.get("delta") if place.get("delta") is not None else 0)
        except (TypeError, ValueError):
            pdelta = 0
        stay = str(place.get("stay_reason") or "").strip()
        if int(getattr(book, "seq", 1) or 1) >= 3 and pdelta == 0 and not stay and prev and same_landmark(pname, prev):
            return {
                "code": "iceberg_thin_persist",
                "message": "连续几章还在这儿，要说清为什么还没走",
                "missing": [{"id": "place_frozen", "detail": pname}],
            }
    play = ""
    for bag in (src.get("beats_meta"), (existing or {}).get("beats_meta") if isinstance(existing, dict) else None):
        if isinstance(bag, dict) and str(bag.get("play") or "").strip():
            play = str(bag.get("play") or "")
            break
    if play:
        unlike = table_same_play(play, {"ok": True, "chapter_spine": spine, "beats": beats}, book)
        if unlike:
            return {
                "code": "extract_thin",
                "message": "戏过了，表还没从这篇戏里抄像：" + "；".join(unlike),
                "missing": [{"id": "table_same_play", "detail": x} for x in unlike],
            }
    return None


def reviewed_play_meta(ch: Mapping[str, Any] | None, play: str) -> dict[str, Any]:
    base = {}
    if isinstance(ch, dict) and isinstance(ch.get("beats_meta"), dict):
        base = dict(ch.get("beats_meta") or {})
    text = (play or "")[:4000]
    base["play"] = text
    base["play_review_ok"] = True
    base["play_sha"] = play_sha(text)
    return base


def persist_reviewed_play(persist_fn, ch: Mapping[str, Any] | None, play: str) -> dict[str, Any]:
    """审过那一刻把戏写进章。不等整张表齐。"""
    meta = reviewed_play_meta(ch, play)
    if persist_fn:
        try:
            persist_fn({"beats_meta": meta})
        except Exception:
            pass
    return meta


def load_working_paper(st, seq: int | None, *, ch: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    if isinstance(ch, dict):
        meta = ch.get("beats_meta") if isinstance(ch.get("beats_meta"), dict) else {}
        play = str(meta.get("play") or "").strip()
        if play and meta.get("play_review_ok"):
            return {"play": play, "review_ok": True, "play_sha": meta.get("play_sha") or play_sha(play)}
    rows: list = []
    if st is not None and seq and hasattr(st, "list_design_attempts"):
        try:
            rows = st.list_design_attempts(int(seq), limit=20) or []
        except Exception:
            rows = []
    if isinstance(ch, dict):
        meta = ch.get("beats_meta") if isinstance(ch.get("beats_meta"), dict) else {}
        play = str(meta.get("play") or "").strip()
        sha = str(meta.get("play_sha") or (play_sha(play) if play else ""))
        if play:
            for row in reversed(rows):
                if not (row or {}).get("review_ok"):
                    continue
                rp = str((row or {}).get("play") or "")
                if rp and (play_sha(rp) == sha or rp[:200] == play[:200]):
                    return {"play": play, "review_ok": True, "play_sha": sha}
    for row in reversed(rows):
        if (row or {}).get("review_ok") and str((row or {}).get("play") or "").strip():
            return dict(row)
    return None


def paper_record(
    n: int,
    play: str,
    *,
    review_ok: bool,
    parsed: Mapping[str, Any] | None = None,
    errors: list | None = None,
    slot: str = "",
) -> dict[str, Any]:
    src = parsed if isinstance(parsed, dict) else {}
    return {
        "n": int(n),
        "struct_ok": bool(src.get("ok")),
        "exam_ok": bool(review_ok),
        "errors": list(errors or []),
        "slot": slot,
        "play": play or "",
        "review_ok": bool(review_ok),
        "chapter_spine": src.get("chapter_spine") if isinstance(src.get("chapter_spine"), dict) else {},
        "beats": src.get("beats") if isinstance(src.get("beats"), list) else [],
        "clock": src.get("clock") if isinstance(src.get("clock"), dict) else {},
        "place": src.get("place") if isinstance(src.get("place"), dict) else {},
        "raw_head": (play or "")[:240],
    }


def _call(llm_fn: LlmFn, prompt: str, max_tokens: int) -> str:
    if llm_fn is None or not callable(llm_fn):
        raise ValueError("design_play 必须提供 llm_fn")
    try:
        raw = llm_fn(prompt, max_tokens)
    except TypeError:
        raw = llm_fn(prompt)
    return str(raw or "").strip()


def run_play_review_extract(
    *,
    llm_fn: LlmFn,
    book,
    seq: int | None,
    extra: str = "",
    known_line_ids=None,
    previous_play: str = "",
    resume_extract: bool = False,
) -> dict[str, Any]:
    """写戏 → 机器审 → 模型只问两句 → 拆表。拆不出只重拆。"""
    from scribe3.chapter_spine import assemble_synopsis_from_spine, parse_choice_ab
    from scribe3.fate_dearer import parse_clock_place_labels
    from scribe3.stage_generate import parse_chapter_design_payload

    trail: list[dict[str, Any]] = []
    play = (previous_play or "").strip()
    if not play:
        play = _call(llm_fn, build_play_prompt(book, seq=seq, extra=extra), 2048)
        trail.append({"step": "play", "n": 1, "head": play[:200]})

    review = {"ok": False, "opinion": "还没审"}
    if not resume_extract:
        for i in range(_PLAY_MAX):
            hard = evaluate_play(play, book, seq=seq)
            trail.append({
                "step": "hard_review", "n": i + 1,
                "ok": hard["ok"], "errors": list(hard.get("errors") or []),
                "opinion": (hard.get("opinion") or "")[:200],
            })
            if not hard["ok"]:
                if i + 1 >= _PLAY_MAX:
                    review = {"ok": False, "opinion": hard.get("opinion") or ""}
                    break
                play = _call(
                    llm_fn,
                    build_play_retry_prompt(play, hard.get("opinion") or "这场戏还不像该发生的那一件。", book, seq=seq),
                    2048,
                )
                trail.append({"step": "play", "n": i + 2, "head": play[:200]})
                continue
            rev_raw = _call(llm_fn, build_review_prompt(play, book, seq=seq), 1024)
            review = parse_review(rev_raw)
            trail.append({
                "step": "review", "n": i + 1,
                "ok": review["ok"], "opinion": (review.get("opinion") or "")[:200],
            })
            if review["ok"]:
                break
            if i + 1 >= _PLAY_MAX:
                break
            play = _call(
                llm_fn,
                build_play_retry_prompt(
                    play,
                    review.get("opinion") or "这场戏还不像该发生的那一件。",
                    book,
                    seq=seq,
                ),
                2048,
            )
            trail.append({"step": "play", "n": i + 2, "head": play[:200]})
    else:
        review = {"ok": True, "opinion": ""}
        trail.append({"step": "resume", "n": 1, "head": play[:200]})

    if not review.get("ok"):
        return {
            "ok": False,
            "code": "play_rejected",
            "message": "这场戏还没过：" + (review.get("opinion") or "审戏认为不像该发生的那一件"),
            "play": play,
            "review": review,
            "trail": trail,
        }

    parsed: dict[str, Any] = {"ok": False}
    missing = ""
    for j in range(_EXTRACT_MAX):
        ext = _call(llm_fn, build_extract_prompt(play, book, missing=missing), 4096)
        parsed = parse_chapter_design_payload(ext, known_line_ids=known_line_ids)
        parsed["extract_raw"] = ext
        pc, pp = parse_clock_place_labels(ext)
        if pc:
            parsed["clock"] = pc
        if pp:
            parsed["place"] = pp
        trail.append({
            "step": "extract", "n": j + 1, "struct_ok": bool(parsed.get("ok")),
            "code": parsed.get("code") or "",
        })
        spine = parsed.get("chapter_spine") if isinstance(parsed.get("chapter_spine"), dict) else {}
        beats = parsed.get("beats") if isinstance(parsed.get("beats"), list) else []
        if parsed.get("ok") and parse_choice_ab(spine.get("choice")) and len(beats) >= 3:
            unground = table_ungrounded(play, parsed, book)
            if unground:
                missing = "这些行对不上这篇戏，只按戏重抄：\n" + "；".join(unground)
                trail.append({"step": "ungrounded", "n": j + 1, "missing": unground})
                continue
            parsed["synopsis"] = assemble_synopsis_from_spine(spine)
            return {
                "ok": True,
                "play": play,
                "review": review,
                "parsed": parsed,
                "extract_raw": ext,
                "trail": trail,
            }
        missing = extract_missing(parsed, play=play, book=book)
    unlike = table_same_play(play, parsed, book) if parsed else ["整张表"]
    return {
        "ok": False,
        "code": "extract_thin",
        "message": "戏过了，表还没从这篇戏里抄像" + ("：" + "；".join(unlike) if unlike else ""),
        "play": play,
        "review": review,
        "parsed": parsed,
        "beats_meta": {"play": (play or "")[:4000], "play_review_ok": True, "play_sha": play_sha(play or "")},
        "trail": trail,
    }
