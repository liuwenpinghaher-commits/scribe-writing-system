// 词级 LCS diff(中文用 Intl.Segmenter 分词,更易读;不支持则回退字符级)。
export type DiffSeg = { type: "same" | "del" | "ins"; text: string };

function tokenize(s: string): string[] {
  const SegCtor = (Intl as unknown as { Segmenter?: typeof Intl.Segmenter }).Segmenter;
  if (SegCtor) {
    try {
      const seg = new SegCtor("zh", { granularity: "word" });
      return Array.from(seg.segment(s), (x) => x.segment);
    } catch { /* 回退 */ }
  }
  return Array.from(s);
}

export function diffChars(a: string, b: string): DiffSeg[] {
  const A = tokenize(a || ""), B = tokenize(b || "");
  const n = A.length, m = B.length;
  // LCS DP(token 级)
  const dp = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--)
    for (let k = m - 1; k >= 0; k--)
      dp[i][k] = A[i] === B[k] ? dp[i + 1][k + 1] + 1 : Math.max(dp[i + 1][k], dp[i][k + 1]);
  const out: DiffSeg[] = [];
  const push = (type: DiffSeg["type"], text: string) => {
    if (!text) return;
    const last = out[out.length - 1];
    if (last && last.type === type) last.text += text;
    else out.push({ type, text });
  };
  let i = 0, k = 0;
  while (i < n && k < m) {
    if (A[i] === B[k]) { push("same", A[i]); i++; k++; }
    else if (dp[i + 1][k] >= dp[i][k + 1]) { push("del", A[i++]); }
    else { push("ins", B[k++]); }
  }
  while (i < n) push("del", A[i++]);
  while (k < m) push("ins", B[k++]);
  return out;
}
