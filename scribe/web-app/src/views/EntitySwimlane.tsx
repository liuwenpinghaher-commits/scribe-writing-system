/**
 * EntitySwimlane.tsx — 统一线模型的「实体泳道」(Aeon Subway 范式)。
 * 所有实体(角色/设定/地点/阵营/物品/母题/伏笔)各一条 lane,横轴章节,节点(beats)标在线上:
 * ●引入 ·发展/复现 ★兑现/回收,开着的拖虚线;类型配色 + 筛选;顶部健康(久未推进/超期);点 lane 开详情。
 * 把伏笔时间线泛化到所有线——一个界面、类型当字段。复用 ReactFlow(同关系图谱画布)。
 */
import "@xyflow/react/dist/style.css";
import { useMemo, useState } from "react";
import { ReactFlow, Background, Controls, MiniMap, type Node, type NodeProps } from "@xyflow/react";
import { api, type CharacterT, type Setting, type Motif } from "@/api";
import { useData } from "@/common";

const GUT = 150, CHW = 30, ROW = 28, AXIS_H = 24;
const ENTITY_COLOR: Record<string, string> = {
  角色: "#e11d48", 设定: "#64748b", 地点: "#0e7490", 阵营: "#b45309", 物品: "#7c3aed",
  力量体系: "#9333ea", 母题: "#f59e0b", 伏笔: "#3f6b58", 悬念: "#b45309", 契诃夫之枪: "#7c3aed", 红鲱鱼: "#dc2626", 人物承诺: "#0e7490",
};
const colorOf = (t: string) => ENTITY_COLOR[t] || "#64748b";
const SETTING_TYPE = (t?: string) => {
  const m: Record<string, string> = { place: "地点", 地点: "地点", faction: "阵营", 阵营: "阵营", item: "物品", 物品: "物品", 力量体系: "力量体系" };
  return m[t || ""] || "设定";
};
const TYPE_TABS = ["全部", "角色", "设定", "地点", "阵营", "物品", "母题", "伏笔"] as const;

interface Mark { ch: number; sym: string }
interface Lane {
  key: string; etype: string; name: string; color: string;
  intro: number; end: number; open: boolean; overdue: boolean; marks: Mark[];
  click: () => void;
}

const KIND_SYM = (k: string) => (/(payoff|兑现|回收|use)/.test(k) ? "★" : /(plant|引入|intro)/.test(k) ? "●" : "·");

function LaneNode({ data }: NodeProps) {
  const { lane, nowCh, w, x } = data as { lane: Lane; maxC: number; nowCh: number; w: number; x: (c: number) => number };
  const y = ROW / 2;
  const end = lane.open ? nowCh : lane.end;
  return (
    <svg width={w} height={ROW} style={{ display: "block", cursor: "pointer" }}>
      <line x1={x(nowCh)} y1={0} x2={x(nowCh)} y2={ROW} stroke="#3f6b58" strokeWidth={1} strokeDasharray="2 3" opacity={0.3} />
      <text x={6} y={y + 3} fontSize={10} fill={lane.color} opacity={0.85}>{lane.etype}</text>
      <text x={42} y={y + 3} fontSize={11} fill={lane.overdue ? "#dc2626" : "var(--foreground)"}>
        {lane.name.slice(0, 6)}{lane.name.length > 6 ? "…" : ""}
      </text>
      <line x1={x(lane.intro)} y1={y} x2={x(Math.max(end, lane.intro))} y2={y} stroke={lane.color} strokeWidth={2}
        strokeDasharray={lane.open ? "1 4" : undefined} opacity={lane.open ? 0.6 : 0.85} />
      {lane.marks.map((m, i) => (
        m.sym === "★"
          ? <text key={i} x={x(m.ch)} y={y + 4.5} fontSize={12} fill={lane.color} textAnchor="middle">★</text>
          : <circle key={i} cx={x(m.ch)} cy={y} r={m.sym === "●" ? 4 : 2.5} fill={lane.color} opacity={m.sym === "●" ? 1 : 0.8} />
      ))}
      {lane.overdue && <text x={x(nowCh) + 6} y={y + 3} fontSize={9} fill="#dc2626">久未推进</text>}
      <rect x={0} y={0} width={w} height={ROW} fill="transparent" />
    </svg>
  );
}
function AxisNode({ data }: NodeProps) {
  const { maxC, w, x } = data as { maxC: number; w: number; x: (c: number) => number };
  const step = maxC <= 12 ? 1 : maxC <= 30 ? 5 : 10;
  const ticks: number[] = [];
  for (let c = 1; c <= maxC; c += step) ticks.push(c);
  return (
    <svg width={w} height={AXIS_H} style={{ display: "block" }}>
      {ticks.map((c) => <text key={c} x={x(c)} y={16} fontSize={10} fill="var(--muted-foreground)" textAnchor="middle">{c}</text>)}
    </svg>
  );
}
const nodeTypes = { lane: LaneNode, axis: AxisNode };

