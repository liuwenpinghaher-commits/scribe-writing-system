/**
 * ForeshadowTimeline.tsx — 承诺线时间线(Promise→Progress→Payoff)。
 * 复用关系图谱同款 ReactFlow 画布(平移/缩放/小地图),但**不用 ELK 自动布局**:
 * 承诺线是时间线,x 钉死在章节、y 钉死在线程。每条承诺=一个自绘 lane 节点
 * (埋●→强化·→回收★,开着的拖虚线┄,超期标红),底部承诺密度。点选可推进/回收/放弃+跳转。
 * 综合 Sanderson 承诺论 + Plottr 时间线泳道 + StoryLine 悬空告警 + Aeon 线索交织。
 */
import "@xyflow/react/dist/style.css";
import { useMemo, useState } from "react";
import { ReactFlow, Background, Controls, MiniMap, type Node, type NodeProps } from "@xyflow/react";
import { Plus, X } from "lucide-react";
import { api, type ForeshadowStatus } from "@/api";
import { useData, useToast } from "@/common";
import { Section } from "@/components/detail";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const TYPES = ["伏笔", "悬念", "契诃夫之枪", "红鲱鱼", "人物承诺"] as const;
const TYPE_COLOR: Record<string, string> = {
  伏笔: "#3f6b58", 悬念: "#b45309", 契诃夫之枪: "#7c3aed", 红鲱鱼: "#dc2626", 人物承诺: "#0e7490",
};
const colorOf = (t?: string) => TYPE_COLOR[t || "伏笔"] || "#3f6b58";

const GUT = 132, CHW = 34, ROW = 30, AXIS_H = 26;

// ── 章节轴 + 当前线节点(全宽自绘) ──
function AxisNode({ data }: NodeProps) {
  const { maxC, nowCh, w } = data as { maxC: number; nowCh: number; w: number };
  const x = (ch: number) => GUT + (ch - 1) * CHW;
  const step = maxC <= 12 ? 1 : maxC <= 30 ? 5 : 10;
  const ticks: number[] = [];
  for (let c = 1; c <= maxC; c += step) ticks.push(c);
  if (ticks[ticks.length - 1] !== maxC) ticks.push(maxC);
  return (
    <svg width={w} height={AXIS_H} style={{ display: "block" }}>
      {ticks.map((c) => (
        <text key={c} x={x(c)} y={16} fontSize={10} fill="var(--muted-foreground)" textAnchor="middle">{c}</text>
      ))}
      <text x={x(nowCh)} y={AXIS_H - 1} fontSize={9} fill={colorOf("伏笔")} textAnchor="middle">现在·{nowCh}</text>
    </svg>
  );
}

// ── 一条承诺线 lane(全宽自绘) ──
function LaneNode({ data }: NodeProps) {
  const { row, maxC, nowCh, w, sel } = data as { row: ForeshadowStatus; maxC: number; nowCh: number; w: number; sel: boolean };
  const x = (ch: number) => GUT + (Math.min(Math.max(ch, 1), maxC) - 1) * CHW;
  const y = ROW / 2;
  const c0 = row.chapter ?? 1;
  const paid = row.state === "paid";
  const aband = row.state === "abandoned";
  const endC = paid ? (row.payoff_chapter ?? c0) : nowCh;
  const col = colorOf(row.ftype);
  const lastProg = row.echoes?.length ? Math.max(...row.echoes) : c0;
  return (
    <svg width={w} height={ROW} style={{ display: "block", cursor: "pointer" }}>
      {sel && <rect x={0} y={0} width={w} height={ROW} fill="var(--accent)" opacity={0.08} rx={4} />}
      {/* 当前竖线(各 lane 拼成一条) */}
      <line x1={x(nowCh)} y1={0} x2={x(nowCh)} y2={ROW} stroke={colorOf("伏笔")} strokeWidth={1} strokeDasharray="2 3" opacity={0.35} />
      {/* 名称 */}
      <text x={6} y={y + 3} fontSize={11} fill={row.overdue ? "#dc2626" : "var(--foreground)"} fontWeight={sel ? 600 : 400}>
        {(row.summary || row.promise || "(未命名)").slice(0, 9)}{(row.summary || "").length > 9 ? "…" : ""}
      </text>
      {/* 线 */}
      <line x1={x(c0)} y1={y} x2={x(endC)} y2={y} stroke={aband ? "var(--muted-foreground)" : col}
        strokeWidth={2} strokeDasharray={paid || aband ? undefined : "1 4"} opacity={aband ? 0.4 : paid ? 0.9 : 0.7} />
      {row.overdue && <line x1={x(lastProg)} y1={y} x2={x(nowCh)} y2={y} stroke="#dc2626" strokeWidth={2} strokeDasharray="1 4" />}
      {/* 埋 ● / 强化 · / 回收 ★ / 放弃 ✕ */}
      <circle cx={x(c0)} cy={y} r={4} fill={col} />
      {(row.echoes ?? []).map((e) => <circle key={e} cx={x(e)} cy={y} r={2.5} fill={col} opacity={0.85} />)}
      {paid && <text x={x(row.payoff_chapter ?? endC)} y={y + 4.5} fontSize={13} fill={col} textAnchor="middle">★</text>}
      {aband && <text x={x(endC)} y={y + 4} fontSize={11} fill="var(--muted-foreground)" textAnchor="middle">✕</text>}
      {row.overdue && <text x={x(nowCh) + 7} y={y + 3} fontSize={9} fill="#dc2626">超期</text>}
    </svg>
  );
}

