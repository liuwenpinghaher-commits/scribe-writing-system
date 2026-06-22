# scribe3 主编 agentic 网关搭建(可复现)

完整 agentic 主编(主编自调 s3_ 工具查/写 SurrealDB)需要一个**独立的 scribe3 profile Hermes 网关**,
与用户主网关(default profile,:8642,挂 scribe2)隔离。本文记录搭建步骤——profile 配置在 `~/.hermes/`
仓库外,故在此存档。

## 架构

```
前端 :3311 → scribe3 后端 :3321 ──/chat/agentic-stream──┐
                                                        ↓
                          scribe3 profile 网关 :8643  /v1/responses(tools=mcp:scribe3)
                                                        ↓ 主编(doubao)决定调用
                          scribe3 MCP(stdio, run_mcp.sh)── s3_* 19 工具
                                                        ↓
                                          SurrealDB :8001 (NS=scribe3, db=main)
```

- **速答模式**(lite)走 default :8642 `/chat/completions`(纯 LLM,无工具),无需本网关。
- **联查实证模式**(agentic)走本 :8643 `/v1/responses`,主编自调 s3_ 工具。

## 搭建步骤

1. **scribe3 MCP 启动脚本**(已在仓库):[run_mcp.sh](run_mcp.sh) —— cd 仓库根 + `scribe3/.venv/bin/python -m scribe3.mcp`(连已运行的 :8001,不 spawn surreal,故中文路径 panic 坑无关)。

2. **建 profile**(若无):`hermes profile create scribe3`。

3. **profile config**(`~/.hermes/profiles/scribe3/config.yaml`)挂 MCP:
   ```yaml
   mcp_servers:
     scribe3:
       command: "/Users/miaoma/Downloads/写作 3.0/scribe3/run_mcp.sh"
       enabled: true
   platforms:
     api_server:
       port: 8643          # 避开 default :8642
       host: 127.0.0.1
   ```

4. **profile .env 端口**(`~/.hermes/profiles/scribe3/.env`)—— **.env 的 `API_SERVER_PORT` 覆盖 config.yaml**,必须同改:
   ```
   API_SERVER_PORT=8643
   ```
   (`API_SERVER_KEY` 与 default 相同,后端 `llm._api_key()` 读 `~/.hermes/.env` 即可复用。)

5. **起网关**:`hermes -p scribe3 gateway run --replace`(后台常驻)。验证:
   - `hermes mcp test scribe3` → ✓ 19 工具。
   - `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8643/v1/models` → 401(up,需鉴权)。

## 已知边界

- **MCP 连 db=main**(`scribe3/mcp.py setup_store(db="main")`)。故 agentic 主编当前以**主参照库**(乱世铜炉设定参照)为准;多书 agentic 需让 s3_ 工具按 work 切 DB(未做)。上下文注入(`_editor_system`)已按 work 正确。
- **写工具走 elicitation 待批**:agentic 流里主编调写工具(s3_add_* 等)会触发审批;非交互上下文 fail-closed(不写),只读工具不受影响。

## 真机验证(2026-06-23)

问「列未回收伏笔」→ 主编自调 `s3_list_promises` → 取回真实 17 伏笔,按章节(第0章世界法则…第5章还丹)+ 类型(人物承诺/悬念/契诃夫之枪)作答。端到端通。
