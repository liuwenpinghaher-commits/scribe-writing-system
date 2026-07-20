"""Task 4: 参考作品 API 端点 RED 测试。"""
import hashlib
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scribe3.quality.api import quality_router, quality_eval_router


@pytest.fixture
def client(store):
    app = FastAPI()
    app.include_router(quality_router)
    app.include_router(quality_eval_router)
    app.state.store = store
    return TestClient(app)


class TestImportEndpoint:
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
            "work": store.db_name,
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
        client.post(f"/references/{ref_id}/fingerprints", json={"work": store.db_name})
        resp = client.get(f"/references/{ref_id}/fingerprints", params={"work": store.db_name})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


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


class _ScriptedDeepSeek:
    def complete_json(self, messages, *, schema, **kwargs):
        from scribe3.quality.evaluator import RawDimensionJudgment
        from scribe3.quality.models import JudgmentState
        return RawDimensionJudgment(
            state=JudgmentState.EVALUABLE, score=4,
            effect="声音中断制造因果压力", mechanism="先停水声后不回头",
            evidence_quotes=(QUOTE,),
        )


class TestQualityEvaluationEndpoints:
    def test_snapshot_evaluation_and_author_judgment_flow(self, client, store, monkeypatch):
        _seed_contract(store)
        store.add_chapter_version(1, PROSE, label="冻结", kind="checkpoint", stage="final")
        monkeypatch.setattr(
            "scribe3.quality.api._get_deepseek_client", lambda: _ScriptedDeepSeek()
        )

        snap = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 1,
            "contract_id": "contract:api", "contract_revision": 1,
        })
        assert snap.status_code == 201
        body = snap.json()
        assert body["chapter"] == 1
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
        })
        assert author.status_code == 201

    def test_evaluation_empty_when_no_job(self, client, store):
        got = client.get("/quality/evaluation", params={"seq": 99})
        assert got.status_code == 200
        assert got.json()["status"] == "empty"

    def test_snapshot_missing_chapter_404(self, client, store):
        resp = client.post("/quality/snapshot", json={
            "work": store.db_name, "seq": 42,
            "contract_id": "contract:api", "contract_revision": 1,
        })
        assert resp.status_code == 404
