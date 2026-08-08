"""Task 4: 参考作品 API 端点 RED 测试。"""
import hashlib
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scribe3.quality.api import quality_router, quality_eval_router
from scribe3.quality.api import _chapter_version_ids_for_seq


@pytest.fixture
def client(store):
    app = FastAPI()
    app.include_router(quality_router)
    app.include_router(quality_eval_router)
    app.state.store = store
    return TestClient(app)


def test_chapter_evaluation_freezes_only_latest_version_for_a_sequence(store):
    old = store.add_chapter_version(1, "旧版本", label="旧", kind="checkpoint", stage="final")
    latest = store.add_chapter_version(1, "当前版本", label="新", kind="checkpoint", stage="final")

    assert _chapter_version_ids_for_seq(store, 1) == [f"chapter_version:{latest}"]
    assert old != latest


class TestImportEndpoint:
    def test_import_resolves_store_by_requested_work_not_legacy_app_state(self, store):
        app = FastAPI()
        app.include_router(quality_router)
        resolved = []

        def store_for(work):
            resolved.append(work)
            return store

        app.state.store_for = store_for
        client = TestClient(app)
        response = client.post("/references/import", json={
            "work": store.db_name, "title": "分库参考", "text": "参考内容。" * 20,
        })

        assert response.status_code == 201
        assert resolved == [store.db_name]

    def test_import_pasted_text(self, client, store):
        resp = client.post("/references/import", json={
            "work": store.db_name, "title": "粘贴参考",
            "text": "参考内容。" * 20,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["reference_work_id"]
        assert body["title"] == "粘贴参考"
        assert body["status"] == "imported"

    def test_list_references_is_scoped_to_requested_work(self, client, store):
        client.post("/references/import", json={
            "work": store.db_name, "title": "当前书参考", "text": "内容。" * 20,
        })
        response = client.get("/references", params={"work": store.db_name})
        assert response.status_code == 200
        assert [row["title"] for row in response.json()] == ["当前书参考"]

    def test_import_requires_title(self, client, store):
        resp = client.post("/references/import", json={
            "work": store.db_name, "text": "内容",
        })
        assert resp.status_code == 422

    def test_import_requires_text_or_file(self, client, store):
        resp = client.post("/references/import", json={
            "work": store.db_name, "title": "空导入",
        })
        assert resp.status_code == 422


class TestFingerprintEndpoints:
    def _import(self, client, store, title="指纹参考"):
        resp = client.post("/references/import", json={
            "work": store.db_name, "title": title,
            "text": "参考正文。" * 50,
        })
        return resp.json()["reference_work_id"]

    def test_generate_fingerprint(self, client, store, monkeypatch):
        ref_id = self._import(client, store)
        fp_json = json.dumps({
            "local_mechanisms": ["悬念"], "cross_chapter_aggregation": "三幕",
            "full_book_fingerprint": "冷硬", "evidence": [{"quote": "a", "location": "b"}],
            "counter_evidence": [{"quote": "c", "location": "d"}],
            "transferable_mechanisms": ["视角"], "non_copyable_elements": ["方言"],
            "applicable_scope": "悬疑",
        }, ensure_ascii=False)

        class FakeResult:
            content = fp_json
            response_id = "r1"
            model = "deepseek-chat"
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

        class FakeClient:
            def complete(self, messages, **kw):
                return FakeResult()

        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: FakeClient()
        )
        resp = client.post(f"/references/{ref_id}/fingerprints", json={
            "work": store.db_name, "async_job": False,
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["fingerprint_id"]
        assert body["status"] == "pending_review"

    def test_list_fingerprints(self, client, store, monkeypatch):
        ref_id = self._import(client, store)
        fp_json = json.dumps({
            "local_mechanisms": ["x"], "cross_chapter_aggregation": "y",
            "full_book_fingerprint": "z", "evidence": [{"quote": "a", "location": "b"}],
            "counter_evidence": [], "transferable_mechanisms": ["m"],
            "non_copyable_elements": ["n"], "applicable_scope": "s",
        }, ensure_ascii=False)

        class FakeResult:
            content = fp_json
            response_id = "r1"
            model = "deepseek-chat"
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

        class FakeClient:
            def complete(self, messages, **kw):
                return FakeResult()

        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: FakeClient()
        )
        client.post(f"/references/{ref_id}/fingerprints", json={"work": store.db_name, "async_job": False})
        resp = client.get(f"/references/{ref_id}/fingerprints", params={"work": store.db_name})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_approve_fingerprint_creates_an_approved_revision(self, client, store, monkeypatch):
        ref_id = self._import(client, store)
        fp_json = json.dumps({
            "local_mechanisms": ["x"], "cross_chapter_aggregation": "y",
            "full_book_fingerprint": "z", "evidence": [{"quote": "a", "location": "b"}],
            "counter_evidence": [], "transferable_mechanisms": ["m"],
            "non_copyable_elements": ["n"], "applicable_scope": "s",
        }, ensure_ascii=False)

        class FakeResult:
            content = fp_json
            response_id = "r1"
            model = "qwen3.8-max-preview"
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

        class FakeClient:
            def complete(self, messages, **kw):
                return FakeResult()

        monkeypatch.setattr("scribe3.quality.api._get_deepseek_client", lambda: FakeClient())
        pending = client.post(
            f"/references/{ref_id}/fingerprints", json={"work": store.db_name, "async_job": False},
        ).json()

        response = client.post(
            f"/references/{ref_id}/fingerprints/{pending['fingerprint_id']}/approve",
            json={"work": store.db_name, "async_job": False},
        )

        assert response.status_code == 201
        approved = response.json()
        assert approved["status"] == "approved"
        assert approved["reference_work_id"] == ref_id
        assert approved["revision"] == pending["revision"] + 1


class TestPatchReference:
    def test_patch_returns_current_record(self, client, store):
        resp = client.post("/references/import", json={
            "work": store.db_name, "title": "原标题", "text": "内容。" * 10,
        })
        ref_id = resp.json()["reference_work_id"]
        patch_resp = client.patch(f"/references/{ref_id}", json={
            "work": store.db_name,
        })
        assert patch_resp.status_code == 200
        assert patch_resp.json()["reference_work_id"] == ref_id


PROSE = "井沿的水声停了。老范没有回头。"
QUOTE = "水声停了"


def _seed_contract(store):
    from scribe3.quality.models import (
        DimensionWeight, QualityContractRevision, SuccessCriterion,
    )
    from scribe3.quality.rubrics import CORE_DIMENSIONS
    from scribe3.quality.store import QualityStore
    quality = QualityStore(store)
    contract = QualityContractRevision(
        contract_id="contract:api", work=store.db_name, revision=1,
        primary_genre="长篇悬疑", overlay_genres=(), target_readers="成年读者",
        reading_context="连续阅读", core_promise="让读者跟随人物穿过真相",
        intended_experience=("不安",), emotional_arc=("疑惧",),
        theme_questions=("真相是否值得代价",),
        success_criteria=tuple(
            SuccessCriterion(key=k, text=f"{k}-c")
            for k in ("character", "relationship", "structure", "language", "originality")
        ),
        dimension_weights=tuple(
            DimensionWeight(dimension=d.key, weight=1.0) for d in CORE_DIMENSIONS
        ),
        evaluation_milestones=("chapter",), completion_criteria=("十维均有判断",),
    )
    quality.save_contract_revision(contract)
    quality.approve_contract("contract:api", 1, expected_approved=False)


def _contract_payload(store, *, revision=1, weights=None):
    from scribe3.quality.models import (
        DecisionWeights, DimensionWeight, QualityContractRevision, SuccessCriterion,
    )
    from scribe3.quality.rubrics import CORE_DIMENSIONS
    contract = QualityContractRevision(
        contract_id="contract:api", work=store.db_name, revision=revision,
        primary_genre="长篇悬疑", overlay_genres=("家族史",), target_readers="成年读者",
        reading_context="连续阅读", core_promise="让读者跟随人物穿过真相",
        intended_experience=("不安",), emotional_arc=("疑惧",),
        theme_questions=("真相是否值得代价",),
        success_criteria=tuple(
            SuccessCriterion(key=k, text=f"{k}-c")
            for k in ("character", "relationship", "structure", "language", "originality")
        ),
        dimension_weights=tuple(
            DimensionWeight(dimension=d.key, weight=1.0) for d in CORE_DIMENSIONS
        ),
        weights=weights or DecisionWeights(),
        evaluation_milestones=("chapter",), completion_criteria=("十维均有判断",),
    )
    return contract.model_dump(mode="json")


class _ScriptedDeepSeek:
    def complete_json(self, messages, *, schema, **kwargs):
        from scribe3.quality.evaluator import RawDimensionJudgment
        from scribe3.quality.models import JudgmentState
        return RawDimensionJudgment(
            state=JudgmentState.EVALUABLE, score=4,
            effect="声音中断制造因果压力", mechanism="先停水声后不回头",
            evidence_quotes=(QUOTE,),
        )


def _dispatch_quality_job_inline(monkeypatch, store, *, swallow_failure: bool = False):
    """API 单测显式替代后台线程，避免 TestClient 生命周期掩盖状态契约。"""
    def dispatch(*, work: str, job_id: str):
        from scribe3.quality.api import _get_deepseek_client
        from scribe3.quality.evaluator import QualityEvaluator
        try:
            return QualityEvaluator(store, _get_deepseek_client()).execute_job(job_id)
        except Exception:
            if not swallow_failure:
                raise
            return None

    monkeypatch.setattr("scribe3.quality.api._dispatch_quality_job", dispatch)


class TestQualityEvaluationEndpoints:
    def test_reference_craft_uses_are_readable_by_work_and_chapter(self, client, store):
        """验收只能只读回查已发生的参考技法消费，不能用 REST 补造证据。"""
        from scribe3.quality.store import QualityStore

        QualityStore(store).record_reference_craft_use(
            work=store.db_name,
            chapter=7,
            request_id="req-reference-craft",
            manifest_id="manifest-reference-craft",
            briefs=(SimpleNamespace(
                fingerprint_id="reference_fingerprint:approved",
                mechanism_ids=("mechanism:action-pressure",),
            ),),
        )

        response = client.get("/quality/reference-craft-uses", params={
            "work": store.db_name, "chapter": 7,
        })

        assert response.status_code == 200
        assert response.json() == [{
            "chapter": 7,
            "request_id": "req-reference-craft",
            "manifest_id": "manifest-reference-craft",
            "reference_fingerprint_ids": ["reference_fingerprint:approved"],
            "mechanism_ids": ["mechanism:action-pressure"],
        }]

    def test_evaluation_traces_expose_only_execution_evidence(self, client, store, monkeypatch):
        """前端验收能核验真实调用身份，但不能读到提示词或参考原文。"""
        _seed_contract(store)
        store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: _ScriptedDeepSeek()
        )
        _dispatch_quality_job_inline(monkeypatch, store)
        assert client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
        }).status_code == 202

        response = client.get("/quality/evaluation-traces", params={
            "work": store.db_name, "seq": 1,
        })

        assert response.status_code == 200
        traces = response.json()
        assert len(traces) == 10
        assert {trace["evaluator_kind"] for trace in traces} == {"system"}
        assert all(set(trace) == {
            "dimension", "evaluator_kind", "outcome_id", "request_id", "manifest_id",
            "provider", "model", "provider_request_id", "usage",
        } for trace in traces)

    def test_snapshot_evaluation_and_author_judgment_flow(self, client, store, monkeypatch):
        _seed_contract(store)
        frozen_version = store.add_chapter_version(
            1, PROSE, label="冻结", kind="checkpoint", stage="final",
        )
        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: _ScriptedDeepSeek()
        )
        _dispatch_quality_job_inline(monkeypatch, store)

        snap = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
        })
        assert snap.status_code == 202
        assert snap.json()["status"] == "queued"
        body = client.get("/quality/evaluation", params={
            "work": store.db_name, "seq": 1,
        }).json()
        assert body["chapter"] == 1
        assert body["job_id"] == snap.json()["job_id"]
        # 质量结论必须可追溯到冻结版本，供长程审计确认没有对旧稿打分；
        # 这里只暴露不可变版本 ID，不返回正文、提示词或参考原文。
        assert body["chapter_version_ids"] == [f"chapter_version:{frozen_version}"]
        assert len(body["dimensions"]) == 10
        first = body["dimensions"][0]
        assert first["system"]["score"] == 4
        assert first["system"]["evidence"][0]["quote"] == QUOTE
        assert first["author"] is None
        assert first["decision_index"] is None

        got = client.get("/quality/evaluation", params={"seq": 1})
        assert got.status_code == 200
        assert len(got.json()["dimensions"]) == 10

        author = client.post("/quality/author-judgment", json={
            "work": store.db_name, "seq": 1,
            "dimension": "coherence_causality", "score": 5,
            "reason": "这条因果链成立，但需要作者明确采纳。",
            "decision": "accept",
            "evidence": [first["system"]["evidence"][0]],
        })
        assert author.status_code == 201

    def test_author_judgment_rejects_stale_snapshot_evidence_as_validation_error(
        self, client, store, monkeypatch,
    ):
        """旧冻结版本的锚点绝不能被误写入最新质量作业。"""
        _seed_contract(store)
        old_version = store.add_chapter_version(
            1, PROSE, label="旧冻结", kind="checkpoint", stage="final",
        )
        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: _ScriptedDeepSeek()
        )
        _dispatch_quality_job_inline(monkeypatch, store)
        first_job = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
        })
        assert first_job.status_code == 202
        old_evidence = client.get("/quality/evaluation", params={
            "work": store.db_name, "seq": 1,
        }).json()["dimensions"][0]["system"]["evidence"][0]
        assert old_evidence["chapter_version_id"] == f"chapter_version:{old_version}"

        store.add_chapter_version(
            1, PROSE + "\n新的结局使选择代价更清晰。", label="新冻结", kind="checkpoint", stage="final",
        )
        latest_job = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
        })
        assert latest_job.status_code == 202

        rejected = client.post("/quality/author-judgment", json={
            "work": store.db_name, "seq": 1,
            "dimension": "coherence_causality", "score": 5,
            "reason": "作者必须只对当前冻结稿的证据作出裁决。",
            "decision": "accept", "evidence": [old_evidence],
        })

        assert rejected.status_code == 422
        assert "冻结快照" in rejected.json()["detail"]

    def test_evaluation_empty_when_no_job(self, client, store):
        got = client.get("/quality/evaluation", params={"seq": 99})
        assert got.status_code == 200
        assert got.json()["status"] == "empty"

    def test_incomplete_job_never_poses_as_a_ready_ten_dimension_evaluation(self, client, store):
        """服务在模型执行中断后只能如实报告未完成，不能展示空壳十维卡。"""
        from scribe3.quality.store import QualityStore

        _seed_contract(store)
        version_id = store.add_chapter_version(
            1, PROSE, label="冻结", kind="checkpoint", stage="final",
        )
        quality = QualityStore(store)
        snapshot = quality.create_chapter_snapshot(
            work=store.db_name, chapter_version_ids=(version_id,),
        )
        quality.create_job(
            work=store.db_name,
            snapshot_id=snapshot.snapshot_id,
            contract_id="contract:api",
            contract_revision=1,
            rubric_revision="test",
            reference_fingerprint_ids=(),
            model_config={"provider": "qwen", "model": "qwen3.8-max-preview"},
            actual_input_hash=hashlib.sha256(b"interrupted-evaluation").hexdigest(),
            idempotency_key="interrupted-evaluation",
        )

        response = client.get("/quality/evaluation", params={"work": store.db_name, "seq": 1})

        assert response.status_code == 200
        assert response.json()["chapter"] == 1
        assert response.json()["dimensions"] == []
        assert response.json()["status"] == "queued"
        assert client.get("/quality/evaluation-traces", params={
            "work": store.db_name, "seq": 1,
        }).json() == []

    def test_snapshot_returns_accepted_job_and_get_hides_queued_axes(self, client, store, monkeypatch):
        """创建接口只负责冻结并排队，作者不能在后台执行前看到十维表单。"""
        _seed_contract(store)
        store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
        monkeypatch.setattr("scribe3.quality.api._dispatch_quality_job", lambda **_kwargs: None)

        created = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
        })

        assert created.status_code == 202
        assert created.json()["status"] == "queued"
        assert created.json()["job_id"]
        queued = client.get("/quality/evaluation", params={
            "work": store.db_name, "seq": 1,
        }).json()
        assert queued["chapter"] == 1
        assert queued["job_id"] == created.json()["job_id"]
        assert queued["dimensions"] == []
        assert queued["status"] == "queued"

    def test_retry_queues_only_a_retryable_frozen_job(self, client, store, monkeypatch):
        from scribe3.quality.store import QualityStore

        _seed_contract(store)
        version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
        quality = QualityStore(store)
        snapshot = quality.create_chapter_snapshot(
            work=store.db_name, chapter_version_ids=(version_id,),
        )
        job = quality.create_job(
            work=store.db_name, snapshot_id=snapshot.snapshot_id,
            contract_id="contract:api", contract_revision=1, rubric_revision="test",
            reference_fingerprint_ids=(), model_config={"provider": "qwen", "model": "qwen3.8-max-preview"},
            actual_input_hash=hashlib.sha256(b"retryable-job").hexdigest(),
            idempotency_key="retryable-job",
        )
        quality.start_job(job.job_id)
        quality.fail_job(job.job_id, "transport_error", "安全错误摘要")
        dispatched = []
        monkeypatch.setattr(
            "scribe3.quality.api._dispatch_quality_job",
            lambda **kwargs: dispatched.append(kwargs),
        )

        response = client.post(f"/quality/jobs/{job.job_id}/retry", json={"work": store.db_name})

        assert response.status_code == 202
        assert response.json() == {"job_id": job.job_id, "status": "queued"}
        assert dispatched == [{"work": store.db_name, "job_id": job.job_id}]

    def test_evaluation_read_recovers_a_stale_running_job(self, client, store):
        from datetime import datetime, timedelta, timezone
        from scribe3.quality.store import QualityStore

        _seed_contract(store)
        version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
        quality = QualityStore(store)
        snapshot = quality.create_chapter_snapshot(
            work=store.db_name, chapter_version_ids=(version_id,),
        )
        job = quality.create_job(
            work=store.db_name, snapshot_id=snapshot.snapshot_id,
            contract_id="contract:api", contract_revision=1, rubric_revision="test",
            reference_fingerprint_ids=(), model_config={"provider": "qwen", "model": "qwen3.8-max-preview"},
            actual_input_hash=hashlib.sha256(b"stale-api-job").hexdigest(),
            idempotency_key="stale-api-job",
        )
        quality.start_job(job.job_id)
        store._execute_write(
            "UPDATE type::record('quality_job',$job_id) SET execution_started_at=$stale_at",
            # 10 轴、2 路并发、每轴最多两次 JSON 修复的受限窗口为 2,775 秒；
            # 3,000 秒明确超过该窗口，才应被判为已失联。
            {"job_id": job.job_id, "stale_at": datetime.now(timezone.utc) - timedelta(seconds=3000)},
        )

        response = client.get("/quality/evaluation", params={"work": store.db_name, "seq": 1})

        assert response.status_code == 200
        assert response.json()["status"] == "retryable_failed"
        assert response.json()["error_code"] == "worker_lost"

    def test_evaluation_read_keeps_multi_axis_reference_job_running_within_its_batch_budget(self, client, store):
        from datetime import datetime, timedelta, timezone
        from scribe3.quality.store import QualityStore, ReferenceFingerprintRecord, ReferenceWorkRecord

        _seed_contract(store)
        version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
        quality = QualityStore(store)
        source = "仅用于恢复窗口测试的原创参考。"
        reference = ReferenceWorkRecord(
            reference_work_id="reference:recovery-window", work=store.db_name,
            title="恢复窗口样本", source_hash=hashlib.sha256(source.encode()).hexdigest(),
            import_revision=1, status="imported",
        )
        quality.save_reference_work(reference, source_text=source)
        fingerprint = quality.save_reference_fingerprint(ReferenceFingerprintRecord(
            reference_work_id=reference.reference_work_id,
            revision=1, source_hash=reference.source_hash, status="approved",
            fingerprint={
                "local_mechanisms": [], "cross_chapter_aggregation": "",
                "full_book_fingerprint": "测试", "evidence": [], "counter_evidence": [],
                "transferable_mechanisms": ["动作承压"],
                "non_copyable_elements": ["具体措辞"], "applicable_scope": "测试",
            },
        ))
        snapshot = quality.create_chapter_snapshot(
            work=store.db_name, chapter_version_ids=(version_id,),
        )
        job = quality.create_job(
            work=store.db_name, snapshot_id=snapshot.snapshot_id,
            contract_id="contract:api", contract_revision=1, rubric_revision="test",
            # 有批准参考时 10 个系统轴 + 10 个参考轴；4 路并发至少需要五批。
            reference_fingerprint_ids=(fingerprint.fingerprint_id,),
            model_config={"provider": "qwen", "model": "qwen3.8-max-preview"},
            actual_input_hash=hashlib.sha256(b"long-running-reference-job").hexdigest(),
            idempotency_key="long-running-reference-job",
        )
        quality.start_job(job.job_id)
        store._execute_write(
            "UPDATE type::record('quality_job',$job_id) SET execution_started_at=$started_at",
            {"job_id": job.job_id, "started_at": datetime.now(timezone.utc) - timedelta(seconds=200)},
        )

        response = client.get("/quality/evaluation", params={"work": store.db_name, "seq": 1})

        assert response.status_code == 200
        assert response.json()["status"] == "running"
        assert response.json()["dimensions"] == []

    def test_author_verdict_persists_reason_evidence_counter_evidence_and_decision(self, client, store, monkeypatch):
        _seed_contract(store)
        version_id = store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: _ScriptedDeepSeek()
        )
        _dispatch_quality_job_inline(monkeypatch, store)
        created = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
        })
        assert created.status_code == 202
        evidence = {
            "chapter_version_id": version_id,
            "start_utf16": 3,
            "end_utf16": 7,
            "quote": QUOTE,
            "content_hash": hashlib.sha256(PROSE.encode("utf-8")).hexdigest(),
        }

        saved = client.post("/quality/author-judgment", json={
            "work": store.db_name,
            "seq": 1,
            "dimension": "coherence_causality",
            "score": 2,
            "reason": "人物没有回头并不足以让这一选择具有不可替代的代价。",
            "decision": "revise",
            "evidence": [evidence],
            "counter_evidence": [evidence],
        })

        assert saved.status_code == 201
        verdict = saved.json()["verdict"]
        assert verdict["decision"] == "revise"
        assert verdict["reason"] == "人物没有回头并不足以让这一选择具有不可替代的代价。"
        assert verdict["counter_evidence"] == [evidence]

        reread = client.get("/quality/evaluation", params={"work": store.db_name, "seq": 1})
        assert reread.status_code == 200
        first = reread.json()["dimensions"][0]["author"]
        assert first["score"] == 2
        assert first["decision"] == "revise"
        assert first["reason"] == verdict["reason"]
        assert first["counter_evidence"] == [evidence]

    def test_snapshot_missing_chapter_404(self, client, store):
        resp = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 42,
            "contract_id": "contract:api", "contract_revision": 1,
        })
        assert resp.status_code == 404

    def test_snapshot_invalid_quality_truth_is_explicit_409(self, client, store):
        """作业合同等业务冲突不能以未处理 500 冒充服务故障。"""
        store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

        resp = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:missing", "contract_revision": 1,
        })

        assert resp.status_code == 409
        assert "质量作业" in resp.json()["detail"]

    def test_snapshot_retryable_provider_failure_is_visible_as_retryable_job(self, client, store, monkeypatch):
        """TokenPlan 瞬时故障应保留冻结作业供作者重试，不能伪装为 HTTP 同步失败。"""
        from scribe3.deepseek_client import DeepSeekTransportError, ProviderIdentity

        _seed_contract(store)
        store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")

        def unavailable(*_args, **_kwargs):
            raise DeepSeekTransportError(
                "连接 Qwen 官方服务接口失败",
                identity=ProviderIdentity(
                    provider="qwen", api_base="https://token-plan.example/v1",
                    model="qwen3.8-max-preview", official=True, transport="httpx",
                ),
                status="transport_error", retryable=True,
            )

        monkeypatch.setattr("scribe3.quality.api._get_deepseek_client", lambda: type(
            "UnavailableClient", (), {"complete_json": staticmethod(unavailable)},
        )())
        _dispatch_quality_job_inline(monkeypatch, store, swallow_failure=True)
        resp = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
        })

        assert resp.status_code == 202
        evaluation = client.get("/quality/evaluation", params={
            "work": store.db_name, "seq": 1,
        }).json()
        assert evaluation["status"] == "retryable_failed"
        assert evaluation["dimensions"] == []
        assert evaluation["error_code"] == "DeepSeekTransportError"


