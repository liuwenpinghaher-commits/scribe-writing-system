import { Sun, Moon, BookOpen, ChevronDown } from "lucide-react";
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
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "@/components/ui/sidebar";

interface AppRailProps {
  works: Work[] | null;
  current: Work | null;
  view: ViewKey;
  onView: (v: ViewKey) => void;
  onSelectWork: (w: Work) => void;
  theme: string;
  onTheme: (t: string) => void;
}

export function AppRail({
  works,
  current,
  view,
  onView,
  onSelectWork,
  theme,
  onTheme,
}: AppRailProps) {
  return (
    <SidebarProvider
      defaultOpen={true}
      className="w-14 shrink-0 h-screen min-h-0"
      style={
        {
          "--sidebar-width": "56px",
          "--sidebar-width-icon": "56px",
        } as React.CSSProperties
      }
    >
      <Sidebar
        collapsible="none"
        className="border-r border-border bg-sidebar h-full"
      >
        {/* 顶部:书切换 dropdown */}
        <SidebarHeader className="p-0 pt-2">
          <SidebarMenu>
            <SidebarMenuItem>
              <DropdownMenu>
                <DropdownMenuTrigger
                  className={cn(
                    "flex flex-col items-center justify-center h-12 w-full px-1 gap-0",
                    "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    "text-sidebar-foreground transition-colors duration-150",
                    "outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  )}
                  aria-label={current ? current.title : "选择作品"}
                >
                  <BookOpen size={18} className="shrink-0" />
                  <ChevronDown size={10} className="mt-0.5 opacity-50" />
                </DropdownMenuTrigger>
                <DropdownMenuContent side="right" align="start" className="w-52">
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
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>

        {/* 中部:5 视图导航按钮 */}
        <SidebarContent className="p-0 mt-1">
          <SidebarGroup className="p-0">
            <SidebarMenu>
              {VIEWS.map(({ key, label, icon: Icon }) => {
                const isActive = view === key;
                return (
                  <SidebarMenuItem key={key}>
                    <SidebarMenuButton
                      onClick={() => onView(key)}
                      isActive={isActive}
                      tooltip={label}
                      className={cn(
                        "flex flex-col items-center justify-center h-12 w-full rounded-none px-1 gap-0.5",
                        isActive
                          ? "bg-accent text-accent-foreground font-medium"
                          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                      )}
                    >
                      <Icon size={18} className="shrink-0" />
                      <span className="text-[9px] leading-none opacity-80 truncate max-w-full px-0.5">
                        {label.length > 4 ? label.slice(0, 4) : label}
                      </span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroup>
        </SidebarContent>

        {/* 底部:主题切换 */}
        <SidebarFooter className="p-0 pb-2">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={() => onTheme(theme === "dark" ? "light" : "dark")}
                tooltip={theme === "dark" ? "切换浅色" : "切换深色"}
                className={cn(
                  "flex flex-col items-center justify-center h-12 w-full rounded-none px-1 gap-0",
                  "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                )}
              >
                {theme === "dark" ? (
                  <Sun size={18} className="shrink-0" />
                ) : (
                  <Moon size={18} className="shrink-0" />
                )}
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarFooter>
      </Sidebar>
    </SidebarProvider>
  );
}
