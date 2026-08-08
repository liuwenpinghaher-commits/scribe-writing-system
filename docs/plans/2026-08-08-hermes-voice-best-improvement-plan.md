# 最佳改进方案：三网关不动 + Hermes 配套优化 + **网页语音全链路真实闭环**

> **状态**：方案（待执行）  
> **日期**：2026-08-08  
> **约束（硬）**：  
> 1. **不改三网关架构**（:8642 零工具 / :8643 只读 / :8644 可写+审批）  
> 2. 剧情/过程记忆仍在 **Surreal `memory_fabric`**，**禁止** Hermes memory 存剧情  
> 3. 语音必须是 **Web 产品内可点可用** 的全链路，不是「本机 CLI 能说话」  
> 4. 验证 = 打 **已部署 demo** 冒烟；不在 Grok 机跑重依赖  

**与既有结论的关系**

| 项 | 处理 |
|----|------|
| Surreal 3.2.4 优化轨 | **已结案（T+P API）**；本方案不重复 |
| Hermes 三网关 | **保持**；本方案只消费其 HTTP 能力 |
| Hermes 0.20 语音 | CLI/IM 能力 **复用配置与 provider**，经 **scribe 后端桥接** 进 Web |

---

## 0. 一句话目标

> 在 **不合并、不削弱三网关安全隔离** 的前提下，让作者在 **www.qing.blue 写作台** 完成：  
> **按住说话 → 转写文本 → 走现有讨论/动稿链路（含 context + 记忆）→ 流式回复 → 朗读播放 → 本轮写入 memory_fabric**，  
> 并配套 Hermes 延迟/分档/超时等 **低成本网关优化**。

---

## 1. 为什么这是「当前最佳」

| 维度 | 选择 | 原因 |
|------|------|------|
| 三网关 | **不动** | 零工具/只读/可写隔离是产品不变量；合并进程属另案 |
| 语音落点 | **Web + FastAPI 桥**，不是 Hermes CLI voice | 多用户、登录态、作品隔离、context 绑定都在 scribe |
| STT/TTS 引擎 | **优先复用 Hermes 已配的 tts/stt provider**（demo `config.yaml` 已有） | 「官方语音栈」真实复用，又不把写工具面暴露给语音 |
| 记忆 | **继续 Surreal capture** | 已验收；语音只是输入输出模态 |
| 范围 | 语音闭环 + Hermes A 档运维优化 | 避免再开 Spectron/A2A 大坑 |

**非目标**

- 改三网关端口/合并进程  
- Hermes 桌面/唤醒词/对讲机模式当主产品  
- WhatsApp 等 IM 语音条  
- 角色「文风 voice_profile」演化（已有 Codex 能力，与麦克风无关）  
- 本机浏览器依赖装在 Grok 机  

---

## 2. 现状（必须认清）

| 层 | 现状 |
|----|------|
| 前端 | **无** 麦克风/TTS 产品控件（仅有「角色声线」voice_flags 业务） |
| 后端 | 聊天/动稿 SSE、context 三件套、memory capture/prefetch **已有** |
| Hermes | **0.20.0**；三网关运行；`config.yaml` 已配 **tts/stt** 多 provider，`voice.auto_tts` 默认 false |
| 记忆 | Surreal fabric 默认开；API 级闭环已验 |

→ 缺口集中在：**浏览器采集 + STT + TTS + 与现有 chat 绑定的产品编排**。

---

## 3. 目标架构（语音全链路）

### 3.1 数据流（真实闭环）

```text
┌──────────── 浏览器（写作台）────────────────────────────┐
│  [🎤 按住说话] MediaRecorder / 可选 WebSpeech           │
│       ↓ audio/webm 或 本地 partial 文本                  │
│  POST /api/voice/stt  ──→  { text, lang, conf }         │
│       ↓ 填入讨论框 / 动稿输入                            │
│  现有链路：                                              │
│    · 讨论 SSE  /chat/stream|agentic-stream               │
│    · 动稿 SSE  /chat/write + context_session 三件套      │
│       ↓ 流式文本 delta                                   │
│  [可选自动朗读] 累计句段 → POST /api/voice/tts          │
│       ↓ audio/mpeg|wav                                   │
│  <audio> 播放；用户可停/跳过                             │
│       ↓                                                  │
│  既有 _capture_turn_memory / capture-turn → Surreal     │
└──────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   Hermes 网关（不动三端口）      STT/TTS Provider
   · 讨论/agentic → :8643         · 优先读 Hermes 配置的
   · 动稿/runs   → :8644            stt/tts 段（edge/openai/…）
   · 纯补全/工具外 → :8642        · 或后端直连同一 API key
   · STT/TTS **不走 :8644 写工具面**
```

### 3.2 关键不变量（与三网关一致）

| 规则 | 说明 |
|------|------|
| 语音 **不** 调用 8644 的 agent 工具 | STT/TTS 是模态转换，不是「改世界」 |
| 动稿/审批仍只走 8644 | 写世界与语音解耦 |
| 文本进模型前与键盘输入 **同一套** context/memory | 避免语音旁路漏记 |
| 音频 **默认不落正典** | 只存转写文本；可选短时 audio cache（TTL） |

