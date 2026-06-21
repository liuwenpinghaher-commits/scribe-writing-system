import { useState } from "react";
import { Stethoscope, NotebookPen, BookMarked, Sparkles, ShieldAlert, Package, Activity, Brain, MessagesSquare } from "lucide-react";
import { api } from "./api";
import { errMsg, useData, useToast } from "./common";
import { QualityCard, Relations, CharStates, Threads, AgentPanel } from "./Panels";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StateBoundary } from "@/components/StateBoundary";
import { Empty } from "@/components/Empty";
import { InlineText } from "@/components/detail";
import { cn } from "@/lib/utils";

// Right — 右栏 Inspector。活动栏拆解:每个能力一个图标,点开渲染单一能力面板。
export const RIGHT_CAPS = [
  { key: "notes", label: "主编札记", icon: NotebookPen, badge: "insights" },
  { key: "bible", label: "设定圣经", icon: BookMarked },
  { key: "foreshadow", label: "伏笔", icon: Sparkles, badge: "foreshadow" },
  { key: "flags", label: "一致性", icon: ShieldAlert, badge: "flags" },
  { key: "material", label: "素材", icon: Package },
  { key: "pulse", label: "脉络·质量", icon: Activity },
  { key: "agent", label: "记忆·技能", icon: Brain },
  { key: "threads", label: "讨论线程", icon: MessagesSquare },
] as const;

