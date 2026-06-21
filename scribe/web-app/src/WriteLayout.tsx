/**
 * WriteLayout.tsx — 写作台 VS Code 式活动栏布局。
 * 两侧 44px 图标轨常驻;点能力图标内联推开对应面板,中栏 1fr 自适应。
 * 左轨=大纲;右轨能力=主编对话/设定圣经/伏笔/一致性/素材/脉络质量/记忆技能。
 * 「与主编对话」即右轨一个能力(渲染 Conversation);划词「讨论这段」自动开对话并带入引文。
 * 面板宽度可拖拽(持久化),打开状态持久化。
 */
import { useEffect, useState } from "react";
import { ListTree, MessagesSquare, BookMarked, Sparkles, ShieldAlert, Package, Activity, Brain } from "lucide-react";
import { api } from "./api";
import { useData } from "./common";
import { cn } from "./lib/utils";
import { Navigator } from "./Navigator";
import { Center } from "./Center";
import { Conversation } from "./Conversation";
import { Right } from "./Right";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "./components/ui/tooltip";

function useStrPref(key: string, def: string): [string, (v: string) => void] {
  const [v, setV] = useState<string>(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : s; } catch { return def; }
  });
  return [v, (nv: string) => { setV(nv); try { localStorage.setItem(key, nv); } catch { /* */ } }];
}
function useNumPref(key: string, def: number): [number, (v: number) => void] {
  const [v, setV] = useState<number>(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : Number(s) || def; } catch { return def; }
  });
  useEffect(() => { try { localStorage.setItem(key, String(v)); } catch { /* */ } }, [key, v]);
  return [v, setV];
}

const CAPS = [
  { key: "chat", label: "主编对话", icon: MessagesSquare, badge: "chat" },
  { key: "bible", label: "设定圣经", icon: BookMarked },
  { key: "foreshadow", label: "伏笔", icon: Sparkles, badge: "foreshadow" },
  { key: "flags", label: "一致性", icon: ShieldAlert, badge: "flags" },
  { key: "material", label: "素材", icon: Package },
  { key: "pulse", label: "脉络·质量", icon: Activity },
  { key: "agent", label: "记忆·技能", icon: Brain },
] as const;

function RailBtn({ icon, label, badge, on, onClick, side = "right" }: {
  icon: React.ReactNode; label: string; badge?: number; on?: boolean; onClick: () => void; side?: "left" | "right";
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <button onClick={onClick} aria-label={label} aria-pressed={on}
            className={cn("relative w-9 h-9 rounded-lg inline-flex items-center justify-center transition-colors",
              on ? "bg-accent text-foreground ring-1 ring-border" : "text-muted-foreground hover:bg-accent hover:text-foreground")}>
            {icon}
            {!!badge && badge > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[15px] h-[15px] px-0.5 rounded-full bg-primary text-primary-foreground text-[9px] font-medium leading-[15px] text-center">{badge > 99 ? "99" : badge}</span>
            )}
          </button>
        }
      />
      <TooltipContent side={side} sideOffset={8}>{label}</TooltipContent>
    </Tooltip>
  );
}

export function WriteLayout({ work, rev, bump, title, seq, setSeq }: {
  work: string; rev: number; bump: () => void; title: string;
  seq: number | null; setSeq: (s: number) => void;
}) {
  const [leftOpen, setLeftOpen] = useStrPref("scribe.leftOpen", "1");
  const [rightCap, setRightCap] = useStrPref("scribe.rightCap", "");
  const [lw, setLw] = useNumPref("scribe.lw", 232);
  const [rw, setRw] = useNumPref("scribe.rw", 320);
  const [quote, setQuote] = useState("");
  const lOpen = leftOpen === "1";

  const insights = useData(() => api.insights(work), [work, rev]);
  const pend = useData(() => api.pendingWrites(work), [work, rev]);
  const fores = useData(() => api.foreshadows(work), [work, rev]);
  const flags = useData(() => api.flags(work), [work, rev]);
  const badgeFor = (key?: string): number => {
    if (key === "chat") return (insights.data?.length ?? 0) + (pend.data?.length ?? 0);
    if (key === "foreshadow") return fores.data?.filter((f) => f.state === "planted" || f.state === "triggered").length ?? 0;
    if (key === "flags") return flags.data?.length ?? 0;
    return 0;
  };

  const startResize = (side: "l" | "r") => (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = side === "l" ? lw : rw;
    const onMove = (ev: MouseEvent) => {
      const dx = ev.clientX - startX;
      const w = Math.max(180, Math.min(620, side === "l" ? startW + dx : startW - dx));
      (side === "l" ? setLw : setRw)(w);
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const discuss = (text: string) => { setQuote(text); setRightCap("chat"); };
  const goChat = () => setRightCap("chat");
  const activeLabel = CAPS.find((c) => c.key === rightCap)?.label ?? "";

  const cls = "app" + (lOpen ? " lopen" : "") + (rightCap ? " ropen" : "");
  return (
    <TooltipProvider delay={0}>
    <div className={cls} style={{ ["--lw" as string]: `${lw}px`, ["--rw" as string]: `${rw}px` }}>
      {/* 左轨 */}
      <div className="rail-col l flex flex-col items-center py-2 gap-1">
        <RailBtn icon={<ListTree size={18} />} label="大纲树" side="right" on={lOpen} onClick={() => setLeftOpen(lOpen ? "0" : "1")} />
      </div>

      {/* 左面板:大纲 */}
      <div className="panel-col l">
        {lOpen && <div className="p-2.5">
          <Navigator work={work} rev={rev} bump={bump} currentSeq={seq} setSeq={setSeq} />
        </div>}
      </div>

      {/* 中栏:正文(自适应) */}
      <main className="center-col">
        <div className="center-inner">
          <Center key={work} work={work} title={title} rev={rev} bump={bump} currentSeq={seq}
            onDiscuss={discuss} onGoChat={goChat} />
        </div>
      </main>

      {/* 右面板:当前能力 */}
      <div className="panel-col r">
        {!!rightCap && (
          <div className="p-2.5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{activeLabel}</span>
            </div>
            {rightCap === "chat"
              ? <Conversation work={work} rev={rev} bump={bump} quote={quote} onQuoteUsed={() => setQuote("")} />
              : <Right work={work} rev={rev} bump={bump} active={rightCap} />}
          </div>
        )}
      </div>

      {/* 右轨:能力活动栏 */}
      <div className="rail-col r flex flex-col items-center py-2 gap-1">
        {CAPS.map((c) => {
          const Icon = c.icon;
          return (
            <RailBtn key={c.key} icon={<Icon size={17} />} label={c.label} side="left"
              badge={badgeFor((c as { badge?: string }).badge)}
              on={rightCap === c.key} onClick={() => setRightCap(rightCap === c.key ? "" : c.key)} />
          );
        })}
      </div>

      {/* 拖拽改宽:置于面板与中栏边界 */}
      {lOpen && <div className="app-resizer" style={{ left: `calc(44px + ${lw}px - 3px)` }} onMouseDown={startResize("l")} />}
      {!!rightCap && <div className="app-resizer" style={{ right: `calc(44px + ${rw}px - 3px)` }} onMouseDown={startResize("r")} />}
    </div>
    </TooltipProvider>
  );
}
