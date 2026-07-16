import { useEffect, useMemo, useState } from 'react'
import { Plus, Search, BookText, Trash2, ArchiveRestore, Trash } from 'lucide-react'
import { api } from './api'
import { Btn, Input } from './ui'
import { Field } from './ui/Field.jsx'
import { AsyncState } from './ui/AsyncState.jsx'
import { ConfirmDialog, Dialog } from './ui/Dialog.jsx'
import { useToast } from './ui/Toast.jsx'

// 废弃时间格式化:容错 null/无效值(废弃箱条目理论上必有 archived_at,但不为脏数据崩页面)。
function fmtArchivedAt(iso) {
  if (!iso) return '废弃时间未知'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '废弃时间未知'
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// 作品库:书卡网格(章数/字数/进度)+ 搜索 + 建 + 删。借鉴 scribe2 Library。
export function Library({ works, reload, onSelect }) {
  const [title, setTitle] = useState('')
  const [createErr, setCreateErr] = useState('')
  const [q, setQ] = useState('')
  const [delTarget, setDelTarget] = useState(null)
  // works 为空时无法区分「尚未加载 / 真空库 / 父层加载失败」:挂载时自拉一次,
  // 失败给真实错误 + 重试(而不是把失败静默成一个误导性的空库页面)。
  const [loadState, setLoadState] = useState(() => ((works || []).length ? 'ready' : 'loading'))
  const [loadErr, setLoadErr] = useState('')
  const toast = useToast()

  // 废弃箱(WL-Task 3):独立于父层 works 的自有列表 + 自有加载生命周期。
  const [trash, setTrash] = useState([])
  const [restoreErr, setRestoreErr] = useState({})   // { [slug]: detail }
  const [purgeTarget, setPurgeTarget] = useState(null)
  const [purgeInput, setPurgeInput] = useState('')
  const [purgeErr, setPurgeErr] = useState('')

  const loadTrash = async () => {
    try { const r = await api.archivedWorks(); setTrash(r?.works || []) }
    catch (_) { /* 废弃箱是次要信息,加载失败不阻断主列表 */ }
  }
  useEffect(() => { loadTrash() }, [])

  const doReload = async () => {
    setLoadState('loading'); setLoadErr('')
    try { await reload(); setLoadState('ready') }
    catch (e) { setLoadErr(e?.body?.detail || e?.message || '加载失败'); setLoadState('error') }
  }
  // 仅在挂载且列表为空时自拉(有数据直接 ready,不重复请求)
  useEffect(() => { if (!(works || []).length) doReload() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  const create = async () => {
    if (!title.trim()) { toast('请填写书名', { tone: 'danger' }); return }
    setCreateErr('')
    try {
      const r = await api.createWork(title.trim())
      setTitle(''); setCreateErr(''); await reload(); onSelect({ slug: r.slug, title: r.title })
    } catch (e) {
      // 409(重名)等就地红字显示,输入保留(不清空,免得用户白打一遍)
      setCreateErr(e?.body?.detail || e?.message || '新建失败')
    }
  }
  const del = (w) => {
    if (w.slug === 'main') { toast('主书不可删除', { tone: 'danger' }); return }
    setDelTarget(w)
  }
  const restore = async (w) => {
    setRestoreErr((m) => ({ ...m, [w.slug]: '' }))
    try {
      await api.restoreWork(w.slug)
      await reload(); await loadTrash()
    } catch (e) {
      setRestoreErr((m) => ({ ...m, [w.slug]: e?.body?.detail || e?.message || '恢复失败' }))
    }
  }
  // 确认门比对须与后端对齐:后端 purge 端点 strip 后比对(title.strip() == confirm.strip()),
  // 前端若按裸串严比,用户复制书名带首尾空格就会「明明输对却点不了确认」(按钮+Enter 双锁死)。
  // 强度不降低:空名/纯空白在后端有 422 兜底(且 store 层从源头拒收空名)。
  const purgeMatch = !!purgeTarget && purgeInput.trim() === (purgeTarget.title || '').trim()
  const closePurge = () => { setPurgeTarget(null); setPurgeInput(''); setPurgeErr('') }
  const doPurge = async () => {
    setPurgeErr('')
    try {
      await api.purgeWork(purgeTarget.slug, purgeInput)
      closePurge()
      await reload(); await loadTrash()
    } catch (e) {
      setPurgeErr(e?.body?.detail || e?.message || '永久删除失败')
    }
  }
  const list = useMemo(() => (works || []).filter((w) => !q.trim() || w.title.includes(q.trim())), [works, q])
  const isEmpty = (works || []).length === 0

  return (
    <>
    <ConfirmDialog
      open={!!delTarget}
      title={`将《${delTarget?.title ?? ''}》移入废弃箱?`}
      body="该书将移入废弃箱,可随时恢复;正文与设定不会被删除。"
      danger
      confirmText="移入废弃箱"
      onConfirm={async () => { await api.deleteWork(delTarget.slug); await reload(); await loadTrash() }}
      onClose={() => setDelTarget(null)}
    />
    <Dialog open={!!purgeTarget} onClose={closePurge} labelledBy="purge-title">
      <div className="p-4">
        <div id="purge-title" className="text-f14 font-medium text-ink mb-1.5">永久删除《{purgeTarget?.title ?? ''}》?</div>
        <div className="text-f13 text-faint leading-relaxed mb-3">
          该书的正文、设定、伏笔、对话将被彻底销毁,无法恢复。请输入完整书名以确认:
        </div>
        <Input autoFocus value={purgeInput} onChange={(e) => setPurgeInput(e.target.value)}
          placeholder={purgeTarget?.title ?? ''} aria-label="确认书名"
          // IME 守卫:中文输入法候选框里按 Enter 只是选词,不该当成「确认永久删除」提交。
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing && purgeMatch) doPurge() }} />
        {purgeErr && <div role="alert" className="mt-2 text-f12 text-danger">{purgeErr}</div>}
        <div className="mt-4 flex justify-end gap-2">
          <Btn variant="ghost" onClick={closePurge}>取消</Btn>
          <Btn variant="primary" className="!bg-danger !text-white" disabled={!purgeMatch}
            onClick={doPurge}>永久删除</Btn>
        </div>
      </div>
    </Dialog>
    <div className="h-full overflow-y-auto bg-canvas">
      <div className="max-w-6xl mx-auto px-8 py-10">
        <h1 className="prose-serif text-f26 font-semibold text-ink mb-1">作品库</h1>
        <p className="text-faint text-f13 mb-6">每本书独立一库,角色/设定/章节/伏笔互不干扰。</p>

        <AsyncState
          // #4:父层已填充列表时无条件 ready——后台刷新失败(loadState='error')不得盖住已有 works
          state={isEmpty ? loadState : 'ready'}
          title={loadState === 'error' ? '作品库加载失败' : '正在载入作品库…'}
          message={loadState === 'error' ? loadErr : undefined}
          onRetry={doReload}
        >
          {isEmpty ? (
            /* 空库引导:第一部作品的显式起点(带书名输入 + 新建按钮),不是一个静默的空网格 */
            <div className="max-w-md mt-10 rounded-xl border border-line bg-surface p-6">
              <BookText size={26} className="text-brand mb-3" />
              <div className="text-body font-semibold text-ink mb-1">还没有作品</div>
              <p className="text-helper text-faint mb-4">新建第一部作品,开始限知写作。</p>
              <Field label="书名" required>
                <Input value={title} onChange={(e) => { setTitle(e.target.value); setCreateErr('') }} placeholder="如:纸命"
                  onKeyDown={(e) => { if (e.key === 'Enter') create() }} />
              </Field>
              {createErr && <div role="alert" className="mt-1.5 text-f12 text-danger">{createErr}</div>}
              <Btn variant="primary" className="mt-4" onClick={create}><Plus size={15} />新建第一部作品</Btn>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 h-10 rounded-xl border border-line bg-surface px-3 mb-5 max-w-md">
                <Search size={15} className="text-faint shrink-0" />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索作品…" aria-label="搜索作品"
                  className="flex-1 bg-transparent text-f14 text-ink outline-none placeholder:text-faint/60" />
              </div>

              {/* 1280/1440/1600 稳定网格:sm2 / lg3 / xl4 列,配 max-w-6xl 铺满而不缩在窄列 */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {list.map((w) => {
                  const words = w.word_count ?? 0
                  const goal = w.total_word_goal ?? 100000  // /works 携带真目标;无则回退默认值
                  const pct = Math.min(100, Math.round((words / goal) * 100))
                  return (
                    /* 作品卡:主「打开」按钮与独立「删除」按钮是兄弟节点——
                       删除嵌在打开按钮内(旧 span onClick)是 a11y 违规且键盘不可达 */
                    <div key={w.slug} className="group relative rounded-xl border border-line bg-surface hover:border-brand/50 hover:shadow-sm transition-all min-h-[124px]">
                      <button onClick={() => onSelect(w)} aria-label={`打开${w.title}`}
                        className="w-full h-full text-left p-4 rounded-xl cursor-pointer flex flex-col gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40">
                        <div className="flex items-start gap-2 pr-6">
                          <BookText size={16} className="text-brand shrink-0 mt-0.5" />
                          <span className="prose-serif text-f15 font-semibold text-ink leading-snug min-w-0 break-words">{w.title}</span>
                        </div>
                        {/* U-011: 后端 stats 查询失败标 stats_error → 显红字,不再假 0(作者会误读"稿子丢了") */}
                        <div className="text-f12 tnum">
                          {w.stats_error
                            ? <span className="text-danger">统计查询失败(见后端日志)</span>
                            : <span className="text-faint">{w.chapter_count ?? 0} 章 · {words.toLocaleString()} 字</span>}
                        </div>
                        <div className="mt-auto">
                          <div className="h-1.5 rounded-full bg-soft overflow-hidden">
                            <div className="h-full bg-brand rounded-full transition-all" style={{ width: pct + '%' }} />
                          </div>
                          <div className="text-meta text-faint mt-1 tnum">约 {pct}% · 目标 {(goal / 10000).toLocaleString()} 万字</div>
                        </div>
                      </button>
                      {w.slug !== 'main' && (
                        <button onClick={() => del(w)} aria-label={`删除${w.title}`} title="删除作品"
                          className="absolute top-3 right-3 w-6 h-6 rounded-md text-faint opacity-0 group-hover:opacity-100 focus-visible:opacity-100 hover:!text-danger hover:bg-danger/10 inline-flex items-center justify-center transition-opacity cursor-pointer">
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  )
                })}
              </div>

              <div className="mt-7 max-w-md">
                <div className="text-meta font-semibold uppercase tracking-wider text-faint mb-2">新建作品</div>
                <div className="flex gap-2">
                  <input value={title} onChange={(e) => { setTitle(e.target.value); setCreateErr('') }} placeholder="书名…" aria-label="书名"
                    onKeyDown={(e) => { if (e.key === 'Enter') create() }}
                    className="flex-1 h-10 rounded-xl border border-line bg-surface px-3 text-f14 text-ink outline-none focus:border-brand placeholder:text-faint/60" />
                  <Btn variant="primary" size="md" className="h-10 px-4" onClick={create}><Plus size={15} />建</Btn>
                </div>
                {createErr && <div role="alert" className="mt-1.5 text-f12 text-danger">{createErr}</div>}
              </div>
            </>
          )}
        </AsyncState>

        {/* 废弃箱:即便 works 全空(所有作品都被废弃)也必须渲染在这里——否则用户被 UI 锁死,
            无法恢复任何书(WL-Task 3 审查明确点名的可达性风险)。为 0 时整体不显示。 */}
        {trash.length > 0 && (
          <details open className="mt-8 max-w-6xl rounded-xl border border-line bg-surface">
            <summary className="cursor-pointer select-none px-4 py-3 text-f13 font-semibold text-ink">
              废弃箱({trash.length})
            </summary>
            <div className="border-t border-line divide-y divide-line">
              {trash.map((w) => (
                <div key={w.slug} className="flex items-center gap-3 px-4 py-3">
                  <BookText size={15} className="text-faint shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-f14 text-ink truncate">{w.title}</div>
                    <div className="text-f12 text-faint">{fmtArchivedAt(w.archived_at)}</div>
                    {restoreErr[w.slug] && (
                      <div role="alert" className="mt-1 text-f12 text-danger">{restoreErr[w.slug]}</div>
                    )}
                  </div>
                  <Btn variant="ghost" size="sm" onClick={() => restore(w)} aria-label={`恢复${w.title}`} title="恢复">
                    <ArchiveRestore size={13} />恢复
                  </Btn>
                  <Btn variant="ghost" size="sm" className="!text-danger" onClick={() => setPurgeTarget(w)}
                    aria-label={`永久删除${w.title}`} title="永久删除">
                    <Trash size={13} />永久删除
                  </Btn>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
    </>
  )
}
