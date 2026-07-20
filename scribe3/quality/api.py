"""参考作品与质量评价 API 路由。"""
from __future__ import annotations

from typing import Any

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


class PatchBody(BaseModel):
    work: str
    title: str | None = None


def _service(request: Request) -> ReferenceService:
    return ReferenceService(request.app.state.store)


@quality_router.post("/import", status_code=201)
def import_reference(body: ImportBody, request: Request):
    if not body.text and not body.file_src:
        from fastapi import HTTPException
        raise HTTPException(422, "必须提供 text 或 file_src")
    svc = _service(request)
    record = svc.import_reference(
        work=body.work, title=body.title,
        text=body.text, file_src=body.file_src,
    )
    return record.model_dump(mode="json")


@quality_router.post("/{reference_work_id}/fingerprints", status_code=201)
def generate_fingerprint(reference_work_id: str, body: FingerprintBody, request: Request):
    svc = _service(request)
    llm = _get_deepseek_client()
    record = svc.generate_fingerprint(
        reference_work_id=reference_work_id, llm=llm,
    )
    return record.model_dump(mode="json")


@quality_router.get("/{reference_work_id}/fingerprints")
def list_fingerprints(reference_work_id: str, work: str, request: Request):
    store = request.app.state.store
    rows = store._query(
        "SELECT fingerprint_id, reference_work_id, revision, source_hash, "
        "status, fingerprint FROM reference_fingerprint "
        "WHERE reference_work_id=$rid ORDER BY revision DESC",
        {"rid": reference_work_id},
    )
    return rows


@quality_router.patch("/{reference_work_id}")
def patch_reference(reference_work_id: str, body: PatchBody, request: Request):
    store = request.app.state.store
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
from scribe3.quality.evaluator import QualityEvaluator
from scribe3.quality.models import JudgmentState, QualityJudgment
from scribe3.quality.rubrics import CORE_DIMENSIONS
from scribe3.quality.store import QualityStore

_DIM_LABEL = {d.key: d.label for d in CORE_DIMENSIONS}
_DEFAULT_WEIGHTS = (0.50, 0.30, 0.20)


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


def _chapter_version_ids_for_seq(store, seq: int) -> list[str]:
    rows = store._query(
        "SELECT VALUE id FROM chapter_version WHERE seq=$seq", {"seq": seq},
    )
    return [str(rid) for rid in rows]


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


def _shape_evaluation(evaluation, seq: int) -> dict[str, Any]:
    by_dim: dict[str, dict[str, Any]] = {}
    for bound in evaluation.system_reference_judgments:
        judgment = bound.judgment
        by_dim.setdefault(judgment.dimension, {})[judgment.evaluator_kind] = judgment
    author_by_dim = {j.dimension: j for j in evaluation.author_judgments}
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
                "evidence": [
                    {"quote": a.quote, "start_utf16": a.start_utf16, "end_utf16": a.end_utf16}
                    for a in sys_j.evidence
                ],
            }
        reference = {"score": ref_j.score} if ref_j is not None else None
        author = {"score": author_j.score} if author_j is not None else None
        decision_index = None
        if author_j is not None and sys_j is not None and ref_j is not None:
            decision_index = merge_three_axes(
                author=author_j.score, system=sys_j.score, reference=ref_j.score,
                weights=_DEFAULT_WEIGHTS,
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
    return {"chapter": seq, "dimensions": dimensions, "status": "ready"}


@quality_eval_router.post("/snapshot", status_code=201)
def create_evaluation(body: SnapshotBody, request: Request):
    store = request.app.state.store
    version_ids = _chapter_version_ids_for_seq(store, body.seq)
    if not version_ids:
        raise HTTPException(404, f"章节 {body.seq} 没有可冻结的版本")
    evaluator = QualityEvaluator(store, _get_deepseek_client())
    evaluation = evaluator.evaluate_chapter(
        work=body.work,
        chapter_version_ids=tuple(version_ids),
        contract_id=body.contract_id,
        contract_revision=body.contract_revision,
        reference_fingerprint_ids=body.reference_fingerprint_ids,
    )
    return _shape_evaluation(evaluation, body.seq)


@quality_eval_router.get("/evaluation")
def get_evaluation(seq: int, request: Request):
    store = request.app.state.store
    job_id = _latest_job_id_for_seq(store, seq)
    if job_id is None:
        return {"chapter": seq, "dimensions": [], "status": "empty"}
    evaluation = QualityStore(store).get_evaluation(job_id)
    return _shape_evaluation(evaluation, seq)


@quality_eval_router.post("/author-judgment", status_code=201)
def save_author_judgment(body: AuthorJudgmentBody, request: Request):
    store = request.app.state.store
    job_id = _latest_job_id_for_seq(store, body.seq)
    if job_id is None:
        raise HTTPException(404, f"章节 {body.seq} 尚无质量作业,请先创建评价")
    quality = QualityStore(store)
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
    evidence = system_judgment.evidence if system_judgment is not None else ()
    author = QualityJudgment(
        dimension=dim_key,
        evaluator_kind="author",
        state=JudgmentState.EVALUABLE,
        score=body.score,
        effect=system_judgment.effect if system_judgment is not None else "作者评分",
        mechanism=system_judgment.mechanism if system_judgment is not None else "作者裁决",
        evidence=evidence,
        confidence_components=(
            system_judgment.confidence_components if system_judgment is not None
            else _author_confidence()
        ),
    )
    quality.save_author_judgment(job_id, unit=unit, judgment=author)
    return {"ok": True, "dimension": dim_key, "score": body.score}


def _author_confidence():
    from scribe3.quality.models import ConfidenceComponents
    return ConfidenceComponents(
        context_coverage=1.0, evidence_validity=1.0,
        calibration_reliability=1.0, independence_factor=1.0, stability_factor=1.0,
    )
