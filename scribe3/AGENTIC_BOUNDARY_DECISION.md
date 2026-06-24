# R3 决策:agentic 主编读写边界

## 决策:甲(agentic 只读,写走 REST 待批)

- **agentic 主编只读**:主编 agent 通过 MCP 工具只读核实世界状态,不直接写。
- **写世界走 REST**:作者经前端 REST 端点直编(作者可信通道,全权含 secret)。
- **MCP 写工具走 elicitation 待批**:s3_add_fact 等写工具经 commit_if_approved,非交互上下文 fail-closed 不写。

## 理由
1. 零代码即消除"配了写工具却写不进"的认知错位。
2. REST 待批写(B3 已落地)是单一落库点 _execute_write,写路径已闭环。
3. 乙(交互批准通道)作为中期可选增强保留,待 F 安全枢纽确立统一写门控后再评估。

## 下游影响
- F(安全)/C(账本)只需守 REST 写门控一条线。
- 若未来转乙,须与 F 同批改门控,并在 C 的幻觉/幂等校验里覆盖 agentic 写路径。
