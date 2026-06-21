/**
 * WriteLayout.tsx — 写作台三栏布局,正文为王。
 * 侧栏三态:智能(默认,收成图标轨+相关性角标)/ 钉住(展开密集栏)/ 抽屉(点轨图标滑出)。
 * 钉住状态持久化(localStorage)。左=大纲树,右=主编/设定面板。
 */
import { useState, type ReactNode } from "react";
import { ListTree, NotebookPen, Pin, PinOff, X } from "lucide-react";
import { api } from "./api";
import { useData } from "./common";
import { cn } from "./lib/utils";

function usePref(key: string, def: boolean): [boolean, (v: boolean) => void] {
  const [v, setV] = useState<boolean>(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : s === "1"; } catch { return def; }
  });
  return [v, (nv: boolean) => { setV(nv); try { localStorage.setItem(key, nv ? "1" : "0"); } catch { /* */ } }];
}

function RailBtn({ icon, label, badge, on, onClick }: {
  icon: ReactNode; label: string; badge?: number; on?: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick} title={label} aria-label={label}
      className={cn("relative w-9 h-9 rounded-lg inline-flex items-center justify-center transition-colors",
        on ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent hover:text-foreground")}>
      {icon}
      {!!badge && badge > 0 && (
        <span className="absolute top-1 right-1 min-w-[14px] h-[14px] px-0.5 rounded-full bg-primary text-primary-foreground text-[9px] leading-[14px] text-center">{badge > 9 ? "9+" : badge}</span>
      )}
    </button>
  );
}

function RailHeader({ title, pinned, onPin, onClose }: {
  title: string; pinned?: boolean; onPin: () => void; onClose?: () => void;
}) {
  return (
    <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-border">
      <span className="text-xs font-medium text-muted-foreground">{title}</span>
      <div className="flex items-center gap-0.5">
        <button onClick={onPin} title={pinned ? "取消固定(收起)" : "固定在侧栏"}
          className="w-6 h-6 rounded inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent">
          {pinned ? <PinOff size={13} /> : <Pin size={13} />}
        </button>
        {onClose && (
          <button onClick={onClose} title="关闭" className="w-6 h-6 rounded inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-accent">
            <X size={13} />
          </button>
        )}
      </div>
    </div>
  );
}

export function WriteLayout({ work, rev, left, center, right }: {
  work: string; rev: number; left: ReactNode; center: ReactNode; right: ReactNode;
}) {
  const [lpin, setLpin] = usePref("scribe.lpin", false);
  const [rpin, setRpin] = usePref("scribe.rpin", false);
  const [drawer, setDrawer] = useState<null | "left" | "right">(null);
  // 智能角标:右栏有新札记时,轨上点提示
  const insights = useData(() => api.insights(work), [work, rev]);
  const newCount = insights.data?.length ?? 0;

  const cls = "app" + (lpin ? " lpin" : "") + (rpin ? " rpin" : "");
  return (
    <div className={cls}>
      {/* 左:大纲树 */}
      <aside className="col left">
        {lpin ? (
          <div className="p-2.5">
            <RailHeader title="大纲" pinned onPin={() => setLpin(false)} />
            {left}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1 py-2">
            <RailBtn icon={<ListTree size={17} />} label="大纲树" on={drawer === "left"} onClick={() => setDrawer(drawer === "left" ? null : "left")} />
            <button onClick={() => { setLpin(true); setDrawer(null); }} title="固定大纲在侧栏"
              className="w-9 h-7 rounded-lg inline-flex items-center justify-center text-muted-foreground hover:bg-accent hover:text-foreground"><Pin size={13} /></button>
          </div>
        )}
      </aside>

      {/* 中:正文(居中限宽) */}
      <main className="col center"><div className="center-inner">{center}</div></main>

      {/* 右:主编 / 设定 */}
      <aside className="col right">
        {rpin ? (
          <div className="p-2.5">
            <RailHeader title="主编 · 设定" pinned onPin={() => setRpin(false)} />
            {right}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1 py-2">
            <RailBtn icon={<NotebookPen size={17} />} label="主编 · 设定 · 札记" badge={newCount} on={drawer === "right"} onClick={() => setDrawer(drawer === "right" ? null : "right")} />
            <button onClick={() => { setRpin(true); setDrawer(null); }} title="固定面板在侧栏"
              className="w-9 h-7 rounded-lg inline-flex items-center justify-center text-muted-foreground hover:bg-accent hover:text-foreground"><Pin size={13} /></button>
          </div>
        )}
      </aside>

      {/* 抽屉 */}
      {drawer === "left" && !lpin && (
        <>
          <div className="side-scrim" onClick={() => setDrawer(null)} />
          <div className="side-drawer left p-2.5">
            <RailHeader title="大纲" onPin={() => { setLpin(true); setDrawer(null); }} onClose={() => setDrawer(null)} />
            {left}
          </div>
        </>
      )}
      {drawer === "right" && !rpin && (
        <>
          <div className="side-scrim" onClick={() => setDrawer(null)} />
          <div className="side-drawer right p-2.5">
            <RailHeader title="主编 · 设定" onPin={() => { setRpin(true); setDrawer(null); }} onClose={() => setDrawer(null)} />
            {right}
          </div>
        </>
      )}
    </div>
  );
}
