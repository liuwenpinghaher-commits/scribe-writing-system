import { useState } from "react";
import { Brain, Cpu } from "lucide-react";
import { api, type AgentSkill } from "@/api";
import { useData } from "@/common";
import { useToast } from "@/common";
import { StateBoundary } from "@/components/StateBoundary";
import { Empty } from "@/components/Empty";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

// ── 命名空间定义 ──────────────────────────────────────────────
const NS_TABS = [
  { key: "",          label: "全部" },
  { key: "semantic",  label: "语义" },
  { key: "episodic",  label: "情节" },
  { key: "session",   label: "会话" },
  { key: "working",   label: "工作" },
  { key: "meta",      label: "元" },
] as const;

// ── 技能状态中文化 + 样式 ─────────────────────────────────────
const SKILL_STATUS_LABEL: Record<string, string> = {
  proposed: "待审批",
  approved: "已批准",
  active:   "启用中",
  retired:  "已退役",
};

function skillStatusVariant(status: string): "default" | "secondary" | "destructive" | "outline" {
  if (status === "active")   return "default";    // 主绿
  if (status === "proposed") return "outline";    // 待审
  if (status === "retired")  return "secondary";  // 灰
  return "secondary";
}

// ── 解析 JSON value ───────────────────────────────────────────
function prettyValue(raw: string): string {
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed === "object" && parsed !== null) {
      // 对象/数组:展示 key:value 摘要
      const entries = Object.entries(parsed).slice(0, 3);
      const preview = entries.map(([k, v]) => `${k}: ${String(v)}`).join(" · ");
      return Object.keys(parsed).length > 3 ? preview + " …" : preview;
    }
    return String(parsed);
  } catch {
    return raw;
  }
}

