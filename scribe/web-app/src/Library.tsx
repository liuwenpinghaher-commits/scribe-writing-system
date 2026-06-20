import { useEffect, useMemo, useState } from "react";
import { Plus, Search, BookText, ChevronDown } from "lucide-react";
import { api } from "./api";
import type { Work } from "./api";
import { Btn, State } from "./common";

export function Library({ works, loading, error, reload, current, onSelect }: {
  works: Work[] | null; loading: boolean; error: string | null; reload: () => void;
  current: Work | null; onSelect: (w: Work) => void;
}) {
  const [title, setTitle] = useState("");
  const [q, setQ] = useState("");
  // binder:选中一本书后折叠作品库为切换器,垂直空间让给左栏大纲树。
  const [expanded, setExpanded] = useState(!current);
  useEffect(() => { setExpanded(!current); }, [current]);
  const create = async () => {
    if (!title.trim()) return;
    await api.createWork(title.trim()); setTitle(""); reload();
  };
  const select = (w: Work) => { onSelect(w); setExpanded(false); };
  const list = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return (works ?? []).filter((w) => !qq || (w.title + (w.genre || "")).toLowerCase().includes(qq));
  }, [works, q]);

  // 折叠态:仅显示当前书 + 展开按钮
  if (current && !expanded) {
    return (
      <div className="topbar">
        <span className="brand">SCRIBE</span>
        <button className="ghost sm work-switch" onClick={() => setExpanded(true)}
          aria-label="切换作品" title="切换作品" aria-expanded={false}>
          <BookText size={14} aria-hidden />
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{current.title}</span>
          <ChevronDown size={14} aria-hidden />
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="topbar">
        <span className="brand">SCRIBE</span>
        <h2 style={{ margin: 0 }}>作品库</h2>
      </div>
      <div className="search">
        <Search size={15} className="muted" aria-hidden />
        <input aria-label="搜索作品" value={q} placeholder="搜索作品…" onChange={(e) => setQ(e.target.value)} />
      </div>

      <State loading={loading} error={error} empty={!works?.length} emptyText="还没有作品,在下方新建" onRetry={reload}>
        <div className="lib-grid">
          {list.map((w) => {
            const words = w.word_count ?? 0;
            const pct = Math.min(100, Math.round((words / 100000) * 100)); // 进度参考(对 10 万字)
            return (
              <button key={w.id} className={"card clickable work-card" + (current?.id === w.id ? " active" : "")}
                aria-current={current?.id === w.id} onClick={() => select(w)}>
                <div className="row end" style={{ gap: 6 }}>
                  <BookText size={15} className="muted" aria-hidden />
                  <span className="t" style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{w.title}</span>
                </div>
                <div className="meta">{w.genre || "未定题材"} · {w.chapter_count ?? 0} 章 · {words.toLocaleString()} 字</div>
                <div className="progress" aria-label={`约 ${pct}%`}><i style={{ width: pct + "%" }} /></div>
                <div className="row" style={{ gap: 6, marginTop: "auto", flexWrap: "wrap" }}>
                  {!!w.new_insight_count && <span className="dot note">主编札记 {w.new_insight_count}</span>}
                  {!!w.pending_optionset_count && <span className="dot opt">待决方案 {w.pending_optionset_count}</span>}
                  {!w.new_insight_count && !w.pending_optionset_count && <span className="muted small">—</span>}
                </div>
              </button>
            );
          })}
        </div>
      </State>

      <div className="field" style={{ marginTop: 14 }}>
        <label htmlFor="newWork">新建作品</label>
        <div className="row">
          <input id="newWork" value={title} placeholder="书名…"
            onChange={(e) => setTitle(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") create(); }} />
          <Btn onClick={create}><Plus size={15} /> 建</Btn>
        </div>
      </div>
    </>
  );
}
