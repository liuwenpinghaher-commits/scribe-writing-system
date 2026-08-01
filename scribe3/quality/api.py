"""参考作品与质量评价 API 路由。"""
from __future__ import annotations

import logging
import threading
from math import ceil
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from scribe3.quality.references import ReferenceService

quality_router = APIRouter(prefix="/references", tags=["references"])
quality_eval_router = APIRouter(prefix="/quality", tags=["quality"])


def _get_deepseek_client():
    from scribe3.deepseek_client import DeepSeekClient
    return DeepSeekClient()


class ImportBody(BaseModel):
    work: str
    title: str = Field(min_length=1)
    text: str | None = None
    file_src: str | None = None


class FingerprintBody(BaseModel):
    work: str


class FingerprintApprovalBody(BaseModel):
    work: str
    corrections: dict[str, Any] | None = None


class PatchBody(BaseModel):
    work: str
    title: str | None = None


def _store_for_request(request: Request, work: str):
    """质量链与主应用同样按 work 绑定一书一库。

    独立路由单测仍可提供 legacy ``app.state.store``；生产应用必须提供
    ``store_for(work)``，避免质量/参考请求悄悄落到默认书。
    """
    resolver = getattr(request.app.state, "store_for", None)
    if callable(resolver):
        return resolver(work)
    return request.app.state.store


def _service(request: Request, work: str) -> ReferenceService:
    return ReferenceService(_store_for_request(request, work))


@quality_router.get("")
def list_references(work: str, request: Request):
    records = _service(request, work).list_references(work=work)
    return [record.model_dump(mode="json") for record in records]


@quality_router.post("/import", status_code=201)
def import_reference(body: ImportBody, request: Request):
    if not body.text and not body.file_src:
        from fastapi import HTTPException
        raise HTTPException(422, "必须提供 text 或 file_src")
    svc = _service(request, body.work)
    record = svc.import_reference(
        work=body.work, title=body.title,
        text=body.text, file_src=body.file_src,
    )
    return record.model_dump(mode="json")


@quality_router.post("/{reference_work_id}/fingerprints", status_code=201)
def generate_fingerprint(reference_work_id: str, body: FingerprintBody, request: Request):
    svc = _service(request, body.work)
    llm = _get_deepseek_client()
    record = svc.generate_fingerprint(
        reference_work_id=reference_work_id, llm=llm,
    )
    return record.model_dump(mode="json")


@quality_router.get("/{reference_work_id}/fingerprints")
def list_fingerprints(reference_work_id: str, work: str, request: Request):
    store = _store_for_request(request, work)
    rows = store._query(
        "SELECT fingerprint_id, reference_work_id, revision, source_hash, status, fingerprint, "
        "provider, model, provider_request_id, usage FROM reference_fingerprint "
        "WHERE reference_work_id=$rid ORDER BY revision DESC",
        {"rid": reference_work_id},
    )
    return rows


