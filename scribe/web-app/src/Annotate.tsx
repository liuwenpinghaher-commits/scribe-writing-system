/**
 * Annotate.tsx — 划词交互层
 * 选中正文文字后浮起工具条:讨论这段(引用对话)/ 让主编改写这段 / 批注 / 高亮。
 * useTextSelection 检测容器内选区;SelectionToolbar 浮动定位 + 4 动作内联表单。
 * applyHighlights 把高亮 quote 在段落文本里着色渲染。
 */
import { useCallback, useState, type RefObject } from "react";
import { MessageSquareQuote, Pencil, StickyNote, Highlighter, Loader2, Check, X } from "lucide-react";
import { api, type Highlight } from "./api";
import { useToast } from "./common";
import { Button } from "./components/ui/button";
import { Textarea } from "./components/ui/textarea";
import { Input } from "./components/ui/input";
import { cn } from "./lib/utils";

export interface SelInfo { text: string; top: number; left: number }

/** 检测 ref 容器内的文字选区,返回 {text, 相对容器的 top/left} 与清除函数。 */
export function useTextSelection(ref: RefObject<HTMLElement | null>): [SelInfo | null, () => void, () => void] {
  const [sel, setSel] = useState<SelInfo | null>(null);
  const capture = useCallback(() => {
    const s = window.getSelection();
    const text = s?.toString().trim() ?? "";
    if (!s || s.isCollapsed || text.length < 2) return;
    const range = s.getRangeAt(0);
    const host = ref.current;
    if (!host || !host.contains(range.commonAncestorContainer)) return;
    const r = range.getBoundingClientRect();
    const c = host.getBoundingClientRect();
    setSel({ text, top: r.bottom - c.top + host.scrollTop + 6, left: Math.max(0, r.left - c.left) });
  }, [ref]);
  return [sel, capture, () => setSel(null)];
}

const HL_COLORS: { key: string; label: string; cls: string }[] = [
  { key: "amber", label: "重点", cls: "bg-amber-300/70 dark:bg-amber-500/40" },
  { key: "rose", label: "待改", cls: "bg-rose-300/70 dark:bg-rose-500/40" },
  { key: "sky", label: "疑问", cls: "bg-sky-300/70 dark:bg-sky-500/40" },
];
export const hlClass = (color: string) => HL_COLORS.find((c) => c.key === color)?.cls ?? HL_COLORS[0].cls;

