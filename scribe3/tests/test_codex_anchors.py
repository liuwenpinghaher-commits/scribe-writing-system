"""主角色弧光锚生成。假 llm_fn，禁止 Surreal。写入必须走 set_char_anchors。"""
from __future__ import annotations

from pathlib import Path


class _Fact:
    def __init__(self, entity_id, attribute, value, valid_from, id=""):
        self.entity_id = entity_id
        self.attribute = attribute
        self.value = value
        self.valid_from = valid_from
        self.id = id or f"fact:{attribute}"


class _Char:
    def __init__(self, name, importance, **traits):
        self.name = name
        self.id = f"role:{name}"
        self.traits = {"importance": importance, **traits}


class _Store:
    def __init__(self, chars, facts, anchors=None):
        self._chars = list(chars)
        self._facts = list(facts)
        self.anchors = {c.id: dict((anchors or {}).get(c.id) or {}) for c in chars}
        self.writes: list[tuple[str, dict]] = []

    def characters(self):
        return list(self._chars)

    def char_anchors(self, cid):
        return dict(self.anchors.get(cid) or {})

    def set_char_anchors(self, cid, anchors):
        self.writes.append((cid, dict(anchors)))
        self.anchors.setdefault(cid, {}).update(anchors)

    def facts_unfolded_at(self, *_a, **_k):
        return list(self._facts)

    def facts_at(self, *_a, **_k):
        return list(self._facts)


_FACT_SHEN = _Fact(
    "role:沈烛", "护监",
    "沈烛用金縢半封挡住开箱，同时承认保护等于监禁",
    40,
)
_LIE_GROUNDED = "金縢半封挡住开箱，保护等于监禁"
_LIE_GENERIC = "人活着就是为了被爱，付出总会有回报。"


def _json_lie(lie: str) -> str:
    return (
        '{"ghost":"那一夜的封条","lie":"' + lie +
        '","truth":"保护就是监禁","want":"差一步开箱",'
        '"need":"承认半封是锁","arc_type":"disillusionment"}'
    )


def test_skip_when_lie_already_set():
    from scribe3.codex_anchors import generate_char_anchors

    st = _Store(
        [_Char("沈烛", "major")],
        [_FACT_SHEN],
        anchors={"role:沈烛": {"lie": "旧错误信念已经写过"}},
    )
    calls = []

    def llm(prompt, max_tokens=1024):
        calls.append(prompt)
        return _json_lie(_LIE_GROUNDED)

    out = generate_char_anchors(
        st, {"name": "沈烛", "id": "role:沈烛", "importance": "major"},
        llm_fn=llm, persist=True,
    )
    assert out.get("skipped") is True
    assert calls == []
    assert st.writes == []


def test_skip_non_main_cast():
    from scribe3.codex_anchors import generate_missing_main_anchors

    st = _Store([_Char("温贩婆", "minor")], [_FACT_SHEN])
    calls = []

    def llm(prompt, max_tokens=1024):
        calls.append(prompt)
        return _json_lie(_LIE_GROUNDED)

    out = generate_missing_main_anchors(st, llm_fn=llm, persist=True)
    assert calls == []
    assert st.writes == []
    assert not (out.get("items") or [])


def test_no_facts_does_not_write():
    from scribe3.codex_anchors import generate_char_anchors

    st = _Store([_Char("沈烛", "major")], [])
    calls = []

    def llm(prompt, max_tokens=1024):
        calls.append(prompt)
        return _json_lie(_LIE_GROUNDED)

    out = generate_char_anchors(
        st, {"name": "沈烛", "id": "role:沈烛", "importance": "major"},
        llm_fn=llm, persist=True,
    )
    assert out.get("ok") is False
    assert out.get("code") == "no_facts"
    assert calls == []
    assert st.writes == []


def test_reject_generic_lie_not_in_own_facts():
    from scribe3.codex_anchors import generate_char_anchors

    st = _Store([_Char("沈烛", "major")], [_FACT_SHEN])

    def llm(prompt, max_tokens=1024):
        return _json_lie(_LIE_GENERIC)

    out = generate_char_anchors(
        st, {"name": "沈烛", "id": "role:沈烛", "importance": "major"},
        llm_fn=llm, persist=True,
    )
    assert out.get("ok") is False
    assert out.get("code") == "ungrounded"
    assert st.writes == []