// ── 承诺密度条(全宽自绘) ──
function DensityNode({ data }: NodeProps) {
  const { density, w } = data as { density: number[]; w: number };
  const maxDen = Math.max(1, ...density);
  const x = (ch: number) => GUT + (ch - 1) * CHW;
  return (
    <svg width={w} height={32} style={{ display: "block" }}>
      <text x={6} y={20} fontSize={9} fill="var(--muted-foreground)">密度</text>
      {density.map((d, i) => {
        const ch = i + 1; const bh = (d / maxDen) * 24;
        return <rect key={ch} x={x(ch) - CHW / 2 + 2} y={30 - bh} width={CHW - 4} height={bh}
          fill={d > 6 ? "#dc2626" : colorOf("伏笔")} opacity={d > 6 ? 0.5 : 0.28} />;
      })}
    </svg>
  );
}

const nodeTypes = { axis: AxisNode, lane: LaneNode, density: DensityNode };

export function ForeshadowTimeline({ work, rev }: { work: string; rev: number }) {
  const fs = useData(() => api.foreshadowsStatus(work), [work, rev]);
  const chs = useData(() => api.chapters(work), [work, rev]);
  const [sel, setSel] = useState<string | null>(null);
  const [opCh, setOpCh] = useState("");
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const toast = useToast();

  const rows = useMemo(() => fs.data ?? [], [fs.data]);
  const nowCh = Math.max(1, ...(chs.data ?? []).map((c) => c.seq || 0));
  const maxC = Math.max(nowCh, ...rows.flatMap((r) => [r.chapter ?? 0, r.payoff_chapter ?? 0, ...(r.echoes ?? [])]), 2);
  const opChN = Number(opCh) || nowCh;
  const w = GUT + maxC * CHW + 12;
  const density = useMemo(() => Array.from({ length: maxC }, (_, i) => {
    const ch = i + 1;
    return rows.filter((r) => r.state !== "abandoned" && (r.chapter ?? 1) <= ch
      && (r.state !== "paid" || (r.payoff_chapter ?? maxC) >= ch)).length;
  }), [rows, maxC]);

  const nodes: Node[] = useMemo(() => {
    const ns: Node[] = [{ id: "axis", type: "axis", position: { x: 0, y: 0 }, data: { maxC, nowCh, w }, draggable: false, selectable: false }];
    rows.forEach((r, i) => ns.push({
      id: r.id, type: "lane", position: { x: 0, y: AXIS_H + i * ROW },
      data: { row: r, maxC, nowCh, w, sel: sel === r.id }, draggable: false,
    }));
    ns.push({ id: "density", type: "density", position: { x: 0, y: AXIS_H + rows.length * ROW + 6 }, data: { density, maxC, w }, draggable: false, selectable: false });
    return ns;
  }, [rows, maxC, nowCh, w, density, sel]);

  const act = async (fn: () => Promise<unknown>, msg: string) => {
    setBusy(true);
    try { await fn(); toast(msg); fs.reload(); } catch (e) { toast(String(e)); } finally { setBusy(false); }
  };
  const selected = rows.find((r) => r.id === sel);
  const jump = (ch?: number | null) => { if (ch) location.hash = `#/work/${work}/ch/${ch}`; };

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* 图例 + 新建 */}
      <div className="flex items-center gap-3 flex-wrap text-[11px] text-muted-foreground px-4 py-2 border-b border-border shrink-0">
        <span>● 埋</span><span>· 强化</span><span>★ 回收</span><span className="opacity-60">┄ 悬空</span>
        <span className="w-px h-3 bg-border" />
        {TYPES.map((t) => <span key={t} className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: colorOf(t) }} />{t}</span>)}
        <Button size="sm" variant="outline" className="h-6 text-[11px] gap-1 ml-auto" onClick={() => setCreating((v) => !v)}><Plus size={12} />新建承诺线</Button>
      </div>

      {creating && <div className="px-4 pt-2 shrink-0"><CreateThread work={work} nowCh={nowCh} onDone={() => { setCreating(false); fs.reload(); }} /></div>}

      {/* 画布(复用 ReactFlow) */}
      <div className="flex-1 min-h-0 relative">
        {rows.length === 0 ? (
          <div className="text-sm text-muted-foreground py-10 text-center">还没有承诺线。给读者埋下第一个钩子吧。</div>
        ) : (
          <ReactFlow nodes={nodes} edges={[]} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.1 }}
            minZoom={0.3} maxZoom={2.5} nodesDraggable={false} nodesConnectable={false} proOptions={{ hideAttribution: true }}
            onNodeClick={(_, n) => { if (n.type === "lane") { setSel((s) => (s === n.id ? null : n.id)); setOpCh(String(nowCh)); } }}>
            <Background gap={CHW} />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable />
          </ReactFlow>
        )}
      </div>

      {/* 选中:承诺详情 + 操作 */}
      {selected && (
        <div className="px-4 pb-3 border-t border-border shrink-0 max-h-[40%] overflow-y-auto">
          <Section title={`${selected.ftype || "伏笔"} · ${selected.summary}`}>
            {selected.promise && <p className="text-sm text-foreground px-2 py-1">{selected.promise}</p>}
            <p className="text-[11px] text-muted-foreground px-2">
              埋第{selected.chapter}章{selected.echoes?.length ? ` · 强化 ${selected.echoes.join("/")}` : ""}
              {selected.payoff_chapter ? ` · 回收第${selected.payoff_chapter}章` : ` · ${selected.state}`}
              {selected.overdue ? " · ⚠ 超期未回收" : ""}
            </p>
            <div className="flex items-center gap-1.5 px-2 pt-1.5 flex-wrap">
              <span className="text-xs text-muted-foreground">操作章</span>
              <Input value={opCh} onChange={(e) => setOpCh(e.target.value)} className="h-7 w-14 text-xs" placeholder={String(nowCh)} />
              {selected.state !== "paid" && selected.state !== "abandoned" && <>
                <Button size="sm" variant="outline" className="h-7 text-xs" disabled={busy}
                  onClick={() => act(() => api.addForeshadowEcho(work, selected.id, opChN), "已记进展")}>在此推进</Button>
                <Button size="sm" className="h-7 text-xs" disabled={busy}
                  onClick={() => act(() => api.payoffForeshadow(work, selected.id, opChN), "已回收 ★")}>在此回收 ★</Button>
                <Button size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground" disabled={busy}
                  onClick={() => act(() => api.advanceForeshadow(work, selected.id, "abandon"), "已放弃")}>放弃</Button>
              </>}
              <Button size="sm" variant="ghost" className="h-7 text-xs ml-auto" onClick={() => jump(selected.chapter)}>跳到埋设章</Button>
              {selected.payoff_chapter && <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => jump(selected.payoff_chapter)}>跳到回收章</Button>}
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}

