import { lazy, Suspense, useEffect, useState } from "react";
import { BookText } from "lucide-react";
import { api } from "./api";
import { Btn, useData, useToast } from "./common";
// P4-6:懒加载编辑器(Tiptap 是最大块),缩小首屏 bundle
const ChapterEditor = lazy(() => import("./Editor").then((m) => ({ default: m.ChapterEditor })));

// 中栏 = 专注圣地。P0 重构后只保留:决策卡(按需浮现)→ 北极星条 → 编辑器。
// 大纲树/想象已迁至左栏 Navigator,中栏不再纵向堆叠导航。
export function Center({ work, title, rev, bump, currentSeq }: {
  work: string; title: string; rev: number; bump: () => void;
  currentSeq: number | null;
}) {
  return (
    <>
      <OptionSetPanel work={work} rev={rev} bump={bump} />
      <NorthStar work={work} rev={rev} />
      {currentSeq != null ? (
        <div style={{ marginTop: 14, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <Suspense fallback={<div className="empty">加载编辑器…</div>}>
            <ChapterEditor work={work} seq={currentSeq} rev={rev} bump={bump} />
          </Suspense>
        </div>
      ) : (
        <div className="empty" style={{ paddingTop: 48 }}>
          <BookText size={26} />
          <div style={{ marginTop: 8 }}>从左侧大纲树选择章节开始写作</div>
          <div className="muted small" style={{ marginTop: 4 }}>没有章节?在左栏「加章」,或按 ⌘K 打开命令面板</div>
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
