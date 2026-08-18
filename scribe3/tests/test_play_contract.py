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
from scribe3.playbook.structural import check_contract_struct, check_duty_struct

GOLDEN = Path(__file__).resolve().parent / "judge_golden"

PLAY = "交出去，娘就有一线生机；自己按回去，赌的是这条命。沈烛若合上五指。"


def test_quote_must_be_verbatim():
    assert quote_in_play("交出去，娘就有一线生机", PLAY) is True
    assert quote_in_play("交出碎片换母亲生机", PLAY) is False


def test_norm_strips_punct_and_space_only():
    assert _norm("交 出 去，娘就有一线生机。") == _norm("交出去娘就有一线生机")
    assert quote_in_play("交出去，娘就有一线生机", "交出去娘就有一线生机") is True
    assert quote_in_play("交出去娘就有一线生机啊", PLAY) is False


def test_duty_who_must_be_in_cast():
    duty = make_duty(seq=1, who=["沈烛若", "不存在的人"], available_cast=["沈烛若"])
    hit = check_duty_struct(duty, available_cast=["沈烛若"])
    assert hit["ok"] is False
    assert hit["code"] == "duty_who_cast"


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


def _pass_llm(kind_text: dict[str, str]):
    def llm_fn(prompt, max_tokens=2048, system="", temperature=0.8):
        if "你是审稿的" in prompt or "五问" in prompt or "两问" in prompt or "六问" in prompt or "七问" in prompt or "四问" in prompt:
            return json.dumps({
                "answers": [{"q": 1, "evidence": "沈烛若合上五指", "answer": "yes", "reason": "过"}],
                "verdict": "pass",
                "opinion": "",
            }, ensure_ascii=False)
        if "立\"责任\"" in prompt or "立四件事" in prompt:
            return json.dumps({
                "must_happen": "沈烛若把碎片按回胸口",
                "bill": "四十二度成了他的常态",
                "who": ["沈烛若"],
                "forbidden_reveal": ["炉认主"],
                "line_to_touch": None,
            }, ensure_ascii=False)
        if "你要从戏里抄出契约" in prompt:
            return json.dumps(_sample_contract(PLAY), ensure_ascii=False)
        if "写演绎" in prompt:
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
        if "糙稿" in prompt:
            return "场面。" * 300
        if "打磨成正文" in prompt:
            return "正文。" * 600
        return PLAY * 8
    return llm_fn


def test_force_later_layer_leaves_play_sha():
    store = MemoryPlaybookStore()
    llm = _pass_llm({})
    ctx = {
        "seq": 1,
        "focalizer": "沈烛若",
        "available_cast": ["沈烛若"],
        "available_lines": [],
        "prev_hook_quote": None,
        "forbidden_reveal": ["炉认主"],
    }
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
    ctx = {
        "seq": 1, "focalizer": "沈烛若",
        "available_cast": ["沈烛若"], "available_lines": [],
        "prev_hook_quote": None,
    }
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
