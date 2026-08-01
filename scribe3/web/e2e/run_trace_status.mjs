// Hermes 的远端完成会早于本地事件审计汇总；验收只读 Run 时，以远端完成态和
// 必需读取工具为准，不能把等待审计补全误报为模型仍在运行。
export function isReadOnlyRunCompleted(trace, requiredTool) {
  return trace?.response?.status === 'completed'
    && Array.isArray(trace?.tool_calls)
    && trace.tool_calls.some((call) => call?.name === requiredTool)
}
