// 校验徽章 = 有问题的类目数(0–3),与面板三行同源,永不爆 99+。
export function verifyIssues({ leaks = 0, qcN = 0, causal = 0 }) {
  return (leaks > 0 ? 1 : 0) + (qcN > 0 ? 1 : 0) + (causal > 0 ? 1 : 0)
}
