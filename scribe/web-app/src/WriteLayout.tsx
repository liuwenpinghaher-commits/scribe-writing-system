/**
 * WriteLayout.tsx — 写作台 VS Code 式活动栏布局。
 * 两侧 44px 图标轨常驻;点能力图标内联推开对应面板,中栏 1fr 自适应(开/关面板即伸缩)。
 * 左轨=大纲;右轨=主编札记/设定圣经/伏笔/一致性/素材/脉络质量/记忆技能/讨论线程,各为独立面板。
 * 打开状态持久化(localStorage)。
 */
import { useState, type ReactNode } from "react";
import { ListTree, X } from "lucide-react";
import { api } from "./api";
import { useData } from "./common";
import { cn } from "./lib/utils";
import { Right, RIGHT_CAPS } from "./Right";

function usePref(key: string, def: string): [string, (v: string) => void] {
  const [v, setV] = useState<string>(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : s; } catch { return def; }
  });
  return [v, (nv: string) => { setV(nv); try { localStorage.setItem(key, nv); } catch { /* */ } }];
}

function RailBtn({ icon, label, badge, on, onClick }: {
  icon: ReactNode; label: string; badge?: number; on?: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick} title={label} aria-label={label} aria-pressed={on}
      className={cn("relative w-9 h-9 rounded-lg inline-flex items-center justify-center transition-colors",
        on ? "bg-accent text-foreground ring-1 ring-border" : "text-muted-foreground hover:bg-accent hover:text-foreground")}>
      {icon}
      {!!badge && badge > 0 && (
        <span className="absolute -top-0.5 -right-0.5 min-w-[15px] h-[15px] px-0.5 rounded-full bg-primary text-primary-foreground text-[9px] font-medium leading-[15px] text-center">{badge > 99 ? "99" : badge}</span>
      )}
    </button>
  );
}

export function WriteLayout({ work, rev, bump, left, center }: {
  work: string; rev: number; bump: () => void; left: ReactNode; center: ReactNode;
}) {
  const [leftOpen, setLeftOpen] = usePref("scribe.leftOpen", "1");
  const [rightCap, setRightCap] = usePref("scribe.rightCap", "");
  const lOpen = leftOpen === "1";

  // 轨上角标:札记+待批、未结伏笔、一致性问题
  const insights = useData(() => api.insights(work), [work, rev]);
  const pend = useData(() => api.pendingWrites(work), [work, rev]);
  const fores = useData(() => api.foreshadows(work), [work, rev]);
  const flags = useData(() => api.flags(work), [work, rev]);
  const badgeFor = (key?: string): number => {
    if (key === "insights") return (insights.data?.length ?? 0) + (pend.data?.length ?? 0);
    if (key === "foreshadow") return fores.data?.filter((f) => f.state === "planted" || f.state === "triggered").length ?? 0;
    if (key === "flags") return flags.data?.length ?? 0;
    return 0;
  };
  const activeLabel = RIGHT_CAPS.find((c) => c.key === rightCap)?.label ?? "";

  const cls = "app" + (lOpen ? " lopen" : "") + (rightCap ? " ropen" : "");
  return (
    <div className={cls}>
      {/* 左轨 */}
      <div className="rail-col l flex flex-col items-center py-2 gap-1">
        <RailBtn icon={<ListTree size={18} />} label="大纲树" on={lOpen} onClick={() => setLeftOpen(lOpen ? "0" : "1")} />
      </div>

      {/* 左面板:大纲 */}
      <div className="panel-col l">{lOpen && <div className="p-2.5">{left}</div>}</div>

      {/* 中栏:正文(自适应填充) */}
      <main className="center-col"><div className="center-inner">{center}</div></main>

      {/* 右面板:当前能力 */}
      <div className="panel-col r">
        {!!rightCap && (
          <div className="p-2.5">
            <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-border">
              <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{activeLabel}</span>
              <button onClick={() => setRightCap("")} title="关闭" aria-label="关闭面板"
                className="w-6 h-6 rounded inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent"><X size={13} /></button>
            </div>
            <Right work={work} rev={rev} bump={bump} active={rightCap} />
          </div>
        )}
      </div>

      {/* 右轨:能力活动栏 */}
      <div className="rail-col r flex flex-col items-center py-2 gap-1">
        {RIGHT_CAPS.map((c) => {
          const Icon = c.icon;
          return (
            <RailBtn key={c.key} icon={<Icon size={17} />} label={c.label}
              badge={badgeFor((c as { badge?: string }).badge)}
              on={rightCap === c.key} onClick={() => setRightCap(rightCap === c.key ? "" : c.key)} />
          );
        })}
      </div>
    </div>
  );
}
