import { useState, useMemo, useEffect } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Library,
  User,
  MapPin,
  Bookmark,
  Flame,
  FileText,
  Plus,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  Loader2,
  Sparkles,
  MessageSquareQuote,
} from "lucide-react";
import { api } from "@/api";
import type { CharacterT, Setting, Foreshadow, Material, CharState, Motif, ForeshadowStatus } from "@/api";
import { EntityEditor, type EntityKind } from "./EntityEditor";
import { CodexChat } from "./CodexChat";
import { ExtractPanel } from "./ExtractPanel";
import { useData } from "@/common";
import { StateBoundary } from "@/components/StateBoundary";
import { Empty } from "@/components/Empty";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// ── 工具函数 ──

/** 安全解析 JSON 字符串，失败返回 null */
function tryParseJson(s?: string): Record<string, unknown> | null {
  if (!s) return null;
  try {
    const v = JSON.parse(s);
    if (typeof v === "object" && v !== null && !Array.isArray(v)) return v as Record<string, unknown>;
    return null;
  } catch {
    return null;
  }
}

/** 截断超长文本 */
function truncate(s?: string, max = 60): string {
  if (!s) return "—";
  return s.length > max ? s.slice(0, max) + "…" : s;
}

/** 提取 content 字段的 description */
function extractDesc(content?: string): string {
  const obj = tryParseJson(content);
  if (obj) {
    const desc = obj.description ?? obj.desc ?? obj.state ?? obj.summary;
    if (typeof desc === "string") return truncate(desc);
    return truncate(JSON.stringify(obj));
  }
  return truncate(content);
}

/** 设定类型中文映射 */
const SETTING_TYPE_MAP: Record<string, string> = {
  item: "物品",
  location: "地点",
  organization: "组织",
  concept: "概念",
  worldbuilding: "世界观",
};
function mapSettingType(t?: string): string {
  if (!t) return "—";
  return SETTING_TYPE_MAP[t] ?? t;
}

/** 伏笔状态 Badge 颜色 */
function foreshadowBadgeVariant(state: string): "default" | "secondary" | "destructive" | "outline" {
  if (state === "planted") return "secondary";
  if (state === "triggered" || state === "paid") return "default";
  if (state === "abandoned") return "destructive";
  return "outline";
}

const FORESHADOW_STATE_LABEL: Record<string, string> = {
  planted: "已埋下",
  triggered: "已触发",
  paid: "已回收",
  abandoned: "已放弃",
};

// ── 排序图标 ──
function SortIcon({ direction }: { direction: "asc" | "desc" | false }) {
  if (!direction) return <ArrowUpDown size={14} className="ml-1 text-muted-foreground opacity-60" />;
  if (direction === "asc") return <ArrowUp size={14} className="ml-1 text-primary" />;
  return <ArrowDown size={14} className="ml-1 text-primary" />;
}