@quality_router.post("/{reference_work_id}/fingerprints/{fingerprint_id}/approve", status_code=201)
def approve_fingerprint(
    reference_work_id: str,
    fingerprint_id: str,
    body: FingerprintApprovalBody,
    request: Request,
):
    try:
        record = _service(request, body.work).approve_fingerprint(
            fingerprint_id=fingerprint_id,
            expected_reference_work_id=reference_work_id,
            corrections=body.corrections,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return record.model_dump(mode="json")


@quality_router.patch("/{reference_work_id}")
def patch_reference(reference_work_id: str, body: PatchBody, request: Request):
    store = _store_for_request(request, body.work)
    rows = store._query(
        "SELECT reference_work_id, work, title, source_hash, import_revision, status "
        "FROM reference_work WHERE reference_work_id=$rid "
        "ORDER BY import_revision DESC LIMIT 1",
        {"rid": reference_work_id},
    )
    if not rows:
        raise HTTPException(404, "参考作品不存在")
    return rows[0]


# ── 质量评价纵向链端点 ──────────────────────────────────────────────

from scribe3.quality.confidence import merge_three_axes
from scribe3.quality.evaluator import (
    QUALITY_MAX_CONCURRENCY,
    QUALITY_MAX_REPAIRS,
    QUALITY_TASK_DEADLINE_GRACE_SECONDS,
    QUALITY_TIMEOUT_SECONDS,
    QualityEvaluator,
)
from scribe3.quality.models import (
    EvidenceAnchor,
    JudgmentState,
    QualityContractRevision,
    QualityJudgment,
)
from scribe3.quality.rubrics import CORE_DIMENSIONS
from scribe3.quality.store import QualityStore

_DIM_LABEL = {d.key: d.label for d in CORE_DIMENSIONS}
_QUALITY_JOB_RECOVERY_SAFETY_SECONDS = 30
_quality_job_dispatch_lock = threading.Lock()
_quality_job_dispatching: set[tuple[str, str]] = set()


def _dispatch_quality_job(*, work: str, job_id: str) -> None:
    """在独立连接上执行冻结质量作业，避免占用作者 HTTP 请求或共享 request store。"""
    key = (work, job_id)
    with _quality_job_dispatch_lock:
        if key in _quality_job_dispatching:
            return
        _quality_job_dispatching.add(key)

    def run() -> None:
        store = None
        try:
            from scribe3.store import SurrealStore

            store = SurrealStore(ns="scribe3", db=work)
            QualityEvaluator(store, _get_deepseek_client()).execute_job(job_id)
        except Exception as exc:
            # execute_job 已持久化 retryable_failed/failed；后台异常不得把请求正文、
            # 供应商响应或密钥写进日志。作者由轮询接口看到受限状态与错误代码。
            logging.getLogger("scribe3.quality").warning(
                "质量作业 %s 后台执行结束于 %s", job_id, type(exc).__name__,
            )
        finally:
            if store is not None:
                store.close()
            with _quality_job_dispatch_lock:
                _quality_job_dispatching.discard(key)

    threading.Thread(target=run, name=f"scribe3-quality-{job_id[:12]}", daemon=True).start()


class SnapshotBody(BaseModel):
    work: str
    seq: int
    contract_id: str
    contract_revision: int = 1
    reference_fingerprint_ids: tuple[str, ...] = ()


class AuthorJudgmentBody(BaseModel):
    work: str
    seq: int
    dimension: str
    score: int = Field(ge=1, le=5)
    reason: str = Field(min_length=1)
    decision: Literal["accept", "revise", "reject"]
    evidence: tuple[EvidenceAnchor, ...] = Field(min_length=1)
    counter_evidence: tuple[EvidenceAnchor, ...] = ()


class ContractApprovalBody(BaseModel):
    work: str


def _chapter_version_ids_for_seq(store, seq: int) -> list[str]:
    rows = store._query(
        "SELECT VALUE id FROM chapter_version WHERE seq=$seq "
        "ORDER BY created_at DESC LIMIT 1", {"seq": seq},
    )
    return [str(rid) for rid in rows]


@quality_eval_router.post("/contracts", status_code=201)
def create_contract_revision(contract: QualityContractRevision, request: Request):
    quality = QualityStore(_store_for_request(request, contract.work))
    try:
        saved = quality.save_contract_revision(contract)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return saved.model_dump(mode="json")


@quality_eval_router.get("/contracts/{contract_id}")
def get_contract_revision(
    contract_id: str, revision: int, work: str, request: Request,
    allow_missing: bool = False,
):
    quality = QualityStore(_store_for_request(request, work))
    try:
        contract = quality.get_contract(contract_id, revision)
    except ValueError as exc:
        if allow_missing:
            return {"found": False}
        raise HTTPException(404, str(exc)) from exc
    if contract.work != work:
        raise HTTPException(404, "质量合同不属于当前作品")
    return contract.model_dump(mode="json")


@quality_eval_router.post("/contracts/{contract_id}/{revision}/approve")
def approve_contract_revision(
    contract_id: str, revision: int, body: ContractApprovalBody, request: Request,
):
    quality = QualityStore(_store_for_request(request, body.work))
    try:
        contract = quality.get_contract(contract_id, revision)
        if contract.work != body.work:
            raise ValueError("质量合同不属于当前作品")
        approved = quality.approve_contract(
            contract_id, revision, expected_approved=False,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return approved.model_dump(mode="json")


def _latest_job_id_for_seq(store, seq: int) -> str | None:
    snapshot_rows = store._query(
        "SELECT VALUE snapshot FROM quality_snapshot_member "
        "WHERE chapter_version IN "
        "(SELECT VALUE id FROM chapter_version WHERE seq=$seq)",
        {"seq": seq},
    )
    snapshots = [s for s in snapshot_rows if s is not None]
    if not snapshots:
        return None
    job_rows = store._query(
        "SELECT job_id, created_at FROM quality_job WHERE snapshot IN $snapshots "
        "ORDER BY created_at DESC LIMIT 1",
        {"snapshots": snapshots},
    )
    return job_rows[0]["job_id"] if job_rows else None


def _anchor_payload(anchor: EvidenceAnchor) -> dict[str, Any]:
    return {
        "chapter_version_id": anchor.chapter_version_id,
        "start_utf16": anchor.start_utf16,
        "end_utf16": anchor.end_utf16,
        "quote": anchor.quote,
        "content_hash": anchor.content_hash,
    }


def _shape_evaluation(evaluation, seq: int, *, quality: QualityStore) -> dict[str, Any]:
    expected_axes = len(evaluation.units) * len(CORE_DIMENSIONS)
    if evaluation.job.reference_fingerprint_ids:
        expected_axes *= 2
    if len(evaluation.system_reference_judgments) != expected_axes:
        raise RuntimeError("已完成质量作业缺少完整判断轴")
    by_dim: dict[str, dict[str, Any]] = {}
    for bound in evaluation.system_reference_judgments:
        judgment = bound.judgment
        by_dim.setdefault(judgment.dimension, {})[judgment.evaluator_kind] = judgment
    author_by_dim = {j.dimension: j for j in evaluation.author_judgments}
    latest_verdict_by_dim = {}
    for verdict in quality.get_author_verdicts(evaluation.job.job_id):
        latest_verdict_by_dim.setdefault(verdict.dimension, verdict)
    contract = quality.get_contract(
        evaluation.job.contract_id, evaluation.job.contract_revision,
    )
    weights = contract.weights
    dimensions = []
    for d in CORE_DIMENSIONS:
        axes = by_dim.get(d.key, {})
        sys_j = axes.get("system")
        ref_j = axes.get("reference")
        author_j = author_by_dim.get(d.key)
        system = None
        if sys_j is not None:
            system = {
                "score": sys_j.score,
                "effect": sys_j.effect,
                "mechanism": sys_j.mechanism,
                "confidence": sys_j.confidence,
                "evidence": [_anchor_payload(anchor) for anchor in sys_j.evidence],
            }
        reference = {"score": ref_j.score} if ref_j is not None else None
        verdict = latest_verdict_by_dim.get(d.key)
        author = None
        if author_j is not None:
            author = {"score": author_j.score}
            if verdict is not None:
                author.update({
                    "decision": verdict.decision,
                    "reason": verdict.reason,
                    "evidence": [_anchor_payload(anchor) for anchor in author_j.evidence],
                    "counter_evidence": [
                        _anchor_payload(anchor) for anchor in author_j.counter_evidence
                    ],
                    "revision": verdict.revision,
                })
        decision_index = None
        if author_j is not None and sys_j is not None and ref_j is not None:
            decision_index = merge_three_axes(
                author=author_j.score, system=sys_j.score, reference=ref_j.score,
                weights=(weights.author, weights.system, weights.reference),
            )
        conflicted = (
            author_j is not None and sys_j is not None
            and author_j.score is not None and sys_j.score is not None
            and abs(author_j.score - sys_j.score) >= 2
        )
        dimensions.append({
            "dimension": d.label,
            "state": (sys_j.state.value if sys_j is not None else JudgmentState.INSUFFICIENT.value),
            "system": system,
            "reference": reference,
            "author": author,
            "decision_index": decision_index,
            "conflicted": conflicted,
        })
    return {
        "chapter": seq,
        # 终态与 queued/running 使用同一 job 身份，前端轮询才能证明 ready
        # 结果属于自己刚刚创建的冻结评价，而非同章旧结果。
        "job_id": evaluation.job.job_id,
        # 只暴露本次冻结评价绑定的不可变版本 ID，供审计确认结论没有滞留在
        # 旧正文版本；正文和模型输入仍不离开现有受控读取边界。
        "chapter_version_ids": [unit.chapter_version_id for unit in evaluation.units],
        "dimensions": dimensions,
        "weights": weights.model_dump(mode="json"),
        "status": "ready",
    }


@quality_eval_router.post("/snapshot", status_code=202)
def create_evaluation(body: SnapshotBody, request: Request):
    store = _store_for_request(request, body.work)
    version_ids = _chapter_version_ids_for_seq(store, body.seq)
    if not version_ids:
        raise HTTPException(404, f"章节 {body.seq} 没有可冻结的版本")
    evaluator = QualityEvaluator(store, _get_deepseek_client())
    try:
        job = evaluator.prepare_job(
            work=body.work,
            chapter_version_ids=tuple(version_ids),
            contract_id=body.contract_id,
            contract_revision=body.contract_revision,
            reference_fingerprint_ids=body.reference_fingerprint_ids,
        )
    except ValueError as exc:
        # 合同、快照、指纹或幂等真相不匹配属于作者可修正的业务冲突，
        # 不能以未处理 500 冒充服务端故障。
        raise HTTPException(409, str(exc)) from exc
    status = _recoverable_job_status(QualityStore(store), job.job_id)
    if status.status in ("queued", "retryable_failed"):
        _dispatch_quality_job(work=body.work, job_id=job.job_id)
    return {"job_id": job.job_id, "status": status.status}


def _job_state_payload(*, job_id: str, status, seq: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "chapter": seq,
        "job_id": job_id,
        "dimensions": [],
        "status": status.status,
    }
    if status.status in ("retryable_failed", "failed"):
        payload["error_code"] = status.error_code or "quality_job_failed"
        payload["error_message"] = "质量作业未完成；可重试本次冻结评价。"
    return payload


def _quality_job_recovery_seconds(quality: QualityStore, job_id: str) -> float:
    """按冻结调用量计算 worker 丢失恢复窗口，而不是误杀正常排队批次。"""
    job = quality.get_job(job_id)
    snapshot = quality.get_snapshot(job.snapshot_id)
    axis_count = len(snapshot.members) * len(CORE_DIMENSIONS)
    if job.reference_fingerprint_ids:
        axis_count *= 2
    batches = max(1, ceil(axis_count / QUALITY_MAX_CONCURRENCY))
    return (
        batches * (QUALITY_MAX_REPAIRS + 1)
        * (QUALITY_TIMEOUT_SECONDS + QUALITY_TASK_DEADLINE_GRACE_SECONDS)
        + _QUALITY_JOB_RECOVERY_SAFETY_SECONDS
    )


def _recoverable_job_status(quality: QualityStore, job_id: str):
    return quality.recover_stale_job(
        job_id, max_running_seconds=_quality_job_recovery_seconds(quality, job_id),
    )


@quality_eval_router.get("/evaluation")
def get_evaluation(seq: int, request: Request, work: str = "main"):
    store = _store_for_request(request, work)
    job_id = _latest_job_id_for_seq(store, seq)
    if job_id is None:
        return {"chapter": seq, "dimensions": [], "status": "empty"}
    quality = QualityStore(store)
    status = _recoverable_job_status(quality, job_id)
    if status.status != "completed":
        return _job_state_payload(job_id=job_id, status=status, seq=seq)
    evaluation = quality.get_evaluation(job_id)
    return _shape_evaluation(evaluation, seq, quality=quality)


@quality_eval_router.post("/jobs/{job_id}/retry", status_code=202)
def retry_evaluation(job_id: str, body: ContractApprovalBody, request: Request):
    quality = QualityStore(_store_for_request(request, body.work))
    try:
        job = quality.get_job(job_id)
        status = _recoverable_job_status(quality, job_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    if job.work != body.work:
        raise HTTPException(404, "质量作业不属于当前作品")
    if status.status != "retryable_failed":
        raise HTTPException(409, f"质量作业当前不可重试: {status.status}")
    _dispatch_quality_job(work=body.work, job_id=job.job_id)
    # ``queued`` 表示已交给受限后台执行器；持久态将在 worker 抢到作业后转为 running。
    return {"job_id": job.job_id, "status": "queued"}


@quality_eval_router.get("/reference-craft-uses")
def list_reference_craft_uses(chapter: int, request: Request, work: str = "main"):
    """返回已经发生的参考技法消费账本，供作者与验收只读核验。

    这里绝不返回参考原文、指纹全文、提示词或模型输出；只给可关联到 Manifest 的
    使用标识，避免把验收查询变成新的参考内容读取通道。
    """
    rows = _store_for_request(request, work)._query(
        "SELECT chapter, request_id, manifest_id, reference_fingerprint_ids, mechanism_ids, created_at "
        "FROM reference_craft_use WHERE work=$work AND chapter=$chapter "
        "ORDER BY created_at DESC",
        {"work": work, "chapter": chapter},
    )
    fields = ("chapter", "request_id", "manifest_id", "reference_fingerprint_ids", "mechanism_ids")
    return [{field: row.get(field) for field in fields} for row in rows]


@quality_eval_router.get("/evaluation-traces")
def get_evaluation_traces(seq: int, request: Request, work: str = "main"):
    """返回质量判断对应的最小执行证据，不暴露提示词、正文或参考文本。"""
    store = _store_for_request(request, work)
    job_id = _latest_job_id_for_seq(store, seq)
    if job_id is None:
        return []
    quality = QualityStore(store)
    if quality.get_job_status(job_id).status != "completed":
        return []
    evaluation = quality.get_evaluation(job_id)
    return [{
        "dimension": bound.judgment.dimension,
        "evaluator_kind": bound.judgment.evaluator_kind,
        "outcome_id": bound.trace.outcome_id,
        "request_id": bound.trace.request_id,
        "manifest_id": bound.trace.manifest_id,
        "provider": bound.trace.provider,
        "model": bound.trace.model,
        "provider_request_id": bound.trace.provider_request_id,
        "usage": bound.trace.usage,
    } for bound in evaluation.system_reference_judgments]


@quality_eval_router.post("/author-judgment", status_code=201)
def save_author_judgment(body: AuthorJudgmentBody, request: Request):
    store = _store_for_request(request, body.work)
    job_id = _latest_job_id_for_seq(store, body.seq)
    if job_id is None:
        raise HTTPException(404, f"章节 {body.seq} 尚无质量作业,请先创建评价")
    quality = QualityStore(store)
    if quality.get_job_status(job_id).status != "completed":
        raise HTTPException(409, "质量评价尚未完成，暂不能提交作者裁决")
    evaluation = quality.get_evaluation(job_id)
    dim_key = next((d.key for d in CORE_DIMENSIONS if d.key == body.dimension or d.label == body.dimension), None)
    if dim_key is None:
        raise HTTPException(422, f"未知质量维度: {body.dimension}")
    unit = evaluation.units[0].chapter_version_id
    system_judgment = next(
        (b.judgment for b in evaluation.system_reference_judgments
         if b.judgment.dimension == dim_key and b.judgment.evaluator_kind == "system"),
        None,
    )
    author = QualityJudgment(
        dimension=dim_key,
        evaluator_kind="author",
        state=JudgmentState.EVALUABLE,
        score=body.score,
        effect=body.reason,
        mechanism=f"作者裁决：{body.decision}",
        evidence=body.evidence,
        counter_evidence=body.counter_evidence,
        confidence_components=_author_confidence(),
    )
    try:
        verdict = quality.save_author_verdict(
            job_id, unit=unit, judgment=author,
            decision=body.decision, reason=body.reason,
        )
    except ValueError as exc:
        # 评价卡可能来自旧冻结版本；这属于作者可恢复的校验冲突，不能泄露成 500。
        raise HTTPException(422, str(exc)) from exc
    return {
        "ok": True,
        "dimension": dim_key,
        "score": body.score,
        "verdict": {
            "verdict_id": verdict.verdict_id,
            "revision": verdict.revision,
            "decision": verdict.decision,
            "reason": verdict.reason,
            "evidence": [_anchor_payload(anchor) for anchor in verdict.judgment.evidence],
            "counter_evidence": [
                _anchor_payload(anchor) for anchor in verdict.judgment.counter_evidence
            ],
        },
    }


def _author_confidence():
    from scribe3.quality.models import ConfidenceComponents
    return ConfidenceComponents(
        context_coverage=1.0, evidence_validity=1.0,
        calibration_reliability=1.0, independence_factor=1.0, stability_factor=1.0,
    )
