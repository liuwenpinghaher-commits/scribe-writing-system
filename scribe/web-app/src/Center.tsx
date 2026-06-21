/**
 * Center.tsx — 中栏双模主舞台(Task 1.3b)
 * 北极星黛绿条 → Segmented(正文|对话) → ChapterEditor 或 Conversation
 */
import { lazy, Suspense, useEffect, useState } from "react";
import { FileText, MessagesSquare, Star } from "lucide-react";
import { api } from "./api";
import { useData, useToast } from "./common";
import { Segmented } from "./components/Segmented";
import { Empty } from "./components/Empty";
import { Card, CardContent } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { Textarea } from "./components/ui/textarea";
import { Input } from "./components/ui/input";
import { Skeleton } from "./components/ui/skeleton";
import { Conversation } from "./Conversation";

// 懒加载编辑器(Tiptap 是最大块),缩小首屏 bundle
const ChapterEditor = lazy(() =>
  import("./Editor").then((m) => ({ default: m.ChapterEditor }))
);

type CenterMode = "prose" | "chat";

// ─── 北极星 sticky 条(黛绿左边框)───────────────────────────
function NorthStarBar({ work, rev }: { work: string; rev: number }) {
  const { data, reload } = useData(() => api.intent(work), [work, rev]);
  const [editing, setEditing] = useState(false);
  const [rf, setRf] = useState("");
  const [arc, setArc] = useState("");
  const [dnb, setDnb] = useState("");
  const [dirty, setDirty] = useState(false);
  const toast = useToast();

  // 重构:do_not_betray 是 string[](新底座契约),不再当 JSON 字符串解析
  const redCount = Array.isArray(data?.do_not_betray) ? data!.do_not_betray.length : 0;

  useEffect(() => {
    if (!data) return;
    setRf(data.reader_feeling || "");
    setArc(data.core_emotional_arc || "");
    const list = Array.isArray(data.do_not_betray) ? data.do_not_betray : [];
    setDnb(list.join("，"));
    setDirty(false);
  }, [data]);

  const save = async () => {
    await api.saveIntent(
      work,
      rf,
      dnb.split(/[，,]/).map((s) => s.trim()).filter(Boolean),
      arc
    );
    setDirty(false);
    setEditing(false);
    toast("北极星已保存");
    reload();
  };

  const unset = !data?.reader_feeling;
  const feeling = data?.reader_feeling || "";

  return (
    <Card className="border-l-4 border-l-primary rounded-none border-x-0 border-t-0 border-b border-border shadow-sm">
      <CardContent className="py-2 px-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
            <Star size={13} className="text-primary shrink-0" />
            <span className="text-xs font-semibold text-primary shrink-0">北极星</span>
            {unset ? (
              <span className="text-xs text-amber-600 dark:text-amber-400 truncate">
                尚未设定 —— 没有北极星，AI 会走向均值
              </span>
            ) : (
              <span
                className="text-xs text-foreground font-prose truncate"
                title={feeling}
              >
                「{feeling.length > 50 ? feeling.slice(0, 50) + "…" : feeling}」
              </span>
            )}
            {data?.core_emotional_arc && (
              <span className="text-xs text-muted-foreground hidden sm:inline truncate">
                弧：{data.core_emotional_arc.slice(0, 20)}
              </span>
            )}
            {redCount > 0 && (
              <span className="shrink-0 inline-flex items-center rounded-full bg-destructive/10 px-1.5 py-0.5 text-xs font-medium text-destructive">
                红线 ×{redCount}
              </span>
            )}
            {!unset && (
              <span className="shrink-0 text-xs text-emerald-600 dark:text-emerald-400">·&nbsp;已对齐</span>
            )}
            {dirty && <span className="shrink-0 text-xs text-muted-foreground">（未保存）</span>}
          </div>
          <Button
            variant={!editing && unset ? "default" : "ghost"}
            size="sm"
            className="h-6 text-xs shrink-0"
            onClick={() => setEditing((v) => !v)}
          >
            {editing ? "收起" : unset ? "立即设定 →" : "编辑"}
          </Button>
        </div>

        {editing && (
          <div className="mt-3 flex flex-col gap-2">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground" htmlFor="ns-rf">
                这本书要让读者合上书时感受到什么？
              </label>
              <Textarea
                id="ns-rf"
                rows={2}
                value={rf}
                placeholder="例：温热的孤独感——被爱过，但爱本身短暂"
                onChange={(e) => { setRf(e.target.value); setDirty(true); }}
                className="text-sm font-prose resize-none"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground" htmlFor="ns-arc">
                主角情感弧线（从…到…）
              </label>
              <Input
                id="ns-arc"
                value={arc}
                placeholder="例：从麻木到在意到失去到接受"
                onChange={(e) => { setArc(e.target.value); setDirty(true); }}
                className="h-8 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground" htmlFor="ns-dnb">
                绝不背叛的红线（逗号分隔）
              </label>
              <Input
                id="ns-dnb"
                value={dnb}
                placeholder="例：主角不能在未付出代价下成功"
                onChange={(e) => { setDnb(e.target.value); setDirty(true); }}
                className="h-8 text-sm"
              />
            </div>
            <Button
              size="sm"
              className="self-start"
              onClick={save}
              disabled={!dirty}
            >
              保存北极星
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── 主导出 ──────────────────────────────────────────────────
export function Center({
  work,
  title,
  rev,
  bump,
  currentSeq,
}: {
  work: string;
  title: string;
  rev: number;
  bump: () => void;
  currentSeq: number | null;
}) {
  // 有章节默认正文，无章节默认对话
  const [mode, setMode] = useState<CenterMode>(currentSeq != null ? "prose" : "chat");
  const [quote, setQuote] = useState("");  // 划词「讨论这段」带入主编对话的引文

  // 当章节切换时：选中章→正文，取消选中→对话
  useEffect(() => {
    if (currentSeq != null) setMode("prose");
    else setMode("chat");
  }, [currentSeq]);

  // 划词讨论：带上引文 → 切到对话
  const discuss = (text: string) => { setQuote(text); setMode("chat"); };

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* 北极星条 sticky */}
      <div className="sticky top-0 z-10 bg-background">
        <NorthStarBar work={work} rev={rev} />
      </div>

      {/* 模式切换条 */}
      <div className="px-3 py-1.5 border-b border-border bg-background">
        <Segmented
          value={mode}
          onChange={(k) => setMode(k as CenterMode)}
          options={[
            { key: "prose", label: "正文", icon: <FileText size={14} /> },
            { key: "chat", label: "与主编对话", icon: <MessagesSquare size={14} /> },
          ]}
        />
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {mode === "prose" ? (
          currentSeq != null ? (
            <Suspense
              fallback={
                <div className="flex flex-col gap-2 py-2">
                  <Skeleton className="h-5 w-3/4" />
                  <Skeleton className="h-5 w-1/2" />
                  <Skeleton className="h-32 w-full mt-2" />
                </div>
              }
            >
              <ChapterEditor work={work} seq={currentSeq} rev={rev} bump={bump} onDiscuss={discuss} />
            </Suspense>
          ) : (
            <Empty
              icon={<FileText />}
              title="从左侧大纲树选择章节开始写作"
              hint="没有章节？在左栏「加章」，或切到「与主编对话」出谋划策"
              action={{ label: "去与主编对话", onClick: () => setMode("chat") }}
            />
          )
        ) : (
          <Conversation work={work} rev={rev} bump={bump} quote={quote} onQuoteUsed={() => setQuote("")} />
        )}
      </div>

      {/* 隐藏 title 供外部引用(原逻辑保留) */}
      <span className="sr-only">{title}</span>
    </div>
  );
}
