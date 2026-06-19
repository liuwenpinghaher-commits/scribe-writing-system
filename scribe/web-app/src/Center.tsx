import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Plus, Lightbulb } from "lucide-react";
import { api } from "./api";
import { Btn, State, useData, useToast } from "./common";
// P4-6:懒加载编辑器(Tiptap 是最大块),缩小首屏 bundle
const ChapterEditor = lazy(() => import("./Editor").then((m) => ({ default: m.ChapterEditor })));

export function Center({ work, title, rev, bump, currentSeq, setSeq }: {
  work: string; title: string; rev: number; bump: () => void;
  currentSeq: number | null; setSeq: (s: number | null) => void;
}) {
  return (
    <>
      <OptionSetPanel work={work} rev={rev} bump={bump} />
      <NorthStar work={work} rev={rev} />
      <Imagination work={work} rev={rev} bump={bump} />
      <Chapters work={work} rev={rev} bump={bump} currentSeq={currentSeq} setSeq={setSeq} />
      {currentSeq != null && (
        <div style={{ marginTop: 14, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <Suspense fallback={<div className="empty">加载编辑器…</div>}>
            <ChapterEditor work={work} seq={currentSeq} rev={rev} bump={bump} />
          </Suspense>
        </div>
      )}
      <span className="muted small" hidden>{title}</span>
    </>
  );
}

// P1-2:OptionSet 中央区决策 + 差异矩阵(决策是当前主工作,而非右栏小列表)
function OptionGen({ work, onDone }: { work: string; onDone: () => void }) {
  const [dp, setDp] = useState("");
  const toast = useToast();
  const gen = async () => {
    if (!dp.trim()) return;
    await api.generateOptions(work, dp.trim()); setDp(""); toast("主编已出方案"); onDone();
  };
  return (
    <div className="row" style={{ marginBottom: 10 }}>
      <input aria-label="让主编出方案的决策点" value={dp} placeholder="遇到岔路?写下决策点,让主编出几个差异方案…"
        onChange={(e) => setDp(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") gen(); }} />
      <Btn onClick={gen} variant="ghost">出方案</Btn>
    </div>
  );
}

function OptionSetPanel({ work, rev, bump }: { work: string; rev: number; bump: () => void }) {
  const { data, loading, error, reload } = useData(() => api.optionSets(work), [work, rev]);
  const toast = useToast();
  if (loading || error) return null;
  if (!data?.length) return <OptionGen work={work} onDone={() => { reload(); bump(); }} />; // 无待决时给生成入口
  const MATRIX: [string, string][] = [
    ["emotional_direction", "情感走向"], ["character_cost", "人物代价"], ["plot_consequence", "情节后果"],
  ];
  const choose = async (oid: string, opt: string) => {
    await api.choose(work, oid, opt); toast("已选方案(已记入你的品味)"); reload(); bump();
  };
  return (
    <div className="card" style={{ borderColor: "var(--accent)", marginBottom: 14 }}>
      <h3 style={{ color: "var(--accent)", marginTop: 0 }}>⌖ 待你定夺的方案(决策不由 AI 拍板)</h3>
      {data.map((s) => {
        let dp = ""; let opts: Record<string, unknown>[] = [];
        try { dp = JSON.parse(s.decision_point).text || ""; } catch { /* */ }
        try { opts = JSON.parse(s.options); } catch { /* */ }
        return (
          <div key={s.id} style={{ marginBottom: 8 }}>
            <div className="muted small">{dp}</div>
            <div className="sxs" style={{ gridTemplateColumns: `repeat(${Math.min(opts.length, 3)}, 1fr)` }}>
              {opts.map((o, i) => {
                const oid = o.id != null ? String(o.id) : String(i);
                return (
                  <div key={oid} className="card" style={{ margin: 0 }}>
                    <div className="t">{String(o.approach || o.label || "方案 " + oid)}</div>
                    {typeof o.tradeoff === "string" && <div className="muted small">代价:{o.tradeoff}</div>}
                    {MATRIX.filter(([k]) => o[k]).map(([k, label]) => (
                      <div key={k} className="small"><span className="muted">{label}:</span> {String(o[k])}</div>
                    ))}
                    <Btn onClick={() => choose(s.id, oid)} className="sm" >选这个</Btn>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// P2-3:北极星 sticky 常驻条(任意滚动可见)+ 折叠编辑;未设定=橙色提示
// 北极星常驻条 52px · 4 态(工程2b §11.2)
function NorthStar({ work, rev }: { work: string; rev: number }) {
  const { data, reload } = useData(() => api.intent(work), [work, rev]);
  const [editing, setEditing] = useState(false);
  const [rf, setRf] = useState(""); const [arc, setArc] = useState("");
  const [dnb, setDnb] = useState(""); const [dirty, setDirty] = useState(false);
  const toast = useToast();
  let redCount = 0; try { redCount = JSON.parse(data?.do_not_betray || "[]").length; } catch { /* */ }
  useEffect(() => {
    if (!data) return;
    setRf(data.reader_feeling || ""); setArc(data.core_emotional_arc || "");
    let list: string[] = []; try { list = JSON.parse(data.do_not_betray || "[]"); } catch { /* */ }
    setDnb(list.join("，")); setDirty(false);
  }, [data]);
  const save = async () => {
    await api.saveIntent(work, rf, dnb.split(/[，,]/).map((s) => s.trim()).filter(Boolean), arc);
    setDirty(false); setEditing(false); toast("北极星已保存"); reload();
  };
  const unset = !data?.reader_feeling;
  const feeling = data?.reader_feeling || "";
  return (
    <div className={"ns-bar " + (unset ? "unset" : "aligned")}>
      <div className="row end" style={{ justifyContent: "space-between" }}>
        <div style={{ overflow: "hidden", flex: 1, minWidth: 0 }}>
          <span className="ns-star" style={{ marginRight: 6 }}>★ 北极星</span>
          {unset ? (
            <span className="small" style={{ color: "var(--warn)" }}>尚未设定 —— 没有北极星,AI 会走向均值</span>
          ) : (
            <span className="small" title={feeling}>「{feeling.length > 40 ? feeling.slice(0, 40) + "…" : feeling}」</span>
          )}
          {data?.core_emotional_arc && <span className="muted small" style={{ marginLeft: 8 }}>弧:{data.core_emotional_arc.slice(0, 24)}</span>}
          {redCount > 0 && <span className="badge" style={{ marginLeft: 6 }}>红线 ×{redCount}</span>}
          {!unset && <span className="small" style={{ color: "var(--ok)", marginLeft: 6 }}>· ✓ 对齐</span>}
          {dirty && <span className="muted small">（未保存）</span>}
        </div>
        <Btn onClick={() => setEditing((v) => !v)} variant="ghost" className="sm">{editing ? "收起" : unset ? "立即设定 →" : "编辑北极星"}</Btn>
      </div>
      {editing && (
        <div style={{ marginTop: 8 }}>
          <div className="field">
            <label htmlFor="rf">这本书要让读者合上书时感受到什么?</label>
            <textarea id="rf" rows={2} value={rf} placeholder="例:温热的孤独感——被爱过,但爱本身短暂"
              onChange={(e) => { setRf(e.target.value); setDirty(true); }} />
          </div>
          <div className="field">
            <label htmlFor="arc">主角情感弧线(从…到…)</label>
            <input id="arc" value={arc} placeholder="例:从麻木到在意到失去到接受"
              onChange={(e) => { setArc(e.target.value); setDirty(true); }} />
          </div>
          <div className="field">
            <label htmlFor="dnb">绝不背叛的红线(逗号分隔)</label>
            <input id="dnb" value={dnb} placeholder="例:主角不能在未付出代价下成功"
              onChange={(e) => { setDnb(e.target.value); setDirty(true); }} />
          </div>
          <Btn onClick={save} disabled={!dirty}>保存北极星</Btn>
        </div>
      )}
    </div>
  );
}

function Imagination({ work, rev, bump }: { work: string; rev: number; bump: () => void }) {
  const { data } = useData(() => api.imaginations(work), [work, rev]);
  const [t, setT] = useState(""); const toast = useToast();
  const capture = async () => {
    if (!t.trim()) return;
    await api.capture(work, t.trim()); setT(""); toast("想象已存"); bump();
  };
  const recent = (data ?? []).slice(-3).map((x) => x.raw_text.slice(0, 16));
  return (
    <div className="field">
      <label htmlFor="imag"><Lightbulb size={13} style={{ verticalAlign: -2 }} /> 随手抛个想象(Enter 捕获)</label>
      <div className="row">
        <input id="imag" value={t} placeholder="例:我想要一场雨夜的背叛"
          onChange={(e) => setT(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") capture(); }} />
        <Btn onClick={capture} variant="ghost">存</Btn>
      </div>
      {recent.length > 0 && <div className="muted small">想象 {data?.length} 条:{recent.map((r) => `「${r}」`).join(" ")}</div>}
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
  const warnBySeq: Record<number, number> = {};  // §2.3 ⚠N 角标:按章聚合未决一致性问题
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
          <input aria-label="新卷标题" value={vtitle} placeholder="新卷…" style={{ width: 90 }}
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
  // 少量章节不必虚拟化(也避免固定高度浪费空间)
  if (chapters.length <= 30) {
    return (<>{chapters.map((c) => (
      <button key={c.seq} className={"card clickable" + (currentSeq === c.seq ? " active" : "")}
        aria-current={currentSeq === c.seq} onClick={() => setSeq(currentSeq === c.seq ? null : c.seq)}>
        第 {c.seq} 章 · {c.title || "（无题）"} <span className="badge">{c.status}</span>
      </button>))}</>);
  }
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
