/**
 * ExtractPanel.tsx — 从正文 AI 抽取候选设定(§9 AI 抽取入口)。
 * 选章→主编从正文抽候选人物/设定/伏笔(不落库)→勾选→入库。候选先经人审,防幻觉污染。
 */
import { useState } from "react";
import { Loader2, Sparkles, X } from "lucide-react";
import { api, type ExtractResult } from "@/api";
import { useToast } from "@/common";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function ExtractPanel({ work, onSaved, onClose }: { work: string; onSaved: () => void; onClose: () => void }) {
  const [seq, setSeq] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const toast = useToast();

  const toggle = (key: string) => setPicked((p) => { const n = new Set(p); n.has(key) ? n.delete(key) : n.add(key); return n; });

  const extract = async () => {
    const n = Number(seq);
    if (!n) { toast("填章号"); return; }
    setBusy(true); setResult(null);
    try {
      const r = await api.extractEntities(work, n);
      setResult(r);
      const all = new Set<string>();
      r.characters.forEach((c) => all.add("char:" + c.name));
      r.settings.forEach((s) => all.add("set:" + s.name));
      r.foreshadows.forEach((_, i) => all.add("fs:" + i));
      setPicked(all);
      if (!r.characters.length && !r.settings.length && !r.foreshadows.length) toast("这章没抽到新设定");
    } catch (e) { toast(String(e)); } finally { setBusy(false); }
  };

  const save = async () => {
    if (!result) return;
    setBusy(true);
    let n = 0;
    try {
      for (const c of result.characters) if (picked.has("char:" + c.name)) { await api.addCharacter(work, c.name, c.motivation ?? ""); n++; }
      for (const s of result.settings) if (picked.has("set:" + s.name)) { await api.addSetting(work, s.name, s.type ?? "设定"); n++; }
      for (let i = 0; i < result.foreshadows.length; i++) {
        const fs = result.foreshadows[i];
        if (picked.has("fs:" + i)) { await api.plantForeshadow(work, fs.summary, fs.chapter ?? Number(seq)); n++; }
      }
      toast(`已入库 ${n} 条`); onSaved(); setResult(null);
    } catch (e) { toast(String(e)); } finally { setBusy(false); }
  };

  const Row = ({ k, label, sub }: { k: string; label: string; sub?: string }) => (
    <label className="flex items-start gap-2 text-xs rounded-md hover:bg-accent px-2 py-1.5 cursor-pointer">
      <input type="checkbox" checked={picked.has(k)} onChange={() => toggle(k)} className="mt-0.5" />
      <span className="min-w-0"><span className="font-medium text-foreground">{label}</span>{sub && <span className="text-muted-foreground"> · {sub}</span>}</span>
    </label>
  );

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border">
        <span className="text-sm font-medium flex items-center gap-1.5"><Sparkles size={14} className="text-primary" />从正文抽取设定</span>
        <button onClick={onClose} className="w-6 h-6 rounded inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent"><X size={14} /></button>
      </div>
      <div className="px-3 py-2.5 border-b border-border flex gap-2 items-center">
        <Input value={seq} onChange={(e) => setSeq(e.target.value)} placeholder="章号" className="h-8 text-sm w-20"
          onKeyDown={(e) => { if (e.key === "Enter") extract(); }} />
        <Button size="sm" className="h-8 gap-1" onClick={extract} disabled={busy}>
          {busy && !result ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}主编抽取
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto px-1.5 py-2">
        {!result ? (
          <p className="text-xs text-muted-foreground px-2 py-4 text-center">填章号,让主编从该章正文抽出候选人物/设定/伏笔。候选先勾选再入库,不直接污染设定库。</p>
        ) : (
          <div className="flex flex-col gap-2">
            {result.characters.length > 0 && <div><div className="text-[11px] font-semibold text-muted-foreground px-2">人物 {result.characters.length}</div>{result.characters.map((c) => <Row key={c.name} k={"char:" + c.name} label={c.name} sub={c.motivation} />)}</div>}
            {result.settings.length > 0 && <div><div className="text-[11px] font-semibold text-muted-foreground px-2">设定 {result.settings.length}</div>{result.settings.map((s) => <Row key={s.name} k={"set:" + s.name} label={s.name} sub={s.type} />)}</div>}
            {result.foreshadows.length > 0 && <div><div className="text-[11px] font-semibold text-muted-foreground px-2">伏笔 {result.foreshadows.length}</div>{result.foreshadows.map((fs, i) => <Row key={i} k={"fs:" + i} label={fs.summary} sub={fs.chapter ? `第${fs.chapter}章` : ""} />)}</div>}
          </div>
        )}
      </div>
      {result && (
        <div className="flex justify-end gap-2 p-2.5 border-t border-border">
          <span className="text-xs text-muted-foreground mr-auto self-center">已选 {picked.size}</span>
          <Button size="sm" onClick={save} disabled={busy || picked.size === 0}>
            {busy ? <Loader2 size={13} className="animate-spin mr-1" /> : null}入库所选
          </Button>
        </div>
      )}
    </div>
  );
}
