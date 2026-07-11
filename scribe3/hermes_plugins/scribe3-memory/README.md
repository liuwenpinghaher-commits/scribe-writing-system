# scribe3-memory · 可选 Hermes MemoryProvider 适配层

让**直接用 Hermes 会话**(如 `hermes -p scribe3 chat`,而非 Scribe Web)也能读写 Scribe 记忆。

> 定位:**边缘增强,优先级最低,可选启用**。Scribe Web 的写作 / 主编对话**主路不依赖它**——
> 主路走 app 内 `ContextAssembler` / `MemoryRetriever` / `MemoryCapture` 直调。
> 不启用本插件,Scribe Web 一切照常。

## 它做什么

通过 Scribe 后端的 `/memory/*` REST(不直连 DB)接进 Hermes 会话的记忆生命周期:

| Hermes 生命周期钩子           | 调用                         | 作用                                   |
| ----------------------------- | ---------------------------- | -------------------------------------- |
| `prefetch(query)`             | `POST /memory/prefetch`      | 取组装好的记忆块文本注入 prompt        |
| `sync_turn(user, assistant)`  | `POST /memory/capture-turn`  | 幂等捕获一轮对话(**后台线程,非阻塞**)|
| `on_pre_compress` / `on_session_end` | `POST /memory/flush`  | 固化线程工作摘要 + drain 掉线残留      |

## 硬约束

- **work-scoped**:work 从稳定 session key `scribe3|work:{work}|thread:{thread_id}` 解出,
  每个请求都带 `?work=`;服务端按 per-work db 物理隔离 + work 绑定校验(跨 work→409)。**绝不串书**。
- **非阻塞**:`sync_turn` 用 daemon 线程后台捕获,主调用立即返回,绝不等网络。
- **只读工具**:`get_tool_schemas` 只暴露 `scribe_memory_search` / `scribe_memory_trace` /
  `scribe_context_current`;显式"记住偏好"走 Scribe 待批 API,**不在 provider 内直写设定/事实**。

## 依赖

仅 Python 标准库(插件运行在 Hermes 进程内,不共享 Scribe venv)。

## 安装与启用(默认**不**自动启用)

```bash
# 1) 同步 repo-owned 插件到 scribe3 profile(不启用,只列出确认)
bash scribe3/scripts/install_hermes_scribe3_memory.sh

# 2) 指向 Scribe 后端(默认后端 3320)
export SCRIBE3_API_BASE=http://127.0.0.1:3320

# 3) 独立显式启用(两步都要,缺一不生效)
hermes -p scribe3 plugins enable scribe3-memory
hermes -p scribe3 config set memory.provider scribe3-memory
```

未设 `SCRIBE3_API_BASE` 时 `is_available()` 返回 `False`,provider 不介入任何会话。
