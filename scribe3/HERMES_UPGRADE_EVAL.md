# R6: Hermes 升级评估

## 当前基线
- 版本: Hermes Agent v0.17.0 (2026.6.19)
- 落后: 504 commits (截至 2026-06-24)

## 评估流程(不盲升)
1. 拉变更面: `hermes update --dry-run` 或查上游 changelog
2. 影响评估清单:
   - config.yaml 键名(compression/skills.external_dirs/approvals.mode/api_server.port)
   - ctx.elicit 签名
   - /v1/responses tools 协议
   - cron --script 解析语义
3. 隔离演练: 非生产 profile 上 hermes update 后跑回归
4. 窗口: 中期,不进第一阶段

## 决策: 不盲升,待破坏性变更评估后择机

## 结果(2026-07-05,遗留处置批次三执行)

已按协议升级并采纳:v0.17.0(v2026.6.19+51, b88d0007c)→ **v0.18.0(tag v2026.7.1)**。
HERMES_HOME 隔离网关三 e2e 全过(Responses 生成/MCP 工具流/elicitation fail-closed)→
重启 8643 采纳 → 金丝雀 loop-qa 一章绿。回滚锚 b88d0007c。执行记录与运维教训
(前台 restart 勿加 timeout/混血态窗口/launchd 只管 default profile)见台账 D-028。
