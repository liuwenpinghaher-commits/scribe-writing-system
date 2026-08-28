"""设定库 thicken / batch。假 llm_fn，禁止 Surreal。"""
from __future__ import annotations

from scribe3.codex_generate import (
    DUTY_FIELD_MIN,
    PORTRAIT_EXTRACT_TRIES,
    PORTRAIT_FACT_CAP,
    _bible_for,
    apply_codex_persist_fields,
    build_codex_prompt,
    character_duty_issues,
    duty_fields_ready,
    facts_for_portrait,
    first_codex_slot,
    list_codex_thicken_targets,
    load_codex_row,
    merge_codex_slot,
    parse_codex_payload,
    persist_codex_row,
    portrait_grounded,
    portrait_stash_fields,
    thicken_codex,
    thicken_codex_batch,
    _apply_portrait_extract,
)
from scribe3.mcp._common import WRITE_GATED
from scribe3.write_commit import DEFAULT_WRITE_GATED


def _fat_term(_prompt, max_tokens=4096):
    body = (
        "是什么：炉前口头祭火契约。不是什么：不是朝廷文书。本书用法：当场应声。"
        "边界：不得隔夜另造。" + ("义" * 1200)
    )
    return '{"definition": "' + body + '"}'


def test_must_llm():
    import pytest
    with pytest.raises(ValueError, match="llm_fn"):
        thicken_codex("term", {"name": "炉令"}, llm_fn=None)


def test_thicken_term_fat():
    out = thicken_codex("term", {"name": "炉令"}, llm_fn=_fat_term)
    assert out["ok"] is True
    assert "是什么" in out["public_fields"]["definition"]
    assert out.get("bible_attached") is False


def test_thicken_term_thin_then_fail():
    out = thicken_codex("term", {"name": "炉令"}, llm_fn=lambda *a, **k: "短")
    assert out["ok"] is False
    assert out["code"] == "llm_thin"


def _fat_char_json(*, goal: str) -> str:
    import json
    return json.dumps({
        "personality_detail": "冷" * 400,
        "surface_goal": goal,
        "deep_need": "他要确认母亲还在自己的时间线上。" + ("需" * 160),
        "fear": "怕被标成样本后永远单向可见。" + ("惧" * 160),
        "internal_conflict": "救世界和救母亲不能同时成立。" + ("冲" * 160),
        "appearance": "青" * 80,
        "backstory": "史" * 240,
        "abilities": ["按回场核"],
        "weaknesses": ["体温会被世界认走"],
    }, ensure_ascii=False)


def test_thicken_character_portrait_then_extract():
    prompts: list[str] = []

    def llm(prompt, max_tokens=4096):
        prompts.append(prompt)
        if "不要填表" in prompt:
            return (
                "柳岸青要把场核碎片按回裂口，不交给守火人档案局提前开箱。"
                "他还要母亲还能自己走路离开观测名单，不被钉成档案条目。"
                "他会让世界开始认他的心跳，旁人从此付出单向可见的余生。"
                "他还让人付掉能证明他曾经不是样本的那一夜原始记录。"
            )
        return (
            "他要什么：柳岸青要把场核碎片按回裂口，不交给守火人档案局提前开箱。\n"
            "他还要什么：他还要母亲还能自己走路离开观测名单，不被钉成档案条目。\n"
            "他让人付出什么：他会让世界开始认他的心跳，旁人从此付出单向可见的余生。\n"
            "他还让人付出什么：他还让人付掉能证明他曾经不是样本的那一夜原始记录。"
        )

    out = thicken_codex("character", {"name": "柳岸青"}, llm_fn=llm)
    assert any("不要填表" in p for p in prompts)
    assert any("他要什么" in p for p in prompts)
    assert out.get("ok"), out
    fields = out.get("public_fields") or {}
    assert "按回" in str(fields.get("surface_goal") or "")
    assert fields.get("fear")


class _FactRow:
    def __init__(self, entity_id, attribute, value, valid_from, id=""):
        self.entity_id = entity_id
        self.attribute = attribute
        self.value = value
        self.valid_from = valid_from
        self.id = id or f"fact:{attribute}"


