import { useEffect, useRef, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { SegmentNode } from "./SegmentNode";
import { Save, Sparkles, MessageSquareQuote, Check, X, RotateCcw, ShieldCheck, BookText } from "lucide-react";
import { api } from "./api";
import type { Draft, Verdict, Snapshot } from "./api";
import { diffChars } from "./diff";
import { Btn, State, useData, useToast } from "./common";

type Mode = "draft" | "edit" | "history";
const FB_TEMPLATES = ["太长", "节奏慢", "太直白", "不像角色", "更狠", "去掉AI腔"];

export function ChapterEditor({ work, seq, rev, bump }: {
  work: string; seq: number; rev: number; bump: () => void;
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
      // E:有段落数据则按来源构建 segment 节点(AI 淡蓝/人工淡绿);否则退回纯文本
      const esc = (l: string) => (l ? l.replace(/</g, "&lt;") : "<br>");
      const html = segs.data?.length
        ? segs.data.map((s) => `<p data-by="${s.created_by}">${esc(s.text)}</p>`).join("")
        : latest.split("\n").map((l) => `<p>${esc(l)}</p>`).join("");
      editor.commands.setContent(html);
    }
  }, [editor, latest, mode, segs.data]);

  // P4-3 防丢稿:编辑态每 3s 写 localStorage;与最新定稿有差异则提示恢复
  const dkey = `scribe-draft-${work}-${seq}`;
  const [recovered, setRecovered] = useState<string | null>(null);
  useEffect(() => {
    if (mode !== "edit" || !editor) return;
    const t = setInterval(() => { const x = editor.getText(); if (x.trim()) localStorage.setItem(dkey, x); }, 3000);
    return () => clearInterval(t);
  }, [mode, editor, dkey]);
  useEffect(() => {
    if (mode !== "edit") { setRecovered(null); return; }
    const d = localStorage.getItem(dkey);
    setRecovered(d && d.trim() && d !== latest ? d : null);
  }, [mode, dkey, latest]);
  const restore = () => {
    if (!editor || !recovered) return;
    editor.commands.setContent(recovered.split("\n").map((l) => `<p>${l ? l.replace(/</g, "&lt;") : "<br>"}</p>`).join(""));
    setRecovered(null); toast("已恢复未保存草稿");
  };

  // —— AI 动作:流式生成草稿(F),逐字显示;⌘. 取消 ——
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
      const d = await api.streamAction(work, seq, action, instruction,
        (delta) => setStreaming((s) => (s ?? "") + delta), ac.signal);
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
    await api.saveProse(work, seq, draft.content, true);          // 存为锁定定稿
    await api.pref(work, "feedback_accept", "+", fb ? { text: fb } : undefined).catch(() => {}); // 回流品味(带意见文本供学习)
    await api.rebuildSegments(work, seq).catch(() => {});
    await api.check(work, seq).catch(() => {});                   // 门槛自动校验
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

  const vColor = verdict ? { aligned: "var(--ok)", soft_deviation: "var(--warn)", hard_violation: "var(--danger)" }[verdict.status] : undefined;
  const vLabel = verdict ? { aligned: "对齐北极星", soft_deviation: "软偏离", hard_violation: "⚠ 硬红线违反" }[verdict.status] : undefined;

  return (
    <State loading={loading} error={error} empty={false} onRetry={reload}>
      {/* 章头卡(工程2b §3.2) */}
      <div className="ch-header">
        <div className="row end" style={{ justifyContent: "space-between" }}>
          <h3 style={{ margin: 0, color: "var(--text-primary)", fontSize: 16 }}>第 {seq} 章 · {ch?.title || "无题"}</h3>
          <span className="badge">{ch?.status}</span>
        </div>
        <div className="muted small" style={{ marginTop: 4 }}>
          字数 {latest.length.toLocaleString()} · {snaps.length} 个版本
        </div>
      </div>
      <div className="toolbar">
        <div className="row" style={{ flexWrap: "wrap" }}>
          <Btn onClick={toggleDone} variant="ghost" className="sm">
            <Check size={14} /> {ch?.status === "done" ? "标记草稿" : "标记完成"}
          </Btn>
          <Btn onClick={runCritique} variant="ghost" className="sm">{critBusy ? "评改中…" : "✎ 文学评改"}</Btn>
          <Btn onClick={runIntent} variant="ghost" className="sm"><ShieldCheck size={14} /> 查北极星</Btn>
        </div>
      </div>
      {crit && (
        <div className="card" style={{ borderLeft: `3px solid ${crit.last_overall >= 3.5 ? "var(--ok)" : "var(--warn)"}` }}>
          <b>文学评改</b> <span className="muted small">
            总分 {crit.first_overall}{crit.improved ? ` → ${crit.last_overall}(已改写)` : ""}
            {crit.rounds[0]?.critique.worst_dims?.length ? " · 弱项:" + crit.rounds[0].critique.worst_dims.join("/") : ""}
          </span>
          {crit.rounds[0]?.critique.issues?.slice(0, 3).map((it, i) => <div key={i} className="muted small">· {it}</div>)}
          {crit.improved && (
            <div className="row" style={{ marginTop: 6 }}>
              <Btn onClick={acceptCritique} className="sm"><Check size={14} /> 采用评改稿</Btn>
              <Btn onClick={() => setCrit(null)} variant="ghost" className="sm">保留原稿</Btn>
            </div>
          )}
        </div>
      )}
      {verdict && (
        <div className="card" style={{ borderLeft: `3px solid ${vColor}` }} role="status">
          <b style={{ color: vColor }}>{vLabel}</b> <span className="muted small">{verdict.reason}</span>
        </div>
      )}

      {/* F 流式生成预览(逐字) */}
      {streaming !== null && !draft && (
        <div className="card" style={{ borderColor: "var(--accent)" }} aria-live="polite">
          <div className="muted small">主编书写中…(⌘. 取消)</div>
          <div className="seg">{streaming}<span className="cursor-blink">▌</span></div>
        </div>
      )}

      {/* —— 草稿 diff 裁决区(最核心:看得到改了什么 + 接受/放弃/再改)—— */}
      {draft ? (
        <div className="card" style={{ borderColor: "var(--accent)" }}>
          <div className="row end" style={{ justifyContent: "space-between", marginBottom: 4 }}>
            <span className="muted small">AI 草稿 vs 当前(绿=新增 / 红=删除)</span>
            <button className="ghost sm" onClick={() => setSideBySide((v) => !v)}>{sideBySide ? "合并视图" : "并排视图"}</button>
          </div>
          {sideBySide ? (
            <div className="sxs">
              <div className="seg" style={{ opacity: 0.75 }}><div className="muted small">原稿</div>{draft.prev_content || "（空）"}</div>
              <div className="seg"><div className="muted small">新稿</div>
                {diffChars(draft.prev_content, draft.content).filter((s) => s.type !== "del").map((s, i) =>
                  <span key={i} className={s.type === "ins" ? "d-ins" : ""}>{s.text}</span>)}
              </div>
            </div>
          ) : (
            <div className="seg">
              {diffChars(draft.prev_content, draft.content).map((s, i) =>
                s.type === "same" ? <span key={i}>{s.text}</span>
                  : <span key={i} className={s.type === "del" ? "d-del" : "d-ins"}>{s.text}</span>)}
            </div>
          )}
          <div className="row" style={{ marginTop: 8, flexWrap: "wrap" }}>
            <Btn onClick={accept}><Check size={15} /> 接受并定稿</Btn>
            <Btn onClick={reject} variant="ghost"><X size={15} /> 放弃</Btn>
            <Btn onClick={() => { setDraft(null); }} variant="ghost"><RotateCcw size={15} /> 再改(回到意见)</Btn>
          </div>
        </div>
      ) : (
        <>
          {/* 读视图:段落 + 引用展开 */}
          <div className="row" style={{ marginBottom: 6 }}>
            <button className={mode === "draft" ? "" : "ghost"} onClick={() => setMode("draft")} aria-pressed={mode === "draft"}>阅读/引用</button>
            <button className={mode === "edit" ? "" : "ghost"} onClick={() => setMode("edit")} aria-pressed={mode === "edit"}>手动编辑</button>
            <button className={mode === "history" ? "" : "ghost"} onClick={() => setMode("history")} aria-pressed={mode === "history"}>版本 {snaps.length}</button>
          </div>
          {mode === "draft" ? (
            <State loading={segs.loading} error={segs.error} empty={!segs.data?.length} emptyText="还没有正文,点「让主编写这章」" onRetry={segs.reload}>
              {segs.data?.map((s) => <SegmentView key={s.id} text={s.text} cites={s.citation_refs} by={s.created_by} />)}
            </State>
          ) : mode === "history" ? (
            <HistoryView snaps={snaps} onRestore={restoreSnap} work={work} seq={seq}
              onMerged={() => { bump(); reload(); }} />
          ) : (
            <>
              {recovered && (
                <div className="card" style={{ borderColor: "var(--warn)" }} role="status">
                  <span className="small">发现上次未保存的草稿。</span>
                  <div className="row" style={{ marginTop: 6 }}>
                    <Btn onClick={restore} variant="ghost" className="sm">恢复</Btn>
                    <Btn onClick={() => { localStorage.removeItem(dkey); setRecovered(null); }} variant="ghost" className="sm">丢弃</Btn>
                  </div>
                </div>
              )}
              <div className="editor-wrap"><EditorContent editor={editor} /></div>
              <Btn onClick={saveMine} variant="ghost" className="sm"><Save size={14} /> 存为我的定稿</Btn></>
          )}
        </>
      )}

      {/* 操作区 */}
      {!draft && (
        <>
          <div className="row" style={{ marginTop: 10, flexWrap: "wrap" }}>
            <Btn onClick={() => gen("continue")}><Sparkles size={15} /> 让主编写这章</Btn>
          </div>
          <label style={{ marginTop: 12 }}>对这章提意见 → 主编定向重写(出草稿给你比对)</label>
          <div className="row" style={{ flexWrap: "wrap", marginBottom: 4 }}>
            {FB_TEMPLATES.map((t) => <button key={t} className="ghost sm" onClick={() => setFb((v) => (v ? v + "、" : "") + t)}>{t}</button>)}
          </div>
          <textarea rows={2} value={fb} onChange={(e) => setFb(e.target.value)} placeholder="如:开头更紧张、句子更短、删掉说教" />
          <Btn onClick={() => gen("rewrite", fb)} variant="ghost"><MessageSquareQuote size={15} /> 提意见并重写</Btn>
        </>
      )}
    </State>
  );
}

