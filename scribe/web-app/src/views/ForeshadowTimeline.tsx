/**
 * ForeshadowTimeline.tsx — 承诺线时间线(复用关系图谱同款 ReactFlow 画布,平移/缩放/小地图)。
 * 每条承诺=一条 lane(埋●→强化·→回收★,开着拖虚线┄,超期标红);顶部健康条+状态筛选;
 * 底部承诺密度;点 lane → 开「全页详情」(不再底部挤一条)。x 钉死章节、y 钉死线程,不用 ELK。
 */
import "@xyflow/react/dist/style.css";
import { useMemo, useState } from "react";
import { ReactFlow, Background, Controls, MiniMap, type Node, type NodeProps } from "@xyflow/react";
import { api, type ForeshadowStatus } from "@/api";
import { useData } from "@/common";
import { TYPES, colorOf } from "./foreshadowConst";

const GUT = 132, CHW = 34, ROW = 30, AXIS_H = 26;

function AxisNode({ data }: NodeProps) {
  const { maxC, nowCh, w } = data as { maxC: number; nowCh: number; w: number };
  const x = (ch: number) => GUT + (ch - 1) * CHW;
  const step = maxC <= 12 ? 1 : maxC <= 30 ? 5 : 10;
  const ticks: number[] = [];
  for (let c = 1; c <= maxC; c += step) ticks.push(c);
  if (ticks[ticks.length - 1] !== maxC) ticks.push(maxC);
  return (
    <svg width={w} height={AXIS_H} style={{ display: "block" }}>
      {ticks.map((c) => <text key={c} x={x(c)} y={16} fontSize={10} fill="var(--muted-foreground)" textAnchor="middle">{c}</text>)}
      <text x={x(nowCh)} y={AXIS_H - 1} fontSize={9} fill={colorOf("伏笔")} textAnchor="middle">现在·{nowCh}</text>
    </svg>
  );
}

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
      <line x1={x(nowCh)} y1={0} x2={x(nowCh)} y2={ROW} stroke={colorOf("伏笔")} strokeWidth={1} strokeDasharray="2 3" opacity={0.35} />
      <text x={6} y={y + 3} fontSize={11} fill={row.overdue ? "#dc2626" : "var(--foreground)"} fontWeight={sel ? 600 : 400}>
        {(row.summary || row.promise || "(未命名)").slice(0, 9)}{(row.summary || "").length > 9 ? "…" : ""}
      </text>
      <line x1={x(c0)} y1={y} x2={x(endC)} y2={y} stroke={aband ? "var(--muted-foreground)" : col}
        strokeWidth={2} strokeDasharray={paid || aband ? undefined : "1 4"} opacity={aband ? 0.4 : paid ? 0.9 : 0.7} />
      {row.overdue && <line x1={x(lastProg)} y1={y} x2={x(nowCh)} y2={y} stroke="#dc2626" strokeWidth={2} strokeDasharray="1 4" />}
      <circle cx={x(c0)} cy={y} r={4} fill={col} />
      {(row.echoes ?? []).map((e) => <circle key={e} cx={x(e)} cy={y} r={2.5} fill={col} opacity={0.85} />)}
      {paid && <text x={x(row.payoff_chapter ?? endC)} y={y + 4.5} fontSize={13} fill={col} textAnchor="middle">★</text>}
      {aband && <text x={x(endC)} y={y + 4} fontSize={11} fill="var(--muted-foreground)" textAnchor="middle">✕</text>}
      {row.overdue && <text x={x(nowCh) + 7} y={y + 3} fontSize={9} fill="#dc2626">超期</text>}
    </svg>
  );
}

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

