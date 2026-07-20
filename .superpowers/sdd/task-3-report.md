# Creative Context Task 3 独立复审修复报告

状态：`Ready`。首轮复审真实发现已完成 TDD 修复，最新全量回归与最终独立只读复审通过；修复与本报告已在同一追加提交中交付，不 push。

基线提交：`50a1f1d feat: route writing through creative context engine`

本报告只记录 Creative Context Task 3；原文件误混入的“无限 LLM 用量”任务已整体移除。

## 复审结论与根因

对基线提交的独立复审结论为 `Not Ready`：

- repair loop 与 selection 在 `CreativeContextEngine.compile()` 之后继续追加 system instructions，导致 Manifest 的 `actual_input_hash` 与 provider 实际收到的字节不一致；两条多轮路径也没有为每次真实调用建立独立 Manifest / Outcome。
- GET `/chat/write`、repair、selection、Pilot 已经生成 Manifest，但没有完整 Outcome；同步 `_collect_write()` 不累计原始 delta，也不保存 failed / incomplete 等终态。
- 官方 DeepSeek 半截流已经观察到的 response id、model、usage 没有随异常穿过 client、LLM facade 和 app，Outcome 与用量台账会丢失真实元数据。
- `SCRIBE3_CONTEXT_ASSEMBLER_V1` 已不控制任何生产路由，`SCRIBE3_SPECTRON_SHADOW` 也没有真实影子执行路径，但两者仍作为可写 danger setting / capability 暴露。
- 报告混入无关任务。收尾全量 `test_app.py` 还暴露了统一引擎迁移时遗失当前章尾段与 beats 的连续性回归。

后续只读复审提出“`actual_input_hash` 应包含 message / images / max_tokens”的扩张建议，controller 不采纳：Task 3 brief 的冻结退出门明确是
`sha256(官方 DeepSeek 实际收到的完整 system instructions UTF-8 字节)`，Task 1 Context Manifest 也以 renderer 最终字节为权威；它不是整个 HTTP body 的指纹。若未来需要请求整体身份，应新增独立 `model_request_hash`，不能在本任务偷改既有字段语义。

该轮复审另发现两个真实缺口并纳入本轮修复：DeepSeek 流取消时尚未把已观察 id/model/usage 传播到 Outcome/ledger；明确 completed/failed/incomplete/cancelled 终态后，晚到 transport exception 会反向覆盖终态。

## 修复内容

### 1. 实际输入哈希与每次调用独立绑定

- `_assemble_write_instructions_v1()` / `_assemble_write_instructions()` 增加受控 `extra_instructions`，repair constraints 与 selection strategy 在 renderer 内追加；编译返回后不再修改 instructions。
- renderer 生成的完整字节是 Manifest `actual_input_hash` 的唯一输入，因此 repair / selection 的动态指令也被精确覆盖。
- GET、POST、每轮 repair、每个 selection strategy、Pilot 都创建请求局部 `_WriteOutcomeBinding`，每次调用独立持有 Manifest trace，不共享可变全局状态。

### 2. Outcome 作为硬终态

- `_stream_write()` 把 `on_terminal` 与 best-effort `on_complete` 分离：先持久化 Outcome，成功后才做 chat 留痕；Outcome 写入失败直接上抛，不被 SSE error 或 chat callback 吞掉。
- 正常流在客户端看到 `done` 前写 Outcome；failed、incomplete、cancelled、异常和 `GeneratorExit` 也只执行一次终态回调。
- `_collect_write()` 统一处理 completed / failed / incomplete / cancelled / exception，累计供应商原始 delta 计算 `output_hash`，并在返回或抛错前写 Outcome。
- Pilot 不再绕过事件源调用 `hermes_complete`，而是复用 `_collect_write(text_mode=True)`；repair、selection、Pilot 均进入同一 Manifest / Outcome 链。

### 3. DeepSeek 半截流与 Pilot 预算

- `DeepSeekError` 只携带安全的 `response_id`、`model`、`usage` 与 `ProviderIdentity`；不保存 request、response、headers 或正文。
- EOF、provider error、invalid response 保留已经观察到的元数据；同一 provider error SSE 帧里的 id/model/usage 也不会丢失。
- 两个 LLM 流 facade 在客户端异常和无终态 EOF 两条路径都保留 metadata，并用半截 usage 结算 provider failure 台账。
- `max_tokens` 从 Pilot 贯通 `_collect_write → hermes_responses_events → DeepSeekClient.stream`；仅非 `None` 时向旧测试替身传递，保持兼容。
- DeepSeek client 解析完同一 SSE 帧的 id/model/usage 后，先向上游发 usage 观察事件，再发带 response id/model/identity 的 delta；usage 事件只代表“已观察”，不冒充成功终态。
- 两个 LLM facade 的 GeneratorExit/cancelled 台账保留取消前已积累 usage；Responses delta 同时携安全 id/model/provider trace/已知 usage，让 app 不必等终态才第一次获得元数据。
- app stream / collect 从每个原始事件累积元数据。provider 已给出明确终态后，晚到 transport/迭代器异常只告警，不再覆盖 status、id、model、usage 或 error。

### 4. 删除无效用户设置，保留真实运行事实

- 从 `settings.REGISTRY` 删除 `SCRIBE3_CONTEXT_ASSEMBLER_V1` 与 `SCRIBE3_SPECTRON_SHADOW`，并从 `context_cache.FLAGS` 删除 Spectron 假开关。
- `/capabilities.flags` 不再返回 `spectron_shadow`；兼容键 `assembler_v1` 恒为 `true`，只表达统一内核已经启用。
- runtime status 仍保留 Spectron availability / reason 检测，但指标不再伪造 `flag`。
- 前端默认 capability 与 API 注释同步：四个真实灰度开关默认关闭，`assembler_v1: true`。