class TestQualityContractEndpoints:
    def test_contract_draft_lookup_treats_a_missing_initial_draft_as_normal_state(self, client, store):
        """新书首次打开合同编辑器不应以 404 制造浏览器控制台错误。"""
        response = client.get("/quality/contracts/quality-contract:initial", params={
            "work": store.db_name, "revision": 1, "allow_missing": True,
        })

        assert response.status_code == 200
        assert response.json() == {"found": False}

    def test_contract_draft_read_and_approval_are_append_only(self, client, store):
        created = client.post("/quality/contracts", json=_contract_payload(store))
        assert created.status_code == 201
        assert created.json()["approved"] is False

        read = client.get("/quality/contracts/contract:api", params={
            "work": store.db_name, "revision": 1,
        })
        assert read.status_code == 200
        assert read.json()["core_promise"] == "让读者跟随人物穿过真相"

        approved = client.post("/quality/contracts/contract:api/1/approve", json={
            "work": store.db_name,
        })
        assert approved.status_code == 200
        assert approved.json()["approved"] is True

        repeated = client.post("/quality/contracts/contract:api/1/approve", json={
            "work": store.db_name,
        })
        assert repeated.status_code == 409

    def test_evaluation_uses_approved_contract_weights_not_api_defaults(self, client, store, monkeypatch):
        from scribe3.quality.models import DecisionWeights
        from scribe3.quality.store import QualityStore, ReferenceFingerprintRecord, ReferenceWorkRecord

        weights = DecisionWeights(author=0.60, system=0.25, reference=0.15)
        assert client.post("/quality/contracts", json=_contract_payload(store, weights=weights)).status_code == 201
        assert client.post("/quality/contracts/contract:api/1/approve", json={
            "work": store.db_name,
        }).status_code == 200

        source = "参考作品中的安全技法。"
        reference = ReferenceWorkRecord(
            reference_work_id="reference:weight", work=store.db_name,
            title="技法样本", source_hash=hashlib.sha256(source.encode()).hexdigest(),
            import_revision=1, status="imported",
        )
        quality = QualityStore(store)
        quality.save_reference_work(reference, source_text=source)
        fingerprint = quality.save_reference_fingerprint(ReferenceFingerprintRecord(
            reference_work_id=reference.reference_work_id,
            revision=1, source_hash=reference.source_hash, status="approved",
            fingerprint={
                "local_mechanisms": [], "cross_chapter_aggregation": "",
                "full_book_fingerprint": "克制推进", "evidence": [], "counter_evidence": [],
                "transferable_mechanisms": ["以动作制造压力"],
                "non_copyable_elements": ["原作人物、情节和原句"],
                "applicable_scope": "悬疑场景",
            },
        ))
        store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: _ScriptedDeepSeek()
        )
        _dispatch_quality_job_inline(monkeypatch, store)
        created = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
            "reference_fingerprint_ids": [fingerprint.fingerprint_id],
        })
        assert created.status_code == 202
        evidence = client.get("/quality/evaluation", params={
            "work": store.db_name, "seq": 1,
        }).json()["dimensions"][0]["system"]["evidence"][0]
        author = client.post("/quality/author-judgment", json={
            "work": store.db_name, "seq": 1, "dimension": "coherence_causality", "score": 5,
            "reason": "作者确认此处的因果有足够的叙事推动力。",
            "decision": "accept", "evidence": [evidence],
        })
        assert author.status_code == 201

        evaluation = client.get("/quality/evaluation", params={"work": store.db_name, "seq": 1})
        assert evaluation.status_code == 200
        body = evaluation.json()
        assert body["weights"] == {"author": 0.6, "system": 0.25, "reference": 0.15}
        assert body["dimensions"][0]["decision_index"] == pytest.approx(4.6)


