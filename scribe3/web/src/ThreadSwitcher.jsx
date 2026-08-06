// P0a:主编会话下拉——列表/新建/切换/改名/归档/恢复/分支/导出。
// 自门控:非线程模式(无 snapshot.thread_id,flag 关/快照缺席)渲染 null,行为回旧版。
// 浮层用 portal + fixed 定位(修真机 bug:absolute 浮层被 header 的 overflow 裁剪、
// 且 right-0 在窄栏向左溢出盖住中区)——锚定按钮正下方,右缘 clamp 进视口,永不被裁。
// 零降级:列表加载失败显式红字「不代表没有会话」;所有操作失败 danger toast,绝不装没事。
// 新建会话:单飞守卫 + 创建后绑定失败可对同一 thread_id 重试(不二次 create/fork)。
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { ChevronDown, History, Plus, Pencil, Archive, Sparkles, Download, Loader2, RefreshCw } from 'lucide-react'
import { api } from './api'
import { useContextSnapshot } from './context/ContextSnapshotContext'
import { showToast } from './ui/Toast.jsx'
import { pickLatestActiveThread } from './lib/sessionThreadOps.js'

const MENU_W = 272

export function ThreadSwitcher({ busy = false }) {
  const { snapshot, switchThread } = useContextSnapshot()
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState(null)       // {top,left} 视口坐标(fixed)
  const [threads, setThreads] = useState(null)   // null=未加载
  const [error, setError] = useState(false)
  const [creating, setCreating] = useState(false)
  // 创建成功但 switchThread 失败：保留 thread_id 供重试绑定，绝不静默停在旧会话
  const [pendingBind, setPendingBind] = useState(null) // { threadId, kind: 'fork'|'create' }
  const [binding, setBinding] = useState(false)
  const createInFlightRef = useRef(false)
  const btnRef = useRef(null)
  const menuRef = useRef(null)
  const current = snapshot?.thread_id || null
  const pull = () => api.threads()
    .then((d) => { setThreads(d.threads || []); setError(false) })
    .catch(() => { setThreads([]); setError(true) })
  useEffect(() => { if (open) pull() }, [open])
  useEffect(() => {
    if (!open) return undefined
    const onDown = (e) => {
      if (btnRef.current?.contains(e.target)) return
      if (menuRef.current?.contains(e.target)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])
  if (!current) return null   // 非线程模式:不渲染(旧行为一字不变)

  const toggle = () => {
    if (open) { setOpen(false); return }
    const r = btnRef.current?.getBoundingClientRect()
    const vw = window.innerWidth || 1280
    setPos({
      top: (r?.bottom ?? 0) + 4,
      left: Math.max(8, Math.min(r?.left ?? 8, vw - MENU_W - 8)),   // clamp 进视口,不盖中区也不出右缘
    })
    setOpen(true)
  }

  // 生成中切换=中止本轮(persistKey 变化已有 abort 机制;部分稿 _ChatTurnLog 已留痕)
  const guardBusy = () => !busy
    || window.confirm('主编正在生成:切换会话将中止本轮(已生成部分已留痕)。继续?')
  const doSwitch = (tid) => {
    if (tid === current || !guardBusy() || creating || binding) return
    setOpen(false)
    Promise.resolve(switchThread(tid)).catch(() => { /* toast 已由 switchThread 发出 */ })
  }

  const bindCreatedThread = async (threadId, kind) => {
    setBinding(true)
    try {
      await switchThread(threadId)
      setPendingBind(null)
      setOpen(false)
      showToast(kind === 'create' ? '已进入全新会话' : '已进入新会话', { tone: 'ok' })
      return true
    } catch {
      setPendingBind({ threadId, kind })
      showToast('会话已创建，但绑定到界面失败。请点「重试绑定」，勿再新建。', { tone: 'danger' })
      return false
    } finally {
      setBinding(false)
    }
  }

  // 新建会话(默认=延续):作者语义纠正——新建是为界面清洁/分类,不是失忆。
  // 走 fork(带 parent):后端拷父 summary + 近窗回溯父会话原文,主编无缝记得之前聊的;
  // title 传"新会话"(autotitle 默认集)→ 首条消息自动命名,不与父同名。
  const doNewContinue = async () => {
    if (!guardBusy() || createInFlightRef.current || binding) return
    createInFlightRef.current = true
    setCreating(true)
    setPendingBind(null)
    let createdId = null
    try {
      const t = await api.forkThread(current, { title: '新会话' })
      createdId = t?.thread_id || null
      if (!createdId) throw new Error('服务器未返回 thread_id')
      await bindCreatedThread(createdId, 'fork')
    } catch (e) {
      // bind 失败已在 bindCreatedThread 设 pendingBind + toast；此处仅处理 fork 本身失败
      if (!createdId) {
        showToast(`新建会话失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' })
      }
    } finally {
      createInFlightRef.current = false
      setCreating(false)
    }
  }
  // 全新会话(手动通道):不带任何对话历史(无 parent,注入层不回溯)。
  const doNewFresh = async () => {
    if (!guardBusy() || createInFlightRef.current || binding) return
    createInFlightRef.current = true
    setCreating(true)
    setPendingBind(null)
    let createdId = null
    try {
      const t = await api.createThread()
      createdId = t?.thread_id || null
      if (!createdId) throw new Error('服务器未返回 thread_id')
      await bindCreatedThread(createdId, 'create')
    } catch (e) {
      if (!createdId) {
        showToast(`全新会话失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' })
      }
    } finally {
      createInFlightRef.current = false
      setCreating(false)
    }
  }
  const doRetryBind = async () => {
    if (!pendingBind?.threadId || binding || createInFlightRef.current) return
    await bindCreatedThread(pendingBind.threadId, pendingBind.kind)
  }
  const doRename = async (t) => {
    const name = window.prompt('会话改名', t.title || '')
    if (name == null || !name.trim()) return
    try { await api.patchThread(t.thread_id, { title: name.trim() }); pull() }
    catch (e) { showToast(`改名失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' }) }
  }
  const doArchive = async (t) => {
    try {
      await api.patchThread(t.thread_id, { status: 'archived' })
      if (t.thread_id === current) {
        // 归档当前 → 切到剩余 active 中 updated_at 最新者(非最早创建的默认线)
        const d = await api.threads()
        const list = d.threads || []
        setThreads(list)
        const next = pickLatestActiveThread(list, t.thread_id)
        if (next) {
          try {
            await switchThread(next.thread_id)
            showToast(`当前会话已归档,已切到「${next.title || '会话'}」`, { tone: 'info' })
          } catch {
            showToast('已归档,但切换到其它会话失败,请手动选择', { tone: 'danger' })
          }
        } else {
          showToast('当前会话已归档,无其它活跃会话', { tone: 'info' })
        }
      } else {
        pull()
      }
    } catch (e) { showToast(`归档失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' }) }
  }
  const doRestore = async (t) => {
    try { await api.patchThread(t.thread_id, { status: 'active' }); pull() }
    catch (e) { showToast(`恢复失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' }) }
  }

  const active = (threads || []).filter((t) => t.status === 'active')
  const archived = (threads || []).filter((t) => t.status === 'archived')
  const curTitle = (threads || []).find((t) => t.thread_id === current)?.title || '主编讨论'
  // 惰性构造:只在 open 时求值(否则 href 等表达式在每次 render 都执行——
  // 旧测试的精简 api mock 没有 exportThreadUrl,渲染即崩,连坐整棵 ChiefDock)
  const renderMenu = () => (
    <div ref={menuRef} data-testid="thread-switcher-menu"
      style={{ position: 'fixed', top: pos?.top ?? 0, left: pos?.left ?? 8, width: MENU_W, zIndex: 90 }}
      className="rounded-lg border border-line bg-surface shadow-lg p-1 max-h-[70vh] overflow-y-auto">
      {threads == null && <div className="px-2 py-1.5 text-f12 text-faint">加载中…</div>}
      {error && (
        <div className="px-2 py-1.5 text-f12 text-danger">
          会话列表加载失败(不代表没有会话),稍后重开试试。
        </div>
      )}
      {pendingBind && (
        <div className="mx-1 mb-1 rounded border border-danger/40 bg-danger/10 px-2 py-1.5 space-y-1" data-testid="thread-bind-retry">
          <div className="text-f12 text-danger leading-snug">
            会话已创建但未绑到界面。请重试绑定（不会再建一条）。
          </div>
          <button
            type="button"
            data-testid="thread-bind-retry-btn"
            disabled={binding}
            onClick={doRetryBind}
            className="w-full flex items-center justify-center gap-1 px-2 py-1 text-f12 text-brand bg-surface border border-line rounded cursor-pointer disabled:opacity-50"
          >
            {binding ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            重试绑定
          </button>
        </div>
      )}
      {active.map((t) => (
        <div key={t.thread_id}
          className={`group flex items-center gap-1 px-2 py-1.5 rounded hover:bg-soft ${t.thread_id === current ? 'text-brand' : 'text-ink'}`}>
          <button onClick={() => doSwitch(t.thread_id)}
            className="flex-1 text-left text-f12 truncate cursor-pointer">
            {t.thread_id === current ? '✓ ' : ''}{t.title || '未命名'}
          </button>
          <button title="改名" onClick={() => doRename(t)}
            className="opacity-0 group-hover:opacity-100 text-faint hover:text-ink cursor-pointer"><Pencil size={11} /></button>
          <button title="归档" onClick={() => doArchive(t)}
            className="opacity-0 group-hover:opacity-100 text-faint hover:text-ink cursor-pointer"><Archive size={11} /></button>
        </div>
      ))}
      <div className="border-t border-line/60 mt-1 pt-1 space-y-0.5">
        <button
          type="button"
          onClick={doNewContinue}
          disabled={creating || binding}
          data-testid="thread-new-continue"
          title="主编无缝记得当前会话聊的(近窗+摘要);新会话只是界面归档分组"
          className="w-full flex items-center gap-1.5 px-2 py-1.5 text-f12 text-brand hover:bg-soft rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {creating ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          {creating ? '创建中…' : '新建会话(延续当前上下文)'}
        </button>
        <button
          type="button"
          onClick={doNewFresh}
          disabled={creating || binding}
          data-testid="thread-new-fresh"
          title="不带任何对话历史,从零开始"
          className="w-full flex items-center gap-1.5 px-2 py-1.5 text-f12 text-faint hover:bg-soft rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {creating ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
          {creating ? '创建中…' : '全新会话(不带历史)'}
        </button>
        {/* P0b:导出当前会话(md;只含对话文本与时间,不含工具输出) */}
        <a href={api.exportThreadUrl(current, 'md')} download
          className="w-full flex items-center gap-1.5 px-2 py-1.5 text-f12 text-faint hover:bg-soft rounded cursor-pointer"><Download size={12} />导出会话(.md)</a>
      </div>
      {archived.length > 0 && (
        <div className="border-t border-line/60 mt-1 pt-1">
          <div className="px-2 py-0.5 text-meta text-faint">已归档 {archived.length}</div>
          {archived.map((t) => (
            <div key={t.thread_id} className="flex items-center gap-1 px-2 py-1 text-f12 text-faint">
              <span className="flex-1 truncate">{t.title || '未命名'}</span>
              <button className="text-brand cursor-pointer hover:underline" onClick={() => doRestore(t)}>恢复</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
  return (
    <div className="relative shrink-0" data-testid="thread-switcher">
      <button ref={btnRef} onClick={toggle} title="会话(历史列表/新建/切换/管理都在这)"
        className="flex items-center gap-1 text-f12 text-faint hover:text-brand cursor-pointer max-w-[200px]">
        <History size={12} className="shrink-0" />
        <span className="truncate">{curTitle}</span><ChevronDown size={12} />
      </button>
      {open && createPortal(renderMenu(), document.body)}
    </div>
  )
}
