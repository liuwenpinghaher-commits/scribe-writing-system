"""北极星方案任务11 · 选择环 TDD(蓝图 §4-①:关键章 N 候选→确定性过滤→批次粗排→人终选)。

攻上限的唯一自动化辅助:LLM 供多样性(prompt 显式分派策略,PlanSearch 证据:
idea 层多样性>解码采样)、本体做过滤(blocking 杀)、rubric 只排序绝不门禁
(pairwise>绝对分;全循环双向+位置对换,循环偏好→标'评审无共识'直接交人——
调研五建议);伪多样判定用特征轴自由维度(合同约束维度不算,防死循环);
终选理由入 lesson 流(强制留一句,超主流实践的增量)。
"""
import pytest

from scribe3.pipeline_journal import PipelineJournal
from scribe3.selection import (L1_STRATEGIES, STRATEGIES, apply_light_pick,
                               is_key_chapter, pseudo_diversity,
                               round_robin_rank, run_light_selection, run_selection)


# ===== 关键章判定 =====

def test_is_key_chapter_by_role_or_reversal():
    assert is_key_chapter({"role": "高压"}) is True, \
        "生产键名是 role(parse_chapter_meta 输出;P2 真机抓出的契约假绿)"
    assert is_key_chapter({"role": "关系回收", "pressure": 3}) is True
    assert is_key_chapter({"chapter_role": "高压"}) is True, "旧键名兼容"
    assert is_key_chapter({"role": "推进", "reversal_type": "身份反转"}) is True
    assert is_key_chapter({"role": "低压"}) is False
    assert is_key_chapter({}) is False, "无标注不触发(N 倍成本只花在刀刃上)"


def test_is_key_chapter_against_real_parse(store):
    """契约测试:直接吃 parse_chapter_meta 的真实输出,防 stub 键名再次假绿。"""
    from scribe3.brief import parse_chapter_meta
    meta = parse_chapter_meta("井台对峙。压力级:5 chapter_role:高压")
    assert meta and is_key_chapter(meta) is True


# ===== 全循环赛排序(rubric 只排序) =====

def _judge_prefer_shorter(a, b):
    """stub 判官:偏好更短文本;返回 'A'/'B'。"""
    return "A" if len(a) <= len(b) else "B"


def test_round_robin_rank_consistent_preference():
    texts = ["短", "中等长度文本", "这是最长的一段候选文本内容"]
    r = round_robin_rank(texts, _judge_prefer_shorter)
    assert r["consensus"] is True
    assert r["order"][0] == 0 and r["order"][-1] == 2, "胜场序=短者胜"
    assert sum(r["wins"].values()) == 6, "3 候选双向全循环=6 次比较(位置对换)"


def test_round_robin_rank_cycle_no_consensus():
    """A>B>C>A 循环偏好(非传递性,ICML 2025 实证)→ 不给排序,标无共识交人。"""
    prefs = {("0", "1"): "0", ("1", "2"): "1", ("2", "0"): "2"}

    def cyclic_judge(a, b):
        key = (a, b) if (a, b) in prefs else (b, a)
        winner = prefs[key]
        return "A" if winner == a else "B"

    r = round_robin_rank(["0", "1", "2"], cyclic_judge)
    assert r["consensus"] is False
    assert r["order"] is None, "循环偏好绝不硬给排序(评审无共识,直接交人)"


def test_round_robin_position_bias_detected():
    """判官只认位置(永远选 A)→ 位置对换后每对两方向互相矛盾 → 无共识。"""
    r = round_robin_rank(["x", "y", "z"], lambda a, b: "A")
    assert r["consensus"] is False, "纯位置偏置在双向对换下必然自相矛盾,须交人"


# ===== 伪多样判定(只看合同未约束的自由维度) =====

def _prof(cv, ratio, shape=0):
    """shape:标点节奏形状档(0/1/2 三种分布)——真实候选的标点向量天然不同,
    夹具若全同会把 punct 距离拉成 0 误触发伪多样。"""
    base = [(50, 30, 2, 0, 1, 10), (20, 60, 8, 4, 6, 25), (80, 10, 1, 12, 0, 5)][shape % 3]
    keys = ("comma", "period", "exclaim_q", "ellipsis", "dash", "quote")
    return {"sent_cv": cv, "dialogue_ratio": ratio,
            "punct_per_k": dict(zip(keys, base))}


