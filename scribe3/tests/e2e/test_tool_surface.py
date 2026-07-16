"""矩阵④:工具面白名单——默认网关零工具面、写作模型无 reveal 钥(U-006/U-003)。
与 test_reveal_isolation.py(单元 20 个)互补:这里断言整体启动守卫在当前配置下无违规。"""
import scribe3.app as A


def test_startup_guard_no_toolface_no_reveal_violations():
    """启动守卫探针:当前配置不得暴露默认网关工具面(U-006)或 reveal 全知工具(U-003)。
    config 读不到(CI 无 provision)→ 返回空,测试仍绿;配置被污染引入违规 → 此测试变红。"""
    violations = A._gateway_security_violations()
    assert isinstance(violations, list)
    assert not any("U-006" in v for v in violations), f"默认网关暴露工具面:{violations}"
    assert not any("_reveal" in v for v in violations), f"网关挂 reveal 全知工具:{violations}"
