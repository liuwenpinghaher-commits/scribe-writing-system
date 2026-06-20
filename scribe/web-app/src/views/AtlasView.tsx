import "@xyflow/react/dist/style.css";
import { useEffect, useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeChange,
  type EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  MarkerType,
} from "@xyflow/react";
import ELK from "elkjs/lib/elk.bundled.js";
import { Network } from "lucide-react";
import { api, type Relation } from "@/api";
import { useData } from "@/common";
import { StateBoundary } from "@/components/StateBoundary";
import { Empty } from "@/components/Empty";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";

// ── 类型分类色板 ──
const TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  角色:    { bg: "#ffe4e6", border: "#fb7185", text: "#9f1239" },
  地点:    { bg: "#d1fae5", border: "#34d399", text: "#064e3b" },
  阵营:    { bg: "#fef3c7", border: "#fbbf24", text: "#78350f" },
  物品:    { bg: "#dbeafe", border: "#60a5fa", text: "#1e3a8a" },
  组织:    { bg: "#ede9fe", border: "#a78bfa", text: "#4c1d95" },
  概念:    { bg: "#f1f5f9", border: "#94a3b8", text: "#334155" },
  default: { bg: "#f8f9fa", border: "#adb5bd", text: "#343a40" },
};

function getTypeColor(type?: string) {
  if (!type) return TYPE_COLORS["default"];
  return TYPE_COLORS[type] ?? TYPE_COLORS["default"];
}

// ── ELK 实例 ──
const elk = new ELK();

// ── 从关系数据构建初始 nodes/edges ──
function buildGraph(relations: Relation[], upto: number | null) {
  // 过滤章节
  const filtered = upto == null
    ? relations
    : relations.filter((r) => r.valid_from_chapter == null || r.valid_from_chapter <= upto);

  // 收集所有实体（去重）
  const entityMap = new Map<string, { name: string; type?: string }>();
  filtered.forEach((r) => {
    if (!entityMap.has(r.src_entity)) entityMap.set(r.src_entity, { name: r.src_entity, type: r.src_type });
    if (!entityMap.has(r.dst_entity)) entityMap.set(r.dst_entity, { name: r.dst_entity, type: r.dst_type });
  });

  const nodes: Node[] = Array.from(entityMap.values()).map(({ name, type }) => {
    const color = getTypeColor(type);
    return {
      id: name,
      data: { label: name },
      position: { x: 0, y: 0 }, // ELK 会计算真实位置
      style: {
        background: color.bg,
        border: `1.5px solid ${color.border}`,
        color: color.text,
        borderRadius: 8,
        padding: "6px 12px",
        fontSize: 13,
        fontWeight: 500,
        minWidth: 80,
        textAlign: "center" as const,
      },
    };
  });

  const edges: Edge[] = filtered.map((r, i) => {
    const w = Math.max(1, Math.min(4, r.weight ?? 1));
    const isDirected = r.directed == null || r.directed === 1;
    return {
      id: r.id || `e-${i}`,
      source: r.src_entity,
      target: r.dst_entity,
      label: r.relation,
      animated: false,
      style: { strokeWidth: w },
      markerEnd: isDirected ? { type: MarkerType.ArrowClosed, width: 14, height: 14 } : undefined,
      labelStyle: { fontSize: 11, fill: "#64748b" },
      labelBgStyle: { fill: "#fff", fillOpacity: 0.85 },
    };
  });

  return { nodes, edges };
}

// ── ELK 布局 ──
async function layoutGraph(nodes: Node[], edges: Edge[]): Promise<{ nodes: Node[]; edges: Edge[] }> {
  if (nodes.length === 0) return { nodes, edges };

  const elkGraph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "60",
      "elk.layered.spacing.nodeNodeBetweenLayers": "80",
    },
    children: nodes.map((n) => ({ id: n.id, width: 120, height: 40 })),
    edges: edges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  };

  try {
    const result = await elk.layout(elkGraph);
    const positioned = (result.children ?? []).map((n) => {
      const orig = nodes.find((x) => x.id === n.id);
      return { ...orig!, position: { x: n.x ?? 0, y: n.y ?? 0 } };
    });
    return { nodes: positioned, edges };
  } catch {
    return { nodes, edges };
  }
}

// ── 主组件 ──
export function AtlasView({ work }: { work: string }) {
  const { data, loading, error, reload } = useData(() => api.relations(work), [work]);
  const [upto, setUpto] = useState<number | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [layoutDone, setLayoutDone] = useState(false);

  // 当数据或过滤条件变化时重新构建并布局
  useEffect(() => {
    if (!data) return;
    const { nodes: rawNodes, edges: rawEdges } = buildGraph(data, upto);
    setLayoutDone(false);
    layoutGraph(rawNodes, rawEdges).then(({ nodes: ln, edges: le }) => {
      setNodes(ln);
      setEdges(le);
      setLayoutDone(true);
    });
  }, [data, upto]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await api.analyzeWork(work);
      reload();
    } finally {
      setAnalyzing(false);
    }
  };

  // 获取最大章节号用于 Select 选项
  const maxChapter = data
    ? Math.max(0, ...data.map((r) => r.valid_from_chapter ?? 0))
    : 0;

  const isEmpty = !loading && !error && (data == null || data.length === 0);

  return (
    <div className="h-full w-full flex flex-col">
      {/* 顶部工具条 */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-background/80 shrink-0">
        <span className="text-sm font-medium text-foreground">关系图谱</span>
        <div className="flex-1" />
        {maxChapter > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">显示到第</span>
            <Select
              value={upto == null ? "all" : String(upto)}
              onValueChange={(v) => setUpto(v === "all" ? null : Number(v))}
            >
              <SelectTrigger className="h-7 w-24 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部章节</SelectItem>
                {Array.from({ length: maxChapter }, (_, i) => i + 1).map((ch) => (
                  <SelectItem key={ch} value={String(ch)}>
                    第 {ch} 章
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="text-xs text-muted-foreground">章</span>
          </div>
        )}
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          disabled={analyzing}
          onClick={handleAnalyze}
        >
          {analyzing ? "分析中…" : "重新分析全书"}
        </Button>
      </div>

      {/* 内容区 */}
      <div className="flex-1 min-h-0" style={{ position: "relative" }}>
        <StateBoundary
          loading={loading}
          error={error}
          empty={isEmpty}
          onRetry={reload}
          emptyNode={
            <Empty
              icon={<Network />}
              title="还没有实体关系"
              hint="点下方分析全书，让主编从已写章节抽取人物/地点/关系"
              action={{ label: analyzing ? "分析中…" : "分析全书", onClick: handleAnalyze }}
            />
          }
        >
          <div style={{ position: "absolute", inset: 0 }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              fitView={layoutDone}
              fitViewOptions={{ padding: 0.2 }}
              minZoom={0.2}
              maxZoom={2}
            >
              <Background />
              <Controls />
              <MiniMap zoomable pannable />
            </ReactFlow>
          </div>
        </StateBoundary>
      </div>
    </div>
  );
}
