import { useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Plus, Lightbulb } from "lucide-react";
import { api } from "./api";
import { Btn, State, useData, useToast } from "./common";

// 左栏 Navigator(Scrivener binder):卷/章大纲树 + 想象捕获页脚。
// P0 重构:章节树从中栏搬到左栏,中栏腾给编辑器。
export function Navigator({ work, rev, bump, currentSeq, setSeq }: {
  work: string; rev: number; bump: () => void;
  currentSeq: number | null; setSeq: (s: number | null) => void;
}) {
  return (
    <div className="binder" style={{ marginTop: 14, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
      <Chapters work={work} rev={rev} bump={bump} currentSeq={currentSeq} setSeq={setSeq} />
      <ImaginationFooter work={work} rev={rev} bump={bump} />
    </div>
  );
}

function Chapters({ work, rev, bump, currentSeq, setSeq }: {
  work: string; rev: number; bump: () => void; currentSeq: number | null; setSeq: (s: number | null) => void;
}) {
  const ch = useData(() => api.chapters(work), [work, rev]);
  const vol = useData(() => api.volumes(work), [work, rev]);
  const fl = useData(() => api.flags(work), [work, rev]);
  const [title, setTitle] = useState("");
  const [vtitle, setVtitle] = useState("");
  const chapters = ch.data ?? [];
  const volumes = vol.data ?? [];
  const warnBySeq: Record<number, number> = {};  // ⚠N 角标:按章聚合未决一致性问题
  for (const f of fl.data ?? []) { const s = (f as { chapter_seq?: number }).chapter_seq; if (s != null) warnBySeq[s] = (warnBySeq[s] || 0) + 1; }
  const maxSeq = chapters.reduce((m, c) => Math.max(m, c.seq), 0);
  const maxVol = volumes.reduce((m, v) => Math.max(m, v.seq), 0);

  const addVolume = async () => { await api.createVolume(work, maxVol + 1, vtitle.trim()); setVtitle(""); vol.reload(); };
  const addChapter = async (volume_id?: string) => {
    await api.addChapter(work, maxSeq + 1, title.trim(), volume_id); setTitle(""); bump();
  };

  // 分组:每卷的章 + 未分卷
  const byVol = (vid: string | null) => chapters.filter((c) => (c.volume_id ?? null) === vid);
  const unassigned = byVol(null);

  return (
    <>
      <div className="row end" style={{ justifyContent: "space-between" }}>
        <h3 style={{ margin: 0 }}>大纲树</h3>
        <div className="row">
          <input aria-label="新卷标题" value={vtitle} placeholder="新卷…" style={{ width: 80 }}
            onChange={(e) => setVtitle(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") addVolume(); }} />
          <Btn onClick={addVolume} variant="ghost" className="sm">+卷</Btn>
        </div>
      </div>
      <div className="row" style={{ marginBottom: 6 }}>
        <input aria-label="新章标题" value={title} placeholder="新章标题…"
          onChange={(e) => setTitle(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") addChapter(volumes[volumes.length - 1]?.id); }} />
        <Btn onClick={() => addChapter(volumes[volumes.length - 1]?.id)} variant="ghost"><Plus size={15} /> 加章</Btn>
      </div>
      <State loading={ch.loading || vol.loading} error={ch.error || vol.error}
        empty={!chapters.length && !volumes.length} emptyText="还没有卷/章。先 +卷,再加章。" onRetry={() => { ch.reload(); vol.reload(); }}>
        {volumes.map((v) => (
          <div key={v.id} style={{ marginBottom: 8 }}>
            <div className="muted small" style={{ fontWeight: 600, margin: "6px 0 2px" }}>
              第 {v.seq} 卷 · {v.title || "(无题)"} <span className="badge">{byVol(v.id).length} 章</span>
            </div>
            <ChapterList chapters={byVol(v.id)} currentSeq={currentSeq} setSeq={setSeq} work={work} bump={bump} warn={warnBySeq} />
          </div>
        ))}
        {unassigned.length > 0 && (
          <div>
            {volumes.length > 0 && <div className="muted small" style={{ fontWeight: 600, margin: "6px 0 2px" }}>未分卷</div>}
            <ChapterList chapters={unassigned} currentSeq={currentSeq} setSeq={setSeq} work={work} bump={bump} warn={warnBySeq} />
          </div>
        )}
      </State>
    </>
  );
}

const _SD: Record<string, string> = { done: "sd-done", revising: "sd-reviewing", draft: "sd-draft" };

function ChapterList({ chapters, currentSeq, setSeq, work, bump, warn }: {
  chapters: { seq: number; title?: string; status: string }[];
  currentSeq: number | null; setSeq: (s: number | null) => void; work: string; bump: () => void;
  warn: Record<number, number>;
}) {
  if (chapters.length > 30) return <VirtualChapters chapters={chapters} currentSeq={currentSeq} setSeq={setSeq} />;
  const move = async (seq: number, dir: "up" | "down") => { await api.moveChapter(work, seq, dir); bump(); };
  return (<>{chapters.map((c, i) => (
    <div key={c.seq} className="row" style={{ gap: 2, alignItems: "center" }}>
      <button className={"ch-row" + (currentSeq === c.seq ? " active" : "")}
        aria-current={currentSeq === c.seq} onClick={() => setSeq(currentSeq === c.seq ? null : c.seq)}>
        <span className={"status-dot " + (_SD[c.status] || "sd-planned")} aria-hidden />
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>第 {c.seq} 章 · {c.title || "无题"}</span>
        <span className="chips">
          {warn[c.seq] ? <span className="chip warn" title="一致性问题">⚠{warn[c.seq]}</span> : null}
        </span>
      </button>
      <button className="ghost sm" aria-label={`上移第${c.seq}章`} title="上移" disabled={i === 0} onClick={() => move(c.seq, "up")} style={{ padding: "2px 6px", minHeight: 24 }}>▲</button>
      <button className="ghost sm" aria-label={`下移第${c.seq}章`} title="下移" disabled={i === chapters.length - 1} onClick={() => move(c.seq, "down")} style={{ padding: "2px 6px", minHeight: 24 }}>▼</button>
    </div>))}</>);
}

function VirtualChapters({ chapters, currentSeq, setSeq }: {
  chapters: { seq: number; title?: string; status: string }[];
  currentSeq: number | null; setSeq: (s: number | null) => void;
}) {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowH = 50;
  const v = useVirtualizer({
    count: chapters.length, getScrollElement: () => parentRef.current, estimateSize: () => rowH, overscan: 8,
  });
  return (
    <div ref={parentRef} style={{ maxHeight: "45vh", overflow: "auto" }}>
      <div style={{ height: v.getTotalSize(), position: "relative" }}>
        {v.getVirtualItems().map((vi) => {
          const c = chapters[vi.index];
          return (
            <button key={c.seq} className={"card clickable" + (currentSeq === c.seq ? " active" : "")}
              aria-current={currentSeq === c.seq} onClick={() => setSeq(currentSeq === c.seq ? null : c.seq)}
              style={{ position: "absolute", top: 0, left: 0, width: "100%",
                transform: `translateY(${vi.start}px)`, height: rowH - 8, marginBottom: 0 }}>
              第 {c.seq} 章 · {c.title || "（无题）"} <span className="badge">{c.status}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// 想象捕获:每本书的灵感源头。从中栏挪到左栏页脚(⌘I 仍可全局唤起模态)。
function ImaginationFooter({ work, rev, bump }: { work: string; rev: number; bump: () => void }) {
  const { data, reload } = useData(() => api.imaginations(work), [work, rev]);
  const [t, setT] = useState(""); const toast = useToast();
  const capture = async () => {
    if (!t.trim()) return;
    await api.capture(work, t.trim()); setT(""); toast("想象已存"); bump(); reload();
  };
  const mark = async (iid: string, status: "used" | "obsolete") => {
    await api.setImagStatus(work, iid, status);
    toast(status === "used" ? "已标记用过(不再注入)" : "已弃用"); reload();
  };
  const recent = (data ?? []).slice(-4).reverse();
  return (
    <div className="field" style={{ marginTop: 14, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
      <label htmlFor="imag"><Lightbulb size={13} style={{ verticalAlign: -2 }} /> 随手抛个想象(Enter · ⌘I)</label>
      <div className="row">
        <input id="imag" value={t} placeholder="例:一场雨夜的背叛"
          onChange={(e) => setT(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") capture(); }} />
        <Btn onClick={capture} variant="ghost" className="sm">存</Btn>
      </div>
      {recent.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div className="muted small" style={{ marginBottom: 2 }}>想象 {data?.length} 条</div>
          {recent.map((x) => (
            <div key={x.id} className="row end" style={{ justifyContent: "space-between", gap: 4, padding: "1px 0" }}>
              <span className="small" style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", opacity: x.status === "used" || x.status === "obsolete" ? 0.5 : 1 }}>
                「{x.raw_text.slice(0, 18)}」{x.status === "used" ? " ✓" : ""}
              </span>
              {x.status !== "used" && x.status !== "obsolete" && (
                <button className="ghost sm" title="标记用过" onClick={() => mark(x.id, "used")} style={{ padding: "1px 6px", minHeight: 22 }}>用了</button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