class TestMultipartImportAndApprovedList:
    def test_import_file_multipart_job_persists_reference_not_material(self, client, store):
        """multipart 上传走 shipped import-file，不经 JSON 全文 body。"""
        content = ("第一章内容。" * 200 + "\n\n## 第二章\n" + "二章内容。" * 200).encode("utf-8")
        resp = client.post(
            "/references/import-file",
            data={"work": store.db_name, "title": "上传标尺"},
            files={"file": ("yardstick.txt", content, "text/plain")},
        )
        assert resp.status_code == 202, resp.text
        job_id = resp.json()["job_id"]
        job = client.get(
            f"/references/import-jobs/{job_id}",
            params={"work": store.db_name},
        )
        assert job.status_code == 200
        body = job.json()
        assert body["done"] is True
        assert body["error"] == ""
        assert body["reference_work_id"]
        # 列表可见
        listed = client.get("/references", params={"work": store.db_name})
        assert any(r["reference_work_id"] == body["reference_work_id"] for r in listed.json())
        # 不进 material
        materials = store._query("SELECT * FROM material", {})
        assert materials == []
        # 原文在 reference_work 可寻址
        rows = store._query(
            "SELECT source_text FROM reference_work WHERE reference_work_id=$rid LIMIT 1",
            {"rid": body["reference_work_id"]},
        )
        assert rows and "第一章内容" in (rows[0].get("source_text") or "")

    def test_approved_fingerprints_list_for_quality_bind(self, client, store, monkeypatch):
        import json as _json
        fp_json = _json.dumps({
            "local_mechanisms": ["x"], "cross_chapter_aggregation": "y",
            "full_book_fingerprint": "全书冷硬", "evidence": [{"quote": "a", "location": "b"}],
            "counter_evidence": [], "transferable_mechanisms": ["可迁移节奏"],
            "non_copyable_elements": ["专名"], "applicable_scope": "s",
        }, ensure_ascii=False)

        class FakeResult:
            content = fp_json
            response_id = "r1"
            model = "deepseek-chat"
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

        class FakeClient:
            def complete(self, messages, **kw):
                return FakeResult()

        monkeypatch.setattr("scribe3.quality.api._get_deepseek_client", lambda: FakeClient())
        created = client.post("/references/import", json={
            "work": store.db_name, "title": "可选标尺", "text": "正文。" * 40,
        }).json()
        rid = created["reference_work_id"]
        pending = client.post(
            f"/references/{rid}/fingerprints", json={"work": store.db_name, "async_job": False},
        ).json()
        client.post(
            f"/references/{rid}/fingerprints/{pending['fingerprint_id']}/approve",
            json={"work": store.db_name},
        )
        listed = client.get("/references/approved-fingerprints", params={"work": store.db_name})
        assert listed.status_code == 200
        rows = listed.json()
        assert len(rows) >= 1
        assert rows[0]["fingerprint_id"]
        assert rows[0]["title"] == "可选标尺"
        assert "可迁移节奏" in (rows[0].get("transferable_mechanisms_preview") or [])
        # 与 material 端点分离
        assert "/materials" not in str(listed.url)


