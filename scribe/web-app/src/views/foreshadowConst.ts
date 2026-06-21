/** 承诺线共享常量(时间线 / 详情页 共用) */
export const TYPES = ["伏笔", "悬念", "契诃夫之枪", "红鲱鱼", "人物承诺"] as const;
export const EFFECTS = ["惊讶", "悬念", "戏剧反讽", "不祥", "好奇"] as const;
export const KINDS = [
  { key: "plant", label: "埋", sym: "●" },
  { key: "reinforce", label: "强化", sym: "·" },
  { key: "misdirect", label: "误导", sym: "?" },
  { key: "twist", label: "转折", sym: "↯" },
  { key: "payoff", label: "回收", sym: "★" },
] as const;
export const KIND_LABEL: Record<string, string> = Object.fromEntries(KINDS.map((k) => [k.key, k.label]));
export const TYPE_COLOR: Record<string, string> = {
  伏笔: "#3f6b58", 悬念: "#b45309", 契诃夫之枪: "#7c3aed", 红鲱鱼: "#dc2626", 人物承诺: "#0e7490",
};
export const colorOf = (t?: string) => TYPE_COLOR[t || "伏笔"] || "#3f6b58";