def test_pseudo_diversity_flags_near_identical():
    out = pseudo_diversity([_prof(0.5, 0.30), _prof(0.51, 0.31), _prof(0.9, 0.65)])
    assert out["pseudo"] is True
    assert (0, 1) in [tuple(p) for p in out["near_pairs"]]


def test_pseudo_diversity_ok_when_spread():
    out = pseudo_diversity([_prof(0.4, 0.2), _prof(0.7, 0.45), _prof(1.0, 0.7)])
    assert out["pseudo"] is False and out["near_pairs"] == []


# ===== 编排(依赖注入,含过滤杀/重生成/journal) =====

def _wire_sel(tmp_path, gen_map, posts, profiles):
    """gen_map: strategy_key -> prose;posts: prose -> post_check 响应;profiles: prose -> 特征。"""
    calls = {"gen": [], "judged": 0}

    def gen(strategy):
        calls["gen"].append(strategy["key"])
        return gen_map[strategy["key"]]

    def pc(prose):
        return posts.get(prose, {"leaks": [], "issues": [], "degraded_stages": [],
                                 "leaks_degraded": False, "punct_suggestions": []})

    def pv(prose, strategy_key):
        return f"v-{strategy_key}"

    def prof(prose):
        # 缺省按文本长度撒开(防夹具本身触发伪多样)
        return profiles.get(prose, _prof(0.3 + (len(prose) % 7) * 0.1,
                                         0.1 + (len(prose) % 5) * 0.12))

    def judge(a, b):
        calls["judged"] += 1
        return "A" if len(a) >= len(b) else "B"   # 偏好更长

    j = PipelineJournal(tmp_path / "sel.json")
    return calls, dict(generate=gen, post_check=pc, persist_candidate=pv,
                       profile_fn=prof, judge_fn=judge, journal=j)


def test_run_selection_filters_blocking_and_ranks(tmp_path):
    gen_map = {"cold_open": "干净的长候选文本内容一二三四五",
               "in_medias_res": "带泄密的候选",
               "slow_burn": "干净短候选"}
    posts = {"带泄密的候选": {"leaks": [{"marker": "治眼", "fact_id": "fact:治眼"}],
                              "issues": [], "degraded_stages": [],
                              "leaks_degraded": False, "punct_suggestions": []}}
    profiles = {"干净的长候选文本内容一二三四五": _prof(0.4, 0.2, shape=0),
                "带泄密的候选": _prof(0.65, 0.42, shape=1),
                "干净短候选": _prof(0.9, 0.6, shape=2)}
    calls, deps = _wire_sel(tmp_path, gen_map, posts, profiles)
    res = run_selection(chapter=9, **deps)
    assert len(res["candidates"]) == 3
    killed = [c for c in res["candidates"] if c["filtered"]]
    assert len(killed) == 1 and killed[0]["strategy"] == "in_medias_res"
    assert "find_leaks" in killed[0]["filter_reason"], "过滤原因必须可见(谁被杀、为什么)"
    alive = [c for c in res["candidates"] if not c["filtered"]]
    assert all(c.get("rubric_rank") is not None for c in alive), "幸存者才参与排序"
    assert res["consensus"] is True
    assert res["verdict"] == "awaiting_human", "机器只备料,终选永远在人"


def test_run_selection_generate_failure_fail_soft(tmp_path):
    """B1(爆炸半径):某候选 generate 抛异常(LLM 网关/日帽/超时)→ run_selection 不崩、
    跳过该候选、其余正常返回。此前 generate 循环无 try-catch,一发失败炸全部候选
    (前面已烧的候选丢失)+ journal 停 in_progress + 端点 500。"""
    def gen(strategy):
        if strategy["key"] == "in_medias_res":
            raise RuntimeError("LLM 网关连接失败")
        return {"cold_open": "候选甲文本" * 40, "slow_burn": "候选乙的文本内容" * 30}[strategy["key"]]
    deps = dict(
        generate=gen,
        post_check=lambda prose: {"leaks": [], "issues": [], "degraded_stages": [],
                                  "leaks_degraded": False, "punct_suggestions": []},
        persist_candidate=lambda prose, key: f"v-{key}",
        profile_fn=lambda prose: _prof(0.3 + (len(prose) % 7) * 0.1, 0.1 + (len(prose) % 5) * 0.12),
        judge_fn=lambda a, b: "A" if len(a) >= len(b) else "B",
        journal=PipelineJournal(tmp_path / "sel.json"),
    )
    res = run_selection(chapter=9, **deps)   # 不得抛
    assert res["verdict"] == "awaiting_human", "有成功候选→正常交人,不炸全部"
    assert len(res["candidates"]) == 2, "失败候选被跳过,其余 2 个正常返回"
    assert all(c.get("version_id") for c in res["candidates"]), "成功候选正常留版"


