import { useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Plus } from "lucide-react";
import { api } from "./api";
import { useData } from "./common";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { StateBoundary } from "@/components/StateBoundary";
import { Empty } from "@/components/Empty";
import { cn } from "@/lib/utils";

// 左栏 Navigator:卷/章大纲树。想象捕获已移到 ⌘I 模态 / 命令面板(不再常驻左栏)。
export function Navigator({ work, rev, bump, currentSeq, setSeq }: {
  work: string; rev: number; bump: () => void;
  currentSeq: number | null; setSeq: (s: number | null) => void;
}) {
  return (
    <div className="mt-3 border-t border-border pt-3">
      <Chapters work={work} rev={rev} bump={bump} currentSeq={currentSeq} setSeq={setSeq} />
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
  const warnBySeq: Record<number, number> = {};
  for (const f of fl.data ?? []) {
    const s = (f as { chapter_seq?: number }).chapter_seq;
    if (s != null) warnBySeq[s] = (warnBySeq[s] || 0) + 1;
  }
  const maxSeq = chapters.reduce((m, c) => Math.max(m, c.seq), 0);
  const maxVol = volumes.reduce((m, v) => Math.max(m, v.seq), 0);

  const addVolume = async () => {
    await api.createVolume(work, maxVol + 1, vtitle.trim());
    setVtitle(""); vol.reload();
  };
  const addChapter = async (volume_id?: string) => {
    await api.addChapter(work, maxSeq + 1, title.trim(), volume_id);
    setTitle(""); bump();
  };

  const byVol = (vid: string | null) => chapters.filter((c) => (c.volume_id ?? null) === vid);
  const unassigned = byVol(null);

  return (
    <>
      {/* 标题行 + 加卷 */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground m-0">大纲树</h3>
        <div className="flex items-center gap-1">
          <Input
            aria-label="新卷标题"
            value={vtitle}
            placeholder="新卷…"
            className="h-6 w-20 text-xs px-2"
            onChange={(e) => setVtitle(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") addVolume(); }}
          />
          <Button variant="ghost" size="xs" onClick={addVolume}>+卷</Button>
        </div>
      </div>

      {/* 加章表单 */}
      <div className="flex items-center gap-1 mb-2">
        <Input
          aria-label="新章标题"
          value={title}
          placeholder="新章标题…"
          className="h-7 text-xs"
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") addChapter(volumes[volumes.length - 1]?.id); }}
        />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => addChapter(volumes[volumes.length - 1]?.id)}
        >
          <Plus size={13} /> 加章
        </Button>
      </div>

      <StateBoundary
        loading={ch.loading || vol.loading}
        error={ch.error || vol.error}
        empty={!chapters.length && !volumes.length}
        emptyNode={<Empty title="还没有卷/章" hint="先 +卷,再加章。" />}
        onRetry={() => { ch.reload(); vol.reload(); }}
      >
        {volumes.map((v) => (
          <div key={v.id} className="mb-2">
            <div className="flex items-center gap-1.5 px-1 py-0.5 mb-1">
              <span className="text-xs font-semibold text-muted-foreground truncate">
                第 {v.seq} 卷 · {v.title || "(无题)"}
              </span>
              <Badge variant="secondary" className="shrink-0 text-[10px] h-4 px-1.5">
                {byVol(v.id).length}章
              </Badge>
            </div>
            <ChapterList
              chapters={byVol(v.id)}
              currentSeq={currentSeq}
              setSeq={setSeq}
              work={work}
              bump={bump}
              warn={warnBySeq}
            />
          </div>
        ))}
        {unassigned.length > 0 && (
          <div>
            {volumes.length > 0 && (
              <div className="px-1 py-0.5 mb-1">
                <span className="text-xs font-semibold text-muted-foreground">未分卷</span>
              </div>
            )}
            <ChapterList
              chapters={unassigned}
              currentSeq={currentSeq}
              setSeq={setSeq}
              work={work}
              bump={bump}
              warn={warnBySeq}
            />
          </div>
        )}
      </StateBoundary>
    </>
  );
}

// 状态点颜色 map
const STATUS_DOT: Record<string, string> = {
  done: "bg-[#22c55e]",
  revising: "bg-[#f59e0b]",
  draft: "bg-[#94a3b8]",
};

function ChapterList({ chapters, currentSeq, setSeq, work, bump, warn }: {
  chapters: { seq: number; title?: string; status: string }[];
  currentSeq: number | null; setSeq: (s: number | null) => void; work: string; bump: () => void;
  warn: Record<number, number>;
}) {
  if (chapters.length > 30) {
    return <VirtualChapters chapters={chapters} currentSeq={currentSeq} setSeq={setSeq} />;
  }
  const move = async (seq: number, dir: "up" | "down") => {
    await api.moveChapter(work, seq, dir); bump();
  };
  return (
    <>
      {chapters.map((c, i) => (
        <div key={c.seq} className="flex items-center gap-0.5 group">
          <button
            className={cn(
              "flex-1 flex items-center gap-1.5 min-w-0 rounded-md px-2 py-1 text-left text-xs transition-colors",
              currentSeq === c.seq
                ? "bg-accent text-accent-foreground font-medium"
                : "text-foreground/80 hover:bg-muted hover:text-foreground"
            )}
            aria-current={currentSeq === c.seq}
            onClick={() => setSeq(currentSeq === c.seq ? null : c.seq)}
          >
            {/* 状态点 */}
            <span
              className={cn(
                "size-1.5 shrink-0 rounded-full",
                STATUS_DOT[c.status] ?? "bg-muted-foreground/40"
              )}
              aria-hidden
            />
            <span className="flex-1 truncate">第 {c.seq} 章 · {c.title || "无题"}</span>
            {warn[c.seq] ? (
              <Badge variant="destructive" className="shrink-0 text-[10px] h-4 px-1" title="一致性问题">
                ⚠{warn[c.seq]}
              </Badge>
            ) : null}
          </button>
          {/* 移动按钮:只在 hover 时显示 */}
          <button
            className="opacity-0 group-hover:opacity-100 transition-opacity rounded px-1 py-0.5 text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-20"
            aria-label={`上移第${c.seq}章`}
            title="上移"
            disabled={i === 0}
            onClick={() => move(c.seq, "up")}
          >▲</button>
          <button
            className="opacity-0 group-hover:opacity-100 transition-opacity rounded px-1 py-0.5 text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-20"
            aria-label={`下移第${c.seq}章`}
            title="下移"
            disabled={i === chapters.length - 1}
            onClick={() => move(c.seq, "down")}
          >▼</button>
        </div>
      ))}
    </>
  );
}

function VirtualChapters({ chapters, currentSeq, setSeq }: {
  chapters: { seq: number; title?: string; status: string }[];
  currentSeq: number | null; setSeq: (s: number | null) => void;
}) {
  const parentRef = useRef<HTMLDivElement>(null);
  const rowH = 32;
  const v = useVirtualizer({
    count: chapters.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowH,
    overscan: 8,
  });
  return (
    <div ref={parentRef} className="max-h-[45vh] overflow-auto">
      <div style={{ height: v.getTotalSize(), position: "relative" }}>
        {v.getVirtualItems().map((vi) => {
          const c = chapters[vi.index];
          return (
            <button
              key={c.seq}
              className={cn(
                "absolute left-0 w-full flex items-center gap-1.5 rounded-md px-2 py-1 text-left text-xs transition-colors",
                currentSeq === c.seq
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-foreground/80 hover:bg-muted hover:text-foreground"
              )}
              aria-current={currentSeq === c.seq}
              onClick={() => setSeq(currentSeq === c.seq ? null : c.seq)}
              style={{ top: 0, transform: `translateY(${vi.start}px)`, height: rowH - 4 }}
            >
              <span
                className={cn("size-1.5 shrink-0 rounded-full", STATUS_DOT[c.status] ?? "bg-muted-foreground/40")}
                aria-hidden
              />
              <span className="flex-1 truncate">第 {c.seq} 章 · {c.title || "（无题）"}</span>
              <Badge variant="secondary" className="shrink-0 text-[10px] h-4 px-1.5">{c.status}</Badge>
            </button>
          );
        })}
      </div>
    </div>
  );
}

