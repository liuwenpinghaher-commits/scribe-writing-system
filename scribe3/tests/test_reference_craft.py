"""已批准参考指纹进入写作前的安全技法编译合同。"""
from __future__ import annotations

from scribe3.quality.references import ReferenceService


class _FingerprintLLM:
    def complete(self, messages, **kwargs):
        class _Result:
            content = '''{
              "local_mechanisms": ["局部张力"],
              "cross_chapter_aggregation": "跨章递进",
              "full_book_fingerprint": "克制的悬念组织",
              "evidence": [{"quote": "雾港的钟响了", "location": "第一章"}],
              "counter_evidence": [{"quote": "雾散以后", "location": "第二章"}],
              "transferable_mechanisms": ["以环境变化迫使人物做出主动选择", "用动作后果替代情绪解释", "潮汐旧书的段落节奏"],
              "non_copyable_elements": ["沈浪", "雾港", "参考作品的原句与句式"],
              "applicable_scope": "悬疑开场"
            }'''
        return _Result()


def _approved_fingerprint(store, *, work: str, title: str = "潮汐旧书"):
    service = ReferenceService(store)
    reference = service.import_reference(
        work=work,
        title=title,
        text="雾港的钟响了。沈浪没有回头，只把湿透的票根塞进掌心。",
    )
    pending = service.generate_fingerprint(
        reference_work_id=reference.reference_work_id, llm=_FingerprintLLM(),
    )
    return service.approve_fingerprint(fingerprint_id=pending.fingerprint_id)


def test_approved_fingerprint_compiles_to_safe_craft_sources(store):
    from scribe3.reference_craft import approved_craft_briefs, render_craft_briefs

    approved = _approved_fingerprint(store, work="book-a")
    briefs = approved_craft_briefs(store, "book-a")
    rendered = render_craft_briefs(briefs)

    assert [brief.fingerprint_id for brief in briefs] == [approved.fingerprint_id]
    assert "以环境变化迫使人物做出主动选择" in rendered
    assert "动作后果替代情绪解释" in rendered
    assert "不得复用参考作品的角色名、专名、情节、措辞或句式" in rendered
    for forbidden in ("潮汐旧书", "雾港的钟响了", "沈浪", "雾港", "参考作品的原句"):
        assert forbidden not in rendered
    source = briefs[0].context_source("book-a")
    assert source.source_kind == "reference_craft"
    assert source.source_id == f"reference_fingerprint:{approved.fingerprint_id}"
    assert source.content_digest


def test_reference_craft_is_strictly_scoped_to_current_work(store):
    from scribe3.reference_craft import approved_craft_briefs

    first = _approved_fingerprint(store, work="book-a", title="甲书")
    _approved_fingerprint(store, work="book-b", title="乙书")

    assert [brief.fingerprint_id for brief in approved_craft_briefs(store, "book-a")] == [
        first.fingerprint_id
    ]
    assert approved_craft_briefs(store, "book-missing") == ()


def test_contract_targets_filter_write_craft_to_selected_yardstick(store):
    """已批准合同带 reference_targets 时，写路径只注入选中标尺；无 targets 则全部。"""
    from scribe3.quality.models import (
        DecisionWeights, QualityContractRevision, ReferenceTarget,
    )
    from scribe3.quality.store import QualityStore
    from scribe3.reference_craft import (
        approved_craft_briefs,
        craft_briefs_for_write,
        selected_reference_work_ids_from_contract,
    )

    a = _approved_fingerprint(store, work="book-a", title="标尺甲")
    b = _approved_fingerprint(store, work="book-a", title="标尺乙")
    # 无合同时：全部已批准
    assert selected_reference_work_ids_from_contract(store, "book-a") is None
    all_ids = {brief.fingerprint_id for brief in craft_briefs_for_write(store, "book-a")}
    assert a.fingerprint_id in all_ids and b.fingerprint_id in all_ids

    quality = QualityStore(store)
    # reference_work_id on fingerprint records
    rows = store._query(
        "SELECT reference_work_id, fingerprint_id FROM reference_fingerprint "
        "WHERE status='approved'",
        {},
    )
    by_fp = {r["fingerprint_id"]: r["reference_work_id"] for r in rows}
    only_a_work = by_fp[a.fingerprint_id]
    dims = (
        "coherence_causality", "character_truth", "scene_necessity", "structure_pacing",
        "suspense_payoff", "emotional_effect", "reading_experience", "language_voice",
        "theme_subtext", "originality",
    )
    contract = QualityContractRevision(
        contract_id="quality_contract:book-a",
        work="book-a",
        revision=1,
        primary_genre="悬疑",
        overlay_genres=(),
        custom_genre_description="",
        target_readers="成年读者",
        reading_context="连续阅读",
        core_promise="选择推动关系与代价",
        intended_experience=("好奇",),
        emotional_arc=("疑惧",),
        theme_questions=("真相是否值得代价？",),
        allowed_ambiguities=(),
        prohibited_preaching=(),
        success_criteria={
            "character": "选择来自人物",
            "relationship": "关系由行动改变",
            "structure": "章有推进",
            "language": "克制",
            "originality": "机制参与因果",
        },
        non_negotiables=(),
        allowed_tradeoffs=(),
        dimension_weights={d: 1.0 for d in dims},
        weights=DecisionWeights(),
        reference_targets=(
            ReferenceTarget(
                reference_work_id=only_a_work,
                dimension="language_voice",
                mode="inspired",
                intensity=0.5,
                mechanism="以环境变化迫使人物选择",
                difference_requirement="人物与意象必须不同",
            ),
        ),
        evaluation_milestones=("chapter",),
        attention_budget={"blocking": -1, "major": 5, "ordinary": 10},
        completion_criteria=("有证据",),
        approved=False,
    )
    quality.save_contract_revision(contract)
    quality.approve_contract(
        contract.contract_id, contract.revision, expected_approved=False,
    )
    selected = selected_reference_work_ids_from_contract(store, "book-a")
    assert selected == frozenset({only_a_work})
    filtered = craft_briefs_for_write(store, "book-a")
    assert [brief.fingerprint_id for brief in filtered] == [a.fingerprint_id]
    # 显式 all-approved 路径仍可用
    assert len(approved_craft_briefs(store, "book-a")) >= 2


def test_pending_fingerprint_never_appears_in_craft_briefs(store):
    from scribe3.quality.references import ReferenceService
    from scribe3.reference_craft import craft_briefs_for_write

    service = ReferenceService(store)
    reference = service.import_reference(
        work="book-p", title="未批准", text="雾港的钟响了。沈浪没有回头。",
    )
    service.generate_fingerprint(
        reference_work_id=reference.reference_work_id, llm=_FingerprintLLM(),
    )
    assert craft_briefs_for_write(store, "book-p") == ()
