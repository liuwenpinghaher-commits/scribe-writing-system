import { createContext, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { ApiError } from "./api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/* ---------- Toast(独立层,aria-live;审查 #10/#13) ---------- */
type Toast = { id: number; msg: string; kind: "ok" | "err" };
const ToastCtx = createContext<(msg: string, kind?: "ok" | "err") => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = (msg: string, kind: "ok" | "err" = "ok") => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, msg, kind }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), kind === "err" ? 5000 : 3000);
  };
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite" aria-atomic="true">
        {items.map((t) => (
          <div key={t.id} className={"toast" + (t.kind === "err" ? " err" : "")} role="status">{t.msg}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : e instanceof Error ? e.message : String(e));
export { errMsg };

/* ---------- 防重入 + 加载态按钮(审查 #2/#16) ---------- */
export function Btn({
  onClick, children, variant = "primary", className = "", title, disabled,
}: {
  onClick: () => void | Promise<unknown>; children: ReactNode;
  variant?: "primary" | "ghost" | "danger"; className?: string; title?: string; disabled?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  // 统一走 shadcn Button:primary→default · ghost→ghost · danger→ghost+红字(克制,不用实心红块)
  const v = variant === "primary" ? "default" : "ghost";
  return (
    <Button
      variant={v} size="sm" title={title} disabled={busy || disabled}
      className={cn(variant === "danger" && "text-destructive", className)}
      onClick={async () => {
        if (busy) return; // 防重复提交
        try { setBusy(true); await onClick(); }
        catch (e) { toast(errMsg(e), "err"); }
        finally { setBusy(false); }
      }}
    >
      {busy ? <span className="spinner" aria-hidden /> : null} {children}
    </Button>
  );
}

/* ---------- 统一加载/错误/空 数据 hook(审查 #3) ---------- */
export function useData<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fnRef = useRef(fn); fnRef.current = fn;
  const reload = useCallbackSafe(async () => {
    setLoading(true); setError(null);
    try { setData(await fnRef.current()); }
    catch {
      // 瞬时 404/网络抖动(如后端重启)→ 自动重试一次再报错
      try { await new Promise((r) => setTimeout(r, 400)); setData(await fnRef.current()); }
      catch (e2) { setError(errMsg(e2)); }
    }
    finally { setLoading(false); }
  });
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, deps);
  return { data, loading, error, reload };
}

// React 18 没导出 useCallback 拼写差异保护:本项目用标准 useCallback
function useCallbackSafe<T extends (...a: never[]) => unknown>(cb: T): T {
  const ref = useRef(cb); ref.current = cb;
  return useRef(((...a: never[]) => ref.current(...a)) as T).current;
}

/* ---------- 加载/错误/空 渲染包装 ---------- */
export function State({ loading, error, empty, emptyText = "空", children, onRetry }: {
  loading: boolean; error: string | null; empty: boolean; emptyText?: string;
  children: ReactNode; onRetry?: () => void;
}) {
  if (loading) return <div className="empty">加载中…</div>;
  if (error) return (
    <div className="error" role="alert">
      {error}{onRetry ? <> · <button className="ghost sm" onClick={onRetry}>重试</button></> : null}
    </div>
  );
  if (empty) return <div className="empty">{emptyText}</div>;
  return <>{children}</>;
}
