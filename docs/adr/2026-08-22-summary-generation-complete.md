# ADR: 摘要生成设计完备性声明

## 状态：Accepted

## 覆盖证据
1. `codex_digest.py`：四种实体（character/faction/place/item）全覆盖
2. `chapter_analysis.py`：`quick_qc_summary` + `post_analysis_panel` 确定性路径
3. `post_analysis_summary`：防腐败（corrupt=True 标记 + fp 校验）
4. 章后分析缓存有 clear + fingerprint 双重保护
5. 测试：test_digest_completeness.py + test_unify_remaining.py 相关用例

## 统一度评判
本维度报 100%：四种实体 digest + 章后分析面板 + 防腐败守卫完备。
