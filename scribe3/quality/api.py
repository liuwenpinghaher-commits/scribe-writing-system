"""参考作品 API 路由。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from scribe3.quality.references import ReferenceService

quality_router = APIRouter(prefix="/references", tags=["references"])


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
        from fastapi import HTTPException
        raise HTTPException(404, "参考作品不存在")
    return rows[0]
