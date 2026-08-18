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
    if extra and "force=1" not in extra.lower():
        clean = extra.replace("force=1", "").strip()
        if clean:
            bits.append(clean)
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
        "「选择」写他还没选时的两难，两头都要付出，中间用「还是」。",
        "「决断」写他选了哪边。",
        "冒号后面只写戏里有的句子。",
    ]
    if missing:
        bits.append("上一轮这些还没从戏里抽清，只补这些，别的按戏原样：\n" + missing)
    else:
        bits.append(
            "需要从戏里抄出的行名：时空、在场、咬上章、本章要、挡、触发、升级、"
            "选择、决断、代价、信息差、动哪条线、钩、禁令、时长、增量、地点、地点增量、世界事实。"
            "再拆三场上台的压力，拍头写成 ## 拍1 / ## 拍2 / ## 拍3，每场要/挡/变/付/选。"
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


def extract_missing(parsed: Mapping[str, Any] | None) -> str:
    if not parsed or not parsed.get("ok"):
        return "【章】和三场还没抽全。从戏里把在场、本章要、选择、决断、代价、三场抄出来。"
    bits = []
    spine = parsed.get("chapter_spine") if isinstance(parsed.get("chapter_spine"), dict) else {}
    from scribe3.chapter_spine import slot_text, parse_choice_ab
    if not parse_choice_ab(spine.get("choice")):
        bits.append("选择：戏里他还没选时的两难")
    if not slot_text(spine.get("decision")):
        bits.append("决断：他选了哪边")
    if not slot_text(spine.get("cost")):
        bits.append("代价：世界因此怎么变")
    beats = parsed.get("beats") if isinstance(parsed.get("beats"), list) else []
    if len(beats) < 3:
        bits.append("三场上台的压力")
    clock = parsed.get("clock") if isinstance(parsed.get("clock"), dict) else {}
    place = parsed.get("place") if isinstance(parsed.get("place"), dict) else {}
    if not str((clock or {}).get("span") or "").strip():
        bits.append("时长：这一场多重")
    if not str((place or {}).get("name") or "").strip():
        bits.append("地点：人还在哪")
    return "；".join(bits)


def table_ungrounded(play: str, parsed: Mapping[str, Any] | None, book) -> list[str]:
    """表上有、戏里对不上的行名。"""
    from scribe3.chapter_spine import slot_text
    from scribe3.clue_density import _distinctive_overlap, invented_cast_names

    if not parsed:
        return ["整张表"]
    spine = parsed.get("chapter_spine") if isinstance(parsed.get("chapter_spine"), dict) else {}
    hits: list[str] = []
    for key, label in _TABLE_KEYS:
        val = slot_text(spine.get(key))
        if not val:
            continue
        if not _distinctive_overlap(play or "", val, book):
            hits.append(label)
    names = set(getattr(book, "character_names", None) or []) if book is not None else set()
    if names:
        invented = invented_cast_names(slot_text(spine.get("cast")), book)
        if invented:
            hits.append("在场（戏里多了个没立档的人）")
    return hits


def persist_play_design_blocked(
    fields: Mapping[str, Any] | None,
    *,
    book=None,
    store=None,
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """主编戏过之后：只拦半稿、无户口、编人、换地没说清。"""
    del existing
    from scribe3.chapter_spine import is_v1, slot_text
    from scribe3.clue_density import invented_cast_names, same_landmark

    if store is not None and book is None:
        return {
            "code": "iceberg_thin_persist",
            "message": "有书却没带上户口，禁止只考表格",
            "missing": [{"id": "design_book_missing", "detail": "store_without_book"}],
        }
    src = dict(fields or {})
    spine = src.get("chapter_spine")
    beats = src.get("beats")
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
    return None


def load_working_paper(st, seq: int | None) -> dict[str, Any] | None:
    if st is None or not seq or not hasattr(st, "list_design_attempts"):
        return None
    try:
        rows = st.list_design_attempts(int(seq), limit=20) or []
    except Exception:
        return None
    for row in reversed(rows):
        if str((row or {}).get("play") or "").strip():
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
    bounced = False
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
        if parsed.get("ok") and not parse_choice_ab(spine.get("choice")):
            if not play_has_dilemma(play) and not bounced:
                bounced = True
                play = _call(
                    llm_fn,
                    build_play_retry_prompt(
                        play, "他还没选时两头各要付出什么，你没写出来。", book, seq=seq,
                    ),
                    2048,
                )
                trail.append({"step": "play", "n": "bounce", "head": play[:200]})
                hard = evaluate_play(play, book, seq=seq)
                if not hard["ok"]:
                    return {
                        "ok": False,
                        "code": "play_rejected",
                        "message": "这场戏还没过：" + (hard.get("opinion") or ""),
                        "play": play,
                        "review": {"ok": False, "opinion": hard.get("opinion") or ""},
                        "trail": trail,
                    }
                review = {"ok": True, "opinion": ""}
                missing = ""
                continue
            missing = extract_missing(parsed)
            continue
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
        missing = extract_missing(parsed)
    return {
        "ok": False,
        "code": "extract_thin",
        "message": "戏过了，表还没从这篇戏里拆清",
        "play": play,
        "review": review,
        "parsed": parsed,
        "trail": trail,
    }