### 3.3 为何不「Hermes CLI voice 接 Web」

| 做法 | 问题 |
|------|------|
| 浏览器转 WebSocket 到 hermes voice | 多用户、鉴权、作品隔离难；三网关工具面易串 |
| 仅 SSH 上 `hermes voice` | **不是产品闭环** |

正确：**scribe 拥有会话与鉴权；Hermes 继续当 LLM 网关；STT/TTS 用 Hermes 已配 provider 或等价 HTTP。**

---

## 4. 语音闭环 · 分阶段交付（必须可演示）

### 阶段 V0 · 可演示最小闭环（约 3–5 天）— **必须先做**

**目标**：demo 上点麦克风能完成一轮「说 → 回 → 听 → 库有记忆」。

| 模块 | V0 选择（务实） | 验收 |
|------|-----------------|------|
| STT | **浏览器 Web Speech API（zh-CN）** 为主；失败提示用键盘 | 中文口令转写进输入框 |
| 对话 | 转写文本 → **现有讨论 SSE**（不强制动稿） | 流式回复可见 |
| TTS | **浏览器 speechSynthesis（zh-CN）** 或后端 **edge-tts** 二选一（优先后端 edge，可控） | 回复自动/点按钮朗读 |
| 记忆 | 讨论落盘 + capture（走现有路径） | `memory_item` 增加或 messages 可查 |
| 三网关 | 讨论仍 8643；不改端口 | systemctl 三服务仍 active |

**V0 不做**：唤醒词、打断、流式 TTS 逐句、动稿语音、方言、说话人分离。

**V0 页面入口**

- 主编讨论区：🎤 按钮 + 「朗读回复」开关  
- 权限：HTTPS（demo 已有）+ 麦克风授权文案  

**V0 API（后端）**

| 方法 | 路径 | 作用 |
|------|------|------|
| POST | `/api/voice/stt` | V0 可 **薄封装**（若纯浏览器 STT 则可先不做；建议仍留接口便于 V1） |
| POST | `/api/voice/tts` | `text` → audio 流；鉴权 + 长度限制 |
| GET | `/api/voice/status` | 能力：stt_mode/tts_provider/ready |

### 阶段 V1 · Hermes Provider 真接 + 动稿语音（约 1–2 周）

| 模块 | V1 |
|------|-----|
| STT | 浏览器 `MediaRecorder` → `/api/voice/stt` → **Whisper/OpenAI 兼容或 Hermes stt 配置的 provider** |
| TTS | `/api/voice/tts` 读 **与 Hermes 同源** 的 provider 配置（env 拷贝或只读解析 `~/.hermes` 中非密钥结构 + 服务端密钥） |
| 动稿 | 语音转写 + **context_session 三件套** + `POST /chat/write` SSE；流式句末触发 TTS 队列 |
| 打断 | 用户再按麦 → 停播 + 可选 abort 流 |
| 网关 | 仍 8642/8643/8644；**LLM 不变** |

**V1 验收剧本（门禁）**

1. 登录 demo → 打开作品 main  
2. 讨论：说「备忘：密室铜炉先写寒意」→ 看到转写 → 发送 → 有回复 → 自动朗读  
3. 查库或 Inspector：相关记忆/消息存在  
4. 动稿：带 context，语音说写作指令 → SSE 出正文 → 可朗读  
5. 三网关 `systemctl is-active` 仍为三个 active；写工具面未因语音暴露到 8642  

### 阶段 V2 · 体验打磨（可选）

- 流式 TTS（分句合成，降首包听感）  
- 音色/语速设置（用户级，进 settings）  
- 转写置信度低时二次确认  
- 音频短缓存与隐私清理策略  
- 与 pending-claims 语音确认（高级）  

---

## 5. 配套：Hermes 网关优化（三网关不动）

与语音并行、**不阻塞 V0**。

| ID | 项 | 验收 |
|----|----|------|
| H1 | TTFB / 整轮耗时基线脚本 | 文档数字 |
| H2 | 三 profile 模型/max_tokens/reasoning 分档（仅配置） | provision 不破坏 toolsets |
| H3 | gateway_timeout 与后端 client 对齐 | 长写作不假死 |
| H4 | 三网关重启 + models/completion smoke | 三端口 200 |
| H5 | 语音相关 **禁止** 改 8642 toolsets 为空以外的值 | 护栏测试 |

**禁止**：为语音在 8642 挂 MCP；为语音合并网关。

---

## 6. 模块设计要点

### 6.1 后端 `scribe3/api/routers/voice.py`

- 鉴权：与现网 cookie session 一致  
- `work`：`X-Work` / query  
- 限流：每用户 STT/TTS 次数与正文长度上限  
- TTS 输入：纯文本，strip；拒绝对路径/HTML  
- 日志：不写完整音频到应用日志；可记 duration/provider  

### 6.2 STT 适配器

