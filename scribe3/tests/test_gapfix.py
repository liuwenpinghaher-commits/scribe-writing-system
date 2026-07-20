"""断头修复批 TDD(2026-07-05 闭环审计:22 断头+清债欠账的后端侧)。

覆盖:纪律判解析失败计 degraded / ingest 失败状态可见 / embedding fail-soft /
LLM 日调用帽接线 / qc_scan 多书 / M1 刷新耗尽提醒 / unverified ignored 不复活 /
ingest voice flag 幂等 / health 真探测 / final 版去重。
"""
import json

import pytest

import scribe3.app as A
import scribe3.llm as L
from scribe3.brief import promise_directives
from scribe3.ontology import Entity

from .test_app import _client


# ===== 1. parse_discipline 失败 → degraded 可见(审计 E-2/#58,fail-open 保持但不再假绿)=====

def test_discipline_parse_failure_marks_degraded(store):
    c = _client(store)
    A.set_complete_fn(lambda p, **kw: "这不是JSON,LLM抽风了")
    r = c.post("/post-check?seq=1", json={"prose": "他把伞收了,雨还没停。"}).json()
    assert "discipline_parse" in r["degraded_stages"], "解析失败必须计 degraded(没查≠没病)"
    assert r["discipline"].get("parse_failed") is True and not r["discipline"]["violations"], \
        "fail-open 语义保持(不误拦)且带失败标记"
    assert not [i for i in r["issues"] if i["type"] == "discipline"], "解析失败不产伪 issue"


# ===== 2. 后台 ingest 失败状态落库(审计 P1-6,知识账本悄悄落后的止血)=====

def test_bg_ingest_records_failed_status(store, monkeypatch):
    store.save_chapter(3, "正文。", title="三")
    monkeypatch.setenv("SCRIBE3_SURREAL_URL", store.url)
    import scribe3.ingest as I

    def boom(st, seq, llm):
        raise RuntimeError("LLM挂了")
    monkeypatch.setattr(I, "ingest_chapter", boom)
    A._bg_ingest("test", 3)
    ch = store.get_chapter(3)
    assert ch.get("ingest_status") == "failed"
    assert "LLM挂了" in (ch.get("ingest_error") or "")


def test_bg_ingest_records_ok_status(store, monkeypatch):
    store.save_chapter(4, "正文。", title="四")
    monkeypatch.setenv("SCRIBE3_SURREAL_URL", store.url)
    import scribe3.ingest as I
    monkeypatch.setattr(I, "ingest_chapter", lambda st, seq, llm: {})
    A._bg_ingest("test", 4)
    ch = store.get_chapter(4)
    assert ch.get("ingest_status") == "ok"
    assert not ch.get("ingest_error")


# ===== 3. save_chapter embedding fail-soft(审计 E-1,存稿命门)=====

def test_save_chapter_survives_embed_failure(store, monkeypatch):
    import scribe3.embed as E
    monkeypatch.setattr(E, "embed", lambda texts: (_ for _ in ()).throw(RuntimeError("bge挂了")))
    store.save_chapter(5, "正文不能因向量挂而丢。", title="五")
    ch = store.get_chapter(5)
    assert ch["prose"] == "正文不能因向量挂而丢。", "存稿绝不能被 embedding 故障拖死"


# ===== 4. LLM 日调用帽真接线(审计 P1-12,方案原文"接线或删除二选一")=====

def test_daily_llm_cap_enforced(monkeypatch):
    monkeypatch.setattr(L, "_cap", lambda: 2)
    L._reset_daily_counter()

    class FakeClient:
        def complete(self, _messages, **_kwargs):
            from scribe3.deepseek_client import CompletionResult, ProviderIdentity
            return CompletionResult(
                content="ok",
                model="deepseek-chat",
                usage={},
                finish_reason="stop",
                identity=ProviderIdentity(
                    provider="deepseek",
                    api_base="https://api.deepseek.com",
                    model="deepseek-chat",
                    official=True,
                    transport="httpx",
                ),
            )

    monkeypatch.setattr(L, "DeepSeekClient", FakeClient)
    assert L.hermes_complete("a") == "ok"
    assert L.hermes_complete("b") == "ok"
    with pytest.raises(RuntimeError, match="日调用上限"):
        L.hermes_complete("c")
    L._reset_daily_counter()


# ===== 5. qc_scan 多书体检(审计 P2-9,单书失明)=====

def test_qc_scan_covers_all_works(store):
    from scribe3.qc_scan import build_reports
    store.save_chapter(1, "第一章。", title="一")
    reports = build_reports(works=["test"], url=store.url)
    assert set(reports.keys()) == {"test"}, "按传入书单逐书体检"


# ===== 6. M1 刷新耗尽提醒(工艺引擎 M1:刷新≥3 次仍未兑现 → 读者已猜到)=====

def test_promise_refresh_exhausted_escalates():
    rows = [{"text": "井底的赎骨钱", "refresh_count": 3,
             "window": {"state": "over_half", "salience_gap": 9}}]
    d = promise_directives(rows)
    joined = "\n".join(d["directives"] + d["decisions"])
    assert "猜到" in joined, "刷新≥3 次未兑现必须升级提示(再刷读者就腻了)"


