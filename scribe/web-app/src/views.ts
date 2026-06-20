import { PenLine, Network, BarChart3, Library, Brain } from "lucide-react"

export const VIEWS = [
  { key: "write",   label: "写作台",     icon: PenLine   },
  { key: "atlas",   label: "关系图谱",   icon: Network   },
  { key: "insight", label: "质量仪表盘", icon: BarChart3  },
  { key: "codex",   label: "设定库",     icon: Library   },
  { key: "agent",   label: "记忆与技能", icon: Brain     },
] as const

export type ViewKey = typeof VIEWS[number]["key"]
