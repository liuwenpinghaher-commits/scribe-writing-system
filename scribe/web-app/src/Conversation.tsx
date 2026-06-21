/**
 * Conversation.tsx — 主编对话主舞台(Task 1.3b)
 * 四区自上而下:
 *   1. 主编札记(insights + proactive-review)
 *   2. 待你定夺(option-sets + choose)
 *   3. 实时对话(chat + scribe-card 解析)
 *   4. 历史议题(threads + resolve)
 */
import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileText,
  Flame,
  Info,
  Lightbulb,
  Loader2,
  MessagesSquare,
  Search,
  Send,
  Sparkles,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import { api } from "./api";
import type { Insight, OptionSet, Thread } from "./api";
import { useData, useToast, errMsg } from "./common";
import { StateBoundary } from "./components/StateBoundary";
import { Empty } from "./components/Empty";
import { Card, CardContent, CardHeader } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { Input } from "./components/ui/input";
import { Badge } from "./components/ui/badge";
import { ScrollArea } from "./components/ui/scroll-area";
import { cn } from "./lib/utils";

// ─── 类型 ───────────────────────────────────────────────────
interface ToolCall {
  name: string;
  args?: string;
}
interface ChatMsg {
  role: "user" | "editor";
  content: string;
  thread_id?: string;
  tools?: ToolCall[]; // 该条回复期间主编调用的工具序列(B2 折叠时间线)
}

// 工具名 → 人话(主编可能用 scribe 工具或 hermes 自带记忆工具)
function toolLabel(name: string, args?: string): string {
  const bare = name.replace(/^mcp_scribe_/, "");
  const map: Record<string, string> = {
    list_works: "查作品库",
    list_characters: "查人物",
    list_settings: "查设定",
    search_book: "检索原文",
    get_chapter: "读章节",
    list_open_foreshadows: "查伏笔",
    list_relations: "查人物关系",
    session_search: "检索记忆",
  };
  let label = map[bare] ?? bare;
  // 从 args 里抠出 query 作为副标题,帮作者看主编在找什么
  try {
    const q = args ? (JSON.parse(args).query as string | undefined) : undefined;
    if (q) label += `「${q}」`;
  } catch { /* ignore */ }
  return label;
}

