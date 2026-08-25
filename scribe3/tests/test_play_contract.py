"""Play-contract goldens: quote, struct, freeze, stages, force/rewrite.

Drives shipped playbook functions. No Surreal, no live LLM except injected stubs.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scribe3.playbook.assemble import assemble_final_prompt
from scribe3.playbook.context import make_duty, prev_play_with_hook
from scribe3.playbook.errors import FrozenAssetError
from scribe3.playbook.memory_store import MemoryPlaybookStore, freeze_artifact, overwrite_play
from scribe3.playbook.pipeline import run_stage
from scribe3.playbook.quote import _norm, quote_in_play
from scribe3.playbook.stages import LIVE_STAGES, reject_gone_stage
from scribe3.playbook.structural import check_contract_struct, check_deduce_struct, check_duty_struct

GOLDEN = Path(__file__).resolve().parent / "judge_golden"

PLAY = "交出去，娘就有一线生机；自己按回去，赌的是这条命。沈烛若合上五指。"


def test_quote_must_be_verbatim():
    assert quote_in_play("交出去，娘就有一线生机", PLAY) is True
    assert quote_in_play("交出碎片换母亲生机", PLAY) is False


def test_quote_slice_rejects_prefix_trim_and_punct_swap():
    from scribe3.playbook.quote import quote_is_slice
    play = "我希望你今晚睡着的时候，别再把碳条压在膝盖底下。"
    assert quote_is_slice("我希望你今晚睡着的时候", play) is True
    assert quote_is_slice("你今晚睡着的时候", play) is False
    play2 = "一条路，留下数字，另一条路撕掉贴条。"
    assert quote_is_slice("一条路。留下数字", play2) is False
    hit = check_contract_struct(
        {
            "fields": {
                "goal": {"text": "睡", "quote": "你今晚睡着的时候"},
                "choice": {
                    "text": "两难", "quote": "我希望你今晚睡着的时候",
                    "side_a": {"text": "a", "quote": "我希望你今晚睡着的时候"},
                    "side_b": {"text": "b", "quote": "别再把碳条压在膝盖底下"},
                },
                "decision": {"text": "走", "quote": "你今晚睡着的时候"},
                "hook": {"text": "钩", "quote": "我希望你今晚睡着的时候"},
            },
            "beats": [
                {"n": 1, "goal": {"text": "g", "quote": "我希望你今晚睡着的时候"}, "turn": {"text": "t", "quote": "别再把碳条压在膝盖底下"}, "stages_choice": True, "conflict": {"text": "c", "quote": "我希望你今晚睡着的时候"}},
                {"n": 2, "goal": {"text": "g", "quote": "我希望你今晚睡着的时候"}, "turn": {"text": "t", "quote": "别再把碳条压在膝盖底下"}},
                {"n": 3, "goal": {"text": "g", "quote": "我希望你今晚睡着的时候"}, "turn": {"text": "t", "quote": "别再把碳条压在膝盖底下"}},
            ],
        },
        play,
    )
    assert hit["ok"] is False
    assert hit["code"] in ("quote_edited", "quote_not_in_play")


def test_norm_strips_punct_and_space_only():
    assert _norm("交 出 去，娘就有一线生机。") == _norm("交出去娘就有一线生机")
    assert quote_in_play("交出去，娘就有一线生机", "交出去娘就有一线生机") is True
    assert quote_in_play("交出去娘就有一线生机啊", PLAY) is False


def test_duty_who_must_be_in_cast():
    duty = make_duty(seq=1, who=["沈烛若", "不存在的人"], available_cast=["沈烛若"])
    hit = check_duty_struct(duty, available_cast=["沈烛若"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_who_cast"


def test_deduce_struct_asks_undercurrent_not_ore_count():
    hit = check_deduce_struct({
        "scene_truth": "沈烛要的是他亲手按下去那份证据。",
        "characters": [
            {"id": "柳岸青", "believed": "付一只手就能完", "blind": "裂口拿他当管子"},
        ],
        "ore": [],
    })
    assert hit["ok"] is True
    empty = check_deduce_struct({
        "scene_truth": "发生了一些事。",
        "characters": [{"id": "柳岸青", "perceived": "看见裂口", "known": "要按"}],
    })
    assert empty["ok"] is False
    assert empty["code"] == "no_undercurrent"


def test_duty_line_must_be_known():
    duty = make_duty(seq=1, line_to_touch="ghost")
    hit = check_duty_struct(duty, available_cast=["沈烛若"], available_lines=[{"id": "p7"}])
    assert hit["ok"] is False
    assert hit["code"] == "duty_line"


def test_bite_is_prev_hook_verbatim():
    prev_hook_quote = "门外的呼吸声停了半拍"
    duty = make_duty(prev_play_with_hook(prev_hook_quote))
    assert duty["bite_from_prev"] == prev_hook_quote
    hit = check_duty_struct(
        duty, available_cast=["沈烛若"], prev_hook_quote=prev_hook_quote,
    )
    assert hit["ok"] is True


def test_ch1_bite_is_null():
    duty = make_duty(prev_play_with_hook("不该出现"), seq=1)
    assert duty["bite_from_prev"] is None


def test_available_cast_reads_entity_name():
    from scribe3.ontology import Entity
    from scribe3.playbook.context import available_cast

    class _St:
        def characters(self):
            return [Entity("role:柳岸青", "character", "柳岸青")]

    assert available_cast(_St()) == ["柳岸青"]


def test_secret_list_from_red_lines():
    from scribe3.playbook.context import secret_list

    class _St:
        def get_intent(self):
            return {"red_lines": "不让柳岸青看见场核坐标\n不提前拆穿炉认主"}

    secrets = secret_list(_St())
    assert any("场核坐标" in x for x in secrets)
    assert any("炉认主" in x for x in secrets)


def test_gen_duty_fills_forbid_from_secret_list():
    from scribe3.playbook.layers import gen_duty

    ctx = {
        "seq": 1,
        "focalizer": "role:柳岸青",
        "available_cast": ["柳岸青"],
        "available_lines": [],
        "secret_list": ["柳岸青看不见场核坐标", "炉认主的真名"],
        "prev_hook_quote": None,
    }

    def llm_fn(prompt, **kwargs):
        return '{"must_happen": "按回碎片", "bill": "体温", "who": ["柳岸青"], "forbidden_reveal": [], "line_to_touch": null}'

    raw = gen_duty(ctx, llm_fn)
    assert raw["forbidden_reveal"]
    assert "场核坐标" in "".join(raw["forbidden_reveal"])


def test_frozen_play_cannot_be_overwritten():
    store = MemoryPlaybookStore()
    play = freeze_artifact(
        store, "chapter_play", 1, {"seq": 1, "text": PLAY}, schema="chapter_play.v1",
    )
    with pytest.raises(FrozenAssetError):
        overwrite_play(store, play["sha"], "new text")


def test_same_sha_freeze_is_noop():
    store = MemoryPlaybookStore()
    a = freeze_artifact(store, "chapter_play", 1, {"seq": 1, "text": PLAY}, schema="chapter_play.v1")
    b = freeze_artifact(store, "chapter_play", 1, {"seq": 1, "text": PLAY}, schema="chapter_play.v1")
    assert a["sha"] == b["sha"]
    assert a["version"] == b["version"]
    assert len(store.list_versions("chapter_play", 1)) == 1


def _sample_contract(play: str) -> dict:
    return {
        "play_sha": "x",
        "fields": {
            "goal": {"text": "弄明白体温", "quote": "交出去，娘就有一线生机"},
            "choice": {
                "text": "交还是按",
                "quote": "交出去，娘就有一线生机；自己按回去，赌的是这条命",
                "side_a": {"text": "交", "quote": "交出去，娘就有一线生机"},
                "side_b": {"text": "按", "quote": "自己按回去，赌的是这条命"},
            },
            "decision": {"text": "按回", "quote": "沈烛若合上五指"},
            "hook": {"text": "没做完", "quote": "沈烛若合上五指"},
        },
        "beats": [
            {"n": 1, "goal": {"text": "g", "quote": "交出去，娘就有一线生机"},
             "turn": {"text": "t", "quote": "交出去，娘就有一线生机"}, "stages_choice": False},
            {"n": 2, "goal": {"text": "g", "quote": "自己按回去，赌的是这条命"},
             "turn": {"text": "t", "quote": "沈烛若合上五指"}, "stages_choice": True},
            {"n": 3, "goal": {"text": "g", "quote": "沈烛若合上五指"},
             "turn": {"text": "t", "quote": "沈烛若合上五指"}, "stages_choice": False},
        ],
    }


def test_contract_missing_core_quote_fails():
    c = _sample_contract(PLAY)
    c["fields"]["hook"] = {"text": "编的钩", "quote": "这句戏里根本没有"}
    hit = check_contract_struct(c, PLAY)
    assert hit["ok"] is False
    assert hit["code"] == "quote_not_in_play"
    assert hit["field"] == "hook"


def test_stages_choice_must_be_one():
    c = _sample_contract(PLAY)
    c["beats"][0]["stages_choice"] = True
    hit = check_contract_struct(c, PLAY)
    assert hit["ok"] is False
    assert hit["code"] == "stages_choice"


def test_good_contract_passes():
    assert check_contract_struct(_sample_contract(PLAY), PLAY)["ok"] is True


def _duty_ctx(**extra):
    ctx = {
        "seq": 1,
        "focalizer": "沈烛若",
        "available_cast": ["沈烛若"],
        "available_lines": [],
        "prev_hook_quote": None,
        "synopsis": "井台上还在排队。沈烛若必须决定按不按回碎片。",
    }
    ctx.update(extra)
    return ctx


def _pass_llm(kind_text: dict[str, str]):
    def llm_fn(prompt, max_tokens=2048, system="", temperature=0.8):
        if "你是审稿的" in prompt or "五问" in prompt or "两问" in prompt or "六问" in prompt or "七问" in prompt or "四问" in prompt or "八问" in prompt or "三问" in prompt or "九问" in prompt or "十一问" in prompt or "十二问" in prompt:
            return json.dumps({
                "answers": [{"q": 1, "evidence": "沈烛若合上五指", "answer": "yes", "reason": "过"}],
                "verdict": "pass",
                "opinion": "",
            }, ensure_ascii=False)
        if "立\"责任\"" in prompt or "立四件事" in prompt or "立五件事" in prompt or "立六件事" in prompt or "立八件事" in prompt:
            return json.dumps({
                "day": "井台上还在排队打水",
                "said": "认自家攒的油",
                "needed": "灯盏是空的",
                "must_happen": "沈烛若把碎片按回胸口",
                "bill": "四十二度成了他的常态",
                "who": ["沈烛若"],
                "forbidden_reveal": ["炉认主"],
                "line_to_touch": None,
            }, ensure_ascii=False)
        if "只抄不编" in prompt and "open_loops" in prompt:
            return json.dumps({
                "seq": 1,
                "characters": [{"name": "沈烛若", "gender": "男", "state": "按回碎片", "quote": "场面。场面。场面。"}],
                "objects": [{"name": "碎片", "location": "胸口", "state": "按回", "quote": "场面。场面。场面。"}],
                "open_loops": [],
                "timeline": {"at": "当夜", "elapsed_from_prev": ""},
                "imagery": ["掌心"],
            }, ensure_ascii=False)
        if "你要从戏里抄出契约" in prompt:
            return json.dumps(_sample_contract(PLAY), ensure_ascii=False)
        if "写演绎" in prompt or "写水面下" in prompt:
            return json.dumps({
                "scene_truth": "他按回碎片，账当场付了。" * 20,
                "characters": [{
                    "id": "沈烛若",
                    "perceived": "掌心发烫",
                    "known": "碎片在手里",
                    "believed": "交出去娘能活",
                    "acted": "合上五指",
                    "blind": "门外有人",
                }],
                "ore": ["掌心发烫", "药面热气", "门外呼吸"],
            }, ensure_ascii=False)
        if "打磨成正文" in prompt:
            return ("「按回去。」沈烛说。\n正文正文正文正文。\n" * 120)
        if "写一遍糙稿" in prompt:
            return ("「按回去。」沈烛说。\n场面场面场面场面场面场面。\n" * 120)
        return PLAY * 8
    return llm_fn


def test_force_later_layer_leaves_play_sha():
    store = MemoryPlaybookStore()
    llm = _pass_llm({})
    ctx = _duty_ctx(forbidden_reveal=["炉认主"])
    d = run_stage(store, 1, "duty", llm_fn=llm, ctx=ctx)
    assert d["ok"] is True
    design = run_stage(store, 1, "design", llm_fn=llm, ctx={**ctx, "duty": d["artifact"]})
    assert design["ok"] is True
    play_sha = design["sha"]
    run_stage(store, 1, "deduce", llm_fn=llm, ctx=ctx)
    again = run_stage(store, 1, "deduce", extra="force=1", llm_fn=llm, ctx=ctx)
    assert again["ok"] is True
    assert again["sha"] == play_sha
    assert store.get_frozen("chapter_play", 1)["sha"] == play_sha


def test_rewrite_design_supersedes_play_and_downstream():
    store = MemoryPlaybookStore()
    llm = _pass_llm({})
    ctx = _duty_ctx()
    d = run_stage(store, 1, "duty", llm_fn=llm, ctx=ctx)
    design = run_stage(store, 1, "design", llm_fn=llm, ctx={**ctx, "duty": d["artifact"]})
    old_sha = design["sha"]
    run_stage(store, 1, "deduce", llm_fn=llm, ctx=ctx)
    rewritten = run_stage(store, 1, "design", extra="rewrite=1", llm_fn=llm, ctx={**ctx, "duty": d["artifact"]})
    assert rewritten["ok"] is True
    old = store.get_by_sha("chapter_play", old_sha)
    assert old["status"] == "superseded"
    deduce_rows = store.list_versions("chapter_deduce", 1)
    assert any(r.get("status") == "superseded" for r in deduce_rows)
    assert store.get_frozen("chapter_play", 1)["version"] >= 2


def test_rewrite_rejected_on_deduce():
    store = MemoryPlaybookStore()
    out = run_stage(store, 1, "deduce", extra="rewrite=1", llm_fn=lambda *a, **k: "{}")
    assert out["ok"] is False
    assert out["code"] == "rewrite_not_allowed"


def test_old_stages_are_410():
    for name in ("outline", "beats", "chapter_design"):
        hit = reject_gone_stage(name)
        assert hit is not None
        assert hit["http"] == 410
        assert "duty" in hit["message"]
    for name in LIVE_STAGES:
        assert reject_gone_stage(name) is None


def test_generate_stage_surface_uses_shipped_reject():
    from scribe3.playbook.pipeline import run_stage as shipped
    store = MemoryPlaybookStore()
    out = shipped(store, 1, "outline", llm_fn=lambda *a, **k: "x")
    assert out.get("http") == 410
    assert out.get("code") == "stage_gone"


def test_write_assemble_v1_has_no_craft_call():
    src = Path(__file__).resolve().parents[1] / "api" / "services" / "write_assemble_v1.py"
    text = src.read_text(encoding="utf-8")
    assert "build_craft_block(" not in text
    assert "PALETTE" not in text


def test_final_assembler_has_core_not_palette():
    contract = _sample_contract(PLAY)
    prompt = assemble_final_prompt({
        "draft_text": "糙稿场面",
        "contract": contract,
        "deduction": {"ore": ["霜花"]},
        "forbidden_reveal": ["炉认主"],
    })
    assert "要办的事" in prompt
    assert "交出去，娘就有一线生机" in prompt or "弄明白体温" in prompt
    assert "PALETTE" not in prompt
    assert "每 500 字" not in prompt
    assert "≥3 闲笔" not in prompt
    assert "build_craft_block" not in prompt


def test_deleted_old_gate_files_absent():
    root = Path(__file__).resolve().parents[1]
    gone = [
        "clue_density.py", "fate_dearer.py", "design_play.py", "design_attempt.py",
        "chapter_spine.py", "world_surface.py", "verify_craft_compliance.py",
        "stage_craft_prompt.py",
        "api/services/pilot_actions/beats.py",
        "api/services/pilot_actions/deduce.py",
        "api/services/pilot_actions/draft.py",
    ]
    still = [p for p in gone if (root / p).exists()]
    assert still == []


def test_write_assemble_v1_imports_without_phantom_names():
    from scribe3.api.services.write_assemble_blocks import strip_codex_pad
    from scribe3.injection_compact import phase_role_has_substance
    import scribe3.api.services.write_assemble_v1 as v1
    assert callable(strip_codex_pad)
    assert phase_role_has_substance("## 阶段角色(排演)。") is False
    assert "strip_codex_pad" in dir(v1)


def test_production_does_not_import_old_gates():
    root = Path(__file__).resolve().parents[1]
    banned = (
        "scribe3.clue_density", "scribe3.fate_dearer",
        "scribe3.chapter_spine", "scribe3.design_play",
        "scribe3.verify_craft_compliance",
    )
    hits = []
    for p in root.rglob("*.py"):
        if "/tests/" in str(p) or p.name.startswith("test_"):
            continue
        text = p.read_text(encoding="utf-8")
        for name in banned:
            if f"from {name}" in text or f"import {name}" in text:
                hits.append(f"{p.relative_to(root)}:{name}")
    assert hits == []


def test_generate_stage_req_old_names_are_410():
    from fastapi import HTTPException
    from scribe3.api.routers.write import GenerateStageReq, generate_stage
    for name in ("outline", "beats", "chapter_design"):
        req = GenerateStageReq(seq=1, stage=name)
        try:
            generate_stage(req, work="main")
            raise AssertionError("expected 410")
        except HTTPException as exc:
            assert exc.status_code == 410
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            assert detail.get("code") == "stage_gone"


def test_judge_goldens_exist_and_crooked_fails_struct():
    needed = {
        "good_play", "false_dilemma", "wrong_event", "bill_unpaid",
        "leak_play", "missing_hook", "crooked_contract", "incomplete_contract",
    }
    files = {p.stem for p in GOLDEN.glob("*.json")}
    missing = needed - files
    assert not missing, missing
    for path in GOLDEN.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("artifact_type")
        assert "expected_verdict" in data
        assert "expected_fail_question" in data
        assert "input" in data
    crooked = json.loads((GOLDEN / "crooked_contract.json").read_text(encoding="utf-8"))
    play = crooked["input"]["play_text"]
    hit = check_contract_struct(crooked["input"]["contract"], play)
    assert hit["ok"] is False
    assert hit["code"] == "quote_not_in_play"


class CopyingStore(MemoryPlaybookStore):
    """Surreal-like: list_versions returns copies so in-place mutation is a no-op."""

    def list_versions(self, table, seq):
        return [dict(r) for r in super().list_versions(table, seq)]


def test_playbook_persists_via_surreal_mixin_methods():
    """freeze/rewrite 必须打到 PlaybookOpsMixin.insert / mark_superseded，不是内存店。"""
    from scribe3.playbook.store import PlaybookOpsMixin
    from scribe3.store.surreal import SurrealStore
    from scribe3.stage_generate import _as_playbook_store

    assert issubclass(SurrealStore, PlaybookOpsMixin)

    class FakeSQL(PlaybookOpsMixin):
        def __init__(self):
            self.writes: list[tuple[str, dict]] = []
            self.recs: list[dict] = []

        def _query(self, sql, params=None):
            params = params or {}
            table_hint = ""
            for t in ("duty_card", "chapter_play", "chapter_contract", "chapter_deduce", "chapter_draft", "chapter_state"):
                if t in sql:
                    table_hint = t
                    break
            rows = [r for r in self.recs if not table_hint or r.get("_table") == table_hint]
            if "math::max" in sql:
                seq = int(params.get("seq") or 0)
                vers = [int(r.get("version") or 0) for r in rows if int(r.get("seq") or 0) == seq]
                return [{"v": max(vers) if vers else None}]
            if "status='frozen'" in sql:
                seq = int(params.get("seq") or 0)
                frozen = [
                    r for r in rows
                    if int(r.get("seq") or 0) == seq and r.get("status") == "frozen"
                ]
                frozen.sort(key=lambda r: int(r.get("version") or 0), reverse=True)
                if not frozen:
                    return []
                rec = dict(frozen[0])
                return [{"body": json.dumps(rec, ensure_ascii=False)}]
            if "ORDER BY version ASC" in sql:
                seq = int(params.get("seq") or 0)
                hits = [r for r in rows if int(r.get("seq") or 0) == seq]
                hits.sort(key=lambda r: int(r.get("version") or 0))
                return [{"body": json.dumps(dict(r), ensure_ascii=False)} for r in hits]
            if "sha=$sha" in sql:
                sha = str(params.get("sha") or "")
                for r in rows:
                    if r.get("sha") == sha:
                        return [{"body": json.dumps(dict(r), ensure_ascii=False)}]
                return []
            return []

        def _execute_write(self, sql, params=None):
            params = params or {}
            self.writes.append((sql, dict(params)))
            if "UPSERT" in sql:
                rec = json.loads(params["body"])
                rec["_table"] = "chapter_play" if "chapter_play" in sql else ""
                for t in ("duty_card", "chapter_play", "chapter_contract", "chapter_deduce", "chapter_draft", "chapter_state"):
                    if t in sql:
                        rec["_table"] = t
                self.recs.append(rec)
            if "status='superseded'" in sql:
                seq = int(params.get("seq") or 0)
                ver = int(params.get("ver") or 0)
                for r in self.recs:
                    if int(r.get("seq") or 0) == seq and int(r.get("version") or 0) == ver:
                        r["status"] = "superseded"

    st = FakeSQL()
    assert _as_playbook_store(st) is st
    first = freeze_artifact(st, "chapter_play", 1, {"seq": 1, "text": PLAY}, schema="chapter_play.v1")
    assert any("UPSERT" in sql for sql, _ in st.writes)
    assert st.get_frozen("chapter_play", 1)["sha"] == first["sha"]
    second = freeze_artifact(
        st, "chapter_play", 1, {"seq": 1, "text": PLAY + "门外的呼吸声停了半拍"},
        schema="chapter_play.v1", rewrite=True,
    )
    assert second["version"] == 2
    assert any("status='superseded'" in sql for sql, _ in st.writes)
    old = st.get_by_sha("chapter_play", first["sha"])
    assert old["status"] == "superseded"


def test_rewrite_persists_downstream_supersede_on_copying_store():
    store = CopyingStore()
    llm = _pass_llm({})
    ctx = _duty_ctx()
    d = run_stage(store, 1, "duty", llm_fn=llm, ctx=ctx)
    run_stage(store, 1, "design", llm_fn=llm, ctx={**ctx, "duty": d["artifact"]})
    run_stage(store, 1, "deduce", llm_fn=llm, ctx=ctx)
    assert store.get_frozen("chapter_deduce", 1) is not None
    rewritten = run_stage(store, 1, "design", extra="rewrite=1", llm_fn=llm, ctx={**ctx, "duty": d["artifact"]})
    assert rewritten["ok"] is True
    assert store.get_frozen("chapter_deduce", 1) is None
    play = store.get_frozen("chapter_play", 1)
    contract = store.get_frozen("chapter_contract", 1)
    assert contract is not None
    assert (contract.get("play_sha") or contract.get("source_sha")) == play.get("sha")


def test_json_parse_fail_is_infra_not_needs_human():
    store = MemoryPlaybookStore()

    def llm_fn(prompt, **_k):
        return "<<<not-json>>>"

    out = run_stage(
        store, 1, "duty", llm_fn=llm_fn,
        ctx=_duty_ctx(),
    )
    assert out.get("ok") is False
    assert out.get("code") == "infra"
    assert out.get("status") != "needs_human"


def test_review_and_freeze_play_supersedes_old():
    from scribe3.playbook.pipeline import review_and_freeze_play
    store = CopyingStore()
    llm = _pass_llm({})
    ctx = _duty_ctx()
    d = run_stage(store, 1, "duty", llm_fn=llm, ctx=ctx)
    first = run_stage(store, 1, "design", llm_fn=llm, ctx={**ctx, "duty": d["artifact"]})
    old = first["sha"]
    run_stage(store, 1, "deduce", llm_fn=llm, ctx=ctx)
    out = review_and_freeze_play(
        store, 1, ("沈烛若把碎片按回胸口。" * 40),
        llm_fn=llm, ctx={**ctx, "duty": d["artifact"]},
    )
    assert out["ok"] is True
    assert out["sha"] != old
    assert store.get_by_sha("chapter_play", old)["status"] == "superseded"
    assert store.get_frozen("chapter_deduce", 1) is None


def test_final_last_mile_calls_finalize_gate(monkeypatch):
    seen = {"n": 0}

    def fake(st, seq, prose, **_k):
        seen["n"] += 1
        seen["prose"] = prose
        return {"allowed": False, "code": "finalize_gate", "detail": "定稿门没过"}

    import scribe3.playbook.structural as structural_mod
    import scribe3.playbook.pipeline as pipeline_mod

    orig = structural_mod.check_final_last_mile

    def wrapped(text, store=None, seq=None, **kw):
        seen["entered"] = True
        return orig(text, store=store, seq=seq, **kw)

    monkeypatch.setattr("scribe3.finalize_gate.check_finalize_for_save", fake)
    monkeypatch.setattr(pipeline_mod, "check_final_last_mile", wrapped)
    store = MemoryPlaybookStore()
    llm = _pass_llm({})
    ctx = _duty_ctx()
    d = run_stage(store, 1, "duty", llm_fn=llm, ctx=ctx)
    run_stage(store, 1, "design", llm_fn=llm, ctx={**ctx, "duty": d["artifact"]})
    run_stage(store, 1, "deduce", llm_fn=llm, ctx=ctx)
    run_stage(store, 1, "draft", llm_fn=llm, ctx=ctx)
    out = run_stage(store, 1, "final", llm_fn=llm, ctx=ctx)
    assert seen["n"] >= 1
    assert out.get("ok") is False


def test_needs_human_insert_does_not_clobber_frozen_v1():
    """math::max 失效时，未过审稿不得 UPSERT 掉已冻的 1 号糙稿。"""
    from scribe3.playbook.envelope import wrap, pass_review
    from scribe3.playbook.store import PlaybookOpsMixin

    class FakeSQL(PlaybookOpsMixin):
        def __init__(self):
            self.recs: list[dict] = []

        def _query(self, sql, params=None):
            params = params or {}
            if "math::max" in sql:
                raise RuntimeError("math::max broken on surreal 3")
            seq = int(params.get("seq") or 0)
            rows = [r for r in self.recs if int(r.get("seq") or 0) == seq]
            if "status='frozen'" in sql:
                frozen = [r for r in rows if r.get("status") == "frozen"]
                frozen.sort(key=lambda r: int(r.get("version") or 0), reverse=True)
                if not frozen:
                    return []
                return [{"body": json.dumps(dict(frozen[0]), ensure_ascii=False)}]
            if "ORDER BY version ASC" in sql:
                hits = sorted(rows, key=lambda r: int(r.get("version") or 0))
                return [{"body": json.dumps(dict(r), ensure_ascii=False)} for r in hits]
            return []

        def _execute_write(self, sql, params=None):
            params = params or {}
            if "UPSERT" not in sql:
                return
            rec = json.loads(params["body"])
            ver = int(params.get("ver") or rec.get("version") or 1)
            rec["version"] = ver
            rec["seq"] = int(params.get("seq") or rec.get("seq") or 0)
            rec["status"] = params.get("st") or rec.get("status")
            self.recs = [
                r for r in self.recs
                if not (int(r.get("seq") or 0) == rec["seq"] and int(r.get("version") or 0) == ver)
            ]
            self.recs.append(rec)

    st = FakeSQL()
    frozen = wrap(
        "chapter_draft.v1",
        {"seq": 1, "text": "冻稿" * 200},
        status="frozen",
        review=pass_review(),
    )
    frozen["seq"] = 1
    frozen["version"] = 1
    st.insert("chapter_draft", frozen)
    assert st.get_frozen("chapter_draft", 1)["text"].startswith("冻稿")

    hung = {"seq": 1, "version": 1, "status": "needs_human", "text": "短稿"}
    st.insert("chapter_draft", hung)
    still = st.get_frozen("chapter_draft", 1)
    assert still is not None
    assert still["text"].startswith("冻稿")
    assert hung["version"] == 2


def test_catalog_teaches_play_contract_not_old_plan():
    from scribe3.orchestration.catalog import get_domain
    design = get_domain("chapter.design")
    tools = design.get("write_tools") or ()
    assert "s3_patch_play" in tools
    assert "s3_patch_contract" in tools
    assert "s3_patch_chapter_plan" not in tools
    assert "14 槽" not in (design.get("instruction_duty") or "")
    deduce = get_domain("chapter.deduce")
    assert "s3_patch_chapter_plan" not in (deduce.get("write_tools") or ())
    assert "s3_generate_stage" in (deduce.get("write_tools") or ())


def test_draft_copy_play_fails_struct():
    from scribe3.playbook.structural import check_draft_struct
    play = "沈烛若把场核碎片按回胸口，四十二度顺着袖口往上爬。" * 80
    draft = play + "他又看了一眼裂口。" * 20
    hit = check_draft_struct(draft, play_text=play)
    assert hit["ok"] is False
    assert hit["code"] == "draft_copy_play"


def test_draft_hook_exempt_does_not_trip_overlap():
    from scribe3.playbook.structural import check_draft_struct
    hook = "袖口里碳化屏还在滚"
    play = hook + "。沈烛若把碎片按回胸口。" * 30
    draft = ("「铁皮还在响。」柳岸青说。\n食堂铁皮落下半扇。\n" * 80) + hook + (
        "他用指腹压住屏，不让它休眠。\n" * 80
    )
    hit = check_draft_struct(draft, play_text=play, exempt_quotes=(hook,))
    assert hit["ok"] is True, hit


def test_draft_metaphor_density_fails_struct():
    from scribe3.playbook.structural import check_draft_struct
    play = "沈烛若把场核碎片按回胸口，四十二度顺着袖口往上爬。" * 40
    draft = ("他按回碎片。像火。仿佛夜。似的冷。袖口发烫。沈烛把盒子推近。" * 80)
    hit = check_draft_struct(draft, play_text=play)
    assert hit["ok"] is False
    assert hit["code"] == "draft_metaphor"


def test_final_metaphor_density_fails_last_mile():
    from scribe3.playbook.structural import check_final_last_mile
    prose = ("他按回碎片。像火。仿佛夜。袖口发烫。沈烛把盒子推近。" * 80)
    hit = check_final_last_mile(prose)
    assert hit["ok"] is False
    assert hit["code"] == "final_metaphor"


def test_contract_nail_quotes_exempt_overlap_keeps_threshold():
    from scribe3.playbook.pipeline import contract_nail_quotes
    from scribe3.playbook.quality_metrics import measure_chapter
    from scribe3.playbook.structural import check_draft_struct, draft_play_overlap
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "playbook/structural.py").read_text(encoding="utf-8")
    assert "rate > 0.15" in src
    nails = {
        "goal": {"quote": "他把碎片按回胸口那一夜"},
        "choice": {"quote": "交出去还是按回去"},
        "decision": {"quote": "指腹压住碳化屏不让它休眠"},
        "cost": {"quote": "四十二度顺着袖口往上爬"},
        "hook": {"quote": "袖口里碳化屏还在滚"},
    }
    contract = {"fields": nails}
    bite = "等着人来兑现"
    exempt = contract_nail_quotes(contract, bite)
    assert nails["goal"]["quote"] in exempt
    assert bite in exempt
    play = nails["hook"]["quote"] + "。沈烛若把碎片按回胸口。" * 40
    body = "「铁皮还在响。」柳岸青说。\n食堂铁皮落下半扇。\n" * 80
    draft = body + nails["hook"]["quote"] + nails["goal"]["quote"] + bite
    rate = draft_play_overlap(draft, play, exempt_quotes=exempt)
    assert rate >= 0
    hit = check_draft_struct(draft, play_text=play, exempt_quotes=exempt)
    assert hit.get("code") != "draft_copy_play"
    long_play = "沈烛若把场核碎片按回胸口，四十二度顺着袖口往上爬。" * 80
    copied = long_play + "他又看了一眼裂口。" * 20
    bad = check_draft_struct(copied, play_text=long_play, exempt_quotes=exempt)
    assert bad["ok"] is False
    assert bad["code"] == "draft_copy_play"

    class St:
        def get_frozen(self, table, seq):
            if table == "chapter_play":
                return {"text": play}
            if table == "chapter_contract":
                return contract
            if table == "chapter_draft":
                return {"text": draft}
            if table == "duty_card":
                return {"who": []}
            return {}

        def get_chapter(self, seq):
            return {}

    m = measure_chapter(St(), 1)
    assert m["overlap"] <= 0.15
    from scribe3.playbook.pipeline import contract_nail_quotes as same
    assert same(contract, bite) == exempt


def test_sparse_metaphor_still_ok():
    from scribe3.playbook.structural import check_draft_struct
    play = "沈烛若把场核碎片按回胸口，四十二度顺着袖口往上爬。" * 40
    draft = (
        "「按回去。」沈烛说。\n他按回碎片，袖口发烫。沈烛把盒子推过来。柳岸青没说话。任务书摊在桌上。\n" * 80
    )
    hit = check_draft_struct(draft, play_text=play)
    assert hit.get("ok") is True, hit


def test_draft_and_final_block_chapter_boundary():
    from scribe3.playbook.structural import check_draft_struct, check_final_last_mile
    draft = ("他按回碎片，袖口发烫。" * 220) + "上一章末他就数过。"
    hit = check_draft_struct(draft, play_text="完全不同的戏文" * 40)
    assert hit["ok"] is False
    assert hit["code"] == "meta_chapter_ref"
    prose = ("他按回碎片，袖口发烫。" * 120) + "这一章里没有人说话。"
    hit2 = check_final_last_mile(prose)
    assert hit2["ok"] is False
    assert hit2["code"] == "meta_chapter_ref"


def test_judge_malformed_verdict_is_needs_human():
    from scribe3.playbook.judge import _normalize
    out = _normalize({"verdict": "maybe", "answers": [], "opinion": ""})
    assert out["verdict"] == "needs_human"
    out2 = _normalize({
        "verdict": "???",
        "answers": [{"q": 1, "evidence": "", "answer": "yes", "reason": "空"}],
    })
    assert out2["verdict"] == "needs_human"
    out3 = _normalize({
        "verdict": "bad",
        "answers": [{"q": 1, "evidence": "他付了账", "answer": "no", "reason": "旁白"}],
    })
    assert out3["verdict"] == "fail"


def test_final_without_frozen_contract_blocks():
    from scribe3.playbook.structural import check_final_last_mile
    store = MemoryPlaybookStore()
    prose = "他按回碎片，袖口发烫。" * 120
    hit = check_final_last_mile(prose, store=store, seq=1)
    assert hit["ok"] is False
    assert hit["code"] == "no_chapter_contract"