/** 浮动划词工具条:4 动作 + 内联表单。 */
export function SelectionToolbar({
  sel, work, seq, onDiscuss, onReplace, onChanged, onClose,
}: {
  sel: SelInfo;
  work: string;
  seq: number;
  onDiscuss: (text: string) => void;
  onReplace: (original: string, rewritten: string) => void;
  onChanged: () => void;
  onClose: () => void;
}) {
  type View = "menu" | "rewrite" | "annotate" | "highlight";
  const [view, setView] = useState<View>("menu");
  const [instr, setInstr] = useState("");
  const [note, setNote] = useState("");
  const [target, setTarget] = useState("self");
  const [busy, setBusy] = useState(false);
  const [rewritten, setRewritten] = useState<string | null>(null);
  const toast = useToast();

  const doRewrite = async () => {
    setBusy(true);
    try {
      const r = await api.rewritePassage(work, seq, sel.text, instr);
      setRewritten(r.rewritten);
    } catch (e) { toast(String(e)); } finally { setBusy(false); }
  };
  const doAnnotate = async () => {
    setBusy(true);
    try { await api.addAnnotation(work, seq, sel.text, note, target); toast("已批注"); onChanged(); onClose(); }
    catch (e) { toast(String(e)); } finally { setBusy(false); }
  };
  const doHighlight = async (color: string) => {
    setBusy(true);
    try { await api.addHighlight(work, seq, sel.text, color); onChanged(); onClose(); }
    catch (e) { toast(String(e)); } finally { setBusy(false); }
  };

  return (
    <div
      className="absolute z-30 rounded-lg border border-border bg-popover shadow-xl text-sm"
      style={{ top: sel.top, left: sel.left, maxWidth: "min(440px, 90%)" }}
      onMouseDown={(e) => e.preventDefault()}  // 别清掉选区
    >
      {view === "menu" && (
        <div className="flex items-center gap-0.5 p-1">
          <ToolBtn icon={<MessageSquareQuote size={14} />} label="讨论" onClick={() => { onDiscuss(sel.text); onClose(); }} />
          <ToolBtn icon={<Pencil size={14} />} label="改写" onClick={() => setView("rewrite")} />
          <ToolBtn icon={<StickyNote size={14} />} label="批注" onClick={() => setView("annotate")} />
          <ToolBtn icon={<Highlighter size={14} />} label="高亮" onClick={() => setView("highlight")} />
          <button className="px-1.5 text-muted-foreground hover:text-foreground" onClick={onClose} aria-label="关闭"><X size={13} /></button>
        </div>
      )}

      {view === "rewrite" && (
        <div className="p-2 w-[420px] max-w-[90vw] flex flex-col gap-2">
          <div className="text-xs text-muted-foreground line-clamp-2">「{sel.text}」</div>
          {rewritten == null ? (
            <>
              <Input autoFocus placeholder="怎么改?如:更冷、删形容词、提速…" value={instr}
                     onChange={(e) => setInstr(e.target.value)}
                     onKeyDown={(e) => { if (e.key === "Enter" && !busy) doRewrite(); }} />
              <div className="flex gap-1.5 justify-end">
                <Button size="sm" variant="ghost" onClick={onClose}>取消</Button>
                <Button size="sm" onClick={doRewrite} disabled={busy}>
                  {busy ? <Loader2 size={13} className="animate-spin" /> : "让主编改写"}
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="rounded-md bg-muted/60 p-2 text-sm font-prose leading-relaxed max-h-48 overflow-auto whitespace-pre-wrap">{rewritten}</div>
              <div className="flex gap-1.5 justify-end">
                <Button size="sm" variant="ghost" onClick={() => setRewritten(null)}>重改</Button>
                <Button size="sm" variant="ghost" onClick={onClose}>弃用</Button>
                <Button size="sm" onClick={() => { onReplace(sel.text, rewritten); onClose(); }}>
                  <Check size={13} className="mr-1" /> 替换这段
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {view === "annotate" && (
        <div className="p-2 w-[360px] max-w-[90vw] flex flex-col gap-2">
          <div className="text-xs text-muted-foreground line-clamp-2">「{sel.text}」</div>
          <Textarea autoFocus rows={3} placeholder="写点批注…" value={note} onChange={(e) => setNote(e.target.value)} />
          <div className="flex items-center justify-between">
            <div className="flex gap-1">
              {[["self", "自留"], ["chief", "给主编"]].map(([k, lbl]) => (
                <button key={k} onClick={() => setTarget(k)}
                  className={cn("px-2 py-0.5 rounded text-xs border", target === k ? "border-primary text-primary" : "border-border text-muted-foreground")}>
                  {lbl}
                </button>
              ))}
            </div>
            <div className="flex gap-1.5">
              <Button size="sm" variant="ghost" onClick={onClose}>取消</Button>
              <Button size="sm" onClick={doAnnotate} disabled={busy || !note.trim()}>
                {busy ? <Loader2 size={13} className="animate-spin" /> : "保存批注"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {view === "highlight" && (
        <div className="p-2 flex items-center gap-1.5">
          {HL_COLORS.map((c) => (
            <button key={c.key} onClick={() => doHighlight(c.key)} disabled={busy}
              className={cn("px-2.5 py-1 rounded text-xs font-medium", c.cls)}>{c.label}</button>
          ))}
          <button className="px-1.5 text-muted-foreground hover:text-foreground" onClick={onClose}><X size={13} /></button>
        </div>
      )}
    </div>
  );
}

function ToolBtn({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1 px-2 py-1 rounded-md hover:bg-accent text-foreground transition-colors">
      {icon}<span className="text-xs">{label}</span>
    </button>
  );
}

/** 把段落文本按高亮 quote 切片着色。命中的子串包到带底色的 <mark>。 */
export function applyHighlights(text: string, highlights: Highlight[]): React.ReactNode {
  const hits = highlights.filter((h) => h.quote && text.includes(h.quote));
  if (!hits.length) return text;
  // 取最先出现的命中,递归处理两侧(简单稳妥,避免重叠)
  let best: Highlight | null = null, bestIdx = Infinity;
  for (const h of hits) {
    const i = text.indexOf(h.quote);
    if (i >= 0 && i < bestIdx) { bestIdx = i; best = h; }
  }
  if (!best) return text;
  const before = text.slice(0, bestIdx);
  const mid = text.slice(bestIdx, bestIdx + best.quote.length);
  const after = text.slice(bestIdx + best.quote.length);
  return (
    <>
      {before && applyHighlights(before, highlights)}
      <mark className={cn("rounded px-0.5", hlClass(best.color))}>{mid}</mark>
      {after && applyHighlights(after, highlights)}
    </>
  );
}
