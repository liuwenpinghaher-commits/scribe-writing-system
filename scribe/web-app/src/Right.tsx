import { useRef, useState } from "react";
import { Stethoscope, Send } from "lucide-react";
import { api } from "./api";
import { errMsg, useData, useToast } from "./common";
import { QualityCard, Relations, CharStates, Threads, AgentPanel } from "./Panels";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StateBoundary } from "@/components/StateBoundary";
import { Empty } from "@/components/Empty";
import { cn } from "@/lib/utils";

// Right — 右栏 Inspector
// Task 1.3a: shadcn 换皮,保留全部数据逻辑。
export function Right({ work, rev, bump }: { work: string; rev: number; bump: () => void }) {
  return (
    <div className="flex flex-col gap-3">
      <PendingWrites work={work} rev={rev} bump={bump} />
      <Insights work={work} rev={rev} />
      <Sidebar work={work} rev={rev} />
      <Chat work={work} bump={bump} />
      <Threads work={work} rev={rev} />
    </div>
  );
}

const PENDING_LABEL: Record<string, string> = {
  upsert_setting: "新增/更新设定",
  save_chapter: "保存章节",
  save_snapshot: "保存正文快照",
  upsert_character: "新增/更新角色",
  plant_foreshadow: "埋伏笔",
  advance_foreshadow: "推进伏笔",
  set_author_intent: "改北极星",
};

