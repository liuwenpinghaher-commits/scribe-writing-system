"""质量决策领域的 SurrealDB 权威存储适配器。"""
from __future__ import annotations

from hashlib import sha256
import json
import time
from typing import Any, Literal, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, model_validator
from surrealdb import RecordID

from scribe3.quality.models import QualityContractRevision, QualityJudgment

if TYPE_CHECKING:
    from scribe3.store import SurrealStore


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


def _bare(record_id: str, table: str) -> str:
    value = str(record_id).strip()
    prefix = f"{table}:"
    return value[len(prefix):] if value.startswith(prefix) else value


def _full(record_id: str, table: str) -> str:
    return f"{table}:{_bare(record_id, table)}"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ReferenceWorkRecord(_FrozenModel):
    reference_work_id: str = Field(min_length=1)
    work: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    import_revision: int = Field(ge=1)
    status: str = Field(min_length=1)


class ReferenceFingerprintRecord(_FrozenModel):
    fingerprint_id: str = ""
    reference_work_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str = Field(min_length=1)
    fingerprint: dict[str, Any]

    @model_validator(mode="after")
    def fill_identity(self) -> "ReferenceFingerprintRecord":
        expected = _digest({
            "reference_work_id": self.reference_work_id,
            "revision": self.revision,
        })
        if self.fingerprint_id and self.fingerprint_id != expected:
            raise ValueError("fingerprint_id 与参考作品修订不一致")
        if not self.fingerprint_id:
            object.__setattr__(self, "fingerprint_id", expected)
        return self


class QualitySnapshotMember(_FrozenModel):
    chapter_version_id: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    ordinal: int = Field(ge=0)


class QualitySnapshotRecord(_FrozenModel):
    snapshot_id: str = Field(min_length=1)
    work: str = Field(min_length=1)
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    members: tuple[QualitySnapshotMember, ...] = Field(min_length=1)


class QualityJobRecord(_FrozenModel):
    job_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    work: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    contract_id: str = Field(min_length=1)
    contract_revision: int = Field(ge=1)
    rubric_revision: str = Field(min_length=1)
    reference_fingerprint_ids: tuple[str, ...] = ()
    model_settings: dict[str, Any]
    actual_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_id: str | None = None
    manifest_id: str | None = None
    provider_request_id: str | None = None
    provider_model: str | None = None
    provider_usage: dict[str, Any] | None = None

class QualityEvaluationUnit(_FrozenModel):
    chapter_version_id: str
    ordinal: int
    content_hash: str
    prose: str


class QualityEvaluation(_FrozenModel):
    job: QualityJobRecord
    units: tuple[QualityEvaluationUnit, ...]
    system_reference_judgments: tuple["BoundQualityJudgment", ...]
    author_judgments: tuple[QualityJudgment, ...]


class JudgmentTraceBinding(_FrozenModel):
    outcome_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    manifest_id: str = Field(min_length=1)
    actual_input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    provider_request_id: str = Field(min_length=1)
    usage: dict[str, Any]


class BoundQualityJudgment(_FrozenModel):
    judgment: QualityJudgment
    trace: JudgmentTraceBinding