# ===== 端点级:D1 pilot 互斥 / B4 日帽预检 / C3 终选反哺 ingest =====
from .test_app import _client   # noqa: E402


def test_select_chapter_blocked_during_pilot(store):
    """D1:pilot 非 loop 步在途/连写中出候选 → 409(防互踩,同终选 R2-3)。"""
    import scribe3.app as A
    store.save_chapter(5, "正文", title="五")
    A._pilot_inflight.add(("main", 5))
    try:
        r = _client(store).post("/select/chapter?work=main", json={"chapter": 5, "force": True})
        assert r.status_code == 409, f"pilot 在途出候选须 409,实际 {r.status_code}"
    finally:
        A._pilot_inflight.discard(("main", 5))


def test_select_chapter_daily_cap_precheck(store, monkeypatch):
    """B4:日帽剩余不足 → 出候选前 429 预检(不半途烧一半再炸)。"""
    import scribe3.llm as L
    monkeypatch.setattr(L, "daily_remaining", lambda: 2)   # 剩 2 < 选择环约需 10
    store.save_chapter(6, "正文", title="六")
    r = _client(store).post("/select/chapter?work=main", json={"chapter": 6, "force": True})
    assert r.status_code == 429 and "日帽" in r.text, f"帽不足须 429,实际 {r.status_code}"


def test_select_chapter_unlimited_cap_skips_precheck(store, monkeypatch):
    """无限模式 remaining=None，不得被选择环成本预检误判为 429。"""
    import scribe3.app as A
    import scribe3.llm as L
    import scribe3.selection as S
    from fastapi.testclient import TestClient

    monkeypatch.setattr(L, "daily_remaining", lambda: None)
    monkeypatch.setattr(S, "run_selection", lambda **kwargs: {
        "candidates": [], "verdict": "awaiting_human",
    })
    store.save_chapter(8, "正文", title="八")
    _client(store)  # 注入隔离 store 与本地 complete_fn
    r = TestClient(A.app, raise_server_exceptions=False).post(
        "/select/chapter?work=main", json={"chapter": 8, "force": True})
    assert r.status_code == 200, f"无限模式不得阻断选择环，实际 {r.status_code}:{r.text[:120]}"


def test_select_finalize_enqueues_ingest(store, monkeypatch):
    """C3(D-13):终选定稿后排后台 ingest 反哺知识账本(不再停在旧稿)。"""
    import scribe3.app as A
    store.save_chapter(7, "旧正文", title="七")
    vid = store.add_chapter_version(7, "候选正文内容", kind="checkpoint", stage="candidate",
                                    label="选择环候选·cold_open")
    enqueued = []
    monkeypatch.setattr(A, "_enqueue_ingest", lambda bg, w, seq: enqueued.append(seq) or True)
    r = _client(store).post("/select/finalize?work=main", json={
        "chapter": 7, "version_id": vid, "reason_axis": "切入点", "reason_text": "更冷更克制"})
    assert r.status_code == 200, f"终选须 200,实际 {r.status_code}:{r.text[:120]}"
    assert 7 in enqueued, "终选后须排 ingest 反哺"


def test_select_finalize_rejects_filtered_candidate(store):
    """击杀稿(label 含 ·filtered)不得定稿——防 API 绕过前端。"""
    store.save_chapter(11, "旧", title="十一")
    vid = store.add_chapter_version(
        11, "被杀候选", kind="checkpoint", stage="candidate",
        label="选择环候选·cold_open·filtered")
    r = _client(store).post("/select/finalize?work=main", json={
        "chapter": 11, "version_id": vid, "reason_axis": "其他", "reason_text": "不该能定"})
    assert r.status_code == 422, r.text
    assert "击杀" in r.text or "过滤" in r.text or "候选" in r.text


