import { useCallback } from 'react'
import { Toaster as SonnerToaster, toast as sonnerToast } from 'sonner'

// 统一 toast:底层换成 sonner(更稳的进出场/堆叠/可访问性)。
// 保留既有调用签名 toast(msg, { tone, duration }) —— 各调用点(ContainerOutline/
// WriteLayout/ChapterStudio/Library…)无需改动。
//
// 对外 tone 词表(唯一四词,别再直传 sonner 的 success/error):
//   'ok'     → success(成功/完成)
//   'danger' → error  (失败/破坏性/断连)
//   'warn'   → warning(风险提示)
//   'info'   → info   (中性信息)
//   其它/缺省 → 默认(无语义中性 toast)
export function showToast(msg, opts = {}) {
  const tone = opts.tone || 'ink'
  // action {label, onClick}:可点动作(断头修复#8:软门"去补"此前只有文案无入口)
  const o = (opts.duration || opts.action || opts.cancel)
    ? { ...(opts.duration ? { duration: opts.duration } : {}),
        ...(opts.action ? { action: opts.action } : {}),
        ...(opts.cancel ? { cancel: opts.cancel } : {}) }   // R2-10:第二动作(如「不再提醒」静音)
    : undefined
  if (tone === 'danger') return sonnerToast.error(msg, o)
  if (tone === 'ok') return sonnerToast.success(msg, o)
  if (tone === 'warn') return sonnerToast.warning(msg, o)
  if (tone === 'info') return sonnerToast.info(msg, o)
  return sonnerToast(msg, o)
}

// 主动关闭某条 toast(showToast 返回的 id);用于把「进行中」提示替换成结果提示。
export function dismissToast(id) {
  if (id != null) sonnerToast.dismiss(id)
}

// 兼容旧用法:组件里 const toast = useToast(); toast('xx', { tone })
export const useToast = () => {
  return useCallback((msg, opts) => showToast(msg, opts), [])
}

// 全局挂载点(App 顶层渲染一次)。沿用主题色变量,深浅色自适应。
export function ToastHost() {
  return (
    <SonnerToaster
      position="bottom-center"
      toastOptions={{
        style: {
          background: 'var(--color-surface)',
          color: 'var(--color-ink)',
          border: '1px solid var(--color-line)',
          fontSize: '12.5px',
        },
      }}
    />
  )
}

// 兼容旧 import { ToastProvider }:现在只是透传(<Toaster/> 由 App 的 ToastHost 挂)。
export function ToastProvider({ children }) {
  return children
}