class _PortraitFactStore:
    def __init__(self, facts):
        self._facts = list(facts)
        self.terms = []

    def characters(self):
        return []

    def list_factions(self):
        return []

    def list_items(self):
        return []

    def list_world_rules(self):
        return []

    def list_motifs(self):
        return []

    def list_terms(self):
        return list(self.terms)

    def facts_unfolded_at(self, *_a, **_k):
        return list(self._facts)

    def facts_at(self, *_a, **_k):
        return list(self._facts)

    def entity_relations_at(self, *_a, **_k):
        return []


def test_portrait_bible_includes_own_facts_not_others():
    """写厚圣经必须带这个人自己的命题，含 隐瞒·；别人的一条都不能进。"""
    st = _PortraitFactStore([
        _FactRow("role:温贩婆", "亲情价", "把柳母余温写进价单", 13),
        _FactRow("role:温贩婆", "隐瞒·瞒抵押条款", "对role:柳母瞒：瞒抵押条款", 19),
        _FactRow("role:柳岸青", "扣温", "不该出现在温贩婆圣经里", 11),
    ])
    got = facts_for_portrait(st, "character", {"name": "温贩婆"})
    attrs = [f.attribute for f in got]
    assert "亲情价" in attrs
    assert "隐瞒·瞒抵押条款" in attrs
    assert "扣温" not in attrs
    bible = _bible_for(st, None, "character", {"name": "温贩婆"}, "", False)
    assert "【这个实体在书里已经发生的事】" in bible
    assert "把柳母余温写进价单" in bible
    assert "瞒抵押条款" in bible
    assert "不该出现在温贩婆圣经里" not in bible


def test_portrait_bible_zero_facts_has_no_block():
    """阳性对照：没有命题时不得假装有「已经发生的事」。"""
    empty = _bible_for(
        _PortraitFactStore([]), None, "character", {"name": "温贩婆"}, "", False)
    assert "【这个实体在书里已经发生的事】" not in empty
    filled = _bible_for(
        _PortraitFactStore([
            _FactRow("role:温贩婆", "亲情价", "把柳母余温写进价单", 13),
        ]),
        None, "character", {"name": "温贩婆"}, "", False)
    assert "【这个实体在书里已经发生的事】" in filled
    assert "把柳母余温写进价单" in filled


def test_portrait_facts_cap_and_chapter_order():
    facts = [
        _FactRow("role:温贩婆", f"a{i:02d}", f"v{i}", 40 - i)
        for i in range(20)
    ]
    got = facts_for_portrait(
        _PortraitFactStore(facts), "character", {"name": "温贩婆"})
    assert len(got) == PORTRAIT_FACT_CAP
    chapters = [f.valid_from for f in got]
    assert chapters == sorted(chapters)


def test_thicken_prompt_sees_own_facts():
    """短文提示必须看见这个人自己的命题。过不过闸是另一件事。"""
    prompts: list[str] = []

    def llm(prompt, max_tokens=4096):
        prompts.append(prompt)
        return "短"

    st = _PortraitFactStore([
        _FactRow("role:温贩婆", "亲情价", "把柳母余温写进价单", 13),
    ])
    thicken_codex("character", {"name": "温贩婆"}, llm_fn=llm, st=st)
    assert prompts, "写厚至少要调一次模型"
    assert any("把柳母余温写进价单" in p for p in prompts)


_PORTRAIT = (
    "温贩婆要把柳母余温写进价单，让亲情可抵成为入口条款。"
    "她还要把体温做成下一季能卖出去的余温金融账本条目。"
    "她让人付出抵押条款，价单交给温税吏收走还能再活的一年。"
    "她还让人付走能走回头路的那一年余温和全部亲情抵押权。"
)
_EXTRACT_OK = (
    "他要什么：温贩婆要把柳母余温写进价单，让亲情可抵成为入口条款。\n"
    "他还要什么：她还要把体温做成下一季能卖出去的余温金融账本条目。\n"
    "他让人付出什么：她让人付出抵押条款，价单交给温税吏收走还能再活的一年。\n"
    "他还让人付出什么：她还让人付走能走回头路的那一年余温和全部亲情抵押权。"
)


