"""质量决策 Task 2：真实 SurrealDB 权威存储合同。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib

import pytest

from scribe3.quality.models import (
    ConfidenceComponents,
    DimensionWeight,
    EvidenceAnchor,
    JudgmentState,
    QualityContractRevision,
    QualityJudgment,
    SuccessCriterion,
)
from scribe3.quality.rubrics import CORE_DIMENSIONS
from scribe3.quality.store import (
    BoundQualityJudgment,
    JudgmentTraceBinding,
    QualityEvaluation,
    QualityJobRecord,
    QualitySnapshotRecord,
    QualityStore,
    ReferenceFingerprintRecord,
    ReferenceWorkRecord,
)
from scribe3.context_manifest import build_context_manifest
from scribe3.context_models import (
    ContextBlock,
    ContextEnvelope,
    ContextFocus,
    ContextRequest,
    ContextSnapshot,
    ContextSource,
)
from scribe3.context_outcome import ContextOutcomeTrace
from scribe3.context_policy import ContextPolicy
from scribe3.context_store import ContextStore


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _contract(*, revision: int = 1, promise: str = "让读者跟随人物穿过真相") -> QualityContractRevision:
    return QualityContractRevision(
        contract_id="contract:book-quality",
        work="book-quality",
        revision=revision,
        primary_genre="长篇悬疑",
        overlay_genres=("家族史",),
        target_readers="成年类型小说读者",
        reading_context="连续阅读",
        core_promise=promise,
        intended_experience=("不安", "释然"),
        emotional_arc=("疑惧", "对峙", "余韵"),
        theme_questions=("真相是否值得所有代价",),
        success_criteria=tuple(
            SuccessCriterion(key=key, text=f"{key}-criterion")
            for key in ("character", "relationship", "structure", "language", "originality")
        ),
        dimension_weights=tuple(
            DimensionWeight(dimension=item.key, weight=1.0)
            for item in CORE_DIMENSIONS
        ),
        evaluation_milestones=("chapter", "volume", "book"),
        completion_criteria=("十维均有可追溯判断",),
    )


def _reference_work() -> ReferenceWorkRecord:
    return ReferenceWorkRecord(
        reference_work_id="reference-work:favorite-1",
        work="book-quality",
        title="参考作品甲",
        source_hash=_sha("参考作品原文"),
        import_revision=1,
        status="imported",
    )


def _fingerprint() -> ReferenceFingerprintRecord:
    return ReferenceFingerprintRecord(
        reference_work_id="reference-work:favorite-1",
        revision=1,
        source_hash=_sha("参考作品原文"),
        status="approved",
        fingerprint={
            "local_mechanisms": ["以动作替代解释"],
            "whole_book": "延迟信息与物证回响",
        },
    )


def _approved_contract(store) -> QualityContractRevision:
    quality = QualityStore(store)
    quality.save_contract_revision(_contract())
    return quality.approve_contract(
        "contract:book-quality", 1, expected_approved=False,
    )


def _snapshot(store, prose: str = "井沿的水声停了。老范没有回头。") -> QualitySnapshotRecord:
    version_id = store.add_chapter_version(
        1, prose, label="质量冻结", kind="checkpoint", stage="final",
    )
    return QualityStore(store).create_chapter_snapshot(
        work="book-quality", chapter_version_ids=(version_id,),
    )


def _confidence() -> ConfidenceComponents:
    return ConfidenceComponents(
        context_coverage=1.0,
        evidence_validity=1.0,
        calibration_reliability=0.9,
        independence_factor=0.8,
        stability_factor=0.9,
    )


def _judgment(
    *, evaluator_kind: str, version_id: str, prose: str, score: int = 4,
) -> QualityJudgment:
    quote = "水声停了"
    prefix = prose[:prose.index(quote)]
    start = len(prefix.encode("utf-16-le")) // 2
    quote_units = len(quote.encode("utf-16-le")) // 2
    return QualityJudgment(
        dimension="coherence_causality",
        evaluator_kind=evaluator_kind,
        state=JudgmentState.EVALUABLE,
        score=score,
        effect="动作与声音形成因果压力",
        mechanism="先声音中断，后人物拒绝回头",
        evidence=(EvidenceAnchor(
            chapter_version_id=f"chapter_version:{version_id}",
            start_utf16=start,
            end_utf16=start + quote_units,
            quote=quote,
            content_hash=_sha(prose),
        ),),
        confidence_components=_confidence(),
    )


def _bound_judgment(
    store, judgment: QualityJudgment, *, suffix: str,
    outcome_status: str = "succeeded",
) -> BoundQualityJudgment:
    request = ContextRequest(
        request_id=f"quality-request-{suffix}",
        task_kind="draft",
        target_ref="chapter:1",
        navigation_snapshot_id=f"quality-navigation-{suffix}",
        work="book-quality",
        chapter=1,
        phase="draft",
        policy_version="generation.v1",
    )
    snapshot = ContextSnapshot(
        session_id=f"quality-session-{suffix}",
        work="book-quality",
        revision=1,
        thread_id=f"quality-thread-{suffix}",
        entry="quality",
        directory_path=("quality",),
        focus=ContextFocus(type="chapter", id="chapter:1", label="第一章"),
        detail_route="chapter:1",
        chapter=1,
        phase="draft",
        focalizer=None,
        previous_revision=0,
        navigation_id=f"quality-navigation-{suffix}",
        captured_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
        context_hash="",
    ).with_hash()
    digest = _sha(f"quality-source-{suffix}")
    source = ContextSource(
        source_id=f"quality-source:{suffix}",
        source_kind="canonical",
        work="book-quality",
        content_digest=digest,
    )
    envelope = ContextEnvelope(
        snapshot=snapshot,
        blocks=[ContextBlock(
            name="canonical", text="", token_estimate=0, sources=[source],
        )],
        total_token_estimate=0,
        omitted=[],
        assembled_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
        envelope_hash=_sha(f"quality-envelope-{suffix}"),
    )
    manifest = build_context_manifest(
        request,
        ContextPolicy.for_task("draft"),
        envelope,
        f"quality-system-input-{suffix}",
    )
    ContextStore(store).save_manifest(manifest)
    outcome = ContextOutcomeTrace(
        outcome_id=f"quality-outcome-{suffix}",
        request_id=request.request_id,
        manifest_id=manifest.manifest_hash,
        actual_input_hash=manifest.actual_input_hash,
        status=outcome_status,
        provider="deepseek",
        model="deepseek-chat",
        provider_request_id=f"provider-request-{suffix}",
        transport_provider="httpx",
        reasoning_provider="deepseek",
        reasoning_model="deepseek-chat",
        reasoning_request_id=f"provider-request-{suffix}",
        usage={"input_tokens": 10, "output_tokens": 20},
        output_hash=_sha(f"quality-output-{suffix}"),
    )
    ContextStore(store).save_outcome(outcome)
    return BoundQualityJudgment(
        judgment=judgment,
        trace=JudgmentTraceBinding(
            outcome_id=outcome.outcome_id,
            request_id=outcome.request_id,
            manifest_id=outcome.manifest_id,
            actual_input_hash=outcome.actual_input_hash,
            provider=outcome.provider,
            model=outcome.model,
            provider_request_id=outcome.provider_request_id,
            usage=outcome.usage or {},
        ),
    )


def _seed_job(store) -> tuple[QualityJobRecord, QualitySnapshotRecord, str]:
    _approved_contract(store)
    quality = QualityStore(store)
    quality.save_reference_work(_reference_work())
    fingerprint = quality.save_reference_fingerprint(_fingerprint())
    prose = "井沿😀的水声停了。老范没有回头。"
    snapshot = _snapshot(store, prose)
    job = quality.create_job(
        work="book-quality",
        snapshot_id=snapshot.snapshot_id,
        contract_id="contract:book-quality",
        contract_revision=1,
        rubric_revision="quality-rubric.v1",
        reference_fingerprint_ids=(fingerprint.fingerprint_id,),
        model_config={"provider": "deepseek", "model": "deepseek-chat", "temperature": 0},
        actual_input_hash=_sha("quality-system-input"),
        idempotency_key="quality-job:chapter-1:v1",
    )
    return job, snapshot, prose


def test_contract_revisions_are_append_only_and_approval_is_one_way_cas(store):
    quality = QualityStore(store)
    original = _contract()

    assert quality.save_contract_revision(original) == original
    assert quality.save_contract_revision(original) == original
    with pytest.raises(ValueError, match="contract revision.*冲突|合同修订.*冲突"):
        quality.save_contract_revision(_contract(promise="伪造覆盖"))

    approved = quality.approve_contract(
        original.contract_id, original.revision, expected_approved=False,
    )
    assert approved.approved is True
    with pytest.raises(ValueError, match="CAS|已批准|状态"):
        quality.approve_contract(
            original.contract_id, original.revision, expected_approved=False,
        )

    second = quality.save_contract_revision(_contract(revision=2, promise="第二修订承诺"))
    assert second.revision == 2 and second.approved is False
    assert len(store._query("SELECT id FROM quality_contract_revision")) == 2


def test_reference_work_and_fingerprint_round_trip_without_raw_text_copy(store):
    quality = QualityStore(store)
    work = _reference_work()
    fingerprint = _fingerprint()

    assert quality.save_reference_work(work) == work
    assert quality.save_reference_work(work) == work
    saved_fingerprint = quality.save_reference_fingerprint(fingerprint)
    assert saved_fingerprint == fingerprint
    assert ReferenceWorkRecord.model_validate(work.model_dump(mode="json")) == work
    assert ReferenceFingerprintRecord.model_validate(
        saved_fingerprint.model_dump(mode="json")
    ) == saved_fingerprint

    row = store._query("SELECT * FROM reference_work")[0]
    assert row["source_hash"] == work.source_hash
    assert row["import_revision"] == 1
    assert row["status"] == "imported"
    assert "prose" not in row and "source_text" not in row
    with pytest.raises(ValueError, match="reference work.*冲突|参考作品.*冲突"):
        quality.save_reference_work(work.model_copy(update={"status": "archived"}))


def test_snapshot_references_frozen_chapter_versions_and_never_copies_prose(store):
    prose_a = "第一章冻结正文。"
    prose_b = "第二章冻结正文。"
    version_a = store.add_chapter_version(1, prose_a, stage="final")
    version_b = store.add_chapter_version(2, prose_b, stage="final")

    snapshot = QualityStore(store).create_chapter_snapshot(
        work="book-quality", chapter_version_ids=(version_b, version_a),
    )

    assert [member.chapter_version_id for member in snapshot.members] == [
        f"chapter_version:{version_b}", f"chapter_version:{version_a}",
    ]
    assert [member.ordinal for member in snapshot.members] == [0, 1]
    assert [member.content_hash for member in snapshot.members] == [_sha(prose_b), _sha(prose_a)]
    assert QualitySnapshotRecord.model_validate(snapshot.model_dump(mode="json")) == snapshot
    rows = store._query("SELECT * FROM quality_snapshot_member ORDER BY ordinal")
    assert all("prose" not in row for row in rows)
    # 既有 reset/delete 流程仍可管理 chapter_version；质量快照通过 hash
    # 将它冻结。若权威版本被外部篡改，任何后续质量读必须 fail-loud。
    store._raw_query(
        "UPDATE type::record('chapter_version', $version_id) SET prose='tampered'",
        {"version_id": version_a},
    )
    with pytest.raises(ValueError, match="content_hash|漂移|冻结"):
        QualityStore(store).get_snapshot(snapshot.snapshot_id)


def test_job_binds_contract_rubric_fingerprints_model_and_actual_input_hash(store):
    job, snapshot, _ = _seed_job(store)

    assert job.snapshot_id == snapshot.snapshot_id
    assert job.contract_id == "contract:book-quality"
    assert job.contract_revision == 1
    assert job.rubric_revision == "quality-rubric.v1"
    assert len(job.reference_fingerprint_ids) == 1
    assert job.model_settings == {
        "provider": "deepseek", "model": "deepseek-chat", "temperature": 0,
    }
    assert job.actual_input_hash == _sha("quality-system-input")
    assert QualityJobRecord.model_validate(job.model_dump(mode="json")) == job


def test_system_reference_and_author_judgments_are_isolated_and_evidence_round_trips(store):
    job, snapshot, prose = _seed_job(store)
    version_id = snapshot.members[0].chapter_version_id
    bare_version_id = version_id.split(":", 1)[1]
    quality = QualityStore(store)
    system = _judgment(
        evaluator_kind="system", version_id=bare_version_id, prose=prose,
    )
    reference = _judgment(
        evaluator_kind="reference", version_id=bare_version_id, prose=prose, score=3,
    )
    author = _judgment(
        evaluator_kind="author", version_id=bare_version_id, prose=prose, score=5,
    )
    bound_system = _bound_judgment(store, system, suffix="system")
    bound_reference = _bound_judgment(store, reference, suffix="reference")

    assert quality.save_judgments(
        job.job_id, unit=version_id, judgments=(bound_system, bound_reference),
    ) == (bound_system, bound_reference)
    assert quality.save_author_judgment(job.job_id, unit=version_id, judgment=author) == author
    with pytest.raises(ValueError, match="system|reference"):
        quality.save_judgments(
            job.job_id,
            unit=version_id,
            judgments=(_bound_judgment(store, author, suffix="invalid-author"),),
        )
    with pytest.raises(ValueError, match="author"):
        quality.save_author_judgment(job.job_id, unit=version_id, judgment=system)
    with pytest.raises(ValueError, match="冲突"):
        quality.save_judgments(
            job.job_id,
            unit=version_id,
            judgments=(
                bound_system.model_copy(update={
                    "judgment": system.model_copy(update={"score": 2}),
                }),
                bound_reference,
            ),
        )

    evaluation = quality.get_evaluation(job.job_id)
    assert isinstance(evaluation, QualityEvaluation)
    assert QualityEvaluation.model_validate(
        evaluation.model_dump(mode="json")
    ) == evaluation
    assert evaluation.units[0].prose == prose
    assert evaluation.system_reference_judgments == (bound_system, bound_reference)
    assert evaluation.author_judgments == (author,)
    assert (
        evaluation.system_reference_judgments[0].judgment.evidence[0].quote
        in evaluation.units[0].prose
    )
    assert len(store._query("SELECT id FROM quality_judgment")) == 2
    assert len(store._query("SELECT id FROM quality_author_judgment")) == 1


def test_evidence_must_match_snapshot_member_hash_range_and_authoritative_prose(store):
    job, snapshot, prose = _seed_job(store)
    version_id = snapshot.members[0].chapter_version_id
    bare_version_id = version_id.split(":", 1)[1]
    judgment = _judgment(
        evaluator_kind="system", version_id=bare_version_id, prose=prose,
    )
    bad_anchor = judgment.evidence[0].model_copy(update={"content_hash": "0" * 64})
    forged = judgment.model_copy(update={"evidence": (bad_anchor,)})
    bound_forged = _bound_judgment(store, forged, suffix="forged-evidence")

    with pytest.raises(ValueError, match="content_hash|证据"):
        QualityStore(store).save_judgments(
            job.job_id, unit=version_id, judgments=(bound_forged,),
        )
    assert store._query("SELECT id FROM quality_judgment") == []


@pytest.mark.parametrize("status", ["failed", "incomplete_stream", "cancelled"])
def test_machine_judgment_rejects_non_succeeded_context_outcome(store, status):
    job, snapshot, prose = _seed_job(store)
    version_id = snapshot.members[0].chapter_version_id
    judgment = _judgment(
        evaluator_kind="system",
        version_id=version_id.split(":", 1)[1],
        prose=prose,
    )
    bound = _bound_judgment(
        store, judgment, suffix=f"terminal-{status}", outcome_status=status,
    )

    with pytest.raises(ValueError, match="succeeded|成功"):
        QualityStore(store).save_judgments(
            job.job_id, unit=version_id, judgments=(bound,),
        )
    assert store._query("SELECT id FROM quality_judgment") == []


def test_snapshot_drift_blocks_job_and_evidence_free_judgment_writes(store):
    _approved_contract(store)
    quality = QualityStore(store)
    prose = "原始冻结正文。"
    snapshot = _snapshot(store, prose)
    unit = snapshot.members[0].chapter_version_id
    bare = unit.split(":", 1)[1]

    store._raw_query(
        "UPDATE type::record('chapter_version', $version_id) SET prose='漂移正文'",
        {"version_id": bare},
    )
    with pytest.raises(ValueError, match="content_hash|漂移|冻结"):
        quality.create_job(
            work="book-quality",
            snapshot_id=snapshot.snapshot_id,
            contract_id="contract:book-quality",
            contract_revision=1,
            rubric_revision="quality-rubric.v1",
            reference_fingerprint_ids=(),
            model_config={"provider": "deepseek", "model": "deepseek-chat"},
            actual_input_hash=_sha("drift-job"),
            idempotency_key="quality-job:drift",
        )

    # 先恢复、建 job，再次制造漂移；无证据的 insufficient 也必须被快照门拒绝。
    store._raw_query(
        "UPDATE type::record('chapter_version', $version_id) SET prose=$prose",
        {"version_id": bare, "prose": prose},
    )
    job = quality.create_job(
        work="book-quality",
        snapshot_id=snapshot.snapshot_id,
        contract_id="contract:book-quality",
        contract_revision=1,
        rubric_revision="quality-rubric.v1",
        reference_fingerprint_ids=(),
        model_config={"provider": "deepseek", "model": "deepseek-chat"},
        actual_input_hash=_sha("drift-job-restored"),
        idempotency_key="quality-job:drift-restored",
    )
    store._raw_query(
        "UPDATE type::record('chapter_version', $version_id) SET prose='再次漂移'",
        {"version_id": bare},
    )
    insufficient = QualityJudgment(
        dimension="coherence_causality",
        evaluator_kind="system",
        state=JudgmentState.INSUFFICIENT,
        confidence_components=_confidence(),
    )
    bound = _bound_judgment(store, insufficient, suffix="drift-insufficient")
    with pytest.raises(ValueError, match="content_hash|漂移|冻结"):
        quality.save_judgments(job.job_id, unit=unit, judgments=(bound,))
    with pytest.raises(ValueError, match="content_hash|漂移|冻结"):
        quality.save_author_judgment(
            job.job_id,
            unit=unit,
            judgment=insufficient.model_copy(update={"evaluator_kind": "author"}),
        )


def test_job_transaction_rechecks_snapshot_hash_after_preflight(store, monkeypatch):
    _approved_contract(store)
    quality = QualityStore(store)
    snapshot = _snapshot(store, "事务前冻结正文。")
    bare = snapshot.members[0].chapter_version_id.split(":", 1)[1]
    # 模拟 preflight 通过后、事务开始前的并发漂移：强制公开预检返回旧快照，
    # 只有同一 SurrealDB 写事务内的 hash guard 能阻止 CREATE。
    monkeypatch.setattr(quality, "get_snapshot", lambda _snapshot_id: snapshot)
    store._raw_query(
        "UPDATE type::record('chapter_version', $version_id) SET prose='并发漂移'",
        {"version_id": bare},
    )

    with pytest.raises(ValueError, match="content_hash|漂移|冻结"):
        quality.create_job(
            work="book-quality",
            snapshot_id=snapshot.snapshot_id,
            contract_id="contract:book-quality",
            contract_revision=1,
            rubric_revision="quality-rubric.v1",
            reference_fingerprint_ids=(),
            model_config={"provider": "deepseek", "model": "deepseek-chat"},
            actual_input_hash=_sha("transaction-race"),
            idempotency_key="quality-job:transaction-race",
        )
    assert store._query(
        "SELECT id FROM quality_job WHERE idempotency_key='quality-job:transaction-race'"
    ) == []


def test_permanent_chapter_delete_is_blocked_while_quality_snapshot_references_version(store):
    store.save_chapter(7, "章节当前正文。", title="第七章")
    version_id = store.add_chapter_version(7, "章节冻结正文。", stage="final")
    snapshot = QualityStore(store).create_chapter_snapshot(
        work=store.db_name, chapter_version_ids=(version_id,),
    )

    impact = store.chapter_lifecycle_impact(7)
    assert {item["kind"] for item in impact["references"]} >= {"版本", "质量快照"}
    with pytest.raises(ValueError, match="质量快照|冻结"):
        store.delete_chapter_permanent(7)

    assert store.get_chapter_version(version_id) is not None
    assert QualityStore(store).get_snapshot(snapshot.snapshot_id) == snapshot


def test_concurrent_same_job_idempotency_key_creates_one_truth_and_conflicts_fail(store):
    _approved_contract(store)
    quality = QualityStore(store)
    quality.save_reference_work(_reference_work())
    fingerprint = quality.save_reference_fingerprint(_fingerprint())
    snapshot = _snapshot(store)

    from scribe3.store import SurrealStore
    connections = [
        SurrealStore(url=store.url, ns="scribe3", db=store.db_name)
        for _ in range(8)
    ]
    stores = [QualityStore(connection) for connection in connections]

    def create(target: QualityStore):
        return target.create_job(
            work="book-quality",
            snapshot_id=snapshot.snapshot_id,
            contract_id="contract:book-quality",
            contract_revision=1,
            rubric_revision="quality-rubric.v1",
            reference_fingerprint_ids=(fingerprint.fingerprint_id,),
            model_config={"provider": "deepseek", "model": "deepseek-chat"},
            actual_input_hash=_sha("concurrent-job-input"),
            idempotency_key="quality-job:concurrent",
        )

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(create, stores))
    finally:
        for connection in connections:
            connection.close()

    assert results == [results[0]] * 8
    assert len(store._query(
        "SELECT id FROM quality_job WHERE idempotency_key='quality-job:concurrent'"
    )) == 1
    with pytest.raises(ValueError, match="job.*冲突|作业.*冲突"):
        QualityStore(store).create_job(
            work="book-quality",
            snapshot_id=snapshot.snapshot_id,
            contract_id="contract:book-quality",
            contract_revision=1,
            rubric_revision="quality-rubric.v1",
            reference_fingerprint_ids=(fingerprint.fingerprint_id,),
            model_config={"provider": "deepseek", "model": "deepseek-chat"},
            actual_input_hash=_sha("different-input"),
            idempotency_key="quality-job:concurrent",
        )