function CreateThread({ work, nowCh, onDone }: { work: string; nowCh: number; onDone: () => void }) {
  const [summary, setSummary] = useState("");
  const [promise, setPromise] = useState("");
  const [ftype, setFtype] = useState<string>("伏笔");
  const [ch, setCh] = useState(String(nowCh));
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const save = async () => {
    if (!summary.trim()) { toast("填承诺线简称"); return; }
    setBusy(true);
    try { await api.plantForeshadow(work, summary.trim(), Number(ch) || nowCh, { promise: promise.trim(), ftype }); toast("已埋设"); onDone(); }
    catch (e) { toast(String(e)); } finally { setBusy(false); }
  };
  return (
    <div className="rounded-lg border border-border p-2.5 flex flex-col gap-1.5 bg-muted/30">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground">新建承诺线</span>
        <button onClick={onDone} className="text-muted-foreground hover:text-foreground"><X size={13} /></button>
      </div>
      <Input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="简称(泳道名,如:渡叔的左眼)" className="h-7 text-xs" />
      <Input value={promise} onChange={(e) => setPromise(e.target.value)} placeholder="对读者的承诺(如:左眼藏着四十年前的命案)" className="h-7 text-xs" />
      <div className="flex items-center gap-1.5 flex-wrap">
        {TYPES.map((t) => (
          <button key={t} onClick={() => setFtype(t)}
            className={`text-[11px] px-2 py-1 rounded-md border transition-colors ${ftype === t ? "text-white" : "text-muted-foreground border-border hover:border-foreground"}`}
            style={ftype === t ? { background: colorOf(t), borderColor: colorOf(t) } : undefined}>{t}</button>
        ))}
        <span className="text-xs text-muted-foreground ml-1">埋第</span>
        <Input value={ch} onChange={(e) => setCh(e.target.value)} className="h-7 w-12 text-xs" />
        <span className="text-xs text-muted-foreground">章</span>
        <Button size="sm" className="h-7 text-xs ml-auto" onClick={save} disabled={busy}>埋设</Button>
      </div>
    </div>
  );
}