def test_promise_refresh_normal_path_unchanged():
    rows = [{"text": "旧伏笔", "refresh_count": 1,
             "window": {"state": "over_half", "salience_gap": 9}}]
    d = promise_directives(rows)
    assert any("先刷新" in x for x in d["directives"]), "常规低显著路径保持"


# ===== 7. unverified ignored 决策不复活(审计 C-3)=====

def test_unverified_ignored_not_resurrected(store):
    store.add_unverified_ref("野和尚", 6, "SUBJ")
    uid = store.list_unverified("pending")[0]["id"]
    store.set_unverified_status(uid, "ignored")
    # re-ingest:purge 后再抽到同名 → 不得回到 pending(人已决策忽略)
    store.purge_ingest(6)
    store.add_unverified_ref("野和尚", 6, "SUBJ")
    assert store.list_unverified("pending") == [], "ignored 决策必须在 re-ingest 后存活"
    assert len(store.list_unverified("ignored")) == 1


# ===== 8. ingest 产的 voice flag 随 purge 幂等(审计 C-2)=====

def test_purge_clears_ingest_voice_flags_keeps_manual(store):
    store.add_entity(Entity("role:哑姑", "character", "哑姑"))
    # ingest 路径(带 ingest_seq)与手动路径各产一个 affects_voice flag
    store.add_char_state("role:哑姑", 7, "personality", "开口说话了",
                         affects_voice=True, ingest_seq=7)
    store.add_char_state("role:哑姑", 7, "personality", "手动记录",
                         affects_voice=True)
    assert len(store.list_voice_flags("open")) == 2
    store.purge_ingest(7)
    flags = store.list_voice_flags("open")
    assert len(flags) == 1, "ingest 产的 flag 随 purge 清除(否则 re-ingest 累积重复)"
    assert "手动" in (flags[0].get("reason") or ""), "手动 flag 保留"


# ===== 8b. 演绎阶段注入场景真相(演绎多棱镜 #5:投影同源派生的物理保证)=====

def test_deduce_phase_injects_scene_truth(store):
    store.save_chapter(9, "", title="九")
    store.update_chapter_meta(9, {
        "scene_truth": "井底沉着妹妹的骨殖,哑姑每夜数钱。",
        "deductions": [{"character_id": "role:老范", "character_name": "老范",
                        "prose": "老范只知道井底有水声,不知道骨殖。"}],
    })
    ins_deduce = A._assemble_write_instructions(
        store, chapter=9, focalizer="role:老范", phase="deduce", with_tools=False,
        seed_words=[], short_mode=False)
    assert "井底沉着妹妹的骨殖" in ins_deduce, "deduce 阶段必须把场景真相注入 prompt"
    assert "唯一事实源" in ins_deduce
    # F-1 修复(B-3 同型第四次):正文相位(final=loop/pilot/选择环一步到正文,draft=四阶段草稿)
    # 必须注入演绎块——否则 deduce 步烧的 1+N 发 LLM 产物(场景真相+限知投影)物理不进 prompt,
    # 驱动语"按简报与演绎写"沦为空指令。走 _deduction_block(措辞异于 deduce 分支的"唯一事实源")。
    for ph in ("final", "draft"):
        ins = A._assemble_write_instructions(
            store, chapter=9, focalizer="role:老范", phase=ph, with_tools=False,
            seed_words=[], short_mode=False)
        assert "本章演绎" in ins, f"{ph} 相位必须注入演绎块(F-1)"
        assert "井底沉着妹妹的骨殖" in ins, f"{ph} 相位必须收到场景真相原文(F-1)"
        assert "老范·限知投影" in ins, f"{ph} 相位必须收到角色限知投影(F-1)"
        assert "老范只知道井底有水声" in ins, f"{ph} 相位必须收到限知投影正文(F-1)"
        assert "唯一事实源" not in ins, f"{ph} 走 _deduction_block 而非 deduce 分支措辞"


# ===== 9. /health 真探测 + /ready(审计 #80)=====

def test_health_probes_db(store):
    r = _client(store).get("/health").json()
    assert r["ok"] is True and r["db"] == "ok", "health 必须真 ping DB,不再是纯桩"


def test_ready_endpoint(store):
    assert _client(store).get("/ready").status_code == 200


# ===== 10. final 版同稿去重(审计 P2-1,自动 final 刷屏)=====

def test_final_version_dedup_same_prose(store):
    c = _client(store)
    c.post("/save-chapter", json={"seq": 8, "prose": "同一份正文。", "title": "八"})
    c.post("/save-chapter", json={"seq": 8, "prose": "同一份正文。", "title": "八"})
    finals = [v for v in store.list_chapter_versions(8) if v.get("kind") == "final"]
    assert len(finals) == 1, "内容未变不重复落 final 版"
    c.post("/save-chapter", json={"seq": 8, "prose": "改过的正文。", "title": "八"})
    finals2 = [v for v in store.list_chapter_versions(8) if v.get("kind") == "final"]
    assert len(finals2) == 2, "内容变了照常留版"