def test_select_finalize_rejects_non_selection_version(store):
    """普通存档/非选择环版本不得经 finalize 定稿。"""
    store.save_chapter(12, "旧", title="十二")
    vid = store.add_chapter_version(
        12, "随手存档", kind="checkpoint", stage="final", label="手动存档")
    r = _client(store).post("/select/finalize?work=main", json={
        "chapter": 12, "version_id": vid, "reason_axis": "其他", "reason_text": "误操作"})
    assert r.status_code == 422, r.text


def test_run_selection_all_filtered_verdict(tmp_path):
    """全部候选 blocking → verdict=all_filtered(非假 awaiting_human)。"""
    gen_map = {
        "cold_open": "泄密稿甲密密密",
        "in_medias_res": "泄密稿乙密密密",
        "slow_burn": "泄密稿丙密密密",
    }
    leak_post = {"leaks": [{"marker": "密", "fact_id": "fact:x"}],
                 "issues": [], "degraded_stages": [],
                 "leaks_degraded": False, "punct_suggestions": []}
    posts = {p: leak_post for p in gen_map.values()}
    profiles = {p: _prof(0.3 + i * 0.2, 0.2 + i * 0.15, shape=i)
                for i, p in enumerate(gen_map.values())}
    calls, deps = _wire_sel(tmp_path, gen_map, posts, profiles)
    res = run_selection(chapter=9, **deps)
    assert res["verdict"] == "all_filtered"
    assert all(c["filtered"] for c in res["candidates"])
    # 击杀留版 key 带 ·filtered 后缀(由 persist 收到的 strategy_key 体现)
    assert all(c.get("version_id") for c in res["candidates"])


def test_run_selection_pseudo_diverse_regenerates_with_unused_strategy(tmp_path):
    near = "几乎一样的候选A"
    near2 = "几乎一样的候选B"
    gen_map = {"cold_open": near, "in_medias_res": near2, "slow_burn": "另一种",
               "dialogue_driven": "备用策略产出的候选文本"}
    profiles = {near: _prof(0.5, 0.3, shape=0), near2: _prof(0.505, 0.305, shape=0),
                "另一种": _prof(0.9, 0.65, shape=2),
                "备用策略产出的候选文本": _prof(0.2, 0.1, shape=1)}
    calls, deps = _wire_sel(tmp_path, gen_map, {}, profiles)
    res = run_selection(chapter=9, **deps)
    assert "dialogue_driven" in calls["gen"], \
        "伪多样触发→换未用策略重生成(换轴而非同参重掷,调研建议5)"
    assert res["pseudo_diversity_round"] is True


# ===== 端点集成(stub LLM,真 store) =====

_FENCE = ("⟦PROPOSAL scope=chapter⟧", "⟦/PROPOSAL⟧")
_BODY = ("院门虚掩着,他把伞立在阶下,听见里头有人翻动纸页。灶上坐着半锅冷粥,"
         "碗沿结了一层皮。他没有进去,先绕到窗根底下,数了数窗纸上的破洞。"
         "风从巷口过来,带着一点烧纸的味道。他把袖子按了按,才抬手叩门。")


def _sel_events(texts):
    state = {"n": 0}

    def fn(message, instructions, with_tools=True):
        t = texts[min(state["n"], len(texts) - 1)]
        state["n"] += 1
        yield {"type": "response.output_text.delta",
               "delta": f"{_FENCE[0]}{t}{_FENCE[1]}"}
        yield {
            "type": "response.completed",
            "response": {"id": None, "usage": {}},
        }
    return fn, state


def test_select_endpoint_key_chapter_gate_and_flow(store, monkeypatch):
    import scribe3.app as A
    from .test_app import _client
    c = _client(store)
    # 无标注章:422 拦(force 可越)
    store.save_chapter(3, "普通章正文。", title="三")
    r = c.post("/select/chapter", json={"chapter": 3})
    assert r.status_code == 422 and "关键章" in r.text
    # 三个策略产出三份不同候选(变体后缀撑开特征),judge 恒选 A(位置偏置)→ 无共识
    texts = [_BODY + "甲版收尾。", _BODY + "“你来了。”“嗯。”“坐吧。”乙版对话多。" * 3,
             _BODY * 2 + "丙版更长,句子也拉得开,风从檐下过,水在缸里响,人立在暗处不言。"]
    fn, state = _sel_events(texts)
    monkeypatch.setattr(A, "_responses_events", fn)
    A.set_complete_fn(lambda p, **kw: "A")   # judge 恒 A=纯位置偏置
    r2 = c.post("/select/chapter", json={"chapter": 3, "force": True})
    assert r2.status_code == 200
    body = r2.json()
    assert len(body["candidates"]) == 3
    assert body["verdict"] == "awaiting_human", "机器只备料,终选永远在人"
    assert all(cd["version_id"] for cd in body["candidates"]), "候选全部留版本"
    strategies = {cd["strategy"] for cd in body["candidates"]}
    assert len(strategies) == 3, "三候选策略互不相同"
    for cd in body["candidates"]:   # 真检测器可能击杀构造文本:被杀者必须给出原因
        if cd["filtered"]:
            assert cd["filter_reason"], "谁被杀、为什么必须可见"
    # (位置偏置识破由纯逻辑 test_round_robin_position_bias_detected 覆盖)