def test_portrait_extract_retries_then_ok():
    """第一次抽取改写了短文，第二次照抄才过。非 portrait 那条路有 4 轮，这条也要有。"""
    prompts: list[str] = []
    n = {"i": 0}

    def llm(prompt, max_tokens=4096):
        prompts.append(prompt)
        n["i"] += 1
        if "不要填表" in prompt:
            return _PORTRAIT
        if n["i"] == 2:
            return "他要什么：改写成别的\n他还要什么：也改了\n他让人付出什么：也改写了\n他还让人付出什么：还改"
        return _EXTRACT_OK

    out = thicken_codex("character", {"name": "温贩婆"}, llm_fn=llm)
    assert out.get("ok"), out
    assert n["i"] == 3
    assert any("缺「他要什么」" in p or "缺「他让人付出什么」" in p for p in prompts[1:])
    fields = out.get("public_fields") or {}
    assert "价单" in str(fields.get("surface_goal") or "")
    assert "温税吏" in str(fields.get("fear") or "")
    assert fields.get("deep_need") and fields.get("internal_conflict")


def test_portrait_extract_fail_stashes_short_text():
    written: list[dict] = []

    def llm(prompt, max_tokens=4096):
        if "不要填表" in prompt:
            return _PORTRAIT
        return "短"

    out = thicken_codex(
        "character", {"name": "温贩婆"}, llm_fn=llm,
        persist_fn=written.append,
    )
    assert out.get("ok") is False
    assert out.get("code") == "llm_thin"
    assert out.get("portrait_stashed") is True
    assert written and written[0].get("personality_detail") == _PORTRAIT
    assert out.get("stash_fields", {}).get("personality_detail") == _PORTRAIT


def test_portrait_extract_retries_four_times():
    n = {"extract": 0}

    def llm(prompt, max_tokens=4096):
        if "不要填表" in prompt:
            return _PORTRAIT
        n["extract"] += 1
        return "短"

    thicken_codex("character", {"name": "温贩婆"}, llm_fn=llm)
    assert n["extract"] == PORTRAIT_EXTRACT_TRIES


def test_extract_unlabeled_two_paragraphs():
    """缺陷一：无「他要什么」标签、两段原文也能抽出字段。"""
    raw = (
        "她要把柳母余温写进价单，让亲情可抵成为下一季还能卖的入口条款。\n\n"
        "她让人付出抵押条款，价单交给温税吏收走还能再活的一年余温。"
    )
    got = _apply_portrait_extract("character", {}, {}, raw)
    assert "余温" in got["surface_goal"]
    assert "抵押" in got["fear"]


def test_extract_unlabeled_two_sentences():
    raw = (
        "她要把柳母余温做成下一季还能卖出去的金融账本条目。"
        "她让人付亲情、抵押条款以及还能再活下去的一年余温。"
    )
    got = _apply_portrait_extract("character", {}, {}, raw)
    assert "余温" in got["surface_goal"]
    assert "亲情" in got["fear"]


def test_duty_fields_ready_rejects_five_char_goal():
    """改前非空即过。改后「他要体温。」过不了 25 字下限。"""
    thin = {
        "surface_goal": "他要体温。",
        "deep_need": "他要体温。",
        "fear": "他要体温。",
        "internal_conflict": "他要体温。",
    }
    assert duty_fields_ready("character", thin) is False
    assert "缺他要什么" in character_duty_issues(thin)
    assert DUTY_FIELD_MIN == 25


def test_extract_rejects_five_char_labeled_goal():
    """折光贩子铁证：短文有「他要体温。」，原样抄进槽会被 25 字下限拦住。"""
    raw = (
        "他要什么：他要体温。\n"
        "他还要什么：他要人相信不被看见是一笔可以折成体温的账，不是天赋。\n"
        "他让人付出什么：他会让人付出体温、余额和七息之后被重新锁定的风险。\n"
        "他还让人付出什么：他还会让人付出选择，自由按体温计价、保护按七息到期。"
    )
    got = _apply_portrait_extract("character", {}, {}, raw)
    assert not str(got.get("surface_goal") or "").startswith("他要体温")
    assert "折成体温" in got["deep_need"]
    assert DUTY_FIELD_MIN == 25


