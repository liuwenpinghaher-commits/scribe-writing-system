// P0a:主编会话下拉——列表/新建/切换/改名/归档/恢复/分支。
// 自门控:非线程模式(无 snapshot.thread_id,flag 关/快照缺席)渲染 null,行为回旧版。
// 零降级:列表加载失败显式红字「不代表没有会话」;所有操作失败 danger toast,绝不装没事。
import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Plus, Pencil, Archive, GitBranch, Download } from 'lucide-react'
import { api } from './api'
import { useContextSnapshot } from './context/ContextSnapshotContext'
import { showToast } from './ui/Toast.jsx'

export function ThreadSwitcher({ busy = false }) {
  const { snapshot, switchThread } = useContextSnapshot()
  const [open, setOpen] = useState(false)
  const [threads, setThreads] = useState(null)   // null=未加载
  const [error, setError] = useState(false)
  const boxRef = useRef(null)
  const current = snapshot?.thread_id || null
  const pull = () => api.threads()
    .then((d) => { setThreads(d.threads || []); setError(false) })
    .catch(() => { setThreads([]); setError(true) })
  useEffect(() => { if (open) pull() }, [open])
  useEffect(() => {
    if (!open) return undefined
    const onDown = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open])
  if (!current) return null   // 非线程模式:不渲染(旧行为一字不变)

  // 生成中切换=中止本轮(persistKey 变化已有 abort 机制;部分稿 _ChatTurnLog 已留痕)
  const guardBusy = () => !busy
    || window.confirm('主编正在生成:切换会话将中止本轮(已生成部分已留痕)。继续?')
  const doSwitch = (tid) => { if (tid === current || !guardBusy()) return; setOpen(false); switchThread(tid) }
  const doNew = async () => {
    if (!guardBusy()) return
    try { const t = await api.createThread(); setOpen(false); switchThread(t.thread_id) }
    catch (e) { showToast(`新建会话失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' }) }
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
        // 归档当前会话 → 显式切到默认(剩余最早 active),toast 告知(解析链切换必可见)
        const d = await api.threads()
        const next = (d.threads || []).find((x) => x.status === 'active')
        if (next) { switchThread(next.thread_id); showToast('当前会话已归档,已切到默认会话', { tone: 'info' }) }
      }
      pull()
    } catch (e) { showToast(`归档失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' }) }
  }
  const doFork = async () => {
    try { const t = await api.forkThread(current, {}); setOpen(false); switchThread(t.thread_id) }
    catch (e) { showToast(`分支失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' }) }
  }
  const doRestore = async (t) => {
    try { await api.patchThread(t.thread_id, { status: 'active' }); pull() }
    catch (e) { showToast(`恢复失败:${e?.body?.detail || e?.message || ''}`, { tone: 'danger' }) }
  }

  const active = (threads || []).filter((t) => t.status === 'active')
  const archived = (threads || []).filter((t) => t.status === 'archived')
  const curTitle = (threads || []).find((t) => t.thread_id === current)?.title || '主编讨论'
  return (
    <div ref={boxRef} className="relative shrink-0" data-testid="thread-switcher">
      <button onClick={() => setOpen((v) => !v)} title="会话(历史/新建/管理)"
        className="flex items-center gap-1 text-f12 text-faint hover:text-brand cursor-pointer max-w-[180px]">
        <span className="truncate">{curTitle}</span><ChevronDown size={12} />
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-1 w-64 rounded-lg border border-line bg-surface shadow-lg p-1">
          {threads == null && <div className="px-2 py-1.5 text-f12 text-faint">加载中…</div>}
          {error && (
            <div className="px-2 py-1.5 text-f12 text-danger">
              会话列表加载失败(不代表没有会话),稍后重开试试。
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
            <button onClick={doNew}
              className="w-full flex items-center gap-1.5 px-2 py-1.5 text-f12 text-brand hover:bg-soft rounded cursor-pointer"><Plus size={12} />新建会话</button>
            <button onClick={doFork} title="带早期摘要,消息从空开始"
              className="w-full flex items-center gap-1.5 px-2 py-1.5 text-f12 text-faint hover:bg-soft rounded cursor-pointer"><GitBranch size={12} />从当前分支</button>
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
      )}
    </div>
  )
}
