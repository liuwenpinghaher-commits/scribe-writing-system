# R6: Hermes 升级评估

## 当前基线
- 版本: Hermes Agent v0.18.0 (tag v2026.7.1)·2026-07-05 采纳(下文"结果"节)
- 落后: 837 commits (截至 2026-07-09,`hermes --version`)

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

## 常态化 smoke(2026-07-10,H-11 落地)

一键体检脚本:`scribe3/scripts/hermes_smoke.sh`

- 只读模式(默认,不烧 token):三网关 `/health`+`/health/detailed`+`/v1/capabilities`
  断言(default=chat_completions,:8643=responses_api,:8644=run_submission+
  run_approval_response)、`:8643 /v1/skills` 含 scribe-novel-v2、cron best-effort。
- `--live`:额外真发 1 笔 :8643 Responses 短文本,验证端到端出字(烧 1 笔调用)。
- 退出码 0=全过。每次 `hermes update` 采纳前后、网关重启后、排查"生成失败"类
  问题时先跑它。API key 从各 profile `.env` 读取,只进请求头不回显。

升级演练固定顺序(沿用 D-028 教训):
1. `HERMES_HOME` 隔离环境升级 + 本脚本全过(含 `--live`);
2. 生产逐 profile 重启(nohup 后台 + 轮询 /health,勿前台 timeout);
3. 本脚本全过 + scribe3 `/ai/runtime-status` summary 无 issues;
4. 金丝雀:loop-qa 一章;
5. 异常回滚到台账记录的上一锚(当前锚:b88d0007c,升级前版本 v0.17.0)。

## 结果(2026-07-05,遗留处置批次三执行)

已按协议升级并采纳:v0.17.0(v2026.6.19+51, b88d0007c)→ **v0.18.0(tag v2026.7.1)**。
HERMES_HOME 隔离网关三 e2e 全过(Responses 生成/MCP 工具流/elicitation fail-closed)→
重启 8643 采纳 → 金丝雀 loop-qa 一章绿。回滚锚 b88d0007c。执行记录与运维教训
(前台 restart 勿加 timeout/混血态窗口/launchd 只管 default profile)见台账 D-028。