// B2:回复气泡上方的「主编查阅了什么」折叠时间线
function ToolTimeline({ tools }: { tools: ToolCall[] }) {
  const [open, setOpen] = useState(false);
  if (!tools.length) return null;
  return (
    <div className="mb-1 max-w-[80%] self-start">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
      >
        <Search size={11} />
        主编查阅了 {tools.length} 项资料
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
      </button>
      {open && (
        <ul className="mt-1 ml-1 flex flex-col gap-0.5 border-l border-border pl-2">
          {tools.map((t, i) => (
            <li key={i} className="text-[11px] text-muted-foreground">· {toolLabel(t.name, t.args)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface ScribeCard {
  type: "hard_conflict" | "suggestion" | "option";
  title?: string;
  body?: string;
}

// ─── 工具:解析 scribe-card ──────────────────────────────────
function parseScribeCard(content: string): ScribeCard | null {
  const m = content.match(/```scribe-card\s*(\{[\s\S]*?\})\s*```/);
  if (!m) return null;
  try { return JSON.parse(m[1]) as ScribeCard; }
  catch { return null; }
}

function stripScribeCard(content: string): string {
  return content.replace(/```scribe-card[\s\S]*?```/g, "").trim();
}

// ─── scribe-card 渲染 ────────────────────────────────────────
function ScribeCardView({ card }: { card: ScribeCard }) {
  const cfg = {
    hard_conflict: {
      icon: <Flame size={15} />,
      color: "border-l-destructive",
      badge: "bg-destructive/10 text-destructive",
      label: "硬冲突",
    },
    suggestion: {
      icon: <Lightbulb size={15} />,
      color: "border-l-primary",
      badge: "bg-primary/10 text-primary",
      label: "建议",
    },
    option: {
      icon: <BookOpen size={15} />,
      color: "border-l-amber-500",
      badge: "bg-amber-500/10 text-amber-600",
      label: "方案",
    },
  }[card.type] ?? {
    icon: <Info size={15} />,
    color: "border-l-muted-foreground",
    badge: "bg-muted text-muted-foreground",
    label: card.type,
  };

  return (
    <Card className={cn("mt-2 border-l-4", cfg.color)}>
      <CardContent className="py-2 px-3 flex items-start gap-2">
        <span className="mt-0.5 text-muted-foreground">{cfg.icon}</span>
        <div className="flex-1 min-w-0">
          <span className={cn("inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium mr-2", cfg.badge)}>
            {cfg.label}
          </span>
          {card.title && <span className="text-sm font-medium">{card.title}</span>}
          {card.body && <p className="text-xs text-muted-foreground mt-0.5">{card.body}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── 1. 主编札记 ─────────────────────────────────────────────
function InsightSection({ work, rev }: { work: string; rev: number }) {
  const { data, loading, error, reload } = useData(() => api.insights(work), [work, rev]);
  const toast = useToast();
  const [reviewing, setReviewing] = useState(false);

  const act = async (id: string, action: "ack" | "dismiss") => {
    await api.actInsight(work, id, action);
    toast(action === "ack" ? "已知晓" : "已忽略");
    reload();
  };
  const runReview = async () => {
    setReviewing(true);
    try {
      const r = await api.review(work);
      toast(`全文体检完成，新增 ${r.new_insights} 条主编札记`);
      reload();
    } catch (e) { toast(errMsg(e), "err"); }
    finally { setReviewing(false); }
  };

  const severityConfig = (s?: string) => {
    if (s === "critical") return { color: "border-l-destructive", icon: <AlertTriangle size={14} className="text-destructive" /> };
    if (s === "warning") return { color: "border-l-amber-500", icon: <AlertTriangle size={14} className="text-amber-500" /> };
    return { color: "border-l-primary", icon: <Info size={14} className="text-primary" /> };
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
          <Sparkles size={14} className="text-primary" /> 主编札记
        </h4>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          onClick={runReview}
          disabled={reviewing}
        >
          {reviewing ? <Loader2 size={12} className="animate-spin mr-1" /> : null}
          {reviewing ? "体检中…" : "全文体检"}
        </Button>
      </div>

      <StateBoundary
        loading={loading}
        error={error}
        empty={!data?.length}
        emptyNode={
          <Empty
            icon={<CheckCircle2 />}
            title="主编暂无意见"
            hint="点「全文体检」可主动触发审阅"
          />
        }
        onRetry={reload}
      >
        <div className="flex flex-col gap-2">
          {data?.map((ins: Insight) => {
            const { color, icon } = severityConfig(ins.severity);
            return (
              <Card key={ins.id} className={cn("border-l-4", color)}>
                <CardContent className="py-2 px-3">
                  <div className="flex items-start gap-2">
                    <span className="mt-0.5">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-prose leading-relaxed">{ins.summary}</p>
                      {ins.suggested_action && (
                        <p className="text-xs text-muted-foreground mt-0.5">{ins.suggested_action}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1.5 mt-2">
                    <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={() => act(ins.id, "ack")}>
                      <ThumbsUp size={11} className="mr-1" /> 知道了
                    </Button>
                    <Button size="sm" variant="ghost" className="h-6 text-xs" onClick={() => act(ins.id, "dismiss")}>
                      <XCircle size={11} className="mr-1" /> 忽略
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 text-xs"
                      onClick={() => api.pref(work, ins.summary, "+").catch(() => {})}
                    >
                      这是故意的
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </StateBoundary>
    </section>
  );
}

// ─── 2. 待你定夺 ─────────────────────────────────────────────
const MATRIX: [keyof Record<string, unknown>, string][] = [
  ["emotional_direction", "情感走向"],
  ["character_cost", "人物代价"],
  ["plot_consequence", "情节后果"],
];

function OptionSetSection({ work, rev, bump }: { work: string; rev: number; bump: () => void }) {
  const { data, loading, error, reload } = useData(() => api.optionSets(work), [work, rev]);
  const toast = useToast();
  const [dp, setDp] = useState("");
  const [generating, setGenerating] = useState(false);

  const gen = async () => {
    if (!dp.trim()) return;
    setGenerating(true);
    try {
      await api.generateOptions(work, dp.trim());
      setDp(""); toast("主编已出方案");
      reload(); bump();
    } catch (e) { toast(errMsg(e), "err"); }
    finally { setGenerating(false); }
  };

  const choose = async (oid: string, optId: string) => {
    await api.choose(work, oid, optId);
    toast("已选方案（已记入你的品味）");
    reload(); bump();
  };

  return (
    <section>
      <h4 className="text-sm font-semibold text-foreground flex items-center gap-1.5 mb-2">
        <FileText size={14} className="text-primary" /> 待你定夺
      </h4>

      <StateBoundary loading={loading} error={error} empty={false} onRetry={reload}>
        <>
          {(!data || data.length === 0) ? (
            <div className="flex gap-2">
              <Input
                value={dp}
                placeholder="遇到岔路？写下决策点，让主编出几个差异方案…"
                onChange={(e) => setDp(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") gen(); }}
                className="h-8 text-sm"
              />
              <Button size="sm" variant="ghost" className="h-8 shrink-0" onClick={gen} disabled={generating}>
                {generating ? <Loader2 size={12} className="animate-spin" /> : "出方案"}
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {data.map((s: OptionSet) => {
                let dpText = "";
                let opts: Record<string, unknown>[] = [];
                try { dpText = JSON.parse(s.decision_point).text || ""; } catch { /* */ }
                try { opts = JSON.parse(s.options); } catch { /* */ }
                return (
                  <Card key={s.id} className="border-border">
                    <CardHeader className="py-2 px-3">
                      <p className="text-xs text-muted-foreground">{dpText}</p>
                    </CardHeader>
                    <CardContent className="py-0 px-3 pb-3">
                      <div className={cn(
                        "grid gap-2",
                        opts.length >= 3 ? "grid-cols-3" : opts.length === 2 ? "grid-cols-2" : "grid-cols-1"
                      )}>
                        {opts.map((o, i) => {
                          const oid = o.id != null ? String(o.id) : String(i);
                          return (
                            <Card key={oid} className="border-border bg-muted/30">
                              <CardContent className="py-2 px-2.5">
                                <p className="text-xs font-medium mb-1">
                                  {String(o.approach || o.label || `方案 ${oid}`)}
                                </p>
                                {typeof o.tradeoff === "string" && (
                                  <p className="text-xs text-muted-foreground mb-1">代价：{o.tradeoff}</p>
                                )}
                                {MATRIX.filter(([k]) => o[k]).map(([k, label]) => (
                                  <div key={k} className="text-xs text-muted-foreground">
                                    <span className="font-medium">{label}：</span>{String(o[k])}
                                  </div>
                                ))}
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-6 text-xs mt-2 w-full"
                                  onClick={() => choose(s.id, oid)}
                                >
                                  选这个
                                </Button>
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      </StateBoundary>
    </section>
  );
}

// ─── 3. 实时对话 ─────────────────────────────────────────────
function ChatSection({ work, quote = "", onQuoteUsed }: { work: string; quote?: string; onQuoteUsed?: () => void }) {
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [toolHint, setToolHint] = useState("");
  const toast = useToast();
  const bottomRef = useRef<HTMLDivElement>(null);
  const threadRef = useRef<string | undefined>(undefined);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, thinking]);

  // 划词「讨论这段」:把引文带入输入框,光标待命续写问题
  useEffect(() => {
    if (!quote) return;
    setInput((cur) => `就这一段：\n「${quote}」\n\n` + cur);
    inputRef.current?.focus();
    onQuoteUsed?.();
  }, [quote]);  // eslint-disable-line react-hooks/exhaustive-deps

  const send = async () => {
    const text = input.trim();
    if (!text || thinking) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", content: text }, { role: "editor", content: "" }]);
    setThinking(true);
    setToolHint("");
    try {
      // B1/B2：主编对话走 hermes Responses（带 scribe 工具 + 流式）
      const r = await api.streamChat(work, text, (ev) => {
        if (ev.tool) {
          setToolHint(toolLabel(ev.tool, ev.tool_args));
          setMsgs((m) => {
            const last = m[m.length - 1];
            if (!last || last.role !== "editor") return m;
            const tools = [...(last.tools ?? []), { name: ev.tool!, args: ev.tool_args }];
            return [...m.slice(0, -1), { ...last, tools }];
          });
        }
        if (ev.delta) {
          setToolHint("");
          setMsgs((m) => {
            const last = m[m.length - 1];
            if (!last || last.role !== "editor") return m;
            return [...m.slice(0, -1), { ...last, content: last.content + ev.delta }];
          });
        }
      }, threadRef.current);
      threadRef.current = r.thread_id ?? threadRef.current;
      // 用最终完整文本兜底（覆盖流式拼接，防丢片）
      setMsgs((m) => {
        const last = m[m.length - 1];
        if (!last || last.role !== "editor") return m;
        return [...m.slice(0, -1), { ...last, content: r.content || last.content }];
      });
    } catch (e) {
      toast(errMsg(e), "err");
      setMsgs((m) => m.slice(0, -2)); // 撤回用户消息 + 空回复占位
    } finally {
      setThinking(false);
      setToolHint("");
    }
  };

  return (
    <section className="flex flex-col gap-0">
      <h4 className="text-sm font-semibold text-foreground flex items-center gap-1.5 mb-2">
        <MessagesSquare size={14} className="text-primary" /> 与主编对话
      </h4>

      <ScrollArea className="h-64 rounded-lg border border-border bg-muted/20 p-3">
        {msgs.length === 0 && (
          <Empty
            icon={<MessagesSquare />}
            title="还没有对话"
            hint="在下方输入框与主编探讨剧情、人物、风格…"
          />
        )}
        <div className="flex flex-col gap-3">
          {msgs.map((msg, i) => {
            const isUser = msg.role === "user";
            // 流式中的空回复占位气泡先不渲染（由下方“思考中/工具提示”指示）
            if (!isUser && !msg.content) return null;
            const card = isUser ? null : parseScribeCard(msg.content);
            const text = isUser ? msg.content : stripScribeCard(msg.content);
            return (
              <div key={i} className={cn("flex flex-col", isUser ? "items-end" : "items-start")}>
                {!isUser && msg.tools && <ToolTimeline tools={msg.tools} />}
                <div
                  className={cn(
                    "max-w-[80%] rounded-2xl px-3 py-2 text-sm font-prose leading-relaxed",
                    isUser
                      ? "bg-primary text-primary-foreground rounded-br-sm"
                      : "bg-muted text-foreground rounded-bl-sm"
                  )}
                >
                  {text}
                </div>
                {card && <ScribeCardView card={card} />}
              </div>
            );
          })}
          {thinking && (msgs[msgs.length - 1]?.role !== "editor" || !msgs[msgs.length - 1]?.content) && (
            <div className="flex items-start">
              <div className="bg-muted rounded-2xl rounded-bl-sm px-3 py-2 flex items-center gap-1.5">
                <Loader2 size={13} className="animate-spin text-muted-foreground" />
                <span className="text-xs text-muted-foreground">
                  {toolHint ? `🔍 正在${toolHint}…` : "主编思考中…"}
                </span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <div className="flex gap-2 mt-2">
        <Input
          ref={inputRef}
          value={input}
          placeholder="和主编说…（Enter 发送）"
          className="h-8 text-sm"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
          disabled={thinking}
        />
        <Button
          size="sm"
          className="h-8 shrink-0"
          onClick={send}
          disabled={thinking || !input.trim()}
        >
          <Send size={13} />
        </Button>
      </div>
    </section>
  );
}

// ─── 4. 历史议题 ─────────────────────────────────────────────
function ThreadsSection({ work, rev }: { work: string; rev: number }) {
  const { data, loading, error, reload } = useData(() => api.threads(work), [work, rev]);
  const [open, setOpen] = useState(false);
  const toast = useToast();

  const resolve = async (tid: string) => {
    await api.resolveThread(work, tid);
    toast("议题已归档");
    reload();
  };

  const count = data?.length ?? 0;

  return (
    <section>
      <button
        className="flex w-full items-center justify-between text-sm font-semibold text-foreground py-1 hover:text-primary transition-colors"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="flex items-center gap-1.5">
          <MessagesSquare size={14} className="text-muted-foreground" />
          历史议题
          {count > 0 && (
            <Badge variant="secondary" className="text-xs h-4 px-1">{count}</Badge>
          )}
        </span>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      {open && (
        <div className="mt-2">
          <StateBoundary
            loading={loading}
            error={error}
            empty={!count}
            emptyNode={<Empty title="暂无讨论线程" hint="与主编对话后会自动建立议题" />}
            onRetry={reload}
          >
            <div className="flex flex-col gap-2">
              {data?.map((t: Thread) => {
                let n = 0;
                try { n = JSON.parse(t.messages || "[]").length; } catch { /* */ }
                return (
                  <Card key={t.id} className="border-border">
                    <CardContent className="py-2 px-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 mb-0.5">
                            <Badge
                              variant={t.status === "open" ? "default" : "secondary"}
                              className="text-xs h-4 px-1"
                            >
                              {t.status === "open" ? "进行中" : "已归档"}
                            </Badge>
                            <span className="text-sm font-medium truncate">{t.topic}</span>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {t.trigger} · {n} 条对话
                          </span>
                        </div>
                        {t.status === "open" && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 text-xs shrink-0"
                            onClick={() => resolve(t.id)}
                          >
                            归档
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </StateBoundary>
        </div>
      )}
    </section>
  );
}

// ─── 主导出 ──────────────────────────────────────────────────
export function Conversation({
  work,
  rev,
  bump,
  quote = "",
  onQuoteUsed,
}: {
  work: string;
  rev: number;
  bump: () => void;
  quote?: string;
  onQuoteUsed?: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 py-1">
      <InsightSection work={work} rev={rev} />
      <div className="h-px bg-border" />
      <OptionSetSection work={work} rev={rev} bump={bump} />
      <div className="h-px bg-border" />
      <ChatSection work={work} quote={quote} onQuoteUsed={onQuoteUsed} />
      <div className="h-px bg-border" />
      <ThreadsSection work={work} rev={rev} />
    </div>
  );
}