function Branches({ work, seq, latest, onMerged }: {
  work: string; seq: number; latest: string; onMerged: () => void;
}) {
  const { data, reload } = useData(() => api.branches(work, seq), [work, seq]);
  const [label, setLabel] = useState("");
  const toast = useToast();
  const create = async () => {
    if (!label.trim()) return;
    await api.createBranch(work, seq, label.trim(), latest); setLabel("");
    toast("已建分支(以当前内容)"); reload();
  };
  const merge = async (l: string) => { await api.mergeBranch(work, seq, l); toast(`已合并「${l}」为定稿`); onMerged(); reload(); };
  const branches = (data ?? []).filter((b) => b.label !== "human-final" && b.label !== "ai-draft");
  return (
    <div className="card" style={{ marginTop: 8 }}>
      <div className="muted small">分支(A/B 走向 → 选定合并为定稿)</div>
      <div className="row" style={{ margin: "4px 0" }}>
        <input aria-label="新分支名" value={label} placeholder="如 A走向…"
          onChange={(e) => setLabel(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") create(); }} />
        <Btn onClick={create} variant="ghost" className="sm">建分支</Btn>
      </div>
      {branches.map((b) => (
        <div key={b.label} className="row end" style={{ justifyContent: "space-between", padding: "3px 0" }}>
          <span className="small"><span className="badge">{b.label}</span> {b.content.slice(0, 30)}…</span>
          <Btn onClick={() => merge(b.label)} variant="ghost" className="sm">合并为定稿</Btn>
        </div>
      ))}
    </div>
  );
}

function HistoryView({ snaps, onRestore, work, seq, onMerged }: {
  snaps: Snapshot[]; onRestore: (c: string) => void; work: string; seq: number; onMerged: () => void;
}) {
  const latest = snaps[snaps.length - 1]?.content ?? "";
  const [sel, setSel] = useState(Math.max(0, snaps.length - 2)); // 默认上一版 vs 定稿
  if (snaps.length === 0) return <div className="empty">还没有任何版本</div>;
  const label = (s: Snapshot) => (s.branch_label || s.created_by) + (s.is_human_locked ? " · 🔒定稿" : "");
  const chosen = snaps[Math.min(sel, snaps.length - 1)];
  const isLatest = chosen === snaps[snaps.length - 1];
  return (
    <>
      <div className="muted small" style={{ marginBottom: 4 }}>共 {snaps.length} 版(最新在底)。选一版与当前定稿对比:</div>
      {snaps.map((s, i) => (
        <button key={s.id} className={"card clickable" + (i === sel ? " active" : "")}
          onClick={() => setSel(i)} style={{ padding: "6px 8px" }}>
          <span className="badge">{i + 1}</span> <span className={s.created_by === "human" ? "" : "muted"}>{label(s)}</span>
          {i === snaps.length - 1 && <span className="muted small"> · 当前</span>}
          <div className="muted small">{(s.content || "").slice(0, 40)}…</div>
        </button>
      ))}
      {!isLatest && (
        <div className="card" style={{ marginTop: 6 }}>
          <div className="muted small" style={{ marginBottom: 4 }}>第 {sel + 1} 版 → 当前定稿(绿=新增 / 红=删除):</div>
          <div className="seg">
            {diffChars(chosen.content, latest).map((d, i) =>
              d.type === "same" ? <span key={i}>{d.text}</span>
                : <span key={i} className={d.type === "del" ? "d-del" : "d-ins"}>{d.text}</span>)}
          </div>
          <div style={{ marginTop: 6 }}>
            <Btn onClick={() => onRestore(chosen.content)} variant="ghost" className="sm">
              <RotateCcw size={14} /> 恢复第 {sel + 1} 版为定稿
            </Btn>
          </div>
        </div>
      )}
      <Branches work={work} seq={seq} latest={latest} onMerged={onMerged} />
    </>
  );
}

function SegmentView({ text, cites, by }: { text: string; cites?: string; by: string }) {
  const [open, setOpen] = useState(false);
  let list: { name: string; kind: string }[] = [];
  try { list = JSON.parse(cites || "[]"); } catch { /* */ }
  return (
    <div className="card seg-node" data-by={by === "human" ? "human" : "ai"}>
      <div className="seg-meta">
        <span>{by === "human" ? "✍ 人工" : "🤖 AI"}</span>
        {list.length > 0 && <span>· 引用 {list.length} 项</span>}
      </div>
      <div className="seg">{text}</div>
      {list.length > 0 && (
        <div className="muted small" style={{ marginTop: 4 }}>
          <button className="ghost sm" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
            <BookText size={12} /> 引用 {list.length} 项 {open ? "▾" : "▸"}
          </button>
          {open && <span> {list.map((c, i) => <span key={i} className="badge" style={{ marginLeft: 4 }}>{c.name}</span>)}</span>}
        </div>
      )}
    </div>
  );
}