def test_persist_grounded_lie_via_set_char_anchors():
    from scribe3.codex_anchors import generate_char_anchors

    st = _Store([_Char("沈烛", "major")], [_FACT_SHEN])

    def llm(prompt, max_tokens=1024):
        assert "金縢半封" in prompt
        assert "保护等于监禁" in prompt
        assert "沈烛" in prompt
        return _json_lie(_LIE_GROUNDED)

    out = generate_char_anchors(
        st, {"name": "沈烛", "id": "role:沈烛", "importance": "major"},
        llm_fn=llm, persist=True,
    )
    assert out.get("ok") is True, out
    assert st.writes, "必须调用 set_char_anchors，不许另开旁路"
    cid, anchors = st.writes[0]
    assert cid == "role:沈烛"
    assert anchors.get("lie") == _LIE_GROUNDED
    assert st.char_anchors("role:沈烛").get("lie") == _LIE_GROUNDED


def test_prompt_does_not_include_other_character_facts():
    from scribe3.codex_anchors import generate_char_anchors

    other = _Fact("role:柳岸青", "扣温", "不该出现在沈烛提示里", 11)
    st = _Store([_Char("沈烛", "major")], [_FACT_SHEN, other])
    prompts = []

    def llm(prompt, max_tokens=1024):
        prompts.append(prompt)
        return _json_lie(_LIE_GROUNDED)

    generate_char_anchors(
        st, {"name": "沈烛", "id": "role:沈烛", "importance": "major"},
        llm_fn=llm, persist=True,
    )
    assert prompts
    assert "不该出现在沈烛提示里" not in prompts[0]
    assert "金縢半封" in prompts[0]


def test_missing_main_only_fills_those_without_lie():
    from scribe3.codex_anchors import generate_missing_main_anchors

    st = _Store(
        [_Char("沈烛", "major"), _Char("兰因", "major"), _Char("温贩婆", "minor")],
        [
            _FACT_SHEN,
            _Fact("role:兰因", "锚枷", "相位锚焊在北峰伤兵左肩取不下来", 25),
        ],
        anchors={"role:沈烛": {"lie": "已经有了"}},
    )

    def llm(prompt, max_tokens=1024):
        if "兰因" in prompt:
            return (
                '{"ghost":"焊错了肩","lie":"相位锚焊在北峰伤兵左肩取不下来",'
                '"truth":"名额是枷","want":"活着回来","need":"拆锚",'
                '"arc_type":"disillusionment"}'
            )
        return _json_lie(_LIE_GROUNDED)

    out = generate_missing_main_anchors(st, llm_fn=llm, persist=True)
    names = [i.get("name") for i in (out.get("items") or [])]
    assert "兰因" in names
    assert "沈烛" not in names
    assert "温贩婆" not in names
    written_ids = [cid for cid, _ in st.writes]
    assert written_ids == ["role:兰因"]
    assert "相位锚" in (st.char_anchors("role:兰因").get("lie") or "")


def test_expand_volume_thicken_fills_main_cast_anchors():
    """铺章卷末写厚必须走弧光锚生成，写入 set_char_anchors。"""
    from scribe3.tools.expand_wanjie_chapters import thicken_named_entities

    st = _Store([_Char("沈烛", "major")], [_FACT_SHEN])

    def llm(prompt, max_tokens=4096):
        if "错误信念" in prompt or '"lie"' in prompt or "lie" in prompt:
            return _json_lie(_LIE_GROUNDED)
        return "短"

    out = thicken_named_entities(st, {"charter": {}}, llm_fn=llm, persist=True)
    assert st.writes, out
    assert st.writes[0][0] == "role:沈烛"
    assert st.writes[0][1].get("lie") == _LIE_GROUNDED
    assert (out.get("anchors") or {}).get("items")


def test_pipeline_source_calls_set_char_anchors_not_new_bypass():
    gen = Path(__file__).resolve().parents[1] / "codex_anchors.py"
    expand = Path(__file__).resolve().parents[1] / "tools" / "expand_wanjie_chapters.py"
    text = gen.read_text(encoding="utf-8")
    assert "set_char_anchors" in text
    assert "_execute_write" not in text
    assert "_query" not in text
    assert "generate_missing_main_anchors" in expand.read_text(encoding="utf-8")
