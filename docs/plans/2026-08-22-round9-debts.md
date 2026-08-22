# 第九轮挂账

| 项 | 内容 | 状态 | 预计清理轮次 |
| --- | --- | --- | --- |
| M19 | GitHub 分支保护 | 第十轮 P0 催办已执行；本机无 Settings 写权限，API 实测 `main.protected=false`，未落地 | 第十轮（本轮 L01）；未落则第十一轮评审阻断 |
| ingest_error | 新字段 ingest_message 双写一版 | 兼容期最后一轮。前端确认走 ingest_message（旧字段仅 fallback） | **第十一轮删列 migration** |
| dimensions | 质量评价旧字段兼容一版，消费方改读 gate.hits | 兼容期最后一轮 | **第十一轮确认消费方只读 gate.hits 后删字段** |
| N≥30 钝化 | 第八轮口径维持 800，钝化无必要 | 不实施（永久关闭） | 不实施 |
| K12 补注 | 关旗拼接兜底是安全网，旗开覆写成新渲染 | 已完成 | 已完成 |

→ 第十轮 spec 已产出，接续 L01-L13。兼容期不再延期：第十一轮必须删 `ingest_error` 列和 `dimensions` / `dimensions_deprecated` 旧字段。