def test_select_finalize_persists_and_lessons(store, monkeypatch):
    import scribe3.app as A
    from .test_app import _client
    c = _client(store)
    store.save_chapter(4, "旧正文。", title="四")
    vid = store.add_chapter_version(4, "终选中意的候选正文。", label="选择环候选·slow_burn",
                                    kind="checkpoint", stage="candidate")
    r = c.post("/select/finalize", json={"chapter": 4, "version_id": vid,
                                         "reason_axis": "节奏", "reason_text": "慢炖版收得住"})
    assert r.status_code == 200
    assert store.get_chapter(4)["prose"] == "终选中意的候选正文。"
    body = r.json()
    assert body.get("lesson_saved") is True
    ls = store.list_lessons(chapter=4)
    assert ls and "胜在节奏" in ls[0]["text"] and "慢炖版收得住" in ls[0]["text"], \
        "终选理由必须入 lesson 流(沉淀环最贵输入)"
    r2 = c.post("/select/finalize", json={"chapter": 4, "version_id": vid,
                                          "reason_axis": "其他", "reason_text": "  "})
    assert r2.status_code == 422, "空理由拒绝(强制一句)"


def test_select_latest_reads_result_json(store, tmp_path, monkeypatch):
    """GET /select/latest 读落盘 .result.json,供前端刷新恢复。"""
    import scribe3.app as A
    from pathlib import Path
    # 钉 journal 路径到 tmp
    def _jp(work, ch):
        p = tmp_path / f"{work}_loop_ch{ch}.json"
        p.write_text("{}", encoding="utf-8")
        return p
    monkeypatch.setattr(A, "_loop_journal_path", _jp)
    result = {
        "chapter": 5,
        "verdict": "awaiting_human",
        "candidates": [{"strategy": "cold_open", "version_id": "v1", "filtered": False,
                        "prose_head": "头"}],
    }
    rp = _jp("main", 5)
    rp = rp.with_name(rp.name.replace("loop_ch", "select_ch", 1))
    (Path(str(rp) + ".result.json")).write_text(
        __import__("json").dumps(result, ensure_ascii=False), encoding="utf-8")
    r = _client(store).get("/select/latest?chapter=5&work=main")
    assert r.status_code == 200, r.text
    assert r.json()["verdict"] == "awaiting_human"
    assert r.json()["candidates"][0]["strategy"] == "cold_open"


def test_run_selection_journal_stages(tmp_path):
    gen_map = {s["key"]: f"候选{i}文本长度不一样{'x' * i}" for i, s in enumerate(STRATEGIES[:3])}
    profiles = {v: _prof(0.3 + i * 0.3, 0.15 + i * 0.25, shape=i)
                for i, v in enumerate(gen_map.values())}
    calls, deps = _wire_sel(tmp_path, gen_map, {}, profiles)
    res = run_selection(chapter=4, **deps)
    j = deps["journal"]
    assert j.should_skip("sel_ch4_gen_cold_open")
    assert j.should_skip("sel_ch4_rank")
    assert res["journal_recorded"] is True


# ===== L1 轻选择:2 策略短变体 + pick 持久化 =====

def test_l1_strategies_are_two_distinct():
    assert len(L1_STRATEGIES) == 2
    keys = {s["key"] for s in L1_STRATEGIES}
    assert len(keys) == 2
    assert keys <= {s["key"] for s in STRATEGIES}


