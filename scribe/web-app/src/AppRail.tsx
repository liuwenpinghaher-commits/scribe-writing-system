import { Sun, Moon, BookOpen, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { VIEWS, type ViewKey } from "./views";
import type { Work } from "./api";

interface AppRailProps {
  current: Work | null;
  view: ViewKey;
  onView: (v: ViewKey) => void;
  onOpenLibrary: () => void;   // 点书名 → 回选书页(可靠切书)
  theme: string;
  onTheme: (t: string) => void;
}

export function AppRail({ current, view, onView, onOpenLibrary, theme, onTheme }: AppRailProps) {
  return (
    <header className="h-12 shrink-0 flex items-center border-b border-border bg-background px-3 gap-3">
      {/* 左:字标 + 书切换(普通按钮,点了回选书页) */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="font-semibold tracking-wide text-primary text-sm select-none">SCRIBE</span>
        <button
          onClick={onOpenLibrary}
          title="切换 / 选择作品"
          className={cn(
            "flex items-center gap-1 px-2 py-1 rounded-md text-sm max-w-[160px]",
            "text-muted-foreground hover:text-foreground hover:bg-accent",
            "transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring"
          )}
        >
          <BookOpen size={14} className="shrink-0" />
          <span className="truncate text-xs">{current ? current.title : "选择作品"}</span>
          <ChevronDown size={10} className="shrink-0 opacity-50" />
        </button>
      </div>

      <div className="w-px h-5 bg-border shrink-0" />

      {/* 中:5 视图水平 tab */}
      <nav className="flex items-center gap-1 flex-1 min-w-0 overflow-x-auto" aria-label="主导航">
        {VIEWS.map(({ key, label, icon: Icon }) => {
          const isActive = view === key;
          return (
            <button
              key={key}
              onClick={() => onView(key)}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm transition-colors duration-150 relative shrink-0",
                isActive
                  ? "text-primary font-medium after:absolute after:bottom-[-7px] after:left-0 after:right-0 after:h-0.5 after:bg-primary after:rounded-full"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
            >
              <Icon size={14} className="shrink-0" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          );
        })}
      </nav>

      {/* 右:主题切换 */}
      <button
        onClick={() => onTheme(theme === "dark" ? "light" : "dark")}
        title={theme === "dark" ? "切换浅色" : "切换深色"}
        aria-label={theme === "dark" ? "切换浅色" : "切换深色"}
        className={cn(
          "flex items-center justify-center w-8 h-8 rounded-md shrink-0",
          "text-muted-foreground hover:text-foreground hover:bg-accent",
          "transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring"
        )}
      >
        {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
      </button>
    </header>
  );
}