def test_extract_four_labeled_slots():
    """抽取必须能填四个槽，不能只写 surface_goal / fear。"""
    raw = (
        "他要什么：温贩婆要把柳母余温写进价单，让亲情可抵成为入口条款。\n"
        "他还要什么：她还要把体温做成下一季能卖出去的余温金融账本条目。\n"
        "他让人付出什么：她让人付出抵押条款，价单交给温税吏收走还能再活的一年。\n"
        "他还让人付出什么：她还让人付走能走回头路的那一年余温和全部亲情抵押权。"
    )
    got = _apply_portrait_extract("character", {}, {}, raw)
    assert duty_fields_ready("character", got)
    assert "价单" in got["surface_goal"]
    assert "账本" in got["deep_need"]
    assert "温税吏" in got["fear"]
    assert "抵押权" in got["internal_conflict"]


def test_duty_positive_control_grounded_pass_invented_fail():
    """合格样本必须放行；另编样本必须拦下。判据没有正样本就会把非空当过。"""
    portrait = _PORTRAIT
    ok = {
        "surface_goal": "温贩婆要把柳母余温写进价单，让亲情可抵成为入口条款。",
        "deep_need": "她还要把体温做成下一季能卖出去的余温金融账本条目。",
        "fear": "她让人付出抵押条款，价单交给温税吏收走还能再活的一年。",
        "internal_conflict": "她还让人付走能走回头路的那一年余温和全部亲情抵押权。",
    }
    assert duty_fields_ready("character", ok) is True
    assert portrait_grounded("character", ok, portrait) is True
    fake = {
        "surface_goal": "她要一统天下改写场核坐标锁回裂口，自己当观测主人。",
        "deep_need": "她要当牧场主把观测名单整本卖给天龙座去换令牌和牧场。",
        "fear": "她让人付亲情和抵押条款还要再付一整年的体温读数账。",
        "internal_conflict": "她还让人付走能走回头路的那一年余温和全部亲情抵押权。",
    }
    assert duty_fields_ready("character", fake) is True
    assert portrait_grounded("character", fake, portrait) is False


def test_portrait_grounded_nonadjacent_ok_invented_fail():
    """缺陷二：两句非相邻原话算 grounded；另编的不算。"""
    portrait = (
        "温贩婆要把余温金融化。中间夹着别的句子，跟抽取无关。"
        "她让人付亲情和抵押条款。"
    )
    ok = {
        "surface_goal": "温贩婆要把余温金融化",
        "fear": "她让人付亲情和抵押条款",
    }
    assert portrait_grounded("character", ok, portrait) is True
    fake = {
        "surface_goal": "她要一统天下改写场核",
        "fear": "她让人付亲情和抵押条款",
    }
    assert portrait_grounded("character", fake, portrait) is False


def test_reuse_stashed_portrait_skips_rewrite():
    prompts: list[str] = []

    def llm(prompt, max_tokens=4096):
        prompts.append(prompt)
        return _EXTRACT_OK

    src = {"name": "温贩婆", "personality_detail": _PORTRAIT * 4}
    out = thicken_codex("character", src, llm_fn=llm)
    assert out.get("ok"), out
    assert prompts, "应走抽取"
    assert all("不要填表" not in p for p in prompts)


def test_portrait_stash_skips_empty_and_keeps_existing():
    assert portrait_stash_fields("character", {"name": "温贩婆"}, "") == {}
    assert portrait_stash_fields(
        "character", {"name": "温贩婆", "personality_detail": "已有"}, _PORTRAIT,
    ) == {}
    filled = portrait_stash_fields("character", {"name": "温贩婆"}, _PORTRAIT)
    assert filled.get("personality_detail") == _PORTRAIT
    empty = portrait_stash_fields("character", {"name": "温贩婆"}, "")
    assert empty == {}
    assert filled != empty