def test_run_light_selection_two_variants(tmp_path):
    """L1 编排:注入 generate → 恰 2 条策略标签短变体 + awaiting_pick。"""
    texts = {
        "cold_open": "雨落在青石上。" * 20,
        "slow_burn": "他把茶杯转了一圈才开口。" * 18,
    }
    calls = []

    def gen(strategy):
        calls.append(strategy["key"])
        return texts[strategy["key"]]

    def persist(text, key):
        return f"lv-{key}"

    j = PipelineJournal(tmp_path / "l1.json")
    res = run_light_selection(
        chapter=3, generate=gen, persist_variant=persist, journal=j)
    assert res["tier"] == "L1"
    assert res["verdict"] == "awaiting_pick"
    assert len(res["variants"]) == 2
    strategies = {v["strategy"] for v in res["variants"]}
    assert strategies == set(texts)
    assert all(v["version_id"] for v in res["variants"])
    assert all(v["char_count"] >= 40 for v in res["variants"])
    assert set(calls) == set(texts)


def test_apply_light_pick_and_endpoint_persists_draft(store, monkeypatch, tmp_path):
    """L1 produce(stub)→ pick → 产品读路径 /latest-draft 可见选中短包。

    验收标准 2:点选必须落到与 /save-draft 同构的 stage='draft' 版本,
    前端 DraftTab 经 GET /latest-draft → latest_draft_version 恢复;只写
    chapter.draft 字段不够(前端零消费该字段作草稿 tab 主源)。
    """
    import scribe3.app as A
    import scribe3.selection as S
    from .test_app import _client
    store.save_chapter(9, "原正文。", title="九")
    variants = [
        {"strategy": "cold_open", "version_id": "v-a", "text": "冷开场短包甲" * 15,
         "directive": "d1"},
        {"strategy": "slow_burn", "version_id": "v-b", "text": "慢炖短包乙" * 15,
         "directive": "d2"},
    ]
    picked = apply_light_pick(variants=variants, strategy="slow_burn")
    assert picked["strategy"] == "slow_burn"
    assert "慢炖短包乙" in picked["text"]

    def fake_loop_path(work, chapter):
        p = tmp_path / f"{work}_loop_ch{chapter}.json"
        p.write_text("{}", encoding="utf-8")
        return p
    monkeypatch.setattr(A, "_loop_journal_path", fake_loop_path)

    def fake_run_light(**kwargs):
        out = {
            "tier": "L1", "chapter": kwargs["chapter"],
            "variants": variants, "verdict": "awaiting_pick",
            "gen_errors": [], "note": "stub", "max_chars": 800,
        }
        if kwargs.get("save_result"):
            kwargs["save_result"](out)
        return out
    monkeypatch.setattr(S, "run_light_selection", fake_run_light)
    c = _client(store)
    r = c.post("/select/light?work=main", json={"chapter": 9})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "L1"
    assert len(body["variants"]) == 2
    r2 = c.post("/select/light/pick?work=main", json={
        "chapter": 9, "strategy": "slow_burn"})
    assert r2.status_code == 200, r2.text
    pick_body = r2.json()
    assert pick_body["draft_seeded"] is True
    assert pick_body.get("stage") == "draft"
    assert pick_body.get("id"), "须返回 draft 版本 id(与 /save-draft 同字段)"
    # 产品读路径:GET /latest-draft 必须含选中正文(DraftTab 主源)
    r_ld = c.get("/latest-draft", params={"seq": 9, "work": "main"})
    assert r_ld.status_code == 200, r_ld.text
    ld = r_ld.json()
    assert "慢炖短包乙" in (ld.get("prose") or ""), (
        f"产品 /latest-draft 应含 L1 选中短包, got keys={list(ld.keys())} "
        f"prose_head={(ld.get('prose') or '')[:80]!r}"
    )
    # store 直读同构:latest_draft_version(WHERE stage='draft')
    lv = store.latest_draft_version(9)
    assert lv is not None, "latest_draft_version 须有 stage=draft 行"
    assert "慢炖短包乙" in (lv.get("prose") or "")
    # 兼容字段仍写(非产品主源,但保留)
    ch = store.get_chapter(9)
    assert "慢炖短包乙" in (ch.get("draft") or "")
    # L1 latest 可读回 picked
    r3 = c.get("/select/light/latest?chapter=9&work=main")
    assert r3.status_code == 200
    assert r3.json().get("verdict") == "picked"


def test_select_light_latest_404_without_run(store):
    r = _client(store).get("/select/light/latest?chapter=1&work=main")
    assert r.status_code == 404