export function ForeshadowTimeline({ work, rev, onOpen }: { work: string; rev: number; onOpen: (id: string) => void }) {
  const fs = useData(() => api.foreshadowsStatus(work), [work, rev]);
  const chs = useData(() => api.chapters(work), [work, rev]);
  const [filter, setFilter] = useState<"all" | "open" | "paid" | string>("all");

  const allRows = useMemo(() => fs.data ?? [], [fs.data]);
  const rows = useMemo(() => allRows.filter((r) => {
    if (filter === "all") return true;
    if (filter === "open") return r.state === "planted" || r.state === "triggered";
    if (filter === "paid") return r.state === "paid";
    return r.ftype === filter;       // 按类型
  }), [allRows, filter]);
  const nowCh = Math.max(1, ...(chs.data ?? []).map((c) => c.seq || 0));
  const maxC = Math.max(nowCh, ...rows.flatMap((r) => [r.chapter ?? 0, r.payoff_chapter ?? 0, ...(r.echoes ?? [])]), 2);
  const w = GUT + maxC * CHW + 12;
  const density = useMemo(() => Array.from({ length: maxC }, (_, i) => {
    const ch = i + 1;
    return rows.filter((r) => r.state !== "abandoned" && (r.chapter ?? 1) <= ch
      && (r.state !== "paid" || (r.payoff_chapter ?? maxC) >= ch)).length;
  }), [rows, maxC]);

  // 健康总览
  const openN = allRows.filter((r) => r.state === "planted" || r.state === "triggered").length;
  const overdueN = allRows.filter((r) => r.overdue).length;
  const herringN = allRows.filter((r) => r.ftype === "红鲱鱼" && !(r.beats ?? []).some((b) => b.kind === "twist" || b.kind === "misdirect")).length;

  const nodes: Node[] = useMemo(() => {
    const ns: Node[] = [{ id: "axis", type: "axis", position: { x: 0, y: 0 }, data: { maxC, nowCh, w }, draggable: false, selectable: false }];
    rows.forEach((r, i) => ns.push({
      id: r.id, type: "lane", position: { x: 0, y: AXIS_H + i * ROW },
      data: { row: r, maxC, nowCh, w, sel: false }, draggable: false,
    }));
    ns.push({ id: "density", type: "density", position: { x: 0, y: AXIS_H + rows.length * ROW + 6 }, data: { density, w }, draggable: false, selectable: false });
    return ns;
  }, [rows, maxC, nowCh, w, density]);

  const Chip = ({ k, label }: { k: string; label: string }) => (
    <button onClick={() => setFilter(k)}
      className={`text-[11px] px-2 py-0.5 rounded-md border transition-colors ${filter === k ? "bg-primary text-primary-foreground border-primary" : "text-muted-foreground border-border hover:border-foreground"}`}>{label}</button>
  );

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* 健康条 + 图例 */}
      <div className="flex items-center gap-2 flex-wrap text-[11px] px-4 py-2 border-b border-border shrink-0">
        <span className="text-foreground font-medium">{allRows.length} 条</span>
        <span className="text-muted-foreground">· {openN} 开着</span>
        {overdueN > 0 && <span style={{ color: "#dc2626" }}>· {overdueN} 超期</span>}
        {herringN > 0 && <span style={{ color: "#dc2626" }}>· {herringN} 红鲱鱼待澄清</span>}
        <span className="w-px h-3 bg-border mx-1" />
        <Chip k="all" label="全部" /><Chip k="open" label="开着" /><Chip k="paid" label="已回收" />
        {TYPES.map((t) => <Chip key={t} k={t} label={t} />)}
        <span className="text-muted-foreground ml-auto opacity-70">●埋 ·强化 ★回收 ┄悬空 · 点线看详情</span>
      </div>

      <div className="flex-1 min-h-0 relative">
        {rows.length === 0 ? (
          <div className="text-sm text-muted-foreground py-12 text-center">没有符合条件的承诺线。</div>
        ) : (
          <ReactFlow nodes={nodes} edges={[]} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.1 }}
            minZoom={0.3} maxZoom={2.5} nodesDraggable={false} nodesConnectable={false} proOptions={{ hideAttribution: true }}
            onNodeClick={(_, n) => { if (n.type === "lane") onOpen(n.id); }}>
            <Background gap={CHW} />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
