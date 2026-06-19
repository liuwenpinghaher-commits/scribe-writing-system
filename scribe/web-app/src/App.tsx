import { useEffect, useMemo, useRef, useState } from "react";
import { PanelRight, PanelLeft, BookOpen, Lightbulb, Search } from "lucide-react";
import { api } from "./api";
import type { Work, Chapter } from "./api";
import { Btn, ToastProvider, useData, useToast } from "./common";
import { Library } from "./Library";
import { Center } from "./Center";
import { Right } from "./Right";

function Workspace() {
  const works = useData(() => api.works(), []);
  const [cur, setCur] = useState<Work | null>(null);
  const [seq, setSeq] = useState<number | null>(null);
  const [rev, setRev] = useState(0);
  const bump = () => setRev((r) => r + 1);
  const [showLeft, setShowLeft] = useState(false);
  const [showRight, setShowRight] = useState(false);

  const select = (w: Work) => { setCur(w); setSeq(null); setShowLeft(false); };

  // 全局快捷键:⌘I 想象捕获 · ⌘K 命令面板 · ⌘⇧F 专注模式
  const [imagOpen, setImagOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [focus, setFocus] = useState(false);
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;
      if (meta && e.shiftKey && e.key.toLowerCase() === "f") { e.preventDefault(); setFocus((v) => !v); return; }
      if (meta && e.key.toLowerCase() === "i" && cur) { e.preventDefault(); setImagOpen(true); }
      if (meta && e.key.toLowerCase() === "k") { e.preventDefault(); setCmdOpen((v) => !v); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [cur]);

  // P4-4 深浅色:记忆到 localStorage,落到 documentElement[data-theme]
  const [theme, setTheme] = useState<string>(() => localStorage.getItem("scribe-theme") || "light");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("scribe-theme", theme); }, [theme]);

  // C5/C3-2 SSE:订阅后端事件(待决方案/札记/一致性变化)→ 主动刷新,替代盲目轮询
  useEffect(() => {
    if (!cur) return;
    const base = import.meta.env.VITE_API ?? "http://127.0.0.1:8801";
    const es = new EventSource(`${base}/works/${cur.id}/events?owner=u1`);
    es.onmessage = () => bump();
    es.onerror = () => es.close();
    return () => es.close();
  }, [cur]);

  // URL 深链:#/work/<id>/ch/<seq> —— 可分享/收藏/前进后退(审查 #21)
  useEffect(() => {
    const apply = () => {
      const m = location.hash.match(/^#\/work\/([^/]+)(?:\/ch\/(\d+))?/);
      if (!m || !works.data) return;
      const w = works.data.find((x) => x.id === m[1]);
      if (w) { setCur(w); setSeq(m[2] ? Number(m[2]) : null); }
    };
    apply();
    window.addEventListener("hashchange", apply);
    return () => window.removeEventListener("hashchange", apply);
  }, [works.data]);

  useEffect(() => {
    const want = cur ? `#/work/${cur.id}${seq != null ? `/ch/${seq}` : ""}` : "";
    if (cur && location.hash !== want) history.replaceState(null, "", want || location.pathname);
  }, [cur, seq]);

  return (
    <div className={"app" + (showLeft ? " show-left" : "") + (showRight ? " show-right" : "") + (focus ? " focus" : "")}>
      <aside className="col left">
        <Library works={works.data} loading={works.loading} error={works.error}
          reload={works.reload} current={cur} onSelect={select} />
      </aside>

      <main className="col center">
        <div className="row end" style={{ justifyContent: "space-between", marginBottom: 10 }}>
          <h1>
            <button className="ghost sm left-toggle" aria-label="打开作品库"
              onClick={() => setShowLeft((v) => !v)}><PanelLeft size={16} /></button>{" "}
            {cur ? cur.title : "Scribe 写作工作台"}
          </h1>
          <div className="row">
            <button className="ghost sm" aria-label="命令面板 ⌘K" title="命令面板 ⌘K" onClick={() => setCmdOpen(true)}><Search size={16} /></button>
            <button className="ghost sm" aria-label="深浅色" title="深浅色" onClick={() => setTheme((t) => t === "dark" ? "light" : "dark")}>{theme === "dark" ? "☾" : "☀"}</button>
            <button className="ghost sm" aria-label="专注模式 ⌘⇧F" title="专注模式 ⌘⇧F" onClick={() => setFocus((v) => !v)}>{focus ? "⤢" : "⤡"}</button>
            <button className="ghost sm right-toggle" aria-label="打开主编与设定"
              onClick={() => setShowRight((v) => !v)}><PanelRight size={16} /></button>
          </div>
        </div>
        {cur
          ? <Center key={cur.id} work={cur.id} title={cur.title} rev={rev} bump={bump}
              currentSeq={seq} setSeq={setSeq} />
          : <div className="empty"><BookOpen size={28} /><div style={{ marginTop: 8 }}>从左侧选择或新建一本书</div></div>}
      </main>

      <aside className="col right">
        {cur ? <Right key={cur.id} work={cur.id} rev={rev} bump={bump} />
          : <div className="empty">选择一本书后,这里是主编、设定与对话</div>}
      </aside>

      {imagOpen && cur && (
        <ImagModal work={cur.id} onClose={() => setImagOpen(false)} onSaved={bump} />
      )}
      {cmdOpen && (
        <CommandPalette works={works.data} cur={cur} onClose={() => setCmdOpen(false)}
          onSelectWork={(w) => { select(w); setCmdOpen(false); }}
          onJump={(s) => { setSeq(s); setCmdOpen(false); }}
          onImagine={() => { setCmdOpen(false); if (cur) setImagOpen(true); }} />
      )}
    </div>
  );
}

