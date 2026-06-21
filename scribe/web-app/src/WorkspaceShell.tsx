/**
 * WorkspaceShell.tsx — 全应用共享的工作区骨架(写作台 / 设定库 / … 共用)。
 * VS Code 式活动栏:[左轨][左面板][中区 自适应][右面板][右轨],面板关时该列 0、开则推开中区。
 * 每个视图只需提供:中区主工作面 + 左/右轨能力(render 闭包)。主编对话 = 右轨一个能力,处处可用。
 * 面板宽度可拖拽(按 ns 命名空间持久化),激活能力由父级持有(便于「讨论这段/这个」编程式开对话)。
 */
import { useEffect, useState } from "react";
import { cn } from "./lib/utils";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "./components/ui/tooltip";

export function useStrPref(key: string, def: string): [string, (v: string) => void] {
  const [v, setV] = useState<string>(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : s; } catch { return def; }
  });
  return [v, (nv: string) => { setV(nv); try { localStorage.setItem(key, nv); } catch { /* */ } }];
}
export function useNumPref(key: string, def: number): [number, (v: number) => void] {
  const [v, setV] = useState<number>(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : Number(s) || def; } catch { return def; }
  });
  useEffect(() => { try { localStorage.setItem(key, String(v)); } catch { /* */ } }, [key, v]);
  return [v, setV];
}

export interface RailCap {
  key: string;
  label: string;
  icon: React.ComponentType<{ size?: number }>;
  badge?: number;
  render: () => React.ReactNode;
}
export interface RailSide {
  caps: RailCap[];
  active: string;                 // "" = 全关
  onActive: (k: string) => void;
  variant?: "panel" | "switch";   // panel(默认)=点开侧面板;switch=纯切换器,不开面板(由父级用 active 渲染中区)
}

function RailButton({ icon, label, badge, on, onClick, side }: {
  icon: React.ReactNode; label: string; badge?: number; on?: boolean; onClick: () => void; side: "left" | "right";
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

export function WorkspaceShell({ ns, center, left, right }: {
  ns: string;                     // 宽度持久化命名空间(如 "write" / "codex")
  center: React.ReactNode;
  left?: RailSide;
  right?: RailSide;
}) {
  const [lw, setLw] = useNumPref(`scribe.${ns}.lw`, 232);
  const [rw, setRw] = useNumPref(`scribe.${ns}.rw`, 340);
  const lActive = left?.active ?? "";
  const rActive = right?.active ?? "";
  const lSwitch = left?.variant === "switch";   // 切换器:占轨不占面板
  const rSwitch = right?.variant === "switch";
  const lOpen = !!left && !lSwitch && !!lActive;
  const rOpen = !!right && !rSwitch && !!rActive;
  const leftCap = left?.caps.find((c) => c.key === lActive);
  const rightCap = right?.caps.find((c) => c.key === rActive);

  const startResize = (which: "l" | "r") => (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = which === "l" ? lw : rw;
    const onMove = (ev: MouseEvent) => {
      const dx = ev.clientX - startX;
      const w = Math.max(180, Math.min(720, which === "l" ? startW + dx : startW - dx));
      (which === "l" ? setLw : setRw)(w);
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = ""; document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    document.body.style.cursor = "col-resize"; document.body.style.userSelect = "none";
  };

  const cls = "app" + (lOpen ? " lopen" : "") + (rOpen ? " ropen" : "");
  return (
    <TooltipProvider delay={0}>
      <div className={cls} style={{ ["--lw" as string]: `${lw}px`, ["--rw" as string]: `${rw}px` }}>
        {/* 左轨 */}
        <div className="rail-col l flex flex-col items-center py-2 gap-1">
          {left?.caps.map((c) => {
            const Icon = c.icon;
            return <RailButton key={c.key} icon={<Icon size={18} />} label={c.label} side="right" badge={c.badge}
              on={lActive === c.key} onClick={() => left.onActive(lSwitch ? c.key : (lActive === c.key ? "" : c.key))} />;
          })}
        </div>

        {/* 左面板 */}
        <div className="panel-col l">{lOpen && leftCap && <div className="h-full">{leftCap.render()}</div>}</div>

        {/* 中区:主工作面(自适应) */}
        <main className="center-col">{center}</main>

        {/* 右面板:当前能力 */}
        <div className="panel-col r">
          {rOpen && rightCap && (
            <div className="flex flex-col h-full min-h-0">
              <div className="flex items-center h-9 shrink-0 px-3 border-b border-border">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{rightCap.label}</span>
              </div>
              <div className="flex-1 min-h-0">{rightCap.render()}</div>
            </div>
          )}
        </div>

        {/* 右轨:能力活动栏 */}
        <div className="rail-col r flex flex-col items-center py-2 gap-1">
          {right?.caps.map((c) => {
            const Icon = c.icon;
            return <RailButton key={c.key} icon={<Icon size={17} />} label={c.label} side="left" badge={c.badge}
              on={rActive === c.key} onClick={() => right.onActive(rSwitch ? c.key : (rActive === c.key ? "" : c.key))} />;
          })}
        </div>

        {/* 拖拽改宽 */}
        {lOpen && <div className="app-resizer" style={{ left: `calc(44px + ${lw}px - 3px)` }} onMouseDown={startResize("l")} />}
        {rOpen && <div className="app-resizer" style={{ right: `calc(44px + ${rw}px - 3px)` }} onMouseDown={startResize("r")} />}
      </div>
    </TooltipProvider>
  );
}
