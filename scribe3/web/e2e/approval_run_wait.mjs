// TokenPlan 在作者批准后仍须完成一次模型收尾。真实 MCP 审批可能持续数十秒，
// 因此专项在 Run 级别保留三分钟，而非把成功写入误判为超时。
export const APPROVAL_RUN_SETTLE_ATTEMPTS = 180

export function isApprovedWriteFinalized(trace, tool) {
  return trace?.status === 'completed'
    && Array.isArray(trace?.tool_outputs)
    && trace.tool_outputs.some((output) => output?.tool === tool && output?.result_status === 'written')
}