// ── 通用 DataTable ──
function DataTable<T>({
  columns,
  data,
  globalFilter,
  onGlobalFilterChange,
}: {
  columns: ColumnDef<T>[];
  data: T[];
  globalFilter: string;
  onGlobalFilterChange: (v: string) => void;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    globalFilterFn: "includesString",
  });

  return (
    <div className="flex flex-col gap-2">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((hg) => (
            <TableRow key={hg.id} className="hover:bg-transparent border-border">
              {hg.headers.map((header) => (
                <TableHead key={header.id} className="text-xs font-semibold text-muted-foreground px-3 py-2">
                  {header.isPlaceholder ? null : (
                    <button
                      className={
                        header.column.getCanSort()
                          ? "flex items-center cursor-pointer select-none hover:text-foreground transition-colors"
                          : "flex items-center"
                      }
                      onClick={header.column.getCanSort() ? header.column.getToggleSortingHandler() : undefined}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && (
                        <SortIcon direction={header.column.getIsSorted()} />
                      )}
                    </button>
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={columns.length}
                className="text-center py-8 text-xs text-muted-foreground"
              >
                {globalFilter ? "没有匹配的结果" : "暂无数据"}
              </TableCell>
            </TableRow>
          ) : (
            table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} className="border-border">
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id} className="px-3 py-2 text-sm">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}

// ── 角色状态轨迹 Dialog ──
function CharStatesDialog({
  work,
  charName,
  open,
  onClose,
}: {
  work: string;
  charName: string;
  open: boolean;
  onClose: () => void;
}) {
  const { data, loading, error } = useData(
    () => (open ? api.charStates(work, charName) : Promise.resolve([] as CharState[])),
    [work, charName, open]
  );

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="max-w-lg max-h-[70vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-base flex items-center gap-2">
            <User size={16} className="text-primary" />
            {charName} · 状态轨迹
          </DialogTitle>
        </DialogHeader>
        <StateBoundary loading={loading} error={error} empty={!loading && !error && (!data || data.length === 0)}
          emptyNode={<p className="text-xs text-muted-foreground py-4 text-center">暂无状态记录</p>}
        >
          <div className="space-y-2 mt-2">
            {data?.map((s) => (
              <div key={s.id} className="flex gap-3 items-start rounded-lg border border-border px-3 py-2.5">
                <div className="shrink-0 mt-0.5">
                  <span className="text-xs font-medium text-muted-foreground tabular-nums">第{s.chapter_seq}章</span>
                </div>
                <div className="flex-1 min-w-0">
                  {s.change_type && (
                    <Badge variant="outline" className="text-[10px] mb-1">{s.change_type}</Badge>
                  )}
                  <p className="text-xs text-foreground leading-relaxed">{s.state_desc || "—"}</p>
                </div>
              </div>
            ))}
          </div>
        </StateBoundary>
      </DialogContent>
    </Dialog>
  );
}

// ── 角色 Tab ──
function CharactersTab({ work, rev = 0, onEdit }: { work: string; rev?: number; onEdit?: (e?: CharacterT) => void }) {
  const { data, loading, error, reload } = useData(() => api.characters(work), [work, rev]);
  const [filter, setFilter] = useState("");
  const [addName, setAddName] = useState("");
  const [addMotivation, setAddMotivation] = useState("");
  const [addVoice, setAddVoice] = useState("");
  const [addSamples, setAddSamples] = useState("");
  const [addContradiction, setAddContradiction] = useState("");
  const [addWound, setAddWound] = useState("");
  const [more, setMore] = useState(false);
  const [adding, setAdding] = useState(false);
  const [statesFor, setStatesFor] = useState<string | null>(null);

  const handleAdd = async () => {
    if (!addName.trim()) return;
    setAdding(true);
    try {
      await api.addCharacter(work, addName.trim(), addMotivation.trim(), {
        voice: addVoice.trim(),
        voice_samples: addSamples.split("\n").map((s) => s.trim()).filter(Boolean),
        core_contradiction: addContradiction.trim(),
        wound: addWound.trim(),
      });
      setAddName(""); setAddMotivation(""); setAddVoice(""); setAddSamples("");
      setAddContradiction(""); setAddWound("");
      reload();
    } finally {
      setAdding(false);
    }
  };

  const columns = useMemo<ColumnDef<CharacterT>[]>(() => [
    {
      accessorKey: "name",
      header: "名称",
      cell: ({ row }) => (
        <button className="font-medium text-foreground hover:text-primary hover:underline text-left"
          onClick={() => onEdit?.(row.original)}>{row.original.name}</button>
      ),
    },
    {
      accessorKey: "motivation",
      header: "动机",
      cell: ({ row }) => (
        <span className="text-muted-foreground">{truncate(row.original.motivation, 60) || "—"}</span>
      ),
    },
    {
      id: "core",
      header: "声音 / 内核",
      enableSorting: false,
      cell: ({ row }) => {
        const c = row.original;
        const samples = c.voice_samples ?? [];
        const has = c.voice || samples.length || c.core_contradiction || c.wound;
        return (
          <div className="flex flex-col gap-0.5 max-w-[300px]">
            {c.voice && <span className="text-xs text-muted-foreground">声音:{truncate(c.voice, 36)}</span>}
            {samples.length > 0 && <span className="text-xs">样本:{samples.slice(0, 2).map((s) => `「${s}」`).join(" ")}</span>}
            {c.core_contradiction && <span className="text-xs text-amber-600 dark:text-amber-400">矛盾:{truncate(c.core_contradiction, 36)}</span>}
            {c.wound && <span className="text-xs text-rose-600/80 dark:text-rose-400/80">创伤:{truncate(c.wound, 36)}</span>}
            {!has && <span className="text-xs text-muted-foreground">—</span>}
          </div>
        );
      },
    },
    {
      id: "actions",
      header: "操作",
      enableSorting: false,
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
          onClick={() => setStatesFor(row.original.name)}
        >
          状态轨迹 <ChevronRight size={12} />
        </Button>
      ),
    },
  ], []);

  const isEmpty = !loading && !error && (!data || data.length === 0) && !filter;

  return (
    <div className="flex flex-col gap-3">
      {/* 新增行 */}
      <div className="flex gap-2 items-center">
        <Input
          placeholder="角色名称"
          value={addName}
          onChange={(e) => setAddName(e.target.value)}
          className="h-8 text-sm w-36"
          onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
        />
        <Input
          placeholder="动机（可选）"
          value={addMotivation}
          onChange={(e) => setAddMotivation(e.target.value)}
          className="h-8 text-sm flex-1"
          onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
        />
        <button className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground shrink-0"
          onClick={() => setMore((m) => !m)}>
          内核/声音 {more ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </button>
        <Button size="sm" className="h-8 gap-1 shrink-0" onClick={handleAdd} disabled={adding || !addName.trim()}>
          {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          新增
        </Button>
      </div>

      {/* 内核/声音(Codex 2.0:防 OOC + 立体之本) */}
      {more && (
        <div className="rounded-md border border-border p-2.5 flex flex-col gap-2">
          <Input placeholder="声音(用词/句式/口头禅,如:极静、短句、不解释)" value={addVoice}
            onChange={(e) => setAddVoice(e.target.value)} className="h-8 text-sm" />
          <Textarea placeholder="声音样本(每行一句代表性台词,防 OOC 命门)" rows={2} value={addSamples}
            onChange={(e) => setAddSamples(e.target.value)} className="text-sm resize-none" />
          <Input placeholder="核心矛盾(立体之本,如:守规矩的执念↔为孩子愿破规矩)" value={addContradiction}
            onChange={(e) => setAddContradiction(e.target.value)} className="h-8 text-sm" />
          <Input placeholder="创伤(驱动行为的过去,如:四十年前破规害死师父)" value={addWound}
            onChange={(e) => setAddWound(e.target.value)} className="h-8 text-sm" />
        </div>
      )}

      {/* 搜索框 */}
      <Input
        placeholder="搜索角色…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="h-8 text-sm"
      />

      <StateBoundary
        loading={loading}
        error={error}
        empty={isEmpty}
        onRetry={reload}
        emptyNode={
          <Empty icon={<User />} title="还没有角色" hint="在上方新增第一个角色" />
        }
      >
        <DataTable
          columns={columns}
          data={data ?? []}
          globalFilter={filter}
          onGlobalFilterChange={setFilter}
        />
      </StateBoundary>

      {statesFor && (
        <CharStatesDialog
          work={work}
          charName={statesFor}
          open={!!statesFor}
          onClose={() => setStatesFor(null)}
        />
      )}
    </div>
  );
}

// ── 设定 Tab ──
function SettingsTab({ work, rev = 0, onEdit }: { work: string; rev?: number; onEdit?: (e?: Setting) => void }) {
  const { data, loading, error, reload } = useData(() => api.settings(work), [work, rev]);
  const [filter, setFilter] = useState("");
  const [addName, setAddName] = useState("");
  const [addType, setAddType] = useState("");
  const [addDesc, setAddDesc] = useState("");
  const [addCost, setAddCost] = useState("");
  const [addLimit, setAddLimit] = useState("");
  const [addTrouble, setAddTrouble] = useState("");
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    if (!addName.trim()) return;
    setAdding(true);
    try {
      const fields: Record<string, string> = {};
      if (addCost.trim()) fields.cost = addCost.trim();
      if (addLimit.trim()) fields.limitations = addLimit.trim();
      if (addTrouble.trim()) fields.trouble_it_causes = addTrouble.trim();
      await api.addSetting(work, addName.trim(), addType.trim() || "设定", addDesc.trim(), fields);
      setAddName(""); setAddType(""); setAddDesc("");
      setAddCost(""); setAddLimit(""); setAddTrouble("");
      reload();
    } finally {
      setAdding(false);
    }
  };

  const columns = useMemo<ColumnDef<Setting>[]>(() => [
    {
      accessorKey: "name",
      header: "名称",
      cell: ({ row }) => (
        <button className="font-medium text-foreground hover:text-primary hover:underline text-left"
          onClick={() => onEdit?.(row.original)}>{row.original.name}</button>
      ),
    },
    {
      accessorKey: "type",
      header: "类型",
      cell: ({ row }) => (
        <Badge variant="outline" className="text-[11px]">
          {mapSettingType(row.original.type)}
        </Badge>
      ),
    },
    {
      id: "description",
      header: "描述 / 规则",
      enableSorting: false,
      cell: ({ row }) => {
        const f = row.original.fields ?? {};
        return (
          <div className="flex flex-col gap-0.5 max-w-[440px]">
            <span className="text-muted-foreground text-xs">{extractDesc(row.original.content)}</span>
            {f.cost && <span className="text-xs text-rose-600/80 dark:text-rose-400/80">代价:{truncate(f.cost, 44)}</span>}
            {f.limitations && <span className="text-xs">限制:{truncate(f.limitations, 44)}</span>}
            {f.trouble_it_causes && <span className="text-xs text-amber-600 dark:text-amber-400">会出什么乱子:{truncate(f.trouble_it_causes, 44)}</span>}
          </div>
        );
      },
    },
  ], []);

  const isPower = ["力量", "规则", "rule", "power", "magic", "体系"].some((k) => addType.includes(k));
  const isEmpty = !loading && !error && (!data || data.length === 0) && !filter;

  return (
    <div className="flex flex-col gap-3">
      {/* 新增行 */}
      <div className="flex gap-2 items-center flex-wrap">
        <Input
          placeholder="设定名称"
          value={addName}
          onChange={(e) => setAddName(e.target.value)}
          className="h-8 text-sm w-32"
          onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
        />
        <Input
          placeholder="类型（如 location）"
          value={addType}
          onChange={(e) => setAddType(e.target.value)}
          className="h-8 text-sm w-36"
          onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
        />
        <Input
          placeholder="描述（可选）"
          value={addDesc}
          onChange={(e) => setAddDesc(e.target.value)}
          className="h-8 text-sm flex-1"
          onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
        />
        <Button size="sm" className="h-8 gap-1 shrink-0" onClick={handleAdd} disabled={adding || !addName.trim()}>
          {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          新增
        </Button>
      </div>

      {/* 力量体系/规则:结构化字段(乱世铜炉判据2:带代价+会出什么乱子) */}
      {isPower && (
        <div className="rounded-md border border-border p-2.5 flex flex-col gap-2">
          <div className="text-xs text-muted-foreground">力量体系/规则字段(写硬,否则 AI 会自信违背 canon)</div>
          <Input placeholder="代价 cost(用了要付什么,如:破规一次左眼瞎一分)" value={addCost}
            onChange={(e) => setAddCost(e.target.value)} className="h-8 text-sm" />
          <Input placeholder="限制 limitations(不能做什么,如:四百年丹方能聚魂)" value={addLimit}
            onChange={(e) => setAddLimit(e.target.value)} className="h-8 text-sm" />
          <Input placeholder="会出什么乱子(推不出乱子的规则就不够好)" value={addTrouble}
            onChange={(e) => setAddTrouble(e.target.value)} className="h-8 text-sm" />
        </div>
      )}

      {/* 搜索框 */}
      <Input
        placeholder="搜索设定…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="h-8 text-sm"
      />

      <StateBoundary
        loading={loading}
        error={error}
        empty={isEmpty}
        onRetry={reload}
        emptyNode={
          <Empty icon={<MapPin />} title="还没有设定" hint="在上方新增地点、物品、组织等设定" />
        }
      >
        <DataTable
          columns={columns}
          data={data ?? []}
          globalFilter={filter}
          onGlobalFilterChange={setFilter}
        />
      </StateBoundary>
    </div>
  );
}

// ── 伏笔 Tab ──
function ForeshadowsTab({ work }: { work: string }) {
  const { data, loading, error, reload } = useData(() => api.foreshadowsStatus(work), [work]);
  const [filter, setFilter] = useState("");
  const [advancing, setAdvancing] = useState<string | null>(null);

  const handleAdvance = async (fid: string, action: "trigger" | "pay" | "abandon") => {
    setAdvancing(fid + action);
    try {
      await api.advanceForeshadow(work, fid, action);
      reload();
    } finally {
      setAdvancing(null);
    }
  };

  const columns = useMemo<ColumnDef<ForeshadowStatus>[]>(() => [
    {
      accessorKey: "summary",
      header: "摘要",
      cell: ({ row }) => {
        const r = row.original;
        return (
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-foreground">{truncate(r.summary, 70)}</span>
              {r.overdue && <Badge variant="destructive" className="text-[10px]">超期未回收</Badge>}
            </div>
            <span className="text-[11px] text-muted-foreground">
              埋第{r.chapter ?? "?"}章{r.echoes?.length ? ` · 强化第${r.echoes.join("/")}章` : ""}
            </span>
          </div>
        );
      },
    },
    {
      accessorKey: "state",
      header: "状态",
      cell: ({ row }) => {
        const s = row.original.state;
        return (
          <Badge variant={foreshadowBadgeVariant(s)} className="text-[11px]">
            {FORESHADOW_STATE_LABEL[s] ?? s}
          </Badge>
        );
      },
    },
    {
      id: "actions",
      header: "操作",
      enableSorting: false,
      cell: ({ row }) => {
        const { id, state } = row.original;
        const busy = (action: string) => advancing === id + action;
        return (
          <div className="flex gap-1">
            {state === "planted" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[11px] px-2"
                disabled={!!advancing}
                onClick={() => handleAdvance(id, "trigger")}
              >
                {busy("trigger") ? <Loader2 size={10} className="animate-spin" /> : "触发"}
              </Button>
            )}
            {(state === "planted" || state === "triggered") && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[11px] px-2"
                disabled={!!advancing}
                onClick={() => handleAdvance(id, "pay")}
              >
                {busy("pay") ? <Loader2 size={10} className="animate-spin" /> : "回收"}
              </Button>
            )}
            {state !== "abandoned" && state !== "paid" && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-[11px] px-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                disabled={!!advancing}
                onClick={() => handleAdvance(id, "abandon")}
              >
                {busy("abandon") ? <Loader2 size={10} className="animate-spin" /> : "放弃"}
              </Button>
            )}
          </div>
        );
      },
    },
  ], [advancing]);

  const isEmpty = !loading && !error && (!data || data.length === 0) && !filter;

  return (
    <div className="flex flex-col gap-3">
      {/* 搜索框 */}
      <Input
        placeholder="搜索伏笔…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="h-8 text-sm"
      />
      <p className="text-xs text-muted-foreground -mt-1">
        伏笔由 AI 主编从章节中自动提取，可在此手动推进状态。
      </p>

      <StateBoundary
        loading={loading}
        error={error}
        empty={isEmpty}
        onRetry={reload}
        emptyNode={
          <Empty
            icon={<Bookmark />}
            title="还没有伏笔"
            hint="写完章节后，让主编扫描以自动发现伏笔"
          />
        }
      >
        <DataTable
          columns={columns}
          data={data ?? []}
          globalFilter={filter}
          onGlobalFilterChange={setFilter}
        />
      </StateBoundary>
    </div>
  );
}

// ── 素材 Tab ──
function MaterialsTab({ work }: { work: string }) {
  const { data, loading, error, reload } = useData(() => api.materials(work), [work]);
  const [filter, setFilter] = useState("");
  const [addContent, setAddContent] = useState("");
  const [addType, setAddType] = useState("snippet");
  const [adding, setAdding] = useState(false);
  const [processing, setProcessing] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleAdd = async () => {
    if (!addContent.trim()) return;
    setAdding(true);
    try {
      await api.addMaterial(work, addContent.trim(), addType);
      setAddContent("");
      reload();
    } finally {
      setAdding(false);
    }
  };

  const handleProcess = async (mid: string) => {
    setProcessing(mid);
    try {
      await api.processMaterial(work, mid);
      reload();
    } finally {
      setProcessing(null);
    }
  };

  const handleDelete = async (mid: string) => {
    setDeleting(mid);
    try {
      await api.deleteMaterial(work, mid);
      reload();
    } finally {
      setDeleting(null);
    }
  };

  const columns = useMemo<ColumnDef<Material>[]>(() => [
    {
      id: "excerpt",
      header: "内容摘要",
      enableSorting: false,
      accessorFn: (row) => row.title || truncate(row.content, 60),
      cell: ({ row }) => (
        <span className="text-foreground text-sm">
          {row.original.title
            ? <><span className="font-medium">{row.original.title}</span><span className="text-muted-foreground ml-1 text-xs">{truncate(row.original.content, 40)}</span></>
            : truncate(row.original.content, 80)}
        </span>
      ),
    },
    {
      accessorKey: "type",
      header: "类型",
      cell: ({ row }) => (
        <Badge variant="outline" className="text-[11px]">{row.original.type}</Badge>
      ),
    },
    {
      accessorKey: "tags",
      header: "标签",
      enableSorting: false,
      cell: ({ row }) => {
        const tags = row.original.tags;
        if (!tags) return <span className="text-muted-foreground text-xs">—</span>;
        const list = tags.split(",").map((t) => t.trim()).filter(Boolean);
        return (
          <div className="flex gap-1 flex-wrap max-w-[180px]">
            {list.slice(0, 3).map((t) => (
              <Badge key={t} variant="secondary" className="text-[10px] px-1.5 py-0">{t}</Badge>
            ))}
            {list.length > 3 && (
              <span className="text-[10px] text-muted-foreground">+{list.length - 3}</span>
            )}
          </div>
        );
      },
    },
    {
      id: "actions",
      header: "操作",
      enableSorting: false,
      cell: ({ row }) => {
        const { id } = row.original;
        return (
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[11px] px-2"
              disabled={!!processing}
              onClick={() => handleProcess(id)}
            >
              {processing === id ? <Loader2 size={10} className="animate-spin" /> : "提炼"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-[11px] px-2 text-destructive hover:text-destructive hover:bg-destructive/10"
              disabled={!!deleting}
              onClick={() => handleDelete(id)}
            >
              {deleting === id ? <Loader2 size={10} className="animate-spin" /> : "删除"}
            </Button>
          </div>
        );
      },
    },
  ], [processing, deleting]);

  const isEmpty = !loading && !error && (!data || data.length === 0) && !filter;

  return (
    <div className="flex flex-col gap-3">
      {/* 新增行 */}
      <div className="flex gap-2 items-center">
        <Input
          placeholder="粘贴素材内容…"
          value={addContent}
          onChange={(e) => setAddContent(e.target.value)}
          className="h-8 text-sm flex-1"
          onKeyDown={(e) => { if (e.key === "Enter") handleAdd(); }}
        />
        <select
          value={addType}
          onChange={(e) => setAddType(e.target.value)}
          className="h-8 text-sm rounded-md border border-input bg-background px-2 text-foreground"
        >
          <option value="snippet">片段</option>
          <option value="reference">参考</option>
          <option value="note">笔记</option>
          <option value="inspiration">灵感</option>
        </select>
        <Button size="sm" className="h-8 gap-1 shrink-0" onClick={handleAdd} disabled={adding || !addContent.trim()}>
          {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          新增
        </Button>
      </div>

      {/* 搜索框 */}
      <Input
        placeholder="搜索素材…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="h-8 text-sm"
      />

      <StateBoundary
        loading={loading}
        error={error}
        empty={isEmpty}
        onRetry={reload}
        emptyNode={
          <Empty icon={<FileText />} title="还没有素材" hint="在上方粘贴片段、参考、灵感等素材" />
        }
      >
        <DataTable
          columns={columns}
          data={data ?? []}
          globalFilter={filter}
          onGlobalFilterChange={setFilter}
        />
      </StateBoundary>
    </div>
  );
}

// ── 主视图 ──
function MotifsTab({ work, rev = 0, onEdit }: { work: string; rev?: number; onEdit?: (e?: Motif) => void }) {
  const { data, loading, error, reload } = useData(() => api.motifs(work), [work, rev]);
  const [name, setName] = useState("");
  const [meta, setMeta] = useState("");
  const [theme, setTheme] = useState("");
  const [echoes, setEchoes] = useState("");
  const [adding, setAdding] = useState(false);
  const toast = useToast();
  const add = async () => {
    if (!name.trim()) return;
    setAdding(true);
    try {
      await api.addMotif(work, {
        name, metaphor_unfolding: meta, bound_theme: theme,
        material_echoes: echoes.split(/[，,、]/).map((s) => s.trim()).filter(Boolean),
      });
      setName(""); setMeta(""); setTheme(""); setEchoes(""); reload(); toast("已加母题");
    } catch (e) { toast(String(e)); } finally { setAdding(false); }
  };
  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-lg border border-border p-2.5 flex flex-col gap-2">
        <div className="text-xs text-muted-foreground">新增母题(核心意象:世界观+主题+命名+物质回声 四位一体,贯穿全书)</div>
        <Input placeholder="母题名(如:铜炉)" value={name} onChange={(e) => setName(e.target.value)} className="h-8 text-sm" />
        <Input placeholder="隐喻展开(天地为炉,万物为铜…)" value={meta} onChange={(e) => setMeta(e.target.value)} className="h-8 text-sm" />
        <Input placeholder="绑定主题句(这本书在说什么)" value={theme} onChange={(e) => setTheme(e.target.value)} className="h-8 text-sm" />
        <Input placeholder="物质回声(逗号分隔:长明灯,河面浮炭…)" value={echoes} onChange={(e) => setEchoes(e.target.value)} className="h-8 text-sm" />
        <Button size="sm" className="h-8 gap-1 self-start" onClick={add} disabled={adding || !name.trim()}>
          {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}新增母题
        </Button>
      </div>
      <StateBoundary loading={loading} error={error} empty={!data?.length} onRetry={reload}
        emptyNode={<Empty icon={<Flame />} title="还没有母题" hint="母题=贯穿全书的核心意象(乱世铜炉级设定的精华)" />}>
        <div className="flex flex-col gap-2">
          {data?.map((m, i) => (
            <Card key={m.id ?? i} size="sm">
              <CardContent className="py-2.5 px-3">
                <button className="flex items-center gap-1.5 hover:text-primary" onClick={() => onEdit?.(m)}><Flame size={13} className="text-amber-500" /><span className="text-sm font-medium">{m.name}</span></button>
                {m.bound_theme && <div className="text-xs text-muted-foreground mt-1">主题:{m.bound_theme}</div>}
                {m.metaphor_unfolding && <div className="text-xs mt-1">隐喻:{m.metaphor_unfolding}</div>}
                {!!m.material_echoes?.length && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {m.material_echoes.map((e, j) => <Badge key={j} variant="secondary" className="text-xs">{e}</Badge>)}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </StateBoundary>
    </div>
  );
}

type LeftView = { mode: "list" } | { mode: "edit"; kind: EntityKind; entity: unknown } | { mode: "extract" };

export function CodexView({ work }: { work: string }) {
  const [rev, setRev] = useState(0);
  const bump = () => setRev((r) => r + 1);
  const [left, setLeft] = useState<LeftView>({ mode: "list" });
  const [chatOpen, setChatOpen] = useState(true);   // 右栏主编聊天默认打开
  const [seed, setSeed] = useState<string | undefined>(undefined);
  const KIND_LABEL: Record<EntityKind, string> = { character: "角色", setting: "设定", motif: "母题" };
  const edit = (kind: EntityKind) => (entity?: unknown) => setLeft({ mode: "edit", kind, entity: entity ?? null });
  const discuss = (kind: EntityKind, name: string) => { setChatOpen(true); setSeed(`聊聊「${name}」这个${KIND_LABEL[kind]}：`); };

  // 右侧聊天面板可拖拽改宽(持久化)
  const [pw, setPw] = useState<number>(() => {
    try { return Number(localStorage.getItem("scribe.codexPW")) || 420; } catch { return 420; }
  });
  useEffect(() => { try { localStorage.setItem("scribe.codexPW", String(pw)); } catch { /* */ } }, [pw]);
  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX, startW = pw;
    const onMove = (ev: MouseEvent) => setPw(Math.max(300, Math.min(760, startW - (ev.clientX - startX))));
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = ""; document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    document.body.style.cursor = "col-resize"; document.body.style.userSelect = "none";
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* 顶部标题条 */}
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-background/80 px-4 py-2">
        <Library size={15} className="text-primary" />
        <span className="text-sm font-medium text-foreground">设定库</span>
        {left.mode !== "list" && (
          <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={() => setLeft({ mode: "list" })}>
            <ChevronLeft size={13} /> 返回列表
          </Button>
        )}
        <div className="flex-1" />
        <Button variant={left.mode === "extract" ? "default" : "outline"} size="sm" className="h-7 text-xs gap-1.5"
          onClick={() => setLeft(left.mode === "extract" ? { mode: "list" } : { mode: "extract" })}>
          <Sparkles size={13} /> 从正文抽取
        </Button>
        <Button variant={chatOpen ? "default" : "outline"} size="sm" className="h-7 text-xs gap-1.5"
          onClick={() => setChatOpen((o) => !o)}>
          <MessageSquareQuote size={13} /> 与主编聊设定
        </Button>
      </div>

      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* 左主区:列表 / 实体详情全字段 / 抽取(详情在宽的左区展开)*/}
        <div className="flex-1 min-w-0 overflow-hidden">
          {left.mode === "list" ? (
            <div className="h-full overflow-auto px-4 py-3">
              <Tabs defaultValue="characters" className="flex flex-col gap-3">
                <TabsList className="shrink-0 w-auto">
                  <TabsTrigger value="characters" className="text-xs gap-1.5"><User size={13} />角色</TabsTrigger>
                  <TabsTrigger value="settings" className="text-xs gap-1.5"><MapPin size={13} />设定</TabsTrigger>
                  <TabsTrigger value="motifs" className="text-xs gap-1.5"><Flame size={13} />母题</TabsTrigger>
                  <TabsTrigger value="foreshadows" className="text-xs gap-1.5"><Bookmark size={13} />伏笔</TabsTrigger>
                  <TabsTrigger value="materials" className="text-xs gap-1.5"><FileText size={13} />素材</TabsTrigger>
                </TabsList>
                <TabsContent value="characters" className="mt-0"><CharactersTab work={work} rev={rev} onEdit={edit("character")} /></TabsContent>
                <TabsContent value="settings" className="mt-0"><SettingsTab work={work} rev={rev} onEdit={edit("setting")} /></TabsContent>
                <TabsContent value="motifs" className="mt-0"><MotifsTab work={work} rev={rev} onEdit={edit("motif")} /></TabsContent>
                <TabsContent value="foreshadows" className="mt-0"><ForeshadowsTab work={work} /></TabsContent>
                <TabsContent value="materials" className="mt-0"><MaterialsTab work={work} /></TabsContent>
              </Tabs>
            </div>
          ) : left.mode === "extract" ? (
            <div className="h-full max-w-3xl border-r border-border"><ExtractPanel work={work} onSaved={bump} onClose={() => setLeft({ mode: "list" })} /></div>
          ) : (
            <div className="h-full max-w-3xl border-r border-border"><EntityEditor work={work} kind={left.kind} entity={left.entity as never}
              onSaved={bump} onClose={() => setLeft({ mode: "list" })} onDiscuss={discuss} /></div>
          )}
        </div>

        {/* 右栏:与主编聊设定(默认打开,可拖拽改宽)*/}
        {chatOpen && (
          <div className="shrink-0 border-l border-border bg-background/60 flex flex-col min-h-0 relative" style={{ width: pw }}>
            <div className="absolute left-0 top-0 bottom-0 w-1.5 -translate-x-1/2 cursor-col-resize z-20 hover:bg-accent/60 transition-colors"
              onMouseDown={startResize} title="拖拽改宽" />
            <CodexChat work={work} onChanged={bump} seed={seed} />
          </div>
        )}
      </div>
    </div>
  );
}