function CommandPalette({ works, cur, onClose, onSelectWork, onJump, onImagine }: {
  works: Work[] | null; cur: Work | null; onClose: () => void;
  onSelectWork: (w: Work) => void; onJump: (seq: number) => void; onImagine: () => void;
}) {
  const [q, setQ] = useState("");
  const [chs, setChs] = useState<Chapter[]>([]);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { ref.current?.focus(); if (cur) api.chapters(cur.id).then(setChs).catch(() => {}); }, [cur]);
  const items = useMemo(() => {
    const list: { label: string; hint: string; run: () => void }[] = [];
    if (cur) list.push({ label: "捕获想象", hint: "⌘I", run: onImagine });
    works?.forEach((w) => list.push({ label: `书 · ${w.title}`, hint: w.genre || "", run: () => onSelectWork(w) }));
    chs.forEach((c) => list.push({ label: `第 ${c.seq} 章 · ${c.title || "无题"}`, hint: "跳转", run: () => onJump(c.seq) }));
    const qq = q.trim().toLowerCase();
    return qq ? list.filter((i) => i.label.toLowerCase().includes(qq)) : list;
  }, [q, works, chs, cur]);
  const sel = Math.min(active, Math.max(0, items.length - 1));
  return (
    <div className="scrim" onClick={onClose} role="dialog" aria-modal="true" aria-label="命令面板">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="row end"><Search size={16} />
          <input ref={ref} value={q} placeholder="搜书 / 章 / 动作…  (Esc 关闭)"
            onChange={(e) => { setQ(e.target.value); setActive(0); }}
            onKeyDown={(e) => {
              if (e.key === "Escape") onClose();
              if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, items.length - 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
              if (e.key === "Enter") { items[sel]?.run(); }
            }} />
        </div>
        <div style={{ maxHeight: "44vh", overflow: "auto", marginTop: 8 }}>
          {items.length === 0 && <div className="empty">无匹配</div>}
          {items.map((it, i) => (
            <button key={i} className={"card clickable" + (i === sel ? " active" : "")}
              onMouseEnter={() => setActive(i)} onClick={it.run}
              style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>{it.label}</span><span className="muted small">{it.hint}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ImagModal({ work, onClose, onSaved }: { work: string; onClose: () => void; onSaved: () => void }) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const toast = useToast();
  useEffect(() => { ref.current?.focus(); }, []);
  const save = async () => {
    if (!text.trim()) return;
    await api.capture(work, text.trim()); toast("想象已存(AI 一切文字的源头)"); onSaved(); onClose();
  };
  return (
    <div className="scrim" onClick={onClose} role="dialog" aria-modal="true" aria-label="捕获想象">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3><Lightbulb size={16} style={{ verticalAlign: -2 }} /> 捕获想象</h3>
        <div className="muted small" style={{ marginBottom: 6 }}>随手抛创意/方向 —— ⌘↵ 保存,Esc 关闭</div>
        <textarea ref={ref} rows={3} value={text} placeholder="例:我想要一场雨夜的背叛"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") onClose();
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") save();
          }} />
        <div className="row" style={{ marginTop: 8, justifyContent: "flex-end" }}>
          <Btn onClick={onClose} variant="ghost">取消</Btn>
          <Btn onClick={save}>捕获</Btn>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return <ToastProvider><Workspace /></ToastProvider>;
}
