# Hermes Agent 官方证据缓存

本目录保存用于审计 Hermes Agent 能力的官方、可复现证据。它是独立的文档证据层，不进入小说素材、世界设定、章节记忆或 `CreativeContextEngine` 的业务召回，也不写入 SurrealDB 业务数据。

## 官方来源白名单

只接受下列来源：

- 官网 Sitemap：`https://hermes-agent.nousresearch.com/docs/sitemap.xml`，以及它列出的同源 `/docs` 页面。
- 官方仓库：`NousResearch/hermes-agent`。仓库发现只使用官方 GitHub API，文件按固定 commit SHA 下载。

跨域重定向、带凭据的 URL、非官方镜像和 GitHub HTML 展示页都不是允许的证据来源。

## 不可变快照与当前指针

`snapshots/` 下的每个目录都是不可变快照。刷新会生成新的官网时间快照或新的 `main-<sha>` 快照，不覆盖旧证据。发布标签先解析为固定 SHA；`main` 也必须先解析为固定 SHA，然后才能写入 `main-<sha>`，避免同一快照内文件随分支漂移。

`current.json` 只保存当前推荐的 Manifest、snapshot root 和哈希指针，不是软链接。`all` 只有在 website、release 和 main 三层都无抓取失败且全部通过完整性门时，才会一次性替换这三个指针。任一层失败都保留之前的 `current.json`。

## 四层证据的含义

- `website`：抓取时官网 Sitemap 可见的公开文档。
- `release`：某个发布标签解析后的不可变仓库快照，表示该发布版文档声明的能力。
- `main`：抓取时官方主干的固定 commit 快照，只能证明主干已包含某声明，不能冒充本机已安装或已启用的能力。
- `runtime`：对本机当前安装和实际运行路径的去敏观测。只有这一层可以支持“本机已观测”的结论，文档声明不能代替运行时探针。

## 刷新命令

官网抓取依赖 `scribe3/requirements.txt` 锁定的 `Crawl4AI 0.9.2`。首次安装或重建 venv 后，先安装 Python 依赖和 Chromium，再运行官方 doctor：

```bash
scribe3/.venv/bin/pip install -r scribe3/requirements.txt
scribe3/.venv/bin/crawl4ai-setup
scribe3/.venv/bin/crawl4ai-doctor
scribe3/.venv/bin/pip show crawl4ai
```

`crawl4ai-setup` 安装 Crawl4AI 使用的 Playwright/Patchright Chromium。`pip show crawl4ai` 应报告 `Version: 0.9.2`，doctor 必须完成真实浏览器抓取后才能把本机 runtime 记为可用。Crawl4AI 未安装时，`website` 和包含 website 层的 `all` 都返回退出码 2；`discover`、repository 快照与已有缓存的完整性检查不依赖 Crawl4AI 浏览器。

在仓库根目录执行：

```bash
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli discover --json
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli website --concurrency 5 --batch-size 40
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli website --resume
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli repository --ref v2026.7.7.2
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli repository --ref main
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli all
```

`discover --json` 只读取和校验 Sitemap，不创建 `snapshots/`。官网抓取每批不超过 40 个 URL，实际并发默认为 5 且不允许更高。`--resume` 只接受 source、filter policy 版本、Sitemap SHA-256 和 snapshot ID 全部匹配的未完成 checkpoint；缺失、多个候选或任一不匹配都 fail closed。

## 完整性检查

```bash
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli integrity --all
scribe3/.venv/bin/python -m scribe3.hermes_evidence.cli integrity --manifest docs/external/hermes-agent-docs/manifests/<manifest>.json
```

`integrity --manifest` 会从指定的独立 Manifest 文件重建 `SnapshotManifest`，再根据受校验的层身份定位明确的 snapshot root；不会把 Manifest 的父目录当作 snapshot root。网络、语义、目录布局或完整性失败返回退出码 2；只有选定操作无 failures 且完整性通过才返回 0。

## 动态搜索页与 skills

官网 `/search` 是动态导航表面，快照中显式标记为 `navigation_only`，不把当时的结果壳当成稳定正文或完整检索索引。需要最新搜索结果时，应对当前官网执行动态搜索，并与证据快照分开记录。

`skills/**/SKILL.md` 和 optional skill 文档只是程序性证据：它们可以说明官方推荐的步骤、工具用法或工作流，但不是 Hermes 运行时 API 合同，也不能证明某个本机 profile 已安装、已启用或已验证该能力。

## Secret 边界

快照、Manifest、retry 事件和失败记录都不得保存 API key、token、Authorization header、cookie、密码、私钥、`.env` 内容、用户正文或完整错误响应体。可以保留 `${API_KEY}`、`YOUR_TOKEN` 和 `[REDACTED]` 这类占位文档。发现疑似 secret 时必须在写盘或更新 `current.json` 之前 fail closed，错误输出不回显命中值。
