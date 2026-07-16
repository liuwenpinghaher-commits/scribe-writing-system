"""矩阵③:焦点角色不该知道的秘密泄进正文 → /check 的 leaks 真抓出(U-003)。
与 test_reveal_isolation.py(单元)互补:这里走真端点全链路。"""
from scribe3.tests.e2e import world


def test_check_catches_offlimits_secret_leak(full_stack, store):
    """胡不为视角写出老乌头的秘密隐情 → /check 报 leak,且 leaks_error 为 None(检测器真跑通)。"""
    world.populate(store)
    r = full_stack.post("/check", params={"seq": 2},
                        json={"prose": world.LEAK_PROSE, "focalizer": world.LEAK_FOCALIZER})
    data = r.json()
    assert data["leaks_error"] is None, "检测器应跑通(非故障)"
    assert data["leaks"], "限知泄露必须被抓出,不能静默放行"
    assert any(world.LEAK_SECRET_MARKER in lk.get("marker", "") for lk in data["leaks"])


def test_check_clean_prose_no_false_leak(full_stack, store):
    """反向:一段不含越权秘密的稿子 → 无 leak(排除检测器恒报的假阳性)。"""
    world.populate(store)
    r = full_stack.post("/check", params={"seq": 2},
                        json={"prose": "胡不为牵着驴子,在月色下踉跄前行。", "focalizer": world.LEAK_FOCALIZER})
    data = r.json()
    assert data["leaks_error"] is None
    assert data["leaks"] == []