export function EntitySwimlane({ work, rev, onOpenEntity, onOpenForeshadow }: {
  work: string; rev: number;
  onOpenEntity: (kind: "character" | "setting" | "motif", entity: CharacterT | Setting | Motif) => void;
  onOpenForeshadow: (id: string) => void;
}) {
  const chars = useData(() => api.characters(work), [work, rev]);
  const sets = useData(() => api.settings(work), [work, rev]);
  const motifs = useData(() => api.motifs(work), [work, rev]);
  const fores = useData(() => api.foreshadowsStatus(work), [work, rev]);
  const beats = useData(() => api.entityBeats(work), [work, rev]);
  const chs = useData(() => api.chapters(work), [work, rev]);
  const health = useData(() => api.entityLinesHealth(work), [work, rev]);
  const [filter, setFilter] = useState<string>("全部");

  const nowCh = Math.max(1, ...(chs.data ?? []).map((c) => c.seq || 0));
  const overdueSet = new Set((health.data ?? []).filter((h) => h.overdue).map((h) => `${h.etype}:${h.entity}`));

  const lanes: Lane[] = useMemo(() => {
    const eb = beats.data ?? [];
    const beatsOf = (etype: string, name: string) => eb.filter((b) => b.etype === etype && b.entity === name);
    const out: Lane[] = [];
    const fromBeats = (etype: string, display: string, name: string, click: () => void) => {
      const bs = beatsOf(etype, name).sort((a, b) => a.chapter - b.chapter);
      const marks: Mark[] = bs.map((b) => ({ ch: b.chapter, sym: KIND_SYM(b.kind) }));
      const intro = bs.length ? bs[0].chapter : 1;
      const end = bs.length ? bs[bs.length - 1].chapter : intro;
      const resolved = bs.some((b) => /(payoff|兑现|回收|use)/.test(b.kind));
      out.push({ key: `${etype}:${name}`, etype: display, name, color: colorOf(display), intro, end,
        open: !resolved, overdue: overdueSet.has(`${etype}:${name}`), marks, click });
    };
    (chars.data ?? []).forEach((c) => fromBeats("character", "角色", c.name, () => onOpenEntity("character", c)));
    (motifs.data ?? []).forEach((m) => fromBeats("motif", "母题", m.name, () => onOpenEntity("motif", m)));
    (sets.data ?? []).forEach((s) => fromBeats("setting", SETTING_TYPE(s.type), s.name, () => onOpenEntity("setting", s)));
    (fores.data ?? []).forEach((f) => {
      const marks: Mark[] = [{ ch: f.chapter ?? 1, sym: "●" }, ...(f.echoes ?? []).map((e) => ({ ch: e, sym: "·" }))];
      if (f.payoff_chapter) marks.push({ ch: f.payoff_chapter, sym: "★" });
      out.push({ key: `foreshadow:${f.id}`, etype: f.ftype || "伏笔", name: f.summary || "(伏笔)", color: colorOf(f.ftype || "伏笔"),
        intro: f.chapter ?? 1, end: f.payoff_chapter ?? (f.chapter ?? 1), open: f.state !== "paid" && f.state !== "abandoned",
        overdue: !!f.overdue, marks, click: () => onOpenForeshadow(f.id) });
    });
    return out;
  }, [chars.data, sets.data, motifs.data, fores.data, beats.data, overdueSet, onOpenEntity, onOpenForeshadow]);

  const shown = filter === "全部" ? lanes : lanes.filter((l) => l.etype === filter || (filter === "设定" && l.etype === "力量体系"));
  const maxC = Math.max(nowCh, ...lanes.flatMap((l) => [l.intro, l.end, ...l.marks.map((m) => m.ch)]), 2);
  const w = GUT + maxC * CHW + 12;
  const x = (c: number) => GUT + (Math.min(Math.max(c, 1), maxC) - 1) * CHW;

  const nodes: Node[] = useMemo(() => {
    const ns: Node[] = [{ id: "axis", type: "axis", position: { x: 0, y: 0 }, data: { maxC, w, x }, draggable: false, selectable: false }];
    shown.forEach((l, i) => ns.push({ id: l.key, type: "lane", position: { x: 0, y: AXIS_H + i * ROW }, data: { lane: l, maxC, nowCh, w, x }, draggable: false }));
    return ns;
  }, [shown, maxC, nowCh, w]);

  const overdueN = lanes.filter((l) => l.overdue).length;
  const Chip = ({ t }: { t: string }) => (
    <button onClick={() => setFilter(t)}
      className={`text-[11px] px-2 py-0.5 rounded-md border transition-colors ${filter === t ? "bg-primary text-primary-foreground border-primary" : "text-muted-foreground border-border hover:border-foreground"}`}>{t}</button>
  );

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center gap-2 flex-wrap text-[11px] px-4 py-2 border-b border-border shrink-0">
        <span className="text-foreground font-medium">{lanes.length} 条线</span>
        {overdueN > 0 && <span style={{ color: "#dc2626" }}>· {overdueN} 久未推进</span>}
        <span className="w-px h-3 bg-border mx-1" />
        {TYPE_TABS.map((t) => <Chip key={t} t={t} />)}
        <span className="text-muted-foreground ml-auto opacity-70">●引入 ·发展/复现 ★兑现 · 点线开详情</span>
      </div>
      <div className="flex-1 min-h-0 relative">
        {shown.length === 0 ? (
          <div className="text-sm text-muted-foreground py-12 text-center">没有符合条件的线。</div>
        ) : (
          <ReactFlow nodes={nodes} edges={[]} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.1 }}
            minZoom={0.25} maxZoom={2.5} nodesDraggable={false} nodesConnectable={false} proOptions={{ hideAttribution: true }}
            onNodeClick={(_, n) => { const l = shown.find((x) => x.key === n.id); l?.click(); }}>
            <Background gap={CHW} />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
