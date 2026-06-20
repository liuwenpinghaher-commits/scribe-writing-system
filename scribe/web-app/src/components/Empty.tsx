import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

/**
 * Empty — 统一空状态组件
 * props:
 *   icon?   — 可选图标节点(lucide-react 等)
 *   title   — 主提示文字
 *   hint?   — 次级说明
 *   action? — CTA 配置 { label, onClick }
 */
export interface EmptyProps {
  icon?: ReactNode;
  title: string;
  hint?: string;
  action?: { label: string; onClick: () => void };
  className?: string;
}

export function Empty({ icon, title, hint, action, className }: EmptyProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 py-8 px-4 text-center text-muted-foreground",
        className
      )}
    >
      {icon && (
        <span className="mb-1 opacity-40 [&_svg]:size-8">{icon}</span>
      )}
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="text-xs opacity-70">{hint}</p>}
      {action && (
        <Button
          variant="secondary"
          size="sm"
          className="mt-2"
          onClick={action.onClick}
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}