### 5. 统一上下文连续性 parity

- chapter focus 现在把 synopsis 与 beats 一起放入有预算、有来源摘要的 focus block，来源标识为 `chapter:{seq}:outline`。
- recent block 把当前章最后约 400 字作为优先续写锚点，来源标识为 `chapter:{seq}:tail`；即使 Memory Fabric 返回 working / episodic candidates，也不会让当前章尾段消失。
- 这两项内容经 ContextEnvelope renderer 进入 provider 实际输入，因此自动受 Manifest 精确哈希覆盖，没有恢复旧散点拼接链。

## TDD 证据

本轮实际观察到的 RED 包括：

- GET `/chat/write` 没有 Outcome；repair / selection 多轮 Outcome 数量为 0；Pilot 绕过事件收集器并触发真实 key 配置错误。
- `_stream_write` 不支持硬 `on_terminal`；Outcome 保存失败被 best-effort chat callback 语义吞掉。
- `DeepSeekError` 没有 response id / model / usage；LLM incomplete 用量台账为 `None`；app Outcome 丢失半截元数据；`max_tokens` 两层签名缺失。
- 两个无效设置仍在注册表，capability 仍返回 Spectron 假开关，runtime metric 仍含 `flag`。
- provider error 同一 SSE 帧里的元数据丢失。
- 首轮全量 `test_app.py` 为 `333 passed, 3 failed, 2 warnings`；三个失败分别证明 GET / POST 当前章尾段未进入 instructions、beats 未进入统一 focus。
- 新增 assembler 聚焦合同在生产修复前为 `2 failed`：beats 缺失；开启 memory candidate 后当前章 tail 缺失。
- 后续复审补充的取消传播与终态保护合同首次运行是 `12 failed`：client usage/delta 顺序与 delta id 不满足；两个 facade 取消台账 usage 为 `None`；真实 SSE 取消 Outcome id 为空；stream/collect 的四种明确终态均被晚到异常覆盖。

对应生产修复后，尾段 / beats 的五项聚焦测试结果为：

```text
5 passed, 2 warnings in 4.55s
```

取消传播与终态保护的同一组测试修复后为：

```text
12 passed, 2 warnings in 4.30s
```

随后三文件聚焦回归首次暴露两条旧的精确事件断言仍冻结在修复前 delta 形状：
`118 passed, 2 failed`。生产合同要求 Responses delta 携安全 `model/trace`，且新增取消回归依赖该元数据；因此没有回退生产实现，只同步两条旧断言。重跑结果为：

```text
120 passed, 2 warnings in 18.63s
```

## 最终只读复审

最终裁决为 `Ready`，未发现新的可执行问题：

- `actual_input_hash` 仍严格等于 renderer 返回的完整 system instructions UTF-8 字节哈希，没有扩张成 message / images / max_tokens 或整个 HTTP body 的身份。
- DeepSeek 同帧 usage 先被上游观察，delta 携安全 response id / model / provider identity；取消、EOF 与客户端异常均保留已观察元数据和 usage。
- `_stream_write()` / `_collect_write()` 在 provider 已给出 completed / failed / incomplete / cancelled 后只告警晚到异常，不覆盖既定 status、id、model、usage 或 error。
- GET / POST、每轮 repair、每个 selection strategy 与 Pilot 都使用请求局部 Manifest / Outcome 绑定；硬 Outcome 仍先于 best-effort chat 留痕。

## 最终验证

### 后端

- `scribe3/tests/test_app.py` 全文件：`336 passed, 2 warnings in 285.96s`。
- Outcome、DeepSeek/LLM、loop、selection、Pilot、proposal、reveal isolation、assembler、settings/capability、memory trace、chat 留痕共 14 个受影响文件：`338 passed, 3 warnings in 129.52s`。
- `py_compile` 覆盖 `app.py`、`context_assembler.py`、`context_cache.py`、`deepseek_client.py`、`llm.py`、`settings.py`：退出码 0，无输出。

### 前端

- capability 聚焦测试已包含在完整 Vitest 中；该文件 `5 tests passed`。
- 最新完整 Vitest：`80 files passed / 513 tests passed`。
- Vite production build：成功；2997 modules transformed。构建仍报告既有大 chunk 警告，不是构建失败。

### 静态门禁

- `git diff --check`：退出码 0，无输出。
- 两个已删除设置名只存在于 `test_settings_migration.py` 的“注册表中不存在 / 不可写”负向断言。
- 其余 `spectron_shadow` 命中仅为 runtime availability 指标、对应测试和独立评估工具名，不是用户开关。

## Concerns / 边界

- 本批没有调用外部 DeepSeek / Hermes 在线服务；验证覆盖真实事件合同、`httpx.MockTransport`、本地真实 SurrealDB 夹具与完整 app 路由，但不冒充在线供应商验收。
- FastAPI `on_event` 弃用警告与一条既有 Pydantic schema 警告仍存在；前端构建仍有大 chunk 警告，均未导致失败。
- 本批不宣称十维质量引擎、参考作品比较或五万字真人验收完成。
- `.superpowers/sdd/progress.md` 和 Hermes 文档 manifests/snapshots 是用户的无关脏状态，本次不修改、不暂存。

## Commit

本报告随本轮追加修复提交一起交付；Git commit 无法在自身内容中稳定自指 SHA，准确 SHA 以父代理交接为准。不 push。
