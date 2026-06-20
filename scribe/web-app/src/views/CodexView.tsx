import { useState, useMemo } from "react";
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
  FileText,
  Plus,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { api } from "@/api";
import type { CharacterT, Setting, Foreshadow, Material, CharState } from "@/api";
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
function CharactersTab({ work }: { work: string }) {
  const { data, loading, error, reload } = useData(() => api.characters(work), [work]);
  const [filter, setFilter] = useState("");
  const [addName, setAddName] = useState("");
  const [addMotivation, setAddMotivation] = useState("");
  const [adding, setAdding] = useState(false);
  const [statesFor, setStatesFor] = useState<string | null>(null);

  const handleAdd = async () => {
    if (!addName.trim()) return;
    setAdding(true);
    try {
      await api.addCharacter(work, addName.trim(), addMotivation.trim());
      setAddName("");
      setAddMotivation("");
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
        <span className="font-medium text-foreground">{row.original.name}</span>
      ),
    },
    {
      accessorKey: "motivation",
      header: "动机",
      cell: ({ row }) => (
        <span className="text-muted-foreground">{truncate(row.original.motivation, 80) || "—"}</span>
      ),
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
        <Button size="sm" className="h-8 gap-1 shrink-0" onClick={handleAdd} disabled={adding || !addName.trim()}>
          {adding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          新增
        </Button>
      </div>

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
function SettingsTab({ work }: { work: string }) {
  const { data, loading, error, reload } = useData(() => api.settings(work), [work]);
  const [filter, setFilter] = useState("");
  const [addName, setAddName] = useState("");
  const [addType, setAddType] = useState("");
  const [addDesc, setAddDesc] = useState("");
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    if (!addName.trim()) return;
    setAdding(true);
    try {
      await api.addSetting(work, addName.trim(), addType.trim() || "设定", addDesc.trim());
      setAddName("");
      setAddType("");
      setAddDesc("");
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
        <span className="font-medium text-foreground">{row.original.name}</span>
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
      header: "描述",
      enableSorting: false,
      accessorFn: (row) => extractDesc(row.content),
      cell: ({ getValue }) => (
        <span className="text-muted-foreground text-xs">{getValue() as string}</span>
      ),
    },
  ], []);

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
  const { data, loading, error, reload } = useData(() => api.foreshadows(work), [work]);
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

  const columns = useMemo<ColumnDef<Foreshadow>[]>(() => [
    {
      accessorKey: "summary",
      header: "摘要",
      cell: ({ row }) => (
        <span className="text-foreground">{truncate(row.original.summary, 80)}</span>
      ),
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
                variant="outline"
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
                variant="outline"
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
              variant="outline"
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
export function CodexView({ work }: { work: string }) {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* 顶部标题条 */}
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-background/80 px-4 py-2">
        <Library size={15} className="text-primary" />
        <span className="text-sm font-medium text-foreground">设定库</span>
      </div>

      {/* 内容区:带 Tabs */}
      <div className="flex-1 overflow-auto px-4 py-4">
        <Tabs defaultValue="characters" className="flex flex-col gap-4">
          <TabsList className="shrink-0 w-auto">
            <TabsTrigger value="characters" className="text-xs gap-1.5">
              <User size={13} />角色
            </TabsTrigger>
            <TabsTrigger value="settings" className="text-xs gap-1.5">
              <MapPin size={13} />设定
            </TabsTrigger>
            <TabsTrigger value="foreshadows" className="text-xs gap-1.5">
              <Bookmark size={13} />伏笔
            </TabsTrigger>
            <TabsTrigger value="materials" className="text-xs gap-1.5">
              <FileText size={13} />素材
            </TabsTrigger>
          </TabsList>

          <TabsContent value="characters" className="mt-0">
            <CharactersTab work={work} />
          </TabsContent>
          <TabsContent value="settings" className="mt-0">
            <SettingsTab work={work} />
          </TabsContent>
          <TabsContent value="foreshadows" className="mt-0">
            <ForeshadowsTab work={work} />
          </TabsContent>
          <TabsContent value="materials" className="mt-0">
            <MaterialsTab work={work} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