// ── 跨会话记忆面板 ───────────────────────────────────────────
function MemoryPanel({ work }: { work: string }) {
  const [ns, setNs] = useState<string>("");
  const { data, loading, error, reload } = useData(
    () => api.agentMemory(work, ns || undefined),
    [work, ns]
  );

  return (
    <div className="flex flex-col h-full">
      <CardHeader className="pb-3 shrink-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <Brain size={16} className="text-primary" />
          跨会话记忆
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          置信 ≥0.8 的记忆会跨会话沉淀。跨书记忆为全局共享，本书记忆仅属当前作品。
        </p>
      </CardHeader>

      {/* 命名空间筛选 */}
      <div className="px-4 pb-3 shrink-0">
        <Tabs value={ns} onValueChange={setNs}>
          <TabsList className="h-8 flex-wrap gap-1">
            {NS_TABS.map((t) => (
              <TabsTrigger key={t.key} value={t.key} className="text-xs px-2 py-1 h-7">
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* 记忆列表 */}
      <ScrollArea className="flex-1 px-4 pb-4">
        <StateBoundary
          loading={loading}
          error={error}
          empty={!data?.length}
          onRetry={reload}
          emptyNode={
            <Empty
              icon={<Brain />}
              title="暂无记忆"
              hint="置信 ≥0.8 的跨会话记忆会沉淀在这里"
            />
          }
        >
          <div className="flex flex-col gap-2 pt-1">
            {data?.map((m) => {
              const preview = prettyValue(m.value);
              const isGlobal = !m.work_id;
              return (
                <Card key={m.id} className="border-border/60">
                  <CardContent className="px-4 py-3">
                    <div className="flex items-center gap-2 mb-1.5">
                      <Badge variant="secondary" className="text-xs px-1.5 py-0">
                        {m.namespace}
                      </Badge>
                      <Badge
                        variant="outline"
                        className={
                          isGlobal
                            ? "text-xs px-1.5 py-0 text-primary border-primary/30"
                            : "text-xs px-1.5 py-0"
                        }
                      >
                        {isGlobal ? "跨书" : "本书"}
                      </Badge>
                    </div>
                    <p className="text-sm font-semibold leading-snug">{m.key}</p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2 leading-relaxed">
                      {preview.slice(0, 120)}{preview.length > 120 ? "…" : ""}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1.5 tabular-nums">
                      置信&nbsp;
                      <span className={m.confidence >= 0.8 ? "text-primary font-medium" : ""}>
                        {m.confidence.toFixed(2)}
                      </span>
                      &nbsp;·&nbsp;
                      {new Date(m.updated_at).toLocaleDateString("zh-CN")}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </StateBoundary>
      </ScrollArea>
    </div>
  );
}

// ── 技能审批面板 ─────────────────────────────────────────────
function SkillsPanel({ work }: { work: string }) {
  const { data, loading, error, reload } = useData(
    () => api.agentSkills(work),
    [work]
  );
  const toast = useToast();
  const [skillName, setSkillName] = useState("");
  const [proposing, setProposing] = useState(false);

  const propose = async () => {
    const name = skillName.trim();
    if (!name) return;
    setProposing(true);
    try {
      await api.proposeSkill(work, name);
      setSkillName("");
      toast("已提议技能，等待你审批后生效");
      reload();
    } catch (e) {
      toast((e instanceof Error ? e.message : String(e)), "err");
    } finally {
      setProposing(false);
    }
  };

  const act = async (s: AgentSkill, action: "approve" | "activate" | "retire") => {
    try {
      await api.actSkill(work, s.id, action);
      const label = action === "approve" ? "已批准" : action === "activate" ? "已启用" : "已退役";
      toast(`技能「${s.name}」${label}`);
      reload();
    } catch (e) {
      toast((e instanceof Error ? e.message : String(e)), "err");
    }
  };

  return (
    <div className="flex flex-col h-full">
      <CardHeader className="pb-3 shrink-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <Cpu size={16} className="text-primary" />
          自我优化技能
          <Badge variant="destructive" className="text-xs ml-1">须你放行才生效</Badge>
        </CardTitle>
        <p className="text-xs text-muted-foreground mt-1">
          AI 提议的技能会停在「待审批」状态，只有你明确批准后才会进入运行流。
        </p>
      </CardHeader>

      {/* 提议输入区 */}
      <div className="px-4 pb-4 shrink-0">
        <div className="flex gap-2">
          <Input
            value={skillName}
            onChange={(e) => setSkillName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") propose(); }}
            placeholder="提议一个技能（如：卷尾自动摘要）…"
            className="text-sm h-8"
            aria-label="提议技能名称"
          />
          <Button
            size="sm"
            variant="ghost"
            onClick={propose}
            disabled={proposing || !skillName.trim()}
            className="shrink-0"
          >
            提议
          </Button>
        </div>
      </div>

      {/* 技能列表 */}
      <ScrollArea className="flex-1 px-4 pb-4">
        <StateBoundary
          loading={loading}
          error={error}
          empty={!data?.length}
          onRetry={reload}
          emptyNode={
            <Empty
              icon={<Cpu />}
              title="暂无技能"
              hint="AI 提议的技能会停在待审批，由你放行"
            />
          }
        >
          <div className="flex flex-col gap-2 pt-1">
            {data?.map((s) => {
              const needsApproval = s.approved_by_human === 0;
              const borderColor =
                s.status === "active"
                  ? "border-l-primary"
                  : s.status === "proposed"
                  ? "border-l-yellow-500"
                  : s.status === "retired"
                  ? "border-l-muted-foreground/30"
                  : "border-l-border";

              return (
                <Card
                  key={s.id}
                  className={`border-border/60 border-l-4 ${borderColor}`}
                >
                  <CardContent className="px-4 py-3">
                    {/* 标题行 */}
                    <div className="flex items-center gap-2 flex-wrap mb-2">
                      <span className="text-sm font-semibold">{s.name}</span>
                      <Badge variant={skillStatusVariant(s.status)} className="text-xs px-1.5 py-0">
                        {SKILL_STATUS_LABEL[s.status] ?? s.status}
                      </Badge>
                      {needsApproval && (
                        <Badge
                          variant="destructive"
                          className="text-xs px-1.5 py-0 bg-destructive/15 text-destructive border border-destructive/30"
                        >
                          未审批
                        </Badge>
                      )}
                    </div>

                    {/* spec 预览 */}
                    {s.spec && s.spec !== "{}" && (
                      <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                        {prettyValue(s.spec)}
                      </p>
                    )}

                    {/* 时间 */}
                    <p className="text-xs text-muted-foreground tabular-nums mb-2">
                      提议于 {new Date(s.created_at).toLocaleDateString("zh-CN")}
                      {s.created_by ? ` · by ${s.created_by}` : ""}
                    </p>

                    {/* 操作按钮(按状态显示) */}
                    <div className="flex gap-2 flex-wrap">
                      {s.status === "proposed" && (
                        <Button
                          size="sm"
                          variant="default"
                          className="h-7 text-xs"
                          onClick={() => act(s, "approve")}
                        >
                          批准
                        </Button>
                      )}
                      {(s.status === "proposed" || s.status === "approved") && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs"
                          onClick={() => act(s, "activate")}
                        >
                          启用
                        </Button>
                      )}
                      {s.status !== "retired" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs text-muted-foreground hover:text-destructive"
                          onClick={() => act(s, "retire")}
                        >
                          退役
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </StateBoundary>
      </ScrollArea>
    </div>
  );
}

// ── 主视图:左右分栏 ──────────────────────────────────────────
export function AgentView({ work }: { work: string }) {
  return (
    <div className="flex h-full overflow-hidden">
      {/* 左栏:跨会话记忆 */}
      <div className="w-1/2 border-r border-border flex flex-col overflow-hidden">
        <MemoryPanel work={work} />
      </div>

      {/* 右栏:自我优化技能 */}
      <div className="w-1/2 flex flex-col overflow-hidden">
        <SkillsPanel work={work} />
      </div>
    </div>
  );
}