export function Right({ work, rev, bump, active = "notes" }: {
  work: string; rev: number; bump: () => void; active?: string;
}) {
  switch (active) {
    case "notes":
      return (
        <div className="flex flex-col gap-3">
          <PendingWrites work={work} rev={rev} bump={bump} />
          <Insights work={work} rev={rev} />
        </div>
      );
    case "bible": return <BibleSection work={work} rev={rev} />;
    case "foreshadow": return <ForeshadowSection work={work} rev={rev} />;
    case "flags": return <FlagsSection work={work} rev={rev} />;
    case "material": return <Materials work={work} />;
    case "pulse": return <Pulse work={work} rev={rev} />;
    case "agent": return <AgentPanel work={work} rev={rev} />;
    case "threads": return <Threads work={work} rev={rev} />;
    default: return null;
  }
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

function ForeshadowSection({ work, rev }: { work: string; rev: number }) {
  const [local, setLocal] = useState(0);
  const fo = useData(() => api.foreshadows(work), [work, rev, local]);
  const toast = useToast();
  const onFore = async (fid: string, a: "trigger" | "pay" | "abandon") => {
    try { await api.advanceForeshadow(work, fid, a); toast("伏笔已推进"); setLocal((n) => n + 1); }
    catch (e) { toast(errMsg(e), "err"); }
  };
  return (
    <StateBoundary loading={fo.loading} error={fo.error} empty={!fo.data?.length}
      emptyNode={<Empty title="暂无未了结伏笔" />} onRetry={fo.reload}>
      <div className="flex flex-col gap-2">
        {fo.data?.map((x) => (
          <Card key={x.id} size="sm">
            <CardContent className="pt-3">
              <div className="flex items-start gap-1.5">
                <Badge variant="outline" className="shrink-0 text-[10px] mt-0.5">{x.state}</Badge>
                <span className="text-xs">{x.summary}</span>
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                {x.state === "planted" && <Button variant="ghost" size="xs" onClick={() => onFore(x.id, "trigger")}>触发</Button>}
                {x.state === "triggered" && <Button variant="ghost" size="xs" onClick={() => onFore(x.id, "pay")}>回收</Button>}
                <Button variant="ghost" size="xs" onClick={() => onFore(x.id, "abandon")}>放弃</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </StateBoundary>
  );
}

function FlagsSection({ work, rev }: { work: string; rev: number }) {
  const [local, setLocal] = useState(0);
  const fl = useData(() => api.flags(work), [work, rev, local]);
  const toast = useToast();
  const onFlag = async (fid: string, a: "confirm" | "dismiss" | "fix") => {
    await api.resolveFlag(work, fid, a);
    toast(a === "dismiss" ? "已标记误报" : "已确认"); setLocal((n) => n + 1);
  };
  return (
    <StateBoundary loading={fl.loading} error={fl.error} empty={!fl.data?.length}
      emptyNode={<Empty title="无一致性问题 ✓" hint="太棒了,目前没有发现冲突。" />} onRetry={fl.reload}>
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
  );
}

function BibleSection({ work, rev }: { work: string; rev: number }) {
  const bible = useData(async () => {
    const [chs, st] = await Promise.all([api.characters(work), api.settings(work)]);
    const desc = (c?: string) => c || "";
    return [
      ...chs.map((c) => ({ kind: "char" as const, k: "角色", name: c.name, body: c.motivation || "", type: "" })),
      ...st.map((s) => ({ kind: "set" as const, k: s.type ?? "设定", name: s.name, body: desc(s.content), type: s.type ?? "设定" })),
    ];
  }, [work, rev]);
  return (
    <div>
      <BibleAdd work={work} onAdded={bible.reload} />
      <StateBoundary loading={bible.loading} error={bible.error} empty={!bible.data?.length}
        emptyNode={<Empty title="还没有设定/角色" hint="在上方添加" />} onRetry={bible.reload}>
        <div className="flex flex-col gap-1.5">
          {bible.data?.map((x, i) => (<BibleItem key={i} work={work} item={x} onSaved={bible.reload} />))}
        </div>
      </StateBoundary>
      <RelationsSection work={work} rev={rev} />
    </div>
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
  const [body, setBody] = useState(item.body);
  const [impact, setImpact] = useState<{ seq: number; title?: string; snippet: string }[] | null>(null);
  const [loadingImpact, setLoadingImpact] = useState(false);
  const [showStates, setShowStates] = useState(false);
  const toast = useToast();
  const dirty = body.trim() !== item.body.trim();
  const save = async () => {
    if (item.kind === "char") await api.addCharacter(work, item.name, body.trim());
    else await api.addSetting(work, item.name, item.type || "设定", body.trim());
    toast("已保存"); onSaved();
  };
  const loadImpact = async () => {
    if (impact) { setImpact(null); return; }
    setLoadingImpact(true);
    try { setImpact(await api.impact(work, item.name)); } finally { setLoadingImpact(false); }
  };
  const jump = (seq: number) => { location.hash = `#/work/${work}/ch/${seq}`; };
  return (
    <Card size="sm">
      <CardContent className="pt-2.5 pb-2 flex flex-col gap-0.5">
        <div className="flex items-center gap-1.5 px-1">
          <Badge variant="secondary" className="text-[10px] shrink-0">{item.k}</Badge>
          <span className="font-prose text-sm font-medium">{item.name}</span>
          {dirty && <Button variant="ghost" size="xs" className="ml-auto h-6" onClick={save}>保存</Button>}
        </div>
        {/* body:点击即编辑(统一详情风格) */}
        <InlineText multiline rows={2} v={body} on={(e) => setBody(e.target.value)}
          ph={item.kind === "char" ? "动机/性格…" : "设定描述…"} />
        <div className="flex flex-wrap gap-2 px-2 pt-0.5">
          <button className="text-xs text-muted-foreground hover:text-foreground transition-colors" onClick={loadImpact}>
            {item.kind === "char" ? "出场时间线" : "影响章节"}{impact ? " ▾" : " ▸"}
          </button>
          {item.kind === "char" && (
            <button className="text-xs text-muted-foreground hover:text-foreground transition-colors" onClick={() => setShowStates((v) => !v)}>
              状态轨迹{showStates ? " ▾" : " ▸"}
            </button>
          )}
        </div>
        {showStates && item.kind === "char" && <CharStates work={work} name={item.name} />}
        {loadingImpact && <p className="text-xs text-muted-foreground px-2">查找中…</p>}
        {impact && (
          <div className="flex flex-col gap-1 px-1 pt-1">
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
