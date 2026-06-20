import { Sun, Moon, BookOpen, ChevronDown, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { VIEWS, type ViewKey } from "./views";
import type { Work } from "./api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface AppRailProps {
  works: Work[] | null;
  current: Work | null;
  view: ViewKey;
  onView: (v: ViewKey) => void;
  onSelectWork: (w: Work) => void;
  onCreate: () => void;
  theme: string;
  onTheme: (t: string) => void;
}

export function AppRail({
  works,
  current,
  view,
  onView,
  onSelectWork,
  onCreate,
  theme,
  onTheme,
}: AppRailProps) {
  return (
    <header className="h-12 shrink-0 flex items-center border-b border-border bg-background px-3 gap-3">
      {/* 左:字标 + 书切换 */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="font-semibold tracking-wide text-primary text-sm select-none">
          SCRIBE
        </span>

        <DropdownMenu>
          <DropdownMenuTrigger
            className={cn(
              "flex items-center gap-1 px-2 py-1 rounded-md text-sm",
              "text-muted-foreground hover:text-foreground hover:bg-accent",
              "transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring",
              "max-w-[140px]"
            )}
            aria-label={current ? current.title : "选择作品"}
          >
            <BookOpen size={14} className="shrink-0" />
            <span className="truncate text-xs">
              {current ? current.title : "选择作品"}
            </span>
            <ChevronDown size={10} className="shrink-0 opacity-50" />
          </DropdownMenuTrigger>
          <DropdownMenuContent side="bottom" align="start" className="w-52">
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              作品库
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {works && works.length > 0 ? (
              works.map((w) => (
                <DropdownMenuItem
                  key={w.id}
                  onClick={() => onSelectWork(w)}
                  className={cn(
                    "cursor-pointer",
                    current?.id === w.id && "bg-accent text-accent-foreground"
                  )}
                >
                  <span className="truncate">{w.title}</span>
                  {w.genre && (
                    <span className="ml-auto text-xs text-muted-foreground shrink-0">
                      {w.genre}
                    </span>
                  )}
                </DropdownMenuItem>
              ))
            ) : (
              <DropdownMenuItem disabled className="text-muted-foreground text-xs">
                暂无作品
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onCreate} className="cursor-pointer text-primary">
              <Plus size={14} /> 新建作品
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* 分隔线 */}
      <div className="w-px h-5 bg-border shrink-0" />

      {/* 中:5 视图水平 tab */}
      <nav className="flex items-center gap-1 flex-1 min-w-0" aria-label="主导航">
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
        {theme === "dark" ? (
          <Sun size={15} />
        ) : (
          <Moon size={15} />
        )}
      </button>
    </header>
  );
}
