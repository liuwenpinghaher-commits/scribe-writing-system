/**
 * Editor.tsx — 章编辑器(Task 1.3b 换皮,逻辑全保留)
 * 换皮:shadcn Card/Button/Textarea/Badge/ScrollArea + lucide 图标
 * 保留:streamAction/diffChars/SegmentNode/自动存草稿/所有 api 调用
 */
import { useEffect, useRef, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { SegmentNode } from "./SegmentNode";
import {
  BookText,
  Check,
  ChevronDown,
  ChevronRight,
  GitBranch,
  Loader2,
  MessageSquareQuote,
  RotateCcw,
  Save,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "./api";
import type { Draft, Verdict, Snapshot } from "./api";
import { diffChars } from "./diff";
import { errMsg, useData, useToast } from "./common";
import { StateBoundary } from "./components/StateBoundary";
import { Empty } from "./components/Empty";
import { Card, CardContent, CardHeader } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { Textarea } from "./components/ui/textarea";
import { Input } from "./components/ui/input";
import { Badge } from "./components/ui/badge";
import { cn } from "./lib/utils";

type Mode = "draft" | "edit" | "history";
const FB_TEMPLATES = ["太长", "节奏慢", "太直白", "不像角色", "更狠", "去掉AI腔"];

// ─── 章状态颜色 ──────────────────────────────────────────────
const statusColor: Record<string, string> = {
  done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400",
  draft: "bg-muted text-muted-foreground",
  revising: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400",
};

// ─── 裁决颜色 ────────────────────────────────────────────────
const verdictCfg = {
  aligned: { borderClass: "border-l-emerald-500", label: "对齐北极星", textClass: "text-emerald-600 dark:text-emerald-400" },
  soft_deviation: { borderClass: "border-l-amber-500", label: "软偏离", textClass: "text-amber-600 dark:text-amber-400" },
  hard_violation: { borderClass: "border-l-destructive", label: "⚠ 硬红线违反", textClass: "text-destructive" },
};

export function ChapterEditor({
  work,
  seq,
  rev,
  bump,
}: {
  work: string;
  seq: number;
  rev: number;
  bump: () => void;
}) {
  const { data: ch, loading, error, reload } = useData(() => api.chapter(work, seq), [work, seq, rev]);
  const segs = useData(() => api.segments(work, seq), [work, seq, rev]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [fb, setFb] = useState("");
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [mode, setMode] = useState<Mode>("draft");
  const toast = useToast();
  const snaps = ch?.snapshots ?? [];
  const latest = snaps[snaps.length - 1]?.content ?? "";

  const editor = useEditor({ extensions: [StarterKit, SegmentNode], content: "" }, [seq, work]);
  useEffect(() => {
    if (editor && mode === "edit") {
      const esc = (l: string) => (l ? l.replace(/</g, "&lt;") : "<br>");
      const html = segs.data?.length
        ? segs.data.map((s) => `<p data-by="${s.created_by}">${esc(s.text)}</p>`).join("")
        : latest.split("\n").map((l) => `<p>${esc(l)}</p>`).join("");
      editor.commands.setContent(html);
    }
  }, [editor, latest, mode, segs.data]);

  // P4-3 防丢稿:编辑态每 3s 写 localStorage
  const dkey = `scribe-draft-${work}-${seq}`;
  const [recovered, setRecovered] = useState<string | null>(null);
  useEffect(() => {
    if (mode !== "edit" || !editor) return;
    const t = setInterval(() => {
      const x = editor.getText();
      if (x.trim()) localStorage.setItem(dkey, x);
    }, 3000);
    return () => clearInterval(t);
  }, [mode, editor, dkey]);
  useEffect(() => {
    if (mode !== "edit") { setRecovered(null); return; }
    const d = localStorage.getItem(dkey);
    setRecovered(d && d.trim() && d !== latest ? d : null);
  }, [mode, dkey, latest]);
  const restore = () => {
    if (!editor || !recovered) return;
    editor.commands.setContent(
      recovered.split("\n").map((l) => `<p>${l ? l.replace(/</g, "&lt;") : "<br>"}</p>`).join("")
    );
    setRecovered(null);
    toast("已恢复未保存草稿");
  };

  // 流式生成草稿(F),逐字显示;⌘. 取消
  const [streaming, setStreaming] = useState<string | null>(null);
  const [sideBySide, setSideBySide] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const gen = async (action: "continue" | "rewrite", instruction = "") => {
    if (action === "rewrite") {
      if (!instruction.trim()) { toast("先写下意见", "err"); return; }
      await api.feedback(work, seq, instruction);
    }
    setStreaming(""); setVerdict(null);
    const ac = new AbortController(); abortRef.current = ac;
    try {
      const d = await api.streamAction(
        work, seq, action, instruction,
        (delta) => setStreaming((s) => (s ?? "") + delta),
        ac.signal
      );
      setStreaming(null); abortRef.current = null;
      if (d.content) setDraft(d);
    } catch (e) {
      setStreaming(null); abortRef.current = null;
      if (!(e instanceof DOMException && e.name === "AbortError")) toast("生成失败", "err");
    }
  };

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "." && abortRef.current) {
        e.preventDefault(); abortRef.current.abort(); setStreaming(null); toast("已取消生成");
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [toast]);

  const accept = async () => {
    if (!draft) return;
    await api.saveProse(work, seq, draft.content, true);
    await api.pref(work, "feedback_accept", "+", fb ? { text: fb } : undefined).catch(() => {});
    await api.rebuildSegments(work, seq).catch(() => {});
    await api.check(work, seq).catch(() => {});
    await api.ingest(work, seq).catch(() => {});
    setDraft(null); setFb(""); toast("已接受并定稿"); bump(); reload();
  };
  const reject = () => { setDraft(null); toast("已放弃该草稿(未改动原文)"); };
  const saveMine = async () => {
    const text = editor?.getText().trim() ?? "";
    if (!text) { toast("正文为空", "err"); return; }
    await api.saveProse(work, seq, text, true);
    await api.rebuildSegments(work, seq).catch(() => {});
    localStorage.removeItem(dkey); setRecovered(null);
    toast("已存为你的定稿"); bump(); reload();
  };
  const runIntent = async () => { setVerdict(await api.intentCheck(work, seq)); };

  const [crit, setCrit] = useState<Awaited<ReturnType<typeof api.critique>> | null>(null);
  const [critBusy, setCritBusy] = useState(false);
  const runCritique = async () => {
    setCritBusy(true);
    try { setCrit(await api.critique(work, seq, "", true)); }
    finally { setCritBusy(false); }
  };
  const [deepBusy, setDeepBusy] = useState(false);
  const runDeep = async () => {
    setDeepBusy(true);
    try {
      const r = await api.deepCheck(work, seq);
      toast(`深度体检：新增 ${r.new_flags} 个一致性问题`); bump();
    } catch (e) { toast(errMsg(e), "err"); }
    finally { setDeepBusy(false); }
  };
  const acceptCritique = async () => {
    if (!crit?.improved) return;
    await api.saveProse(work, seq, crit.final, true);
    await api.rebuildSegments(work, seq).catch(() => {});
    setCrit(null); toast("已采用评改稿"); bump(); reload();
  };
  const toggleDone = async () => {
    await api.setStatus(work, seq, ch?.status === "done" ? "draft" : "done");
    toast(ch?.status === "done" ? "已转草稿" : "本章已完成"); bump(); reload();
  };
  const restoreSnap = async (content: string) => {
    await api.saveProse(work, seq, content, true);
    await api.rebuildSegments(work, seq).catch(() => {});
    toast("已恢复该版本为定稿"); bump(); reload();
  };

  const vc = verdict ? verdictCfg[verdict.status] : null;

  return (
    <StateBoundary loading={loading} error={error} empty={false} onRetry={reload}>
      {/* 章头卡 */}
      <Card className="mb-3">
        <CardContent className="py-2.5 px-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-foreground">
              第 {seq} 章 · {ch?.title || "无题"}
            </h3>
            <Badge className={cn("text-xs", ch?.status ? statusColor[ch.status] : statusColor.draft)}>
              {ch?.status ?? "draft"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground tabular-nums mt-0.5">
            字数 {latest.length.toLocaleString()} · {snaps.length} 个版本
          </p>
        </CardContent>
      </Card>

      {/* 工具条 */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={toggleDone}>
          <Check size={12} /> {ch?.status === "done" ? "标记草稿" : "标记完成"}
        </Button>
        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={runCritique} disabled={critBusy}>
          {critBusy ? <Loader2 size={12} className="animate-spin" /> : <MessageSquareQuote size={12} />}
          文学评改
        </Button>
        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={runIntent}>
          <ShieldCheck size={12} /> 查北极星
        </Button>
        <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={runDeep} disabled={deepBusy}>
          {deepBusy ? <Loader2 size={12} className="animate-spin" /> : null}
          深度体检
        </Button>
      </div>

      {/* 任务状态机 */}
      <TaskStepper work={work} seq={seq} rev={rev} />

      {/* 文学评改卡 */}
      {crit && (
        <Card className={cn("mb-3 border-l-4", crit.last_overall >= 3.5 ? "border-l-emerald-500" : "border-l-amber-500")}>
          <CardContent className="py-2.5 px-4">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-medium">文学评改</span>
              <span className="text-xs text-muted-foreground">
                总分 {crit.first_overall}
                {crit.improved ? ` → ${crit.last_overall}（已改写）` : ""}
                {crit.rounds[0]?.critique.worst_dims?.length
                  ? " · 弱项：" + crit.rounds[0].critique.worst_dims.join("/")
                  : ""}
              </span>
            </div>
            {crit.rounds[0]?.critique.issues?.slice(0, 3).map((it, i) => (
              <p key={i} className="text-xs text-muted-foreground">· {it}</p>
            ))}
            {crit.improved && (
              <div className="flex gap-2 mt-2">
                <Button size="sm" className="h-7 text-xs gap-1" onClick={acceptCritique}>
                  <Check size={12} /> 采用评改稿
                </Button>
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setCrit(null)}>
                  保留原稿
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 北极星裁决卡 */}
      {verdict && vc && (
        <Card className={cn("mb-3 border-l-4", vc.borderClass)} role="status">
          <CardContent className="py-2.5 px-4 flex items-center gap-2">
            <span className={cn("text-sm font-medium", vc.textClass)}>{vc.label}</span>
            <span className="text-xs text-muted-foreground">{verdict.reason}</span>
          </CardContent>
        </Card>
      )}

      {/* 流式预览(逐字) */}
      {streaming !== null && !draft && (
        <Card className="mb-3 border-border bg-muted/40" aria-live="polite">
          <CardContent className="py-2.5 px-4">
            <p className="text-xs text-muted-foreground mb-2">主编书写中…（⌘. 取消）</p>
            <p className="text-sm font-prose leading-relaxed whitespace-pre-wrap">
              {streaming}
              <span className="animate-pulse">▌</span>
            </p>
          </CardContent>
        </Card>
      )}

      {/* Diff 裁决区 */}
      {draft ? (
        <Card className="mb-3 border-border">
          <CardContent className="py-2.5 px-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted-foreground">AI 草稿 vs 当前（绿=新增 / 红=删除）</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs"
                onClick={() => setSideBySide((v) => !v)}
              >
                {sideBySide ? "合并视图" : "并排视图"}
              </Button>
            </div>

            {sideBySide ? (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">原稿</p>
                  <p className="text-sm font-prose leading-relaxed opacity-70 whitespace-pre-wrap">
                    {draft.prev_content || "（空）"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">新稿</p>
                  <p className="text-sm font-prose leading-relaxed whitespace-pre-wrap">
                    {diffChars(draft.prev_content, draft.content)
                      .filter((s) => s.type !== "del")
                      .map((s, i) => (
                        <span key={i} className={s.type === "ins" ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" : ""}>
                          {s.text}
                        </span>
                      ))}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm font-prose leading-relaxed whitespace-pre-wrap">
                {diffChars(draft.prev_content, draft.content).map((s, i) =>
                  s.type === "same" ? (
                    <span key={i}>{s.text}</span>
                  ) : s.type === "del" ? (
                    <span key={i} className="bg-red-100 text-red-700 line-through dark:bg-red-900/30 dark:text-red-400">{s.text}</span>
                  ) : (
                    <span key={i} className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">{s.text}</span>
                  )
                )}
              </p>
            )}

            <div className="flex flex-wrap gap-2 mt-3">
              <Button size="sm" className="gap-1" onClick={accept}>
                <Check size={13} /> 接受并定稿
              </Button>
              <Button variant="ghost" size="sm" className="gap-1 text-destructive" onClick={reject}>
                <X size={13} /> 放弃
              </Button>
              <Button variant="ghost" size="sm" className="gap-1" onClick={() => setDraft(null)}>
                <RotateCcw size={13} /> 再改（回到意见）
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 阅读/编辑/历史 标签行 */}
          <div className="flex gap-1 mb-3">
            {(["draft", "edit", "history"] as const).map((m) => (
              <button
                key={m}
                className={cn(
                  "px-3 py-1 rounded-md text-sm font-medium transition-all",
                  mode === m
                    ? "bg-card text-primary shadow-sm border border-border"
                    : "text-muted-foreground hover:text-foreground"
                )}
                onClick={() => setMode(m)}
                aria-pressed={mode === m}
              >
                {m === "draft" ? "阅读/引用" : m === "edit" ? "手动编辑" : `版本 ${snaps.length}`}
              </button>
            ))}
          </div>

          {/* 阅读视图 */}
          {mode === "draft" && (
            <StateBoundary
              loading={segs.loading}
              error={segs.error}
              empty={!segs.data?.length}
              emptyNode={<Empty icon={<BookText />} title="还没有正文" hint="点「让主编写这章」生成，或切手动编辑" />}
              onRetry={segs.reload}
            >
              <div className="flex flex-col gap-2">
                {segs.data?.map((s) => (
                  <SegmentView key={s.id} text={s.text} cites={s.citation_refs} by={s.created_by} />
                ))}
              </div>
            </StateBoundary>
          )}

          {/* 历史版本 */}
          {mode === "history" && (
            <HistoryView
              snaps={snaps}
              onRestore={restoreSnap}
              work={work}
              seq={seq}
              onMerged={() => { bump(); reload(); }}
            />
          )}

          {/* 手动编辑 */}
          {mode === "edit" && (
            <>
              {recovered && (
                <Card className="mb-3 border-amber-400 bg-amber-50 dark:bg-amber-900/20" role="status">
                  <CardContent className="py-2.5 px-4">
                    <p className="text-sm mb-2">发现上次未保存的草稿。</p>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={restore}>恢复</Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 text-xs text-destructive"
                        onClick={() => { localStorage.removeItem(dkey); setRecovered(null); }}
                      >
                        丢弃
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
              <Card className="mb-2">
                <CardContent className="p-0">
                  <div className="editor-wrap min-h-48 p-3 text-sm font-prose leading-relaxed [&_.tiptap]:outline-none">
                    <EditorContent editor={editor} />
                  </div>
                </CardContent>
              </Card>
              <Button variant="ghost" size="sm" className="gap-1 h-7 text-xs" onClick={saveMine}>
                <Save size={12} /> 存为我的定稿
              </Button>
            </>
          )}
        </>
      )}

      {/* 操作区 */}
      {!draft && (
        <div className="mt-4 flex flex-col gap-2">
          <Button className="gap-1.5 self-start" onClick={() => gen("continue")}>
            <Sparkles size={14} /> 让主编写这章
          </Button>

          <label className="text-xs text-muted-foreground mt-1">
            对这章提意见 → 主编定向重写（出草稿给你比对）
          </label>
          <div className="flex flex-wrap gap-1 mb-1">
            {FB_TEMPLATES.map((t) => (
              <button
                key={t}
                className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted-foreground hover:text-foreground hover:border-primary transition-colors"
                onClick={() => setFb((v) => (v ? v + "、" : "") + t)}
              >
                {t}
              </button>
            ))}
          </div>
          <Textarea
            rows={2}
            value={fb}
            onChange={(e) => setFb(e.target.value)}
            placeholder="如：开头更紧张、句子更短、删掉说教"
            className="text-sm resize-none"
          />
          <Button variant="ghost" className="gap-1.5 self-start" onClick={() => gen("rewrite", fb)}>
            <MessageSquareQuote size={14} /> 提意见并重写
          </Button>
        </div>
      )}
    </StateBoundary>
  );
}

// ─── 分支管理 ────────────────────────────────────────────────
function Branches({
  work,
  seq,
  latest,
  onMerged,
}: {
  work: string;
  seq: number;
  latest: string;
  onMerged: () => void;
}) {
  const { data, reload } = useData(() => api.branches(work, seq), [work, seq]);
  const [label, setLabel] = useState("");
  const toast = useToast();

  const create = async () => {
    if (!label.trim()) return;
    await api.createBranch(work, seq, label.trim(), latest);
    setLabel(""); toast("已建分支（以当前内容）"); reload();
  };
  const merge = async (l: string) => {
    await api.mergeBranch(work, seq, l);
    toast(`已合并「${l}」为定稿`); onMerged(); reload();
  };
  const branches = (data ?? []).filter((b) => b.label !== "human-final" && b.label !== "ai-draft");

  return (
    <Card className="mt-3">
      <CardHeader className="py-2 px-3">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <GitBranch size={12} /> 分支（A/B 走向 → 选定合并为定稿）
        </div>
      </CardHeader>
      <CardContent className="py-0 px-3 pb-3">
        <div className="flex gap-2 mb-2">
          <Input
            aria-label="新分支名"
            value={label}
            placeholder="如 A走向…"
            className="h-7 text-xs"
            onChange={(e) => setLabel(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") create(); }}
          />
          <Button variant="ghost" size="sm" className="h-7 text-xs shrink-0" onClick={create}>建分支</Button>
        </div>
        {branches.map((b) => (
          <div key={b.label} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
            <div className="flex items-center gap-1.5 min-w-0">
              <Badge variant="secondary" className="text-xs">{b.label}</Badge>
              <span className="text-xs text-muted-foreground truncate">{b.content.slice(0, 30)}…</span>
            </div>
            <Button variant="ghost" size="sm" className="h-6 text-xs shrink-0" onClick={() => merge(b.label)}>
              合并为定稿
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

// ─── 历史版本视图 ────────────────────────────────────────────
function HistoryView({
  snaps,
  onRestore,
  work,
  seq,
  onMerged,
}: {
  snaps: Snapshot[];
  onRestore: (c: string) => void;
  work: string;
  seq: number;
  onMerged: () => void;
}) {
  const latest = snaps[snaps.length - 1]?.content ?? "";
  const [sel, setSel] = useState(Math.max(0, snaps.length - 2));
  if (snaps.length === 0) return <Empty icon={<GitBranch />} title="还没有任何版本" />;

  const label = (s: Snapshot) =>
    (s.branch_label || s.created_by) + (s.is_human_locked ? " · 🔒定稿" : "");
  const chosen = snaps[Math.min(sel, snaps.length - 1)];
  const isLatest = chosen === snaps[snaps.length - 1];

  return (
    <>
      <p className="text-xs text-muted-foreground mb-2">共 {snaps.length} 版（最新在底）。选一版与当前定稿对比：</p>
      <div className="flex flex-col gap-1 mb-3">
        {snaps.map((s, i) => (
          <button
            key={s.id}
            className={cn(
              "flex items-start gap-2 rounded-lg border px-3 py-2 text-left transition-colors",
              i === sel
                ? "border-primary border-l-2 bg-card shadow-sm"
                : "border-border hover:border-primary/40 hover:bg-muted/50"
            )}
            onClick={() => setSel(i)}
          >
            <Badge variant="secondary" className="text-xs shrink-0 mt-0.5">{i + 1}</Badge>
            <div className="min-w-0">
              <span className={cn("text-xs font-medium", s.created_by === "human" ? "text-foreground" : "text-muted-foreground")}>
                {label(s)}
              </span>
              {i === snaps.length - 1 && <span className="text-xs text-muted-foreground"> · 当前</span>}
              <p className="text-xs text-muted-foreground truncate mt-0.5">{(s.content || "").slice(0, 40)}…</p>
            </div>
          </button>
        ))}
      </div>

      {!isLatest && (
        <Card className="mb-3">
          <CardContent className="py-2.5 px-4">
            <p className="text-xs text-muted-foreground mb-2">第 {sel + 1} 版 → 当前定稿（绿=新增 / 红=删除）：</p>
            <p className="text-sm font-prose leading-relaxed whitespace-pre-wrap">
              {diffChars(chosen.content, latest).map((d, i) =>
                d.type === "same" ? (
                  <span key={i}>{d.text}</span>
                ) : d.type === "del" ? (
                  <span key={i} className="bg-red-100 text-red-700 line-through dark:bg-red-900/30 dark:text-red-400">{d.text}</span>
                ) : (
                  <span key={i} className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">{d.text}</span>
                )
              )}
            </p>
            <Button
              variant="ghost"
              size="sm"
              className="gap-1 h-7 text-xs mt-3"
              onClick={() => onRestore(chosen.content)}
            >
              <RotateCcw size={12} /> 恢复第 {sel + 1} 版为定稿
            </Button>
          </CardContent>
        </Card>
      )}

      <Branches work={work} seq={seq} latest={latest} onMerged={onMerged} />
    </>
  );
}

// ─── 任务状态机(流程步骤器)───────────────────────────────────
const STATE_LABEL: Record<string, string> = {
  PLANNING: "规划中", AWAITING_OUTLINE_CHOICE: "待选大纲", OUTLINED: "已定纲",
  DRAFTING: "起草中", DRAFTED: "初稿成", REFLECTING: "自检中",
  REVISING: "修订中", AWAITING_DRAFT_CHOICE: "待选稿", REVIEWING: "评审中",
  REVIEW_FAILED: "评审未过", AWAITING_HUMAN: "待你裁决", CONSISTENCY_CHECK: "一致性核",
  MEMORY_UPDATE: "记忆更新", DONE: "完成", FAILED: "失败",
};

function TaskStepper({ work, seq, rev }: { work: string; seq: number; rev: number }) {
  const { data, reload } = useData(() => api.task(work, seq), [work, seq, rev]);
  const [open, setOpen] = useState(false);
  const toast = useToast();

  const go = async (to: string) => {
    try {
      await api.advanceTask(work, seq, to);
      toast(`流程 → ${STATE_LABEL[to] || to}`); reload();
    } catch (e) { toast(errMsg(e), "err"); }
  };

  if (!data) return null;

  return (
    <Card className="mb-3">
      <CardContent className="py-2 px-3">
        <button
          className="flex w-full items-center gap-2 text-left"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          <span className="text-xs text-muted-foreground">写作流程</span>
          <span className="text-sm font-medium">{STATE_LABEL[data.status] || data.status}</span>
          {open ? <ChevronDown size={12} className="ml-auto" /> : <ChevronRight size={12} className="ml-auto" />}
        </button>
        {open && data.next.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {data.next.map((s) => (
              <Button key={s} variant="ghost" size="sm" className="h-6 text-xs" onClick={() => go(s)}>
                → {STATE_LABEL[s] || s}
              </Button>
            ))}
          </div>
        )}
        {open && data.next.length === 0 && (
          <p className="text-xs text-muted-foreground mt-2">终态，无后续</p>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 段落阅读视图 ────────────────────────────────────────────
function SegmentView({ text, cites, by }: { text: string; cites?: string; by: string }) {
  const [open, setOpen] = useState(false);
  let list: { name: string; kind: string }[] = [];
  try { list = JSON.parse(cites || "[]"); } catch { /* */ }

  return (
    <Card
      className={cn(
        "border-l-4",
        by === "human" ? "border-l-emerald-400" : "border-l-sky-400/70"
      )}
      data-by={by === "human" ? "human" : "ai"}
    >
      <CardContent className="py-2.5 px-3">
        <div className="flex items-center gap-1.5 mb-1.5">
          <span className="text-xs text-muted-foreground">
            {by === "human" ? "✍ 人工" : "AI"}
          </span>
          {list.length > 0 && (
            <span className="text-xs text-muted-foreground">· 引用 {list.length} 项</span>
          )}
        </div>
        <p className="text-sm font-prose leading-relaxed whitespace-pre-wrap">{text}</p>
        {list.length > 0 && (
          <div className="mt-2">
            <button
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => setOpen((o) => !o)}
              aria-expanded={open}
            >
              <BookText size={11} /> 引用 {list.length} 项 {open ? "▾" : "▸"}
            </button>
            {open && (
              <div className="flex flex-wrap gap-1 mt-1">
                {list.map((c, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">{c.name}</Badge>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