```text
VoiceSttProvider (protocol)
  - WebSpeechClientHint  # 前端本地，后端只返回 capability
  - OpenAIWhisperCompat  # HTTP file upload
  - HermesConfigStt      # V1：读配置选 provider
```

### 6.3 TTS 适配器

```text
VoiceTtsProvider
  - EdgeTts / OpenAITts / 与 Hermes tts 段对齐的实现
  - BrowserHint           # V0 可仅返回 {mode: browser}
```

### 6.4 前端

- `VoiceMicButton`：按住录音 / 松手结束  
- `useVoiceStt` / `useVoiceTts` hooks  
- 与讨论输入框、动稿输入框接线  
- 状态：listening / transcribing / speaking / error  
- **必须** HTTPS  

### 6.5 与记忆闭环

| 事件 | 动作 |
|------|------|
| 用户语音转写确认发送 | 与键盘发送同一 `capture` / chat 落库 |
| 助手回复 | 现有 assistant 落盘；TTS 不另存一份「真相」 |
| prefetch | 下一轮文本 query 仍走 fabric（语音转写的字参与） |

---

## 7. 安全与隐私

| 风险 | 缓解 |
|------|------|
| 音频含敏感剧情 | 默认 **不落盘** 或 TTL 分钟级缓存后删 |
| STT 经第三方 | 密钥仅服务端；用户告知 |
| 误触写库 | 语音不直连 8644 工具；改世界仍审批 |
| 刷接口 | 限流 + 登录 |
| XSS 播恶意文本 | TTS 仅信自己的 SSE 文本，转义 |

---

## 8. 验收矩阵（语音轨专用）

### T 技术

| # | 项 | 通过 |
|---|-----|------|
| VT1 | `/voice/status` 200，标明 stt/tts 模式 | |
| VT2 | STT：固定中文样例句 CER/可听辨 | |
| VT3 | TTS：返回可播 audio，Content-Type 正确 | |
| VT4 | 讨论全链路：说→回→听 | |
| VT5 | 记忆：一轮后 memory 或 messages 可证 | |
| VT6 | 三网关仍隔离（8642 tools 空） | |

### P 产品

| # | 项 | 通过 |
|---|-----|------|
| VP1 | 麦克风授权与失败文案 | |
| VP2 | 转写可编辑再发送 | |
| VP3 | 朗读可关；说话时停播 | |
| VP4 | 动稿语音（V1）context 不 400/500 | |

### 结案

- **V0 结案**：VT1–VT5 + VP1–VP3  
- **V1 结案**：+ VT6 复核 + VP4 + 动稿 SSE 正常  

---

## 9. 实施任务拆分（可排期）

| ID | 任务 | 阶段 | 依赖 |
|----|------|------|------|
| VO-01 | `GET /voice/status` + 能力探测 | V0 | — |
| VO-02 | `POST /voice/tts`（edge 或 browser hint） | V0 | VO-01 |
| VO-03 | 前端 Mic + 转写填框（Web Speech） | V0 | — |
| VO-04 | 前端朗读开关 + 播放器 | V0 | VO-02/03 |
| VO-05 | 讨论发送接线 + 记忆确认脚本 | V0 | VO-03 |
| VO-06 | demo 部署与验收剧本录像/记录 | V0 | VO-05 |
| V1-01 | MediaRecorder + `/voice/stt` 服务端 | V1 | V0 |
| V1-02 | TTS 对齐 Hermes provider 配置 | V1 | V0 |
| V1-03 | 动稿 + context 三件套语音入口 | V1 | V1-01 |
| V1-04 | 打断/停播/队列 | V1 | V1-03 |
| H-01…H-05 | 网关基线与 profile 分档 | 并行 | 不动端口 |

---

## 10. 风险与回滚

| 风险 | 缓解 |
|------|------|
| Web Speech 中文质量不稳 | V0 可编辑转写；V1 上服务端 STT |
| edge-tts/第三方不稳定 | provider 可切换；失败降级为只显示文字 |
| 动稿再 500 | 已修 sse_response；语音走同一 write |
| 资源 | STT/TTS 在 demo 机；限制并发 |
| 回滚 | 隐藏麦克风 feature flag `SCRIBE3_VOICE_V1=0` |

---

## 11. 成功标准（产品语言）

作者在 demo：

1. 点麦克风说完一句中文；  
2. 看到可编辑转写并发送；  
3. 收到主编流式回复；  
4. 能听到朗读（或一键朗读）；  
5. 系统侧本轮进入讨论/记忆链路（可查）；  
6. 全程 **未** 破坏 8642/8643/8644 分工。

满足 1–6 = **语音全链路真实闭环成立**。

---

## 12. 建议执行顺序（拍板用）

```text
第 1 周：V0（Web Speech + TTS + 讨论闭环）← 优先可演示
并行：H1–H4 网关基线（不改端口）
第 2–3 周：V1（服务端 STT + Hermes provider + 动稿语音）
之后：V2 体验
```

**默认下一句指令**：`执行 V0` → 按 VO-01…VO-06 落地到 demo。

---

## 13. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-08-08 | 初版：三网关不动 + 语音全链路真实闭环为中心的最佳改进方案 |
