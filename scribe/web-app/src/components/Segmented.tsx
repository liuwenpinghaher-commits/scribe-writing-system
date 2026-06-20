import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Segmented — 分段控件
 * 供中栏「正文｜对话」等二元/多元切换使用(1.3b 接入)。
 *
 * props:
 *   value     — 当前激活 key
 *   onChange  — 切换回调
 *   options   — 选项列表 { key, label, icon? }
 */
export interface SegmentedOption {
  key: string;
  label: string;
  icon?: ReactNode;
}

export interface SegmentedProps {
  value: string;
  onChange: (key: string) => void;
  options: SegmentedOption[];
  className?: string;
}

export function Segmented({ value, onChange, options, className }: SegmentedProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-lg bg-muted p-1",
        className
      )}
      role="tablist"
    >
      {options.map((opt) => {
        const active = value === opt.key;
        return (
          <button
            key={opt.key}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.key)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1 text-sm font-medium transition-all",
              active
                ? "bg-card text-primary shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {opt.icon && (
              <span className="[&_svg]:size-3.5">{opt.icon}</span>
            )}
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