class QualityStore:
    """只包装调用方注入的 ``SurrealStore``，不拥有连接或正文副本。"""

    def __init__(self, store: "SurrealStore"):
        self._store = store

    @staticmethod
    def _retry_read(loader, attempts: int = 5):
        for attempt in range(attempts):
            value = loader()
            if value is not None:
                return value
            if attempt + 1 < attempts:
                time.sleep(0.01 * (attempt + 1))
        return None

    def save_contract_revision(
        self, contract: QualityContractRevision,
    ) -> QualityContractRevision:
        key = f"{contract.contract_id}:{contract.revision}"
        record_id = _digest(key)
        payload = contract.model_dump(mode="json", exclude={"approved", "reference_targets"})
        expected = contract.model_copy(update={"approved": False})
        try:
            with self._store.transaction():
                self._store._execute_write(
                    "CREATE ONLY type::record('quality_contract_revision',$record_id) SET "
                    "contract_key=$key, contract_id=$contract_id, work=$work, revision=$revision, "
                    "payload=$payload, approved=false, approval_version=0",
                    {"record_id": record_id, "key": key, "contract_id": contract.contract_id,
                     "work": contract.work, "revision": contract.revision, "payload": payload},
                )
                for ordinal, target in enumerate(contract.reference_targets):
                    self._store._execute_write(
                        "CREATE ONLY type::record('reference_target',$record_id) SET "
                        "target_key=$target_key, contract_revision=$contract_revision, "
                        "ordinal=$ordinal, payload=$payload",
                        {"record_id": _digest(f"{key}:{ordinal}"),
                         "target_key": f"{key}:{ordinal}",
                         "contract_revision": RecordID("quality_contract_revision", record_id),
                         "ordinal": ordinal, "payload": target.model_dump(mode="json")},
                    )
        except Exception as conflict:
            existing = self._retry_read(
                lambda: self._get_contract(contract.contract_id, contract.revision)
            )
            if existing is None:
                raise conflict
            if existing.model_copy(update={"approved": False}) != expected:
                raise ValueError("合同修订与既有 append-only 当前真相冲突") from conflict
            return existing
        return expected

    def _get_contract(self, contract_id: str, revision: int) -> QualityContractRevision | None:
        rows = self._store._query(
            "SELECT payload, approved FROM quality_contract_revision "
            "WHERE contract_id=$contract_id AND revision=$revision LIMIT 1",
            {"contract_id": contract_id, "revision": revision},
        )
        if not rows:
            return None
        payload = dict(rows[0]["payload"])
        targets = self._store._query(
            "SELECT payload, ordinal FROM reference_target WHERE contract_revision = "
            "(SELECT VALUE id FROM quality_contract_revision WHERE contract_id=$contract_id "
            "AND revision=$revision LIMIT 1)[0] ORDER BY ordinal",
            {"contract_id": contract_id, "revision": revision},
        )
        payload["reference_targets"] = [row["payload"] for row in targets]
        payload["approved"] = bool(rows[0].get("approved"))
        return QualityContractRevision.model_validate(payload)

    def approve_contract(
        self, contract_id: str, revision: int, *, expected_approved: bool,
    ) -> QualityContractRevision:
        if expected_approved:
            raise ValueError("CAS 只允许从未批准单向转为已批准")
        rows = self._store._query(
            "UPDATE quality_contract_revision SET approved=true, approval_version += 1, "
            "approved_at=time::now() WHERE contract_id=$contract_id AND revision=$revision "
            "AND approved=false AND approval_version=0 RETURN AFTER",
            {"contract_id": contract_id, "revision": revision},
        )
        if len(rows) != 1:
            raise ValueError("合同批准 CAS 失败：修订不存在、状态已批准或已变化")
        approved = self._get_contract(contract_id, revision)
        if approved is None:
            raise RuntimeError("合同批准后无法读回")
        return approved

    def save_reference_work(self, work: ReferenceWorkRecord) -> ReferenceWorkRecord:
        key = f"{work.reference_work_id}:{work.import_revision}"
        record_id = _digest(key)
        try:
            self._store._execute_write(
                "CREATE ONLY type::record('reference_work',$record_id) SET "
                "reference_key=$key, reference_work_id=$reference_work_id, work=$work, "
                "title=$title, source_hash=$source_hash, import_revision=$import_revision, "
                "status=$status",
                {"record_id": record_id, "key": key, **work.model_dump(mode="json")},
            )
        except Exception as conflict:
            existing = self._retry_read(
                lambda: self._get_reference_work(work.reference_work_id, work.import_revision)
            )
            if existing is None:
                raise conflict
            if existing != work:
                raise ValueError("参考作品修订与既有当前真相冲突") from conflict
            return existing
        return work

    def _get_reference_work(
        self, reference_work_id: str, import_revision: int,
    ) -> ReferenceWorkRecord | None:
        rows = self._store._query(
            "SELECT reference_work_id, work, title, source_hash, import_revision, status "
            "FROM reference_work WHERE reference_work_id=$reference_work_id "
            "AND import_revision=$import_revision LIMIT 1",
            {"reference_work_id": reference_work_id, "import_revision": import_revision},
        )
        return ReferenceWorkRecord.model_validate(rows[0]) if rows else None

    def save_reference_fingerprint(
        self, fingerprint: ReferenceFingerprintRecord,
    ) -> ReferenceFingerprintRecord:
        works = self._store._query(
            "SELECT id, source_hash, import_revision FROM reference_work WHERE "
            "reference_work_id=$reference_work_id AND source_hash=$source_hash "
            "ORDER BY import_revision DESC LIMIT 1",
            {"reference_work_id": fingerprint.reference_work_id,
             "source_hash": fingerprint.source_hash},
        )
        if not works or works[0]["source_hash"] != fingerprint.source_hash:
            raise ValueError("参考指纹必须绑定 source_hash 一致的参考作品修订")
        record_id = fingerprint.fingerprint_id
        try:
            self._store._execute_write(
                "CREATE ONLY type::record('reference_fingerprint',$record_id) SET "
                "fingerprint_id=$fingerprint_id, reference_work=$reference_work, "
                "reference_work_id=$reference_work_id, revision=$revision, "
                "source_hash=$source_hash, status=$status, fingerprint=$fingerprint",
                {"record_id": record_id, "fingerprint_id": fingerprint.fingerprint_id,
                 "reference_work": works[0]["id"],
                 **fingerprint.model_dump(mode="json", exclude={"fingerprint_id"})},
            )
        except Exception as conflict:
            existing = self._retry_read(lambda: self._get_fingerprint(record_id))
            if existing is None:
                raise conflict
            if existing != fingerprint:
                raise ValueError("参考指纹修订与既有当前真相冲突") from conflict
            return existing
        return fingerprint

    def _get_fingerprint(self, fingerprint_id: str) -> ReferenceFingerprintRecord | None:
        rows = self._store._query(
            "SELECT fingerprint_id, reference_work_id, revision, source_hash, status, "
            "fingerprint FROM reference_fingerprint WHERE fingerprint_id=$fingerprint_id LIMIT 1",
            {"fingerprint_id": fingerprint_id},
        )
        return ReferenceFingerprintRecord.model_validate(rows[0]) if rows else None

    def create_chapter_snapshot(
        self, *, work: str, chapter_version_ids: tuple[str, ...],
    ) -> QualitySnapshotRecord:
        if not chapter_version_ids:
            raise ValueError("质量快照至少包含一个章节版本")
        members: list[QualitySnapshotMember] = []
        for ordinal, raw_id in enumerate(chapter_version_ids):
            bare = _bare(raw_id, "chapter_version")
            version = self._store.get_chapter_version(bare)
            if version is None:
                raise ValueError(f"章节版本不存在: {raw_id}")
            full_id = _full(bare, "chapter_version")
            prose = version.get("prose") or ""
            members.append(QualitySnapshotMember(
                chapter_version_id=full_id,
                content_hash=sha256(prose.encode("utf-8")).hexdigest(),
                ordinal=ordinal,
            ))
        snapshot_hash = _digest({"work": work, "members": [m.model_dump() for m in members]})
        snapshot = QualitySnapshotRecord(
            snapshot_id=snapshot_hash, work=work, snapshot_hash=snapshot_hash,
            members=tuple(members),
        )
        try:
            with self._store.transaction():
                self._store._execute_write(
                    "CREATE ONLY type::record('quality_snapshot',$record_id) SET "
                    "snapshot_id=$snapshot_id, work=$work, snapshot_hash=$snapshot_hash, "
                    "member_count=$member_count",
                    {"record_id": snapshot.snapshot_id, "snapshot_id": snapshot.snapshot_id,
                     "work": work, "snapshot_hash": snapshot_hash,
                     "member_count": len(members)},
                )
                for member in members:
                    member_id = _digest(f"{snapshot.snapshot_id}:{member.ordinal}")
                    self._store._execute_write(
                        "CREATE ONLY type::record('quality_snapshot_member',$record_id) SET "
                        "member_key=$member_key, snapshot=$snapshot, ordinal=$ordinal, "
                        "chapter_version=$chapter_version, content_hash=$content_hash",
                        {"record_id": member_id,
                         "member_key": f"{snapshot.snapshot_id}:{member.ordinal}",
                         "snapshot": RecordID("quality_snapshot", snapshot.snapshot_id),
                         "ordinal": member.ordinal,
                         "chapter_version": RecordID(
                             "chapter_version", _bare(member.chapter_version_id, "chapter_version")
                         ),
                         "content_hash": member.content_hash},
                    )
        except Exception as conflict:
            existing = self._retry_read(lambda: self._get_snapshot(snapshot.snapshot_id))
            if existing is None:
                raise conflict
            if existing != snapshot:
                raise ValueError("质量快照 hash 与既有当前真相冲突") from conflict
            return existing
        return snapshot

    def _get_snapshot(self, snapshot_id: str) -> QualitySnapshotRecord | None:
        rows = self._store._query(
            "SELECT snapshot_id, work, snapshot_hash, member_count FROM quality_snapshot "
            "WHERE snapshot_id=$snapshot_id LIMIT 1", {"snapshot_id": snapshot_id},
        )
        if not rows:
            return None
        member_rows = self._store._query(
            "SELECT <string> chapter_version AS chapter_version_id, content_hash, ordinal "
            "FROM quality_snapshot_member WHERE snapshot=$snapshot ORDER BY ordinal",
            {"snapshot": RecordID("quality_snapshot", snapshot_id)},
        )
        return QualitySnapshotRecord(
            snapshot_id=rows[0]["snapshot_id"], work=rows[0]["work"],
            snapshot_hash=rows[0]["snapshot_hash"],
            members=tuple(QualitySnapshotMember.model_validate(row) for row in member_rows),
        )

    def get_snapshot(self, snapshot_id: str) -> QualitySnapshotRecord:
        snapshot = self._get_snapshot(snapshot_id)
        if snapshot is None:
            raise ValueError("质量快照不存在")
        self._assert_snapshot_current(snapshot)
        return snapshot

    def _assert_snapshot_current(self, snapshot: QualitySnapshotRecord) -> None:
        for member in snapshot.members:
            version = self._store.get_chapter_version(
                _bare(member.chapter_version_id, "chapter_version")
            )
            prose = (version or {}).get("prose")
            if prose is None or sha256(prose.encode("utf-8")).hexdigest() != member.content_hash:
                raise ValueError("冻结章节版本发生 content_hash 漂移")

    def _queue_snapshot_guard(self, snapshot: QualitySnapshotRecord) -> None:
        """把正文 hash 断言排入调用方的同一 SurrealDB 写事务。"""
        for member in snapshot.members:
            self._store._execute_write(
                "LET $current = (SELECT prose FROM $chapter_version); "
                "IF array::len($current) != 1 OR "
                "crypto::sha256($current[0].prose) != $content_hash "
                "{ THROW 'quality_snapshot_drift' }",
                {"chapter_version": RecordID(
                    "chapter_version", _bare(member.chapter_version_id, "chapter_version")
                ), "content_hash": member.content_hash},
            )

    def create_job(
        self, *, work: str, snapshot_id: str, contract_id: str,
        contract_revision: int, rubric_revision: str,
        reference_fingerprint_ids: tuple[str, ...], model_config: dict[str, Any],
        actual_input_hash: str, idempotency_key: str,
        request_id: str | None = None, manifest_id: str | None = None,
        provider_request_id: str | None = None, provider_model: str | None = None,
        provider_usage: dict[str, Any] | None = None,
    ) -> QualityJobRecord:
        snapshot = self.get_snapshot(snapshot_id)
        contract = self._get_contract(contract_id, contract_revision)
        if snapshot is None or snapshot.work != work:
            raise ValueError("质量作业快照不存在或不属于当前作品")
        if contract is None or not contract.approved or contract.work != work:
            raise ValueError("质量作业必须绑定当前作品已批准的合同修订")
        fingerprints = []
        for fingerprint_id in reference_fingerprint_ids:
            fingerprint = self._get_fingerprint(fingerprint_id)
            if fingerprint is None:
                raise ValueError(f"参考指纹不存在: {fingerprint_id}")
            fingerprints.append(RecordID("reference_fingerprint", fingerprint_id))
        job = QualityJobRecord(
            job_id=_digest(idempotency_key), idempotency_key=idempotency_key, work=work,
            snapshot_id=snapshot_id, contract_id=contract_id,
            contract_revision=contract_revision, rubric_revision=rubric_revision,
            reference_fingerprint_ids=reference_fingerprint_ids,
            model_settings=model_config, actual_input_hash=actual_input_hash,
            request_id=request_id, manifest_id=manifest_id,
            provider_request_id=provider_request_id, provider_model=provider_model,
            provider_usage=provider_usage,
        )
        params = job.model_dump(mode="json")
        try:
            with self._store.transaction():
                self._queue_snapshot_guard(snapshot)
                self._store._execute_write(
                    "CREATE ONLY type::record('quality_job',$record_id) SET job_id=$job_id, "
                    "idempotency_key=$idempotency_key, work=$work, snapshot=$snapshot, "
                    "snapshot_id=$snapshot_id, contract_revision=$contract_revision_record, "
                    "contract_id=$contract_id, contract_revision_number=$contract_revision, "
                    "rubric_revision=$rubric_revision, "
                    "reference_fingerprints=$reference_fingerprints, "
                    "reference_fingerprint_ids=$reference_fingerprint_ids, "
                    "model_config=$model_settings, "
                    "actual_input_hash=$actual_input_hash, request_id=$request_id, "
                    "manifest_id=$manifest_id, provider_request_id=$provider_request_id, "
                    "provider_model=$provider_model, provider_usage=$provider_usage",
                    {**params, "record_id": job.job_id,
                     "snapshot": RecordID("quality_snapshot", snapshot_id),
                     "contract_revision_record": RecordID(
                         "quality_contract_revision", _digest(f"{contract_id}:{contract_revision}")
                     ),
                     "reference_fingerprints": fingerprints},
                )
        except Exception as conflict:
            try:
                self._assert_snapshot_current(snapshot)
            except ValueError as drift:
                raise drift from conflict
            existing = self._retry_read(lambda: self._get_job_by_key(idempotency_key))
            if existing is None:
                raise conflict
            if existing != job:
                raise ValueError("质量 job 幂等键与既有当前真相冲突") from conflict
            return existing
        return job

    def _get_job_by_key(self, idempotency_key: str) -> QualityJobRecord | None:
        rows = self._store._query(
            "SELECT job_id, idempotency_key, work, snapshot.snapshot_id AS snapshot_id, "
            "contract_revision.contract_id AS contract_id, "
            "contract_revision.revision AS contract_revision, rubric_revision, "
            "reference_fingerprints.fingerprint_id AS reference_fingerprint_ids, "
            "model_config AS model_settings, actual_input_hash, request_id, manifest_id, provider_request_id, "
            "provider_model, provider_usage FROM quality_job "
            "WHERE idempotency_key=$idempotency_key LIMIT 1",
            {"idempotency_key": idempotency_key},
        )
        return QualityJobRecord.model_validate(rows[0]) if rows else None

    def _get_job(self, job_id: str) -> QualityJobRecord | None:
        rows = self._store._query(
            "SELECT idempotency_key FROM quality_job WHERE job_id=$job_id LIMIT 1",
            {"job_id": _bare(job_id, "quality_job")},
        )
        return self._get_job_by_key(rows[0]["idempotency_key"]) if rows else None

    def _validate_anchor(self, snapshot: QualitySnapshotRecord, anchor) -> None:
        member = next((m for m in snapshot.members
                       if m.chapter_version_id == _full(anchor.chapter_version_id, "chapter_version")), None)
        if member is None or member.content_hash != anchor.content_hash:
            raise ValueError("证据 content_hash 或章节版本不属于冻结快照")
        version = self._store.get_chapter_version(
            _bare(member.chapter_version_id, "chapter_version")
        )
        prose = (version or {}).get("prose")
        if prose is None or sha256(prose.encode("utf-8")).hexdigest() != member.content_hash:
            raise ValueError("冻结正文 content_hash 已失配")
        raw = prose.encode("utf-16-le")
        try:
            quote = raw[anchor.start_utf16 * 2:anchor.end_utf16 * 2].decode("utf-16-le")
        except UnicodeDecodeError as exc:
            raise ValueError("证据 UTF-16 锚点切断代理对") from exc
        if quote != anchor.quote:
            raise ValueError("证据 UTF-16 范围无法回指权威正文")

    def _save_axis(
        self, *, table: Literal["quality_judgment", "quality_author_judgment"],
        job_id: str, unit: str, judgments: tuple[BoundQualityJudgment, ...],
        allowed: set[str],
    ) -> tuple[BoundQualityJudgment, ...]:
        job = self._get_job(job_id)
        if job is None:
            raise ValueError("质量作业不存在")
        snapshot = self.get_snapshot(job.snapshot_id)
        unit = _full(unit, "chapter_version")
        if unit not in {member.chapter_version_id for member in snapshot.members}:
            raise ValueError("判断单元不属于质量作业冻结快照")
        for bound in judgments:
            judgment = bound.judgment
            if judgment.evaluator_kind not in allowed:
                raise ValueError(
                    f"{table} 只接受 system/reference，不接受 "
                    f"{judgment.evaluator_kind} 判断"
                )
            outcome_rows = self._store._query(
                "SELECT outcome_id, request_id, manifest_id, actual_input_hash, status, provider, "
                "model, provider_request_id, usage FROM context_outcome_trace "
                "WHERE outcome_id=$outcome_id LIMIT 1",
                {"outcome_id": bound.trace.outcome_id},
            )
            if not outcome_rows:
                raise ValueError("LLM 判断没有绑定既有 ContextOutcome")
            if outcome_rows[0].get("status") != "succeeded":
                raise ValueError("LLM 判断只能绑定 status=succeeded 的成功 Outcome")
            persisted_trace = JudgmentTraceBinding.model_validate({
                key: value for key, value in outcome_rows[0].items()
                if key != "status"
            })
            if persisted_trace != bound.trace:
                raise ValueError("LLM 判断 trace 与 ContextOutcome 当前真相不一致")
            for anchor in judgment.evidence + judgment.counter_evidence:
                self._validate_anchor(snapshot, anchor)
        try:
            with self._store.transaction():
                self._queue_snapshot_guard(snapshot)
                for bound in judgments:
                    judgment = bound.judgment
                    identity = f"{job.job_id}:{unit}:{judgment.dimension}:{judgment.evaluator_kind}"
                    judgment_id = _digest(identity)
                    self._store._execute_write(
                        f"CREATE ONLY type::record('{table}',$record_id) SET "
                        "judgment_id=$judgment_id, job=$job, job_id=$job_id, unit=$unit, "
                        "unit_id=$unit_id, dimension=$dimension, evaluator_kind=$evaluator_kind, "
                        "payload=$payload, context_outcome=$context_outcome, "
                        "outcome_id=$outcome_id, request_id=$request_id, manifest_id=$manifest_id, "
                        "actual_input_hash=$actual_input_hash, provider=$provider, model=$model, "
                        "provider_request_id=$provider_request_id, usage=$usage",
                        {"record_id": judgment_id, "judgment_id": judgment_id,
                         "job": RecordID("quality_job", job.job_id),
                         "job_id": job.job_id,
                         "unit": RecordID("chapter_version", _bare(unit, "chapter_version")),
                         "unit_id": unit,
                         "dimension": judgment.dimension,
                         "evaluator_kind": judgment.evaluator_kind,
                         "payload": judgment.model_dump(mode="json"),
                         "context_outcome": RecordID(
                             "context_outcome_trace", bound.trace.outcome_id
                         ),
                         **bound.trace.model_dump(mode="json")},
                    )
        except Exception as conflict:
            try:
                self._assert_snapshot_current(snapshot)
            except ValueError as drift:
                raise drift from conflict
            existing = self._read_axis(table, job.job_id, unit)
            expected_by_key = {
                (j.judgment.dimension, j.judgment.evaluator_kind): j for j in judgments
            }
            existing_by_key = {
                (j.judgment.dimension, j.judgment.evaluator_kind): j for j in existing
            }
            if any(existing_by_key.get(key) != value for key, value in expected_by_key.items()):
                raise ValueError("质量判断与既有不可变当前真相冲突") from conflict
        return judgments

    def save_judgments(
        self, job_id: str, *, unit: str, judgments: tuple[BoundQualityJudgment, ...],
    ) -> tuple[BoundQualityJudgment, ...]:
        return self._save_axis(
            table="quality_judgment", job_id=job_id, unit=unit,
            judgments=judgments, allowed={"system", "reference"},
        )

    def save_author_judgment(
        self, job_id: str, *, unit: str, judgment: QualityJudgment,
    ) -> QualityJudgment:
        if judgment.evaluator_kind != "author":
            raise ValueError("quality_author_judgment 只接受 author 判断")
        job = self._get_job(job_id)
        if job is None:
            raise ValueError("质量作业不存在")
        snapshot = self.get_snapshot(job.snapshot_id)
        unit = _full(unit, "chapter_version")
        if unit not in {m.chapter_version_id for m in snapshot.members}:
            raise ValueError("作者判断单元不属于质量作业冻结快照")
        for anchor in judgment.evidence + judgment.counter_evidence:
            self._validate_anchor(snapshot, anchor)
        identity = f"{job.job_id}:{unit}:{judgment.dimension}:author"
        try:
            with self._store.transaction():
                self._queue_snapshot_guard(snapshot)
                self._store._execute_write(
                    "CREATE ONLY type::record('quality_author_judgment',$record_id) SET "
                    "judgment_id=$judgment_id, job=$job, job_id=$job_id, unit=$unit, "
                    "unit_id=$unit_id, dimension=$dimension, evaluator_kind='author', payload=$payload",
                    {"record_id": _digest(identity), "judgment_id": _digest(identity),
                     "job": RecordID("quality_job", job.job_id), "job_id": job.job_id,
                     "unit": RecordID("chapter_version", _bare(unit, "chapter_version")),
                     "unit_id": unit, "dimension": judgment.dimension,
                     "payload": judgment.model_dump(mode="json")},
                )
        except Exception as conflict:
            try:
                self._assert_snapshot_current(snapshot)
            except ValueError as drift:
                raise drift from conflict
            existing = self._read_author_axis(job.job_id, unit)
            match = next((item for item in existing if item.dimension == judgment.dimension), None)
            if match != judgment:
                raise ValueError("作者判断与既有不可变当前真相冲突") from conflict
        return judgment

    def _read_axis(self, table: str, job_id: str, unit: str | None = None) -> tuple[BoundQualityJudgment, ...]:
        query = (f"SELECT payload, outcome_id, request_id, manifest_id, actual_input_hash, "
                 f"provider, model, provider_request_id, usage, dimension, evaluator_kind "
                 f"FROM {table} WHERE job=$job")
        params: dict[str, Any] = {"job": RecordID("quality_job", _bare(job_id, "quality_job"))}
        if unit is not None:
            query += " AND unit=$unit"
            params["unit"] = RecordID("chapter_version", _bare(unit, "chapter_version"))
        query += " ORDER BY dimension, evaluator_kind"
        rows = self._store._query(query, params)
        parsed = [BoundQualityJudgment(
            judgment=QualityJudgment.model_validate(row["payload"]),
            trace=JudgmentTraceBinding.model_validate({
                key: row[key] for key in (
                    "outcome_id", "request_id", "manifest_id", "actual_input_hash",
                    "provider", "model", "provider_request_id", "usage",
                )
            }),
        ) for row in rows]
        parsed.sort(key=lambda item: (
            item.judgment.dimension,
            {"system": 0, "reference": 1}.get(item.judgment.evaluator_kind, 9),
        ))
        return tuple(parsed)

    def _read_author_axis(self, job_id: str, unit: str | None = None) -> tuple[QualityJudgment, ...]:
        query = "SELECT payload, dimension FROM quality_author_judgment WHERE job=$job"
        params: dict[str, Any] = {"job": RecordID("quality_job", _bare(job_id, "quality_job"))}
        if unit is not None:
            query += " AND unit=$unit"
            params["unit"] = RecordID("chapter_version", _bare(unit, "chapter_version"))
        query += " ORDER BY dimension"
        return tuple(
            QualityJudgment.model_validate(row["payload"])
            for row in self._store._query(query, params)
        )

    def get_evaluation(self, job_id: str) -> QualityEvaluation:
        job = self._get_job(job_id)
        if job is None:
            raise ValueError("质量作业不存在")
        snapshot = self._get_snapshot(job.snapshot_id)
        if snapshot is None:
            raise ValueError("质量快照不存在")
        units = []
        for member in snapshot.members:
            version = self._store.get_chapter_version(
                _bare(member.chapter_version_id, "chapter_version")
            )
            prose = (version or {}).get("prose")
            if prose is None or sha256(prose.encode("utf-8")).hexdigest() != member.content_hash:
                raise ValueError("冻结正文与质量快照 hash 不一致")
            units.append(QualityEvaluationUnit(
                chapter_version_id=member.chapter_version_id, ordinal=member.ordinal,
                content_hash=member.content_hash, prose=prose,
            ))
        return QualityEvaluation(
            job=job, units=tuple(units),
            system_reference_judgments=self._read_axis("quality_judgment", job.job_id),
            author_judgments=self._read_author_axis(job.job_id),
        )
