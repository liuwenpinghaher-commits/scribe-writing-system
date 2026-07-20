# Creative Context Task 3 总复审修复报告

状态：`Ready`。Critical / Important 已经修复、受影响完整回归已通过，最终只读复审未发现新的 Critical / Important。

基线：`511a44e fix: close creative context outcome traces`。

范围：只修复 Creative Context Task 3 总复审的 Critical / Important。不扩大到新质量域包，不修改 Hermes 外部文档镜像，不 push。

## 问题与修复

### C1 动态 system instructions 没有来源清单

根因：写作 renderer 只返回最终字符串，prefix 和 envelope 后追加的设定、工艺、场景真相、请求约束等动态字节没有 `ContextSource`。

修复：

- renderer 支持 `str` 或 `(str, tuple[ContextSource, ...])`。
- secret guard、chapter position、tool scope、craft skills、focalizer、codex、seed words、craft、phase role、avoid、revelation discipline、purpose、scene truth 和 request constraint 均以稳定 `source_id/source_kind` 登记。
- 每个 digest 针对真正追加到 provider 输入的 UTF-8 字节，不保存正文。
- included source 缺 revision 时统一回退为 `content-sha256:<digest>`。

### C2 Pilot grounding / quality 绕过统一引擎

根因：`_grounding_llm` 和 Pilot `full_check -> post_check -> discipline_truncate` 直调 `hermes_complete`，没有 `ContextRequest / Manifest / Outcome`。

修复：

- 新增 `grounding.v1` 与 `quality-chapter.v1` 代码内策略。
- 两条生产审查路径统一经 `_contextual_review_complete` 编译，实际输入建 Manifest，官方 DeepSeek 成功、失败或不完整都写 Outcome。
- `hermes_complete_result` 保留安全的 provider identity、model、usage 与 response id；旧 `hermes_complete` 继续只返回文本，保持兼容。

### C3 error 先截断后脱敏

根因：app 对非字符串 error 先 `json.dumps(... )[:500]`，再交给存储脱敏，存在嵌套认证字段逃逸与被截断秘密片段无法识别的风险。

修复：`ContextStore.save_outcome()` 先用权威故事秘密集合对 dict/list/string 递归脱敏，再序列化，最后安全截断到 500 字符；查秘密失败继续 fail-loud，任何 DB 写入都在其后。

### C4 运行时仍预留第二套记忆适配器

根因：仓库仍保留 Spectron 适配器、影子评估 CLI、对应测试、runtime metric 探测与依赖预留，与“SurrealDB 唯一权威、不接入不预留”相冲突。

修复：

- 删除 `scribe3/spectron_adapter.py`、`scribe3/tools/spectron_shadow_eval.py`、`scribe3/tests/test_spectron_adapter.py`。
- 删除 app runtime 探测 / metric、`requirements-dev.txt` 依赖预留与生产注释引用。
- 增加运行树零适配器/零预留静态门禁。

### I1 不可变审计表并发非原子幂等

根因：Manifest / Outcome / Policy snapshot 的旧路径先查后建，并发时相同内容会直接冲突，异内容同 ID 也没有稳定显式错误。

修复：全部改为 `CREATE ONLY` 先行，唯一冲突后有限读回并逐字段比较；同内容幂等返回，异内容显式 `ValueError`。测试使用多个独立 `SurrealStore` 连接真实并发，不是 mock。

### I2 首个 provider 终态未冻结

根因：`terminal_seen=True` 后事件循环仍观察供应商元数据并应用后续终态，状态/id/model/usage/error 都可被覆盖。

修复：第一个 completed / failed / incomplete / cancelled 成为不可变事实；后续终态忽略，迭代器/transport 异常只告警，不反向改写。

### I3 omitted 决策未持久，Policy 禁用源未真正生效

修复：Manifest v2 每条来源带 `included/reason_code`，omitted 以 `included=false` 进表；Policy 与 request 的 forbidden kinds 合并后传入 assembler，在 render/provenance 前就排除受控原始源。

### I4 Policy snapshot 无法证明规则未漂移

修复：快照持久 `policy_key/version/schema_hash/safe payload`；payload 只含规则和协议版本，不含提示词、故事正文或秘密。同 key/version 但 schema/payload 改变显式冲突。

### I5 `project_frame` 异常被伪装成空帧

根因：`_canonical_frame_facts()` 与 `_faction_known_fact_ids()` catch-all 后返空，使查询/投影故障伪装成“焦点者什么都不知道”。

修复：删除两处 catch-all，查询或投影失败直接中止编译。

### I6 Hermes 网关与实际推理 provider 混为一层

修复：Outcome 在保留旧 `provider/model/provider_request_id` 兼容字段的同时，新增：

- `transport_provider/transport_request_id`
- `reasoning_provider/reasoning_model/reasoning_request_id`

官方直连记录 `httpx + deepseek`；Hermes 路由恒记 transport 为 `hermes_gateway`，只有事件 trace 真实提供下游 provider 时才填 reasoning 层，无证据时保持 `NONE`，不猜测。

### I7 included source revision 可为空

修复：Manifest 纯合同强制 included source revision 非空，无业务 revision 时用内容摘要版本；093 会对 091/092 真旧行回填，并重新收紧 READONLY。

