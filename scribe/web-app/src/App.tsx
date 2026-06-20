import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { BookOpen, Lightbulb, Search, Plus, BookText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "./api";
import type { Work, Chapter } from "./api";
import { Btn, ToastProvider, useData, useToast } from "./common";
import { Navigator } from "./Navigator";
import { Center } from "./Center";
import { Right } from "./Right";
import { VIEWS, type ViewKey } from "./views";
import { AppRail } from "./AppRail";
import { AtlasView } from "./views/AtlasView";
import { InsightView } from "./views/InsightView";
import { CodexView } from "./views/CodexView";
import { AgentView } from "./views/AgentView";

// 视图名映射(占位提示)
const VIEW_LABELS: Record<ViewKey, string> = {
  write: "写作台",
  atlas: "关系图谱",
  insight: "质量仪表盘",
  codex: "设定库",
  agent: "记忆与技能",
};

// 有效 view key 集合
const VALID_VIEWS = new Set<string>(VIEWS.map((v) => v.key));

function Workspace() {
  const works = useData(() => api.works(), []);
  const [cur, setCur] = useState<Work | null>(null);
  const [seq, setSeq] = useState<number | null>(null);
  const [view, setView] = useState<ViewKey>("write");
  const [rev, setRev] = useState(0);
  const bump = () => setRev((r) => r + 1);
  const [showLeft, setShowLeft] = useState(false);
  const [showRight, setShowRight] = useState(false);

  const select = (w: Work) => { setCur(w); setSeq(null); setShowLeft(false); };
  const createWork = async () => {
    const title = window.prompt("新书名?");
    if (!title?.trim()) return;
    const r = await api.createWork(title.trim());
    await works.reload();
    setCur({ id: r.work_id, title: title.trim() } as Work);
    setView("write");
  };

  // 全局快捷键:⌘I 想象捕获 · ⌘K 命令面板 · ⌘⇧F 专注 · ? 快捷键帮助
  const [imagOpen, setImagOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [focus, setFocus] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const toast = useToast();
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA";
      const meta = e.metaKey || e.ctrlKey;
      if (!typing && !meta && e.key === "?") { e.preventDefault(); setHelpOpen((v) => !v); return; }
      if (meta && e.shiftKey && e.key.toLowerCase() === "f") { e.preventDefault(); setFocus((v) => !v); return; }
      if (meta && e.key.toLowerCase() === "i" && cur) { e.preventDefault(); setImagOpen(true); }
      if (meta && e.key.toLowerCase() === "k") { e.preventDefault(); setCmdOpen((v) => !v); }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [cur]);

  // 深浅色主题:记忆到 localStorage,切换 <html> 的 .dark class(shadcn 约定)
  const [theme, setTheme] = useState<string>(() => localStorage.getItem("scribe-theme") || "light");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("scribe-theme", theme);
  }, [theme]);

  // C5/C3-2 SSE:订阅后端事件(待决方案/札记/一致性变化)→ 主动刷新,替代盲目轮询
  useEffect(() => {
    if (!cur) return;
    const base = import.meta.env.VITE_API ?? "http://127.0.0.1:3320";
    const es = new EventSource(`${base}/works/${cur.id}/events?owner=u1`);
    es.onmessage = () => bump();
    es.onerror = () => es.close();
    return () => es.close();
  }, [cur]);

  // URL 深链:#/work/<id>/<view>[/ch/<seq>] —— 向后兼容旧格式 #/work/<id>/ch/<seq>
  // 新格式:  #/work/<id>/<view>[/ch/<seq>]
  // 旧格式:  #/work/<id>[/ch/<seq>]  → view 默认 write
  useEffect(() => {
    const apply = () => {
      const hash = location.hash;
      if (!works.data) return;

      // 新格式:work/<id>/<view>[/ch/<seq>]
      const mNew = hash.match(/^#\/work\/([^/]+)\/([^/]+)(?:\/ch\/(\d+))?$/);
      if (mNew) {
        const w = works.data.find((x) => x.id === mNew[1]);
        const viewCandidate = mNew[2];
        // viewCandidate 可能是 "ch"(旧格式兼容)
        if (viewCandidate === "ch") {
          // 旧格式:#/work/<id>/ch/<seq>  → mNew[3] 是 seq
          if (w) { setCur(w); setView("write"); setSeq(mNew[3] ? Number(mNew[3]) : null); }
          return;
        }
        if (VALID_VIEWS.has(viewCandidate)) {
          if (w) { setCur(w); setView(viewCandidate as ViewKey); setSeq(mNew[3] ? Number(mNew[3]) : null); }
          return;
        }
        // 未知 view 段,忽略 view 部分,仍选中作品
        if (w) { setCur(w); setView("write"); }
        return;
      }

      // 最简格式:#/work/<id>
      const mSimple = hash.match(/^#\/work\/([^/]+)$/);
      if (mSimple && works.data) {
        const w = works.data.find((x) => x.id === mSimple[1]);
        if (w) { setCur(w); setView("write"); setSeq(null); }
      }
    };
    apply();
    window.addEventListener("hashchange", apply);
    return () => window.removeEventListener("hashchange", apply);
  }, [works.data]);

  // 写回 URL
  useEffect(() => {
    if (!cur) return;
    const seqPart = seq != null ? `/ch/${seq}` : "";
    const want = `#/work/${cur.id}/${view}${seqPart}`;
    if (location.hash !== want) history.replaceState(null, "", want);
  }, [cur, seq, view]);

  // 命令面板全动作(Linear 式:键盘可达一切,而非只跳转)
  const globalActions: Action[] = [
    { label: focus ? "退出专注模式" : "进入专注模式", hint: "⌘⇧F", run: () => setFocus((v) => !v) },
    { label: theme === "dark" ? "切到浅色" : "切到深色", hint: "☀/☾", run: () => setTheme((t) => (t === "dark" ? "light" : "dark")) },
    { label: "快捷键帮助", hint: "?", run: () => setHelpOpen(true) },
    { label: "打开作品库(左栏)", hint: "", run: () => setShowLeft(true) },
    ...VIEWS.map((v) => ({
      label: `切换视图 · ${v.label}`,
      hint: "",
      run: () => setView(v.key),
    })),
    ...(cur ? [
      { label: "捕获想象", hint: "⌘I", run: () => setImagOpen(true) },
      { label: "打开主编与设定(右栏)", hint: "", run: () => setShowRight(true) },
      { label: "全文体检 · 让主编主动揪问题", hint: "", run: async () => { const r = await api.review(cur.id); toast(`体检完成,新增 ${r.new_insights} 条札记`); bump(); } },
    ] : []),
  ];

  const renderViewContent = () => {
    // 没选书:所有视图都先给一个可靠的选书页(不依赖顶栏下拉)
    if (!cur) {
      return <WorkPicker works={works.data} loading={works.loading} error={works.error}
        reload={works.reload} onSelect={select} onCreate={createWork} />;
    }
    if (view === "write") {
      return (
        <div className={"app" + (showLeft ? " show-left" : "") + (showRight ? " show-right" : "") + (focus ? " focus" : "")}>
          <aside className="col left">
            {cur
              ? <Navigator work={cur.id} rev={rev} bump={bump}
                  currentSeq={seq} setSeq={(s) => { setSeq(s); setShowLeft(false); }} />
              : <div className="empty">从顶部下拉选择一本书</div>}
          </aside>

          <main className="col center">
            {cur
              ? <Center key={cur.id} work={cur.id} title={cur.title} rev={rev} bump={bump}
                  currentSeq={seq} />
              : <div className="empty"><BookOpen size={28} /><div style={{ marginTop: 8 }}>从顶部下拉选择或新建一本书</div></div>}
          </main>

          <aside className="col right">
            {cur ? <Right key={cur.id} work={cur.id} rev={rev} bump={bump} />
              : <div className="empty">选择一本书后,这里是主编、设定与对话</div>}
          </aside>
        </div>
      );
    }

    // atlas 视图:关系图谱
    if (view === "atlas") {
      return (
        <div className="flex-1 flex flex-col overflow-hidden h-full">
          {cur ? (
            <AtlasView work={cur.id} />
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
              请先从顶部下拉选择一本书
            </div>
          )}
        </div>
      );
    }

    // insight 视图:质量仪表盘
    if (view === "insight") {
      return (
        <div className="flex-1 flex flex-col overflow-hidden h-full">
          {cur ? (
            <InsightView work={cur.id} />
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
              请先从顶部下拉选择一本书
            </div>
          )}
        </div>
      );
    }

    // codex 视图:设定库
    if (view === "codex") {
      return (
        <div className="flex-1 flex flex-col overflow-hidden h-full">
          {cur ? (
            <CodexView work={cur.id} />
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
              请先从顶部下拉选择一本书
            </div>
          )}
        </div>
      );
    }

    // agent 视图:记忆与技能
    if (view === "agent") {
      return (
        <div className="flex-1 flex flex-col overflow-hidden h-full">
          {cur ? (
            <AgentView work={cur.id} />
          ) : (
            <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
              请先从顶部下拉选择一本书
            </div>
          )}
        </div>
      );
    }

    // 其他非写作台视图占位(全宽)
    return (
      <div className="flex-1 flex items-start overflow-auto" style={{ minHeight: "100vh" }}>
        <div className="p-8 text-muted-foreground">
          「{VIEW_LABELS[view]}」视图建设中
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* TopBar:顶部横排导航(切视图/切书/切主题) */}
      <AppRail
        current={cur}
        view={view}
        onView={setView}
        onOpenLibrary={() => setCur(null)}
        theme={theme}
        onTheme={setTheme}
      />

      {/* 主内容区 */}
      <div className="flex-1 overflow-hidden flex">
        {renderViewContent()}
      </div>

      {imagOpen && cur && (
        <ImagModal work={cur.id} onClose={() => setImagOpen(false)} onSaved={bump} />
      )}
      {cmdOpen && (
        <CommandPalette works={works.data} cur={cur} actions={globalActions} onClose={() => setCmdOpen(false)}
          onSelectWork={(w) => { select(w); setCmdOpen(false); }}
          onJump={(s) => { setSeq(s); setCmdOpen(false); }} />
      )}
      {helpOpen && <ShortcutsHelp onClose={() => setHelpOpen(false)} />}
    </div>
  );
}

// 可靠的选书页(不依赖顶栏下拉):没选书时主区显示
function WorkPicker({ works, loading, error, reload, onSelect, onCreate }: {
  works: Work[] | null; loading: boolean; error: string | null; reload: () => void;
  onSelect: (w: Work) => void; onCreate: () => void;
}) {
  return (
    <div className="flex-1 overflow-auto p-8">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-semibold text-foreground">作品库</h1>
            <p className="text-sm text-muted-foreground mt-1">选择一本书开始,或新建一本</p>
          </div>
          <Button onClick={onCreate}><Plus size={16} /> 新建作品</Button>
        </div>
        {loading ? (
          <div className="py-16 text-center text-sm text-muted-foreground">加载中…</div>
        ) : error ? (
          <div className="py-16 text-center text-sm text-destructive">
            {error} · <button className="underline" onClick={reload}>重试</button>
          </div>
        ) : !works?.length ? (
          <div className="py-16 text-center text-sm text-muted-foreground">还没有作品。点「新建作品」开始。</div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {works.map((w) => (
              <button key={w.id} onClick={() => onSelect(w)}
                className="text-left rounded-lg border border-border bg-card p-4 hover:border-primary hover:shadow-sm transition-colors">
                <div className="flex items-center gap-2">
                  <BookText size={16} className="text-muted-foreground shrink-0" />
                  <span className="font-medium truncate text-foreground">{w.title}</span>
                </div>
                <div className="text-xs text-muted-foreground mt-2 tabular-nums">
                  {w.genre || "未定题材"} · {w.chapter_count ?? 0} 章 · {(w.word_count ?? 0).toLocaleString()} 字
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface Action { label: string; hint: string; run: () => void | Promise<unknown> }

function ShortcutsHelp({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  const rows: [string, string][] = [
    ["⌘K", "命令面板(全动作)"], ["⌘I", "捕获想象"], ["⌘⇧F", "专注模式"],
    ["⌘.", "取消 AI 生成(编辑器内)"], ["?", "本帮助"], ["Esc", "关闭弹层"],
    ["Enter", "提交输入框 / 捕获"], ["↑ ↓", "命令面板选择"],
  ];
  return (
    <div className="scrim" onClick={onClose} role="dialog" aria-modal="true" aria-label="快捷键帮助">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>快捷键</h3>
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "6px 14px", marginTop: 8 }}>
          {rows.map(([k, v]) => (
            <Fragment key={k}>
              <kbd className="kbd">{k}</kbd><span className="small">{v}</span>
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

function CommandPalette({ works, cur, actions, onClose, onSelectWork, onJump }: {
  works: Work[] | null; cur: Work | null; actions: Action[]; onClose: () => void;
  onSelectWork: (w: Work) => void; onJump: (seq: number) => void;
}) {
  const [q, setQ] = useState("");
  const [chs, setChs] = useState<Chapter[]>([]);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { ref.current?.focus(); if (cur) api.chapters(cur.id).then(setChs).catch(() => {}); }, [cur]);
  const items = useMemo(() => {
    const list: { label: string; hint: string; run: () => void }[] = [];
    actions.forEach((a) => list.push({ label: a.label, hint: a.hint, run: () => { a.run(); onClose(); } }));
    works?.forEach((w) => list.push({ label: `书 · ${w.title}`, hint: w.genre || "", run: () => onSelectWork(w) }));
    chs.forEach((c) => list.push({ label: `第 ${c.seq} 章 · ${c.title || "无题"}`, hint: "跳转", run: () => onJump(c.seq) }));
    const qq = q.trim().toLowerCase();
    return qq ? list.filter((i) => i.label.toLowerCase().includes(qq)) : list;
  }, [q, works, chs, cur, actions]);
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