function PendingWrites({ work, rev, bump }: { work: string; rev: number; bump: () => void }) {
  const { data, loading, error, reload } = useData(() => api.pendingWrites(work), [work, rev]);
  const toast = useToast();
  if (loading || error || !data || data.length === 0) return null;
  const decide = async (id: string, approve: boolean) => {
    try {
      if (approve) await api.approvePending(work, id);
      else await api.rejectPending(work, id);
      toast(approve ? "已写入" : "已拒绝");
      reload(); bump();
    } catch (e) {
      toast(errMsg(e));
    }
  };
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-sm font-semibold text-foreground">待你确认的写操作（{data.length}）</h4>
      {data.map((p) => {
        const name = (p.args.name as string) || (p.args.summary as string) || "";
        return (
          <Card key={p.id} className="border-amber-300/60">
            <CardContent className="p-3 flex items-center justify-between gap-2">
              <div className="text-sm">
                <span className="font-medium">{PENDING_LABEL[p.tool_name] ?? p.tool_name}</span>
                {name && <span className="text-muted-foreground">：{name}</span>}
              </div>
              <div className="flex gap-1.5 shrink-0">
                <Button size="sm" className="h-7" onClick={() => decide(p.id, true)}>批准</Button>
                <Button size="sm" variant="outline" className="h-7" onClick={() => decide(p.id, false)}>拒绝</Button>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function Insights({ work, rev }: { work: string; rev: number }) {
  const { data, loading, error, reload } = useData(() => api.insights(work), [work, rev]);
  const toast = useToast();
  const act = async (id: string, a: "ack" | "dismiss") => {
    await api.actInsight(work, id, a); reload();
  };
  const intentional = async (id: string) => {
    await api.actInsight(work, id, "dismiss");
    await api.pref(work, "intentional", "+").catch(() => {});
    toast("已记:这是故意的"); reload();
  };
  const review = async () => {
    const r = await api.review(work);
    toast(`体检完成,新增 ${r.new_insights} 条札记`); reload();
  };
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground m-0">
          主编札记
        </h2>
        <Button variant="ghost" size="sm" onClick={review}>
          <Stethoscope size={13} /> 全文体检
        </Button>
      </div>
      <StateBoundary
        loading={loading}
        error={error}
        empty={!data?.length}
        emptyNode={<Empty title="暂无札记" hint="点「全文体检」让主编主动揪问题。" />}
        onRetry={reload}
      >
        <div className="flex flex-col gap-2">
          {data?.map((x) => {
            const borderColor =
              x.severity === "critical"
                ? "border-l-destructive"
                : x.severity === "major"
                ? "border-l-[#f59e0b]"
                : "border-l-primary";
            return (
              <Card key={x.id} size="sm" className={cn("border-l-[3px]", borderColor)}>
                <CardContent className="pt-3">
                  <p className="text-sm">{x.summary}</p>
                  {x.suggested_action && (
                    <p className="text-xs text-muted-foreground mt-1">建议:{x.suggested_action}</p>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    <Button variant="ghost" size="xs" onClick={() => act(x.id, "ack")}>知道了</Button>
                    <Button variant="ghost" size="xs" onClick={() => intentional(x.id)}>这是故意的</Button>
                    <Button variant="ghost" size="xs" onClick={() => act(x.id, "dismiss")}>忽略</Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </StateBoundary>
    </div>
  );
}

function Sidebar({ work, rev }: { work: string; rev: number }) {
  const [tab, setTab] = useState("bible");
  const [local, setLocal] = useState(0);
  const fo = useData(() => api.foreshadows(work), [work, rev, local]);
  const fl = useData(() => api.flags(work), [work, rev, local]);
  const toast = useToast();
  const bump = () => setLocal((n) => n + 1);
  const onFore = async (fid: string, a: "trigger" | "pay" | "abandon") => {
    try { await api.advanceForeshadow(work, fid, a); toast("伏笔已推进"); bump(); }
    catch (e) { toast(errMsg(e), "err"); }
  };
  const onFlag = async (fid: string, a: "confirm" | "dismiss" | "fix") => {
    await api.resolveFlag(work, fid, a);
    toast(a === "dismiss" ? "已标记误报" : "已确认"); bump();
  };
  const bible = useData(async () => {
    const [chs, st] = await Promise.all([api.characters(work), api.settings(work)]);
    const desc = (c?: string) => c || "";  // 重构:setting.content 即纯文本描述(新底座契约)
    return [
      ...chs.map((c) => ({ kind: "char" as const, k: "角色", name: c.name, body: c.motivation || "", type: "" })),
      ...st.map((s) => ({ kind: "set" as const, k: s.type ?? "设定", name: s.name, body: desc(s.content), type: s.type ?? "设定" })),
    ];
  }, [work, rev]);

  const tabs: { value: string; label: string; count?: number }[] = [
    { value: "bible", label: "设定圣经" },
    { value: "foreshadow", label: "伏笔", count: fo.data?.length },
    { value: "flags", label: "一致性", count: fl.data?.length },
    { value: "material", label: "素材" },
    { value: "pulse", label: "脉络/质量" },
    { value: "agent", label: "记忆技能" },
  ];

  return (
    <Tabs value={tab} onValueChange={setTab}>
      <TabsList className="w-full justify-start gap-px p-1 overflow-x-auto">
        {tabs.map((t) => (
          <TabsTrigger key={t.value} value={t.value} className="text-xs px-2 py-0.5 flex-none">
            {t.label}
            {t.count != null && t.count > 0 && (
              <Badge
                variant={t.value === "flags" ? "destructive" : "secondary"}
                className="ml-1 text-[9px] h-3.5 px-1"
              >
                {t.count}
              </Badge>
            )}
          </TabsTrigger>
        ))}
      </TabsList>

      <ScrollArea className="max-h-[32vh]">
        <TabsContent value="foreshadow" className="mt-2 px-0.5">
          <StateBoundary
            loading={fo.loading}
            error={fo.error}
            empty={!fo.data?.length}
            emptyNode={<Empty title="暂无未了结伏笔" />}
            onRetry={fo.reload}
          >
            <div className="flex flex-col gap-2">
              {fo.data?.map((x) => (
                <Card key={x.id} size="sm">
                  <CardContent className="pt-3">
                    <div className="flex items-start gap-1.5">
                      <Badge variant="outline" className="shrink-0 text-[10px] mt-0.5">{x.state}</Badge>
                      <span className="text-xs">{x.summary}</span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {x.state === "planted" && (
                        <Button variant="ghost" size="xs" onClick={() => onFore(x.id, "trigger")}>触发</Button>
                      )}
                      {x.state === "triggered" && (
                        <Button variant="ghost" size="xs" onClick={() => onFore(x.id, "pay")}>回收</Button>
                      )}
                      <Button variant="ghost" size="xs" onClick={() => onFore(x.id, "abandon")}>放弃</Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </StateBoundary>
        </TabsContent>

        <TabsContent value="flags" className="mt-2 px-0.5">
          <StateBoundary
            loading={fl.loading}
            error={fl.error}
            empty={!fl.data?.length}
            emptyNode={<Empty title="无一致性问题 ✓" hint="太棒了,目前没有发现冲突。" />}
            onRetry={fl.reload}
          >
            <div className="flex flex-col gap-2">
              {fl.data?.map((x) => (
                <Card key={x.id} size="sm" className="border-l-[3px] border-l-[#f59e0b]">
                  <CardContent className="pt-3">
                    <div className="flex items-start gap-1.5">
                      <Badge variant="destructive" className="shrink-0 text-[10px] mt-0.5">{x.error_class}</Badge>
                      <span className="text-xs">{x.detail}</span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      <Button variant="ghost" size="xs" onClick={() => onFlag(x.id, "confirm")}>确认真错</Button>
                      <Button variant="ghost" size="xs" onClick={() => onFlag(x.id, "fix")}>已修</Button>
                      <Button variant="ghost" size="xs" onClick={() => onFlag(x.id, "dismiss")}>误报</Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </StateBoundary>
        </TabsContent>

        <TabsContent value="material" className="mt-2 px-0.5">
          <Materials work={work} />
        </TabsContent>

        <TabsContent value="pulse" className="mt-2 px-0.5">
          <Pulse work={work} rev={rev} />
        </TabsContent>

        <TabsContent value="agent" className="mt-2 px-0.5">
          <AgentPanel work={work} rev={rev} />
        </TabsContent>

        <TabsContent value="bible" className="mt-2 px-0.5">
          <BibleAdd work={work} onAdded={bible.reload} />
          <StateBoundary
            loading={bible.loading}
            error={bible.error}
            empty={!bible.data?.length}
            emptyNode={<Empty title="还没有设定/角色" hint="在上方添加" />}
            onRetry={bible.reload}
          >
            <div className="flex flex-col gap-1.5">
              {bible.data?.map((x, i) => (
                <BibleItem key={i} work={work} item={x} onSaved={bible.reload} />
              ))}
            </div>
          </StateBoundary>
          <RelationsSection work={work} rev={rev} />
        </TabsContent>
      </ScrollArea>
    </Tabs>
  );
}

function RelationsSection({ work, rev }: { work: string; rev: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3 border-t border-border pt-2">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full justify-start text-xs"
      >
        实体关系图 {open ? "▾" : "▸"}
      </Button>
      {open && <div className="mt-2"><Relations work={work} rev={rev} /></div>}
    </div>
  );
}

function BibleItem({ work, item, onSaved }: {
  work: string;
  item: { kind: "char" | "set"; k: string; name: string; body: string; type: string };
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(item.body);
  const [impact, setImpact] = useState<{ seq: number; title?: string; snippet: string }[] | null>(null);
  const [loadingImpact, setLoadingImpact] = useState(false);
  const [showStates, setShowStates] = useState(false);
  const toast = useToast();
  const save = async () => {
    if (item.kind === "char") await api.addCharacter(work, item.name, body.trim());
    else await api.addSetting(work, item.name, item.type || "设定", body.trim());
    setOpen(false); toast("已保存"); onSaved();
  };
  const loadImpact = async () => {
    if (impact) { setImpact(null); return; }
    setLoadingImpact(true);
    try { setImpact(await api.impact(work, item.name)); } finally { setLoadingImpact(false); }
  };
  const jump = (seq: number) => { location.hash = `#/work/${work}/ch/${seq}`; };
  return (
    <Card size="sm">
      <CardContent className="pt-3">
        <button
          className="w-full text-left"
          onClick={() => { setBody(item.body); setOpen((o) => !o); }}
          aria-expanded={open}
        >
          <span className="flex items-center gap-1.5">
            <Badge variant="secondary" className="text-[10px] shrink-0">{item.k}</Badge>
            <span className="font-prose text-sm font-medium">{item.name}</span>
            {item.body && !open && (
              <span className="text-xs text-muted-foreground truncate">
                · {item.body.slice(0, 18)}{item.body.length > 18 ? "…" : ""}
              </span>
            )}
          </span>
        </button>
        {open && (
          <div className="mt-2 flex flex-col gap-2">
            <Textarea
              rows={2}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder={item.kind === "char" ? "动机/性格…" : "设定描述…"}
              className="text-xs resize-none"
            />
            <div className="flex flex-wrap gap-1">
              <Button variant="ghost" size="xs" onClick={save}>保存</Button>
              <Button variant="ghost" size="xs" onClick={loadImpact}>
                {item.kind === "char" ? "出场时间线" : "影响章节"}{impact ? " ▾" : " ▸"}
              </Button>
              {item.kind === "char" && (
                <Button variant="ghost" size="xs" onClick={() => setShowStates((v) => !v)}>
                  状态轨迹{showStates ? " ▾" : " ▸"}
                </Button>
              )}
            </div>
            {showStates && item.kind === "char" && <CharStates work={work} name={item.name} />}
            {loadingImpact && <p className="text-xs text-muted-foreground">查找中…</p>}
            {impact && (
              <div className="flex flex-col gap-1">
                {impact.length === 0 && (
                  <p className="text-xs text-muted-foreground">暂无章节引用「{item.name}」</p>
                )}
                {impact.map((c) => (
                  <button
                    key={c.seq}
                    className="flex flex-col items-start rounded-md border border-border px-2 py-1.5 text-left hover:bg-muted transition-colors"
                    onClick={() => jump(c.seq)}
                    title="跳到该章"
                  >
                    <span className="flex items-center gap-1">
                      <Badge variant="secondary" className="text-[10px]">第 {c.seq} 章</Badge>
                      <span className="text-xs">{c.title || "无题"}</span>
                    </span>
                    <span className="text-xs text-muted-foreground mt-0.5">{c.snippet}…</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Pulse({ work, rev }: { work: string; rev: number }) {
  const mem = useData(() => api.memory(work), [work, rev]);
  const tl = useData(() => api.timeline(work), [work, rev]);
  return (
    <div className="flex flex-col gap-3">
      <QualityCard work={work} rev={rev} />
      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">全书主线记忆</h3>
        <StateBoundary
          loading={mem.loading}
          error={mem.error}
          empty={!mem.data?.global && !mem.data?.chapters?.length}
          emptyNode={<Empty title="写几章后自动沉淀" />}
          onRetry={mem.reload}
        >
          <div className="flex flex-col gap-1.5">
            {mem.data?.global && (
              <Card size="sm">
                <CardContent className="pt-3">
                  <p className="font-prose text-sm">{mem.data.global}</p>
                </CardContent>
              </Card>
            )}
            {mem.data?.chapters?.slice(-6).map((c) => (
              <Card key={c.seq} size="sm">
                <CardContent className="pt-3 flex items-start gap-1.5">
                  <Badge variant="secondary" className="shrink-0 text-[10px]">第{c.seq}章</Badge>
                  <span className="text-xs">{c.summary_text}</span>
                </CardContent>
              </Card>
            ))}
          </div>
        </StateBoundary>
      </div>
      <div>
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">时间线</h3>
        <StateBoundary
          loading={tl.loading}
          error={tl.error}
          empty={!tl.data?.length}
          emptyNode={<Empty title="暂无事件" />}
          onRetry={tl.reload}
        >
          <div className="flex flex-col gap-0.5">
            {tl.data?.slice(-12).map((t, i) => (
              <p key={i} className="text-xs text-muted-foreground py-0.5">
                第{t.chapter_seq}章 · {t.description}
              </p>
            ))}
          </div>
        </StateBoundary>
      </div>
    </div>
  );
}

function Materials({ work }: { work: string }) {
  const { data, loading, error, reload } = useData(() => api.materials(work), [work]);
  const [text, setText] = useState("");
  const toast = useToast();
  const add = async () => {
    if (!text.trim()) return;
    await api.addMaterial(work, text.trim()); setText(""); toast("素材已存"); reload();
  };
  const proc = async (mid: string) => {
    await api.processMaterial(work, mid); toast("已提炼摘要+标签"); reload();
  };
  const distill = async (mid: string) => {
    await api.distillMaterial(work, mid, "setting"); toast("已提炼为设定"); reload();
  };
  const del = async (mid: string) => {
    await api.deleteMaterial(work, mid); reload();
  };
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-start gap-1">
        <Textarea
          rows={2}
          aria-label="新素材"
          value={text}
          placeholder="粘贴/记下素材(灵感、设定、句子)…"
          className="text-xs resize-none"
          onChange={(e) => setText(e.target.value)}
        />
        <Button variant="ghost" size="sm" onClick={add}>存</Button>
      </div>
      <StateBoundary
        loading={loading}
        error={error}
        empty={!data?.length}
        emptyNode={<Empty title="还没有素材" />}
        onRetry={reload}
      >
        <div className="flex flex-col gap-1.5">
          {data?.map((m) => {
            // 重构:material.content 是纯文本、tags 是逗号串(新底座契约,不再 JSON-in-field)
            const txt = m.content || "";
            const tags = (m.tags || "").split(/[，,]/).map((s) => s.trim()).filter(Boolean);
            return (
              <Card key={m.id} size="sm">
                <CardContent className="pt-3">
                  <p className="text-xs">{txt.slice(0, 70)}{txt.length > 70 ? "…" : ""}</p>
                  {tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {tags.map((t, i) => (
                        <Badge key={i} variant="secondary" className="text-[10px]">{t}</Badge>
                      ))}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {m.status !== "processed" && (
                      <Button variant="ghost" size="xs" onClick={() => proc(m.id)}>提炼摘要</Button>
                    )}
                    <Button variant="ghost" size="xs" onClick={() => distill(m.id)}>→设定</Button>
                    <Button variant="ghost" size="xs" onClick={() => del(m.id)}>删</Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </StateBoundary>
    </div>
  );
}

function BibleAdd({ work, onAdded }: { work: string; onAdded: () => void }) {
  const [kind, setKind] = useState<"char" | "set">("char");
  const [name, setName] = useState("");
  const toast = useToast();
  const add = async () => {
    const n = name.trim(); if (!n) return;
    if (kind === "char") await api.addCharacter(work, n);
    else await api.addSetting(work, n);
    setName(""); toast(kind === "char" ? "已加角色" : "已加设定"); onAdded();
  };
  return (
    <div className="flex items-center gap-1 mb-3">
      <select
        value={kind}
        onChange={(e) => setKind(e.target.value as "char" | "set")}
        aria-label="类型"
        className="h-7 w-16 shrink-0 rounded-lg border border-input bg-transparent px-1.5 text-xs outline-none"
      >
        <option value="char">角色</option>
        <option value="set">设定</option>
      </select>
      <Input
        aria-label="名称"
        value={name}
        placeholder={kind === "char" ? "角色名…" : "设定名…"}
        className="h-7 text-xs"
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") add(); }}
      />
      <Button variant="ghost" size="sm" onClick={add}>加</Button>
    </div>
  );
}

interface Card { type: string; title: string; options?: string[] }

function parseCards(text: string): { text: string; cards: Card[] } {
  const cards: Card[] = [];
  const clean = text.replace(/```scribe-card\s*([\s\S]*?)```/g, (_m, body) => {
    try { const c = JSON.parse(body.trim()); if (c && c.title) cards.push(c); } catch { /* */ }
    return "";
  }).trim();
  return { text: clean, cards };
}

function ChiefCard({ card, onPick }: { card: Card; onPick: (opt: string) => void }) {
  const isHard = card.type === "hard_conflict";
  const isSuggestion = card.type === "suggestion";
  const borderColor = isHard ? "border-l-destructive" : isSuggestion ? "border-l-[#f59e0b]" : "border-l-primary";
  const icon = isHard ? "⚠ 硬冲突" : isSuggestion ? "💡 建议" : "⌖ 待定夺";
  return (
    <Card size="sm" className={cn("border-l-[3px]", borderColor)}>
      <CardContent className="pt-3">
        <p className="text-xs font-medium">{icon} {card.title}</p>
        {card.options && card.options.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {card.options.map((o, i) => (
              <Button key={i} variant="ghost" size="xs" onClick={() => onPick(o)}>{o}</Button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Chat({ work, bump }: { work: string; bump: () => void }) {
  const [msgs, setMsgs] = useState<{ who: "me" | "ai"; text: string; cards?: Card[] }[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const send = async (raw?: string) => {
    const m = (raw ?? input).trim(); if (!m || busy) return;
    setInput(""); setMsgs((x) => [...x, { who: "me", text: m }]); setBusy(true);
    try {
      const r = await api.chat(`(当前书 work_id=${work})${m}`);
      const { text, cards } = parseCards(r.content);
      setMsgs((x) => [...x, { who: "ai", text: text || "(见下方卡片)", cards }]);
    } catch (e) {
      setMsgs((x) => [...x, { who: "ai", text: "出错:" + errMsg(e) }]);
    } finally {
      setBusy(false); bump();
      setTimeout(() => boxRef.current?.scrollTo(0, 1e9), 0);
    }
  };
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">主编对话</h3>
      <div className="flex flex-col gap-2">
        {/* 消息区 */}
        <ScrollArea className="h-36">
          <div ref={boxRef} aria-live="polite" className="flex flex-col gap-1.5 pr-2">
            {msgs.length === 0 && (
              <Empty
                title="和主编聊聊这本书"
                hint="遇决策/冲突会给可操作卡片"
                className="py-4"
              />
            )}
            {msgs.map((m, i) => (
              <div key={i} className="flex flex-col gap-1">
                <div
                  className={cn(
                    "max-w-[85%] rounded-xl px-3 py-2 text-xs font-prose",
                    m.who === "me"
                      ? "self-end bg-primary text-primary-foreground"
                      : "self-start bg-muted text-foreground"
                  )}
                >
                  {m.text}
                </div>
                {m.cards?.map((c, j) => (
                  <ChiefCard key={j} card={c} onPick={(o) => send(`我选:${o}`)} />
                ))}
              </div>
            ))}
            {busy && (
              <div className="self-start rounded-xl px-3 py-2 text-xs bg-muted text-muted-foreground animate-pulse">
                主编思考中…
              </div>
            )}
          </div>
        </ScrollArea>
        {/* 输入行 */}
        <div className="flex items-center gap-1">
          <Input
            aria-label="对主编说"
            value={input}
            placeholder="说点什么…"
            disabled={busy}
            className="h-7 text-xs"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") send(); }}
          />
          <Button size="sm" onClick={() => send()} disabled={busy}>
            <Send size={13} /> 发
          </Button>
        </div>
      </div>
    </div>
  );
}