def test_merge_codex_slot_keeps_other_fields():
    base = {"personality_detail": "钉住", "surface_goal": "旧", "fear": "旧怕"}
    got = merge_codex_slot(
        "character", base, {"surface_goal": "新要", "fear": "不该动"}, "surface_goal",
    )
    assert got["surface_goal"] == "新要"
    assert got["personality_detail"] == "钉住"
    assert got["fear"] == "旧怕"
    assert first_codex_slot(
        "character",
        [{"id": "pack"}, {"id": "surface_goal"}, {"id": "fear"}],
        base,
    ) == "surface_goal"


def test_batch_persist_is_write_gated():
    """persist=true 必须过审批，与单卡 s3_generate_codex 对齐。"""
    assert "s3_generate_codex" in WRITE_GATED
    assert "s3_generate_codex" in DEFAULT_WRITE_GATED
    assert "s3_generate_codex_batch" in WRITE_GATED
    assert "s3_generate_codex_batch" in DEFAULT_WRITE_GATED


class _BatchStore:
    def __init__(self):
        self.terms = [
            {"name": "炉令", "definition": ""},
            {"name": "隔夜禁忌", "definition": ""},
        ]
        self.written = []

    def characters(self):
        return []

    def list_factions(self):
        return []

    def list_items(self):
        return []

    def list_world_rules(self):
        return []

    def list_motifs(self):
        return []

    def facts_at(self, *_a, **_k):
        return []

    def entity_relations_at(self, *_a, **_k):
        return []

    def list_terms(self):
        return list(self.terms)

    def get_term(self, n):
        return next((t for t in self.terms if t["name"] == n), None)

    def patch_term(self, n, fields):
        self.written.append((n, dict(fields)))
        for t in self.terms:
            if t["name"] == n:
                t.update(fields)
        return True

    def add_term(self, n, **kw):
        self.written.append((n, kw))
        self.terms.append({"name": n, **kw})


def test_batch_persist_zero_ask():
    st = _BatchStore()
    out = thicken_codex_batch(st, llm_fn=_fat_term, persist=True, kinds=["term"])
    assert out["status"] == "ok"
    assert len(out["items"]) == 2
    assert all(i["persist"] == "written" for i in out["items"])
    assert len(st.written) == 2


def test_batch_one_thin_continues():
    n = {"i": 0}

    def llm(prompt, max_tokens=4096):
        n["i"] += 1
        if n["i"] <= 2 and "炉令" in prompt:
            return "短"
        return _fat_term(prompt)

    st = _BatchStore()
    out = thicken_codex_batch(st, llm_fn=llm, persist=True, kinds=["term"])
    statuses = {i["name"]: i["status"] for i in out["items"]}
    assert statuses.get("隔夜禁忌") == "ok" or any(i["persist"] == "written" for i in out["items"])


def test_no_bible_without_store():
    prompt = build_codex_prompt("term", {"name": "炉令"})
    assert "本书设定圣经" not in prompt


def test_character_public_excludes_secret_agenda_bag():
    def llm(prompt, max_tokens=4096):
        return (
            '{"personality_detail":"' + ("慎" * 220) + '",'
            '"surface_goal":"' + ("要" * 90) + '",'
            '"deep_need":"' + ("需" * 90) + '",'
            '"fear":"' + ("惧" * 90) + '",'
            '"internal_conflict":"' + ("撕" * 90) + '",'
            '"appearance":"' + ("貌" * 200) + '",'
            '"backstory":"' + ("史" * 420) + '",'
            '"abilities":["辨潮"],"weaknesses":["不求助"],'
            '"secret_agenda":"不该出现"}'
        )
    out = thicken_codex("character", {"name": "灰七"}, llm_fn=llm)
    assert out["ok"] is True
    assert "secret_agenda" not in (out.get("public_fields") or {})


def _fat_def():
    return (
        "是什么：炉前口头祭火契约。不是什么：不是朝廷文书。"
        "本书用法：当场应声。边界：不得隔夜另造。" + ("义" * 1200)
    )


def test_skip_when_store_ready_name_only():
    calls = {"n": 0}

    def llm(*_a, **_k):
        calls["n"] += 1
        return _fat_term(*_a, **_k)

    st = _BatchStore()
    st.terms = [{"name": "炉令", "definition": _fat_def()}]
    out = thicken_codex("term", {"name": "炉令"}, llm_fn=llm, st=st)
    assert out.get("skipped") is True
    assert calls["n"] == 0
    assert load_codex_row(st, "term", "炉令")["definition"] == _fat_def()