class TestAsyncFingerprintJob:
    def test_async_fingerprint_job_completes_with_pending_review(self, client, store, monkeypatch):
        """产品路径：202 + job 轮询 → pending_review；多段 coverage 写入 job 与 fingerprint。"""
        import json as _json
        chapters = []
        for i in range(6):
            chapters.append(f"## 第{i + 1}章\n" + ("悬念递进与环境压迫。" * 220))
        source = "\n\n".join(chapters)
        assert len(source) > 12_000
        created = client.post("/references/import", json={
            "work": store.db_name, "title": "异步长标尺", "text": source,
        }).json()
        rid = created["reference_work_id"]
        fp_json = _json.dumps({
            "local_mechanisms": ["悬念"], "cross_chapter_aggregation": "三幕",
            "full_book_fingerprint": "冷硬", "evidence": [{"quote": "a", "location": "b"}],
            "counter_evidence": [], "transferable_mechanisms": ["节奏"],
            "non_copyable_elements": ["专名"], "applicable_scope": "悬疑",
        }, ensure_ascii=False)

        class FakeResult:
            content = fp_json
            response_id = "r1"
            model = "deepseek-chat"
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

        class FakeClient:
            def complete(self, messages, **kw):
                return FakeResult()

        monkeypatch.setattr("scribe3.quality.api._get_deepseek_client", lambda: FakeClient())
        resp = client.post(
            f"/references/{rid}/fingerprints",
            json={"work": store.db_name, "async_job": True},
        )
        assert resp.status_code == 202, resp.text
        job_id = resp.json()["job_id"]
        # TestClient runs BackgroundTasks before return; job should be done
        job = client.get(
            f"/references/fingerprint-jobs/{job_id}",
            params={"work": store.db_name},
        )
        assert job.status_code == 200
        body = job.json()
        assert body["done"] is True
        assert body["error"] == ""
        assert body["fingerprint_id"]
        assert body["status"] == "pending_review"
        assert (body.get("segment_count") or 0) >= 2 or (body.get("map_calls") or 0) >= 2
        listed = client.get(f"/references/{rid}/fingerprints", params={"work": store.db_name})
        fps = listed.json()
        assert any(f.get("fingerprint_id") == body["fingerprint_id"] for f in fps)
        pending = next(f for f in fps if f["fingerprint_id"] == body["fingerprint_id"])
        meta = (pending.get("fingerprint") or {}).get("analysis_meta") or {}
        assert meta.get("pipeline") == "map_reduce"
        assert meta.get("segment_count", 0) >= 2
