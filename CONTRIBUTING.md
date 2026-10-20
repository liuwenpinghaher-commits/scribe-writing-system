# 贡献指南 (Contributing to Scribe Writing System)

感谢你关注并参与 **铜炉写作系统 (`scribe-writing-system` / `scribe3`)** 的开源建设！在提交 Issue 或 Pull Request 之前，请仔细阅读本指南。

---

## 1. 核心架构准则（不可违背的工程红线）

1. **渲染前限知投影（Pre-Render Epistemic Projection）**：
   - 角色视角（POV）的限知隔离必须在组装 Prompt 的**渲染前阶段**通过 `fabula ∩ project_frame(focalizer)` 物理过滤完成，绝不能仅依赖生成后的事后判官修补。角色不知道的私密事实（`secret=True` 且无有效 `KnowledgeEdge`）物理上不得进入该角色的生成上下文。
2. **双时态与单一事实源（SurrealDB 3.x SSOT）**：
   - 故事世界设定（`Entity` / `Event` / `Fact` / `KnowledgeEdge`）以 SurrealDB 3.x 为唯一事实源（一书一库 `db=<work_slug>`）。
   - `scribe3/store/` 持久层严禁反向 import `scribe3/api/` 路由层代码。
3. **写路径同步确定性（Sync Write Pipeline）**：
   - `scribe3/playbook/pipeline.py` 与 `scribe3/stage_generate.py` 必须保持同步函数签名（禁止混入 `async def`），以保证流水线状态机与错误回滚的可预测性。
4. **隐私与版权红线**：
   - 严禁提交任何真实 API Key（`sk-*`、`ghp_*` 等）、服务器公网/内网 IP、私人域名、本机绝对路径（macOS/Linux 用户家目录绝对路径）或 `.env`、`.db`、`.sqlite*` 数据库文件。
   - 严禁提交受版权保护的第三方全本商业小说原文；拆文评估仅允许提交结构化章卡、抽象章法与短篇合法节选夹具。

---

## 2. 本地开发环境搭建

### 环境要求
- **Python**：3.11+
- **Node.js**：20+
- **SurrealDB**：3.2.x（推荐 `v3.2.4`，可通过 `curl -sSf https://install.surrealdb.com | sh -s -- --version v3.2.4` 安装）

### 安装依赖
```bash
# 1. 创建 Python 虚拟环境并安装后端与测试依赖
python3 -m venv scribe3/.venv
scribe3/.venv/bin/pip install -r scribe3/requirements-dev.txt

# 2. 安装前端依赖
cd scribe3/web
npm ci
npx playwright install chromium
```

---

## 3. 提交前必跑检查清单

在发起 Pull Request 之前，请确保在本地（使用独立隔离端口与临时内存 SurrealDB）100% 跑通以下检查：

```bash
# 1. 架构分层与语法静态检查
scribe3/.venv/bin/python -m compileall scribe3 -q
scribe3/.venv/bin/python -c "import scribe3.app"

# 2. 后端单元与确定性 E2E 测试（自动拉起临时内存 SurrealDB）
scribe3/.venv/bin/python -m pytest scribe3/tests -q

# 3. 前端单元测试与生产构建
cd scribe3/web
npm test
npm run build

# 4. 隔离环境全链路真实业务 E2E 测试（默认在隔离端口 :18300 / :15173 运行并自动清理）
cd ../..
bash scripts/e2e_ci.sh

# 5. 全仓敏感信息零命中扫描（确认无私有 IP、域名、本机用户名路径或明文密钥）
make check-clean
```

---

## 4. Commit 与 Pull Request 规范

- **Commit Message** 采用 Conventional Commits 格式：
  - `feat(ontology): ...` — 故事本体、双时态或知识帧新特性
  - `feat(craft): ...` — 拆文分析、章法护栏、四层质控增强
  - `feat(web): ...` — 写作台前端三栏交互与可视化改进
  - `fix(api): ...` — 接口、并发锁或恢复流修复
  - `test(e2e): ...` — 单元测试或 Playwright 端到端闭环补齐
  - `docs: ...` — 文档与架构图更新
- 每个 PR 应聚焦单一主题，并在描述中附上本地单测与隔离 E2E 的通过截图或日志摘要。