def test_force_rewrites_ready_row():
    calls = {"n": 0}

    def llm(*_a, **_k):
        calls["n"] += 1
        return _fat_term(*_a, **_k)

    st = _BatchStore()
    st.terms = [{"name": "炉令", "definition": _fat_def()}]
    out = thicken_codex("term", {"name": "炉令"}, llm_fn=llm, st=st, force=True)
    assert out.get("ok") is True
    assert not out.get("skipped")
    assert calls["n"] >= 1


def test_apply_secret_flags():
    fields = apply_codex_persist_fields(
        "character",
        {"personality_detail": "慎" * 40},
        {"backstory": "暗史" * 20},
        {},
    )
    assert fields["backstory"] == "暗史" * 20
    assert fields["backstory_secret"] is True
    assert "secret_agenda" not in fields


def test_apply_chief_only_not_public():
    fields = apply_codex_persist_fields(
        "faction",
        {"ideology": "甲" * 40, "secret_agenda": "不该公开"},
        {},
        {"secret_agenda": "隐秘议程正文"},
    )
    assert fields["secret_agenda"] == "隐秘议程正文"
    assert fields.get("secret_agenda_secret") is True


def test_catalog_codex_duty():
    from scribe3.orchestration.catalog import CATALOG
    domains = {e["domain"]: e for e in CATALOG}
    for d, needle in (
        ("codex.character", "s3_generate_codex"),
        ("codex.faction", "s3_generate_codex"),
        ("codex.item", "s3_generate_codex"),
        ("codex.term", "s3_generate_codex"),
        ("codex.world_rule", "s3_generate_codex"),
        ("codex.lifecycle", "s3_generate_codex_batch"),
        ("motif.manage", "s3_generate_codex"),
        ("voice.manage", "s3_generate_codex"),
    ):
        duty = domains[d].get("instruction_duty") or ""
        assert needle in duty, d


def test_parse_term_unstructured_does_not_inject_slogans():
    blob = "炉令是口头祭火契约。" + ("义" * 1200)
    fields = parse_codex_payload("term", blob)
    d = fields["definition"]
    assert d.startswith("炉令是口头祭火契约。")
    assert "不是其它书的同名物" not in d
    assert "正文按此义使用" not in d
    from scribe3.iceberg import persist_codex_fields_blocked
    blocked = persist_codex_fields_blocked("term", fields, mode="pack")
    assert blocked is not None
    ids = {m["id"] for m in blocked["missing"]}
    assert any(i.startswith("part:") for i in ids)


def test_parse_term_nested_definition_object():
    raw = (
        '{"definition":{"是什么":"' + ("甲" * 80) +
        '","不是什么":"' + ("乙" * 80) +
        '","本书用法":"' + ("丙" * 80) +
        '","边界":"' + ("丁" * 80) + '"}}'
    )
    fields = parse_codex_payload("term", raw)
    d = fields["definition"]
    assert isinstance(d, str)
    for h in ("是什么", "不是什么", "本书用法", "边界"):
        assert h in d


def test_persist_motif_adds_when_missing():
    class _MotifStore:
        def __init__(self):
            self.added = []

        def get_motif(self, _n):
            return None

        def list_motifs(self):
            return []

        def add_motif(self, name, theme="", echoes="", unfolding="", echo_terms=None,
                      phase="seed", tier="book", scope=None):
            self.added.append({"name": name, "theme": theme, "unfolding": unfolding})

    st = _MotifStore()
    ok = persist_codex_row(st, "motif", "回声", {"theme": "潮" * 40, "unfolding": "展" * 80,
                                               "echo_terms": ["潮", "炉", "债"]})
    assert ok is True
    assert st.added and st.added[0]["name"] == "回声"


def test_batch_scans_voice():
    class _VoiceStore(_BatchStore):
        def list_voice_profiles(self):
            return [{"character_id": "role:灰七", "style_summary": ""}]

    st = _VoiceStore()
    listed = list_codex_thicken_targets(st, kinds=["voice"])
    assert any(t["name"] == "role:灰七" for t in listed["queued"])