### 最终复审追加修复

- Policy snapshot 恢复 091 已发布的稳定 ID `sha256(policy_version)`；093 真升级测试在回填后立即执行首次 `save_manifest()`，证明复用旧快照且不触发 `policy_version` 唯一索引冲突。
- renderer 返回的 supplemental sources 同样执行 Policy / request 合并后的 forbidden kinds，在 Manifest、Policy snapshot 或其他 DB 写入前 fail-loud。
- `final/draft` 的演绎块不再伪装成一条 scene truth；场景真相、每条 deduction、header/footer protocol 分别登记，digest 各自对应真正追加到 system instructions 的字节块。
- `ContextStore.save_manifest()` 在任何 Policy / Manifest 写入前重算规范载荷的 `manifest_hash`，拒绝 `model_copy()` 造出的 hash/内容脱节对象，伪造对象无法抢先落库。
- `actual_input_hash` 的已批准合同未改：它仅是 renderer 返回的最终完整 system instructions UTF-8 SHA-256，不包含 user message、images 或 `max_tokens`。复审中一度建议扩张该语义，经对照已批准合同后判为非缺陷。

## 迁移

新增 `093_creative_context_audit_closure.surql`，不修改已发布的 091/092。升级顺序：

1. 添加并回填 Policy / Manifest 新字段。
2. 对 092 已锁为 READONLY 的 optional revision 临时解锁。
3. 回填 included 与 `content-sha256:<digest>` revision。
4. 对所有新字段重新定义 READONLY。
5. 添加 Outcome transport / reasoning 分层字段并收紧不可变。

真实升级测试只先应用 091/092，插入 `revision=NONE` 的旧行，再应用 093；该测试曾真实揭示 092 READONLY 阻断回填，修复迁移顺序后转绿。

## TDD 证据

本修复波实际观察到的 RED：

- Manifest / Policy / 并发原子性：`7 failed, 12 passed`。
- 动态领域来源：`8 failed`。
- 093 真实旧形状升级：`1 failed`，原因为 092 已把 revision 锁为 READONLY。
- B 批聚焦合同：`7 failed`，直接命中首终态覆盖、嵌套 error、provider 分层、非流式 response id 与两条审查绕路。
- C 批：`3 failed`，命中适配器/运行指标/依赖预留与 `project_frame` 静默退空。

已完成的对应 GREEN：

- A 批联合：`29 passed`。
- B 批：Outcome `39 passed`；Pilot 拆分为 `38 passed + 9 passed`；Store `15 passed`；DeepSeek/LLM `92 passed`；provider 三形态与失败终态补充 `5 passed`。
- C 批：聚焦 `3 passed`；相关回归 `46 passed + 47 passed`。

## 最终验证与复审

后端全量首轮（排除父任务 `test_quality_contracts.py`）：

```text
21 failed, 2335 passed, 3 warnings in 1025.16s
```

该轮 21 项已全部逐组复现并修复：`test_app` 5 项、loop/S1 9 项、其余 7 项的节点回归均通过。按最终执行裁决，没有再次运行耗时约 17 分钟的全后端；不把首轮全量写成全绿。替代的完整受影响文件组合证据为：

- app / loop / S1 / gapfix / pulse / purpose / context contracts / persist / Hermes runtime：`451 passed, 3 warnings in 349.02s`。
- Pilot / Outcome / Creative Context Store + Engine / DeepSeek / LLM / Context Assembler + Performance：`248 passed, 2 warnings in 109.54s`。
- 复审追加问题的 RED：三项原 finding 组合 `3 failed`；伪造 manifest hash 单项 `1 failed`。
- 追加修复聚焦 GREEN：`6 passed, 2 warnings`；相关完整文件再回归 `78 passed, 2 warnings in 56.04s`。

前端与静态门：

- `npm run test`：`80` 个 test files、`513` 个 tests 全部通过，耗时 `15.68s`。
- `npm run build`：Vite production build 成功，`2997 modules transformed`，耗时 `633ms`；仅有既有的 `>500 kB` chunk 警告。
- 所有本批变更 Python 文件 `py_compile` 通过。
- `git diff --check` 通过。
- Spectron 运行树零适配器/零依赖预留门禁：`1 passed, 2 warnings`。

内部只读复审首轮发现 1 Critical + 3 Important（其中 `actual_input_hash` 扩张建议经合同核对判为非缺陷），随后又补充 1 Important manifest hash 完整性问题。修复后同一 reviewer 复审结论：无新 Critical / Important，`Ready`。仅余 1 个非阻断 Minor：deduction `source_id` 的位置序号在列表重排时会降低跨 Manifest 稳定性；它不影响当前安全、写入原子性或来源内容真值，本批范围只要求修复 Critical / Important，故记录而不扩大修改。

## 边界

- 不修改、不暂存 `.superpowers/sdd/progress.md`。
- 不修改、不暂存 `docs/external/hermes-agent-docs/manifests/` 与 `snapshots/`。
- 不纳入父任务的质量计划、`scribe3/quality/**` 和 `test_quality_contracts.py`。
- 本批不访问真实外部 DeepSeek / Hermes；未把 mock transport / 本地 SurrealDB 验证冒充在线真人验收。
- 不 push。
