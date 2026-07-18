"""纵切片 · 校验层 TDD。

find_leaks = 兜底 POV 修订 pass(限知渲染已在生成前结构性防住,这里是第二道)。
causal_complete = 把连贯性从"判官评审"前移成"可跑查询"(每事件须有因果入边+目标)。
"""
from scribe3.scenario import luanshi_leak_world
from scribe3.ontology import Event
from scribe3.verify import find_leaks, causal_complete


def test_find_leaks_catches_others_secret_in_pov_prose():
    """老道视角散文若说出焦三私密 → 判官必抓(兜底)。"""
    w = luanshi_leak_world()
    prose = "皂衣道士冷笑:够你给老娘治眼了。"
    leaks = find_leaks(prose, w, "role:老道", 1)
    assert "fact:治眼" in [l.fact_id for l in leaks]


def test_clean_pov_prose_no_leak():
    w = luanshi_leak_world()
    prose = "雨砸在烂泥上。皂衣道士只问那颗丹。"
    assert find_leaks(prose, w, "role:老道", 1) == []


def test_owner_may_voice_own_secret():
    """焦三视角说出自己的动机(在他帧内)→ 不算泄露。"""
    w = luanshi_leak_world()
    prose = "他攥紧那颗丹——给娘治眼的钱,总算够了。"   # 含 marker "治眼"
    assert find_leaks(prose, w, "role:焦三", 1) == []


def test_causal_complete_clean_scenario():
    w = luanshi_leak_world()
    assert causal_complete(w, 1) == []


def test_causal_complete_flags_missing_goal_and_cause():
    w = luanshi_leak_world()
    # 加一个无目标、无因果入边的非首事件 → 两项违规
    w.add_event(Event("ev:逃", "逃", participants={"SUBJ": "role:焦三"},
                      location="place:乱岗", story_time=1))
    viols = causal_complete(w, 1)
    assert "ev:逃" in [v.event_id for v in viols]
    reasons = " ".join(v.reason for v in viols if v.event_id == "ev:逃")
    assert "goal" in reasons and "causal_in" in reasons


def test_causal_complete_allows_explicit_independent_scene_root():
    """同章切换人物/场景的新根事件可免责，但必须留下可审计的因果根理由。"""
    w = luanshi_leak_world()
    w.add_event(Event("ev:支线", "支线", participants={"SUBJ": "role:焦三"},
                      location="place:乱岗", story_time=1, motivated_by_goal="追查另一条线索",
                      causal_root_reason="切换到另一人物视角的独立场景"))
    assert not any(v.event_id == "ev:支线" for v in causal_complete(w, 1))
