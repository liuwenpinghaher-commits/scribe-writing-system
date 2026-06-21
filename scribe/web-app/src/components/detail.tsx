/**
 * detail.tsx — 全系统统一的「详情/属性」风格原语(Notion/Linear 风)。
 * 标签左·值右、可点击进入编辑、分区绿条粗标题。详情面板与编辑表单共用同一套,
 * 一处定义、处处一致。关键布局用内联 style 兜底,不依赖可能未生成的任意值工具类。
 *
 * 用法:
 *   <DetailHeader kicker="角色"><InlineText big v={name} on={setName} /></DetailHeader>
 *   <Section title="身份"><Row label="动机"><InlineText v={m} on={setM} ph="他想要什么" /></Row></Section>
 *   只读展示:<Row label="状态"><Val>已触发</Val></Row>
 */
import { useState } from "react";

export const HAIR = "color-mix(in srgb, var(--border) 55%, transparent)";
type ChangeFn = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;

const focusEnd = (el: HTMLInputElement | HTMLTextAreaElement | null) => {
  if (!el) return; el.focus();
  const n = el.value.length; try { el.setSelectionRange(n, n); } catch { /* */ }
};

/** 点击进入编辑、平时纯展示。失焦/Esc 回展示,Enter 提交单行。 */
export function InlineText({ v, on, ph, multiline, rows, big }: {
  v: string; on: ChangeFn; ph?: string; multiline?: boolean; rows?: number; big?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const sz = big ? "text-2xl font-bold text-foreground" : "text-sm";
  if (editing) {
    const cls = `w-full bg-transparent rounded-md px-2 py-1.5 outline-none transition-colors focus:bg-muted focus:ring-1 focus:ring-ring/30 placeholder:text-muted-foreground/40 ${sz}`;
    return multiline
      ? <textarea ref={focusEnd} value={v} onChange={on} placeholder={ph} rows={rows ?? 3} onBlur={() => setEditing(false)}
          onKeyDown={(ev) => { if (ev.key === "Escape") (ev.target as HTMLTextAreaElement).blur(); }}
          className={cls + " resize-none leading-relaxed"} />
      : <input ref={focusEnd} value={v} onChange={on} placeholder={ph} onBlur={() => setEditing(false)}
          onKeyDown={(ev) => { if (ev.key === "Enter" || ev.key === "Escape") (ev.target as HTMLInputElement).blur(); }}
          className={cls} />;
  }
  return (
    <div onClick={() => setEditing(true)} title="点击编辑" style={{ minHeight: 34 }}
      className={`px-2 py-1.5 rounded-md cursor-text hover:bg-muted/40 transition-colors flex items-center ${sz}`}>
      {v
        ? <span className={multiline ? "whitespace-pre-wrap" : "truncate"}>{v}</span>
        : <span className={`text-muted-foreground/35 font-normal truncate ${big ? "text-2xl" : "text-sm"}`}>{ph || "添加…"}</span>}
    </div>
  );
}

/** 只读值(展示面板用,与 InlineText 视觉对齐但不可编辑) */
export function Val({ children, muted, pre }: { children: React.ReactNode; muted?: boolean; pre?: boolean }) {
  return (
    <div className={`px-2 py-1.5 text-sm flex items-center min-h-[34px] ${muted ? "text-muted-foreground" : "text-foreground"} ${pre ? "whitespace-pre-wrap" : ""}`} style={{ minHeight: 34 }}>
      {children}
    </div>
  );
}

/** 标签左/值右一行(短字段)。内联 grid 保证两列。 */
export function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid items-center gap-3" style={{ gridTemplateColumns: "100px minmax(0,1fr)", borderBottom: `1px solid ${HAIR}` }}>
      <span className="text-xs text-muted-foreground select-none">{label}</span>
      <div className="min-w-0">{children}</div>
    </label>
  );
}

/** 标签上/值下整行(多行/长字段) */
export function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col pb-1" style={{ borderBottom: `1px solid ${HAIR}` }}>
      <span className="text-xs text-muted-foreground select-none pt-0.5">{label}</span>
      {children}
    </label>
  );
}

/** 分区标题:绿色竖条 + 粗黑字,右侧可挂操作 */
export function Section({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2 mt-6 mb-2">
        <span style={{ width: 3, height: 15, background: "var(--accent)", borderRadius: 2, flexShrink: 0 }} />
        <span className="text-sm font-bold text-foreground">{title}</span>
        {action && <div className="ml-auto">{action}</div>}
      </div>
      {children}
    </div>
  );
}

/** 文档头:类型小标(品牌色)+ 大标题区,底部分隔 */
export function DetailHeader({ kicker, children }: { kicker: string; children: React.ReactNode }) {
  return (
    <div className="pb-3 mb-1" style={{ borderBottom: "1px solid var(--border)" }}>
      <div className="text-xs uppercase tracking-wider px-2 mb-0.5" style={{ color: "var(--accent)" }}>{kicker}</div>
      {children}
    </div>
  );
}
