import type { ReactNode } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Empty } from "@/components/Empty";

/**
 * StateBoundary — 异步四态包装
 * loading → Skeleton 骨架
 * error   → 错误提示 + 可选重试 Button
 * empty   → <Empty> 空状态(可自定义 emptyNode)
 * 否则    → children
 */
export interface StateBoundaryProps {
  loading: boolean;
  error: string | null;
  empty: boolean;
  emptyNode?: ReactNode;
  onRetry?: () => void;
  children: ReactNode;
}

export function StateBoundary({
  loading,
  error,
  empty,
  emptyNode,
  onRetry,
  children,
}: StateBoundaryProps) {
  if (loading) {
    return (
      <div className="flex flex-col gap-2 py-2">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-5 w-1/2" />
        <Skeleton className="h-5 w-2/3" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-3 text-sm text-destructive"
      >
        <p className="mb-2">{error}</p>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            重试
          </Button>
        )}
      </div>
    );
  }

  if (empty) {
    return emptyNode ? <>{emptyNode}</> : <Empty title="暂无内容" />;
  }

  return <>{children}</>;
}
