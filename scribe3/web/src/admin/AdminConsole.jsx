/**
 * 管理台：账号 CRUD、跨账号书籍、写路径日志、操作审计。
 * 仅 role=admin 可见；账号/书籍/审计走 /admin/*，写路径日志走 /debug/run-cards。
 */
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import {
  Users, BookOpen, ScrollText, LayoutDashboard, RefreshCw,
  Plus, Shield, UserX, KeyRound, LogOut, Archive, RotateCcw, Trash2,
  ArrowLeft, PenLine, History,
} from 'lucide-react'
import { RunLogsPage } from './RunLogsPage'

const TABS = [
  { key: 'overview', label: '总览', icon: LayoutDashboard },
  { key: 'users', label: '账号', icon: Users },
  { key: 'works', label: '书籍', icon: BookOpen },
  { key: 'run-logs', label: '运行链路', icon: History },
  { key: 'audit', label: '审计', icon: ScrollText },
]

function fmtTs(ts) {
  if (ts == null || ts === '') return '—'
  const n = Number(ts)
  if (!Number.isFinite(n) || n <= 0) return '—'
  try {
    return new Date(n * 1000).toLocaleString()
  } catch {
    return '—'
  }
}

function Err({ e }) {
  if (!e) return null
  const msg = e?.body?.detail || e?.message || String(e)
  return <div className="text-f12 text-red-600 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-md px-3 py-2 mb-3">{msg}</div>
}

function Field({ label, children }) {
  return (
    <label className="block text-f12 mb-2">
      <span className="text-faint mb-1 block">{label}</span>
      {children}
    </label>
  )
}

const inputCls = 'w-full px-2.5 py-1.5 rounded-md border border-line bg-surface text-f13 outline-none focus:ring-2 focus:ring-brand'
const btnCls = 'px-2.5 py-1.5 rounded-md text-f12 border border-line hover:bg-soft cursor-pointer'
const btnPrimary = 'px-2.5 py-1.5 rounded-md text-f12 bg-brand text-white hover:opacity-90 cursor-pointer'

export function AdminConsole({ onExit, hasWork = false }) {
  const [tab, setTab] = useState('overview')
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  // users
  const [users, setUsers] = useState({ items: [], total: 0 })
  const [uq, setUq] = useState('')
  const [uRole, setURole] = useState('')
  const [uStatus, setUStatus] = useState('')
  const [selUser, setSelUser] = useState(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState({
    username: '', password: '', role: 'author', display_name: '', note: '',
  })
  const [pwd, setPwd] = useState('')

  // works
  const [works, setWorks] = useState({ items: [], total: 0 })
  const [wq, setWq] = useState('')
  const [wOwner, setWOwner] = useState('')
  const [wArch, setWArch] = useState('all')
  const [newWork, setNewWork] = useState({ title: '', owner_user_id: '', slug: '' })
  const [transfer, setTransfer] = useState({ slug: '', new_owner: '' })

  // audit
  const [audit, setAudit] = useState({ items: [], total: 0 })

  const loadSummary = useCallback(async () => {
    setError(null)
    try {
      setSummary(await api.adminSummary())
    } catch (e) {
      setError(e)
    }
  }, [])

  const loadUsers = useCallback(async () => {
    setError(null)
    try {
      setUsers(await api.adminUsers({
        q: uq || undefined,
        role: uRole || undefined,
        status: uStatus || undefined,
        limit: 100,
      }))
    } catch (e) {
      setError(e)
    }
  }, [uq, uRole, uStatus])

  const loadWorks = useCallback(async () => {
    setError(null)
    try {
      setWorks(await api.adminWorks({
        q: wq || undefined,
        owner: wOwner || undefined,
        archived: wArch,
        limit: 200,
      }))
    } catch (e) {
      setError(e)
    }
  }, [wq, wOwner, wArch])

  const loadAudit = useCallback(async () => {
    setError(null)
    try {
      setAudit(await api.adminAudit({ limit: 80 }))
    } catch (e) {
      setError(e)
    }
  }, [])

  useEffect(() => {
    if (tab === 'overview') loadSummary()
    if (tab === 'users') loadUsers()
    if (tab === 'works') loadWorks()
    if (tab === 'audit') loadAudit()
  }, [tab, loadSummary, loadUsers, loadWorks, loadAudit])

  const refreshAll = async () => {
    setBusy(true)
    try {
      await Promise.all([loadSummary(), loadUsers(), loadWorks(), loadAudit()])
    } finally {
      setBusy(false)
    }
  }

  const onCreateUser = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.adminCreateUser(form)
      setCreateOpen(false)
      setForm({ username: '', password: '', role: 'author', display_name: '', note: '' })
      await loadUsers()
      await loadSummary()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const openUser = async (username) => {
    setError(null)
    try {
      setSelUser(await api.adminUser(username))
      setPwd('')
    } catch (e) {
      setError(e)
    }
  }

  const saveUser = async () => {
    if (!selUser) return
    setBusy(true)
    setError(null)
    try {
      const u = await api.adminPatchUser(selUser.username, {
        display_name: selUser.display_name,
        role: selUser.role,
        status: selUser.status,
        note: selUser.note,
      })
      setSelUser({ ...selUser, ...u })
      await loadUsers()
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const resetPwd = async () => {
    if (!selUser || !pwd) return
    setBusy(true)
    setError(null)
    try {
      await api.adminSetPassword(selUser.username, pwd)
      setPwd('')
      alert('密码已重置，该用户所有会话已强制下线')
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const doForceLogout = async () => {
    if (!selUser) return
    setBusy(true)
    try {
      await api.adminForceLogout(selUser.username)
      alert('已强制下线')
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const doDeleteUser = async () => {
    if (!selUser) return
    if (!confirm(`永久删除账号「${selUser.username}」？不可恢复。`)) return
    setBusy(true)
    try {
      await api.adminDeleteUser(selUser.username)
      setSelUser(null)
      await loadUsers()
      await loadSummary()
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const onCreateWork = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.adminCreateWork({
        title: newWork.title,
        owner_user_id: newWork.owner_user_id,
        slug: newWork.slug || undefined,
      })
      setNewWork({ title: '', owner_user_id: '', slug: '' })
      await loadWorks()
      await loadSummary()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  const doTransfer = async () => {
    if (!transfer.slug || !transfer.new_owner) return
    setBusy(true)
    try {
      await api.adminTransferWork(transfer.slug, transfer.new_owner)
      setTransfer({ slug: '', new_owner: '' })
      await loadWorks()
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="h-full flex flex-col bg-canvas" data-testid="admin-console">
      <div className="shrink-0 border-b border-line px-4 py-3 flex items-center gap-3 flex-wrap">
        {typeof onExit === 'function' && (
          <button
            type="button"
            data-testid="admin-exit"
            onClick={onExit}
            className={`${btnPrimary} inline-flex items-center gap-1.5 shrink-0`}
            title={hasWork ? '返回当前作品写作区' : '返回作品库'}
          >
            <ArrowLeft size={15} />
            {hasWork ? '返回写作' : '返回作品库'}
          </button>
        )}
        <Shield size={18} className="text-brand shrink-0" />
        <div className="min-w-0">
          <div className="text-f14 font-semibold">管理台</div>
          <div className="text-f12 text-faint">账号 · 书籍归属 · 运行链路 · 操作审计（仅管理员）</div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {typeof onExit === 'function' && hasWork && (
            <button type="button" className={`${btnCls} inline-flex items-center gap-1`} onClick={onExit}>
              <PenLine size={14} /> 写作区
            </button>
          )}
          <button type="button" className={`${btnCls} inline-flex items-center gap-1`} onClick={refreshAll} disabled={busy}>
            <RefreshCw size={14} className={busy ? 'animate-spin' : ''} /> 刷新
          </button>
        </div>
      </div>

      <div className="flex flex-1 min-h-0">
        <nav className="w-40 shrink-0 border-r border-line p-2 space-y-0.5 bg-surface/50">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              data-testid={`admin-tab-${key}`}
              className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-f13 text-left cursor-pointer ${
                tab === key ? 'bg-soft text-brand font-medium' : 'text-faint hover:text-ink hover:bg-soft/70'
              }`}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </nav>

        <div className="flex-1 min-w-0 overflow-auto p-4">
          <Err e={error} />

          {tab === 'overview' && summary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {[
                ['用户总数', summary.users?.users_total],
                ['活跃用户', summary.users?.users_active],
                ['管理员', summary.users?.admins_active],
                ['停用', summary.users?.users_disabled],
                ['书籍总数', summary.works?.total],
                ['活跃书', summary.works?.active],
                ['废弃箱', summary.works?.archived],
              ].map(([k, v]) => (
                <div key={k} className="rounded-lg border border-line bg-surface p-3">
                  <div className="text-f12 text-faint">{k}</div>
                  <div className="text-xl font-semibold mt-1">{v ?? '—'}</div>
                </div>
              ))}
              <div className="col-span-2 md:col-span-4 rounded-lg border border-line bg-surface p-3">
                <div className="text-f12 text-faint mb-2">各账号活跃书籍数</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(summary.works?.by_owner || {}).length === 0 && (
                    <span className="text-f12 text-faint">暂无</span>
                  )}
                  {Object.entries(summary.works?.by_owner || {}).map(([o, n]) => (
                    <span key={o} className="text-f12 px-2 py-1 rounded-md bg-soft">
                      {o}: <b>{n}</b>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === 'users' && (
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
              <div>
                <div className="flex flex-wrap gap-2 mb-3 items-end">
                  <Field label="搜索">
                    <input className={inputCls} value={uq} onChange={(e) => setUq(e.target.value)} placeholder="用户名/显示名/备注" />
                  </Field>
                  <Field label="角色">
                    <select className={inputCls} value={uRole} onChange={(e) => setURole(e.target.value)}>
                      <option value="">全部</option>
                      <option value="admin">admin</option>
                      <option value="author">author</option>
                    </select>
                  </Field>
                  <Field label="状态">
                    <select className={inputCls} value={uStatus} onChange={(e) => setUStatus(e.target.value)}>
                      <option value="">全部</option>
                      <option value="active">active</option>
                      <option value="disabled">disabled</option>
                    </select>
                  </Field>
                  <button type="button" className={btnCls} onClick={loadUsers}>筛选</button>
                  <button type="button" className={`${btnPrimary} inline-flex items-center gap-1`} onClick={() => setCreateOpen(true)}>
                    <Plus size={14} /> 新建账号
                  </button>
                </div>

                {createOpen && (
                  <form onSubmit={onCreateUser} className="mb-4 p-3 rounded-lg border border-line bg-surface space-y-2">
                    <div className="text-f13 font-medium">新建账号</div>
                    <div className="grid grid-cols-2 gap-2">
                      <Field label="用户名 *">
                        <input required className={inputCls} value={form.username}
                          onChange={(e) => setForm({ ...form, username: e.target.value })} />
                      </Field>
                      <Field label="密码 * (≥6)">
                        <input required type="password" minLength={6} className={inputCls} value={form.password}
                          onChange={(e) => setForm({ ...form, password: e.target.value })} />
                      </Field>
                      <Field label="角色">
                        <select className={inputCls} value={form.role}
                          onChange={(e) => setForm({ ...form, role: e.target.value })}>
                          <option value="author">author</option>
                          <option value="admin">admin</option>
                        </select>
                      </Field>
                      <Field label="显示名">
                        <input className={inputCls} value={form.display_name}
                          onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
                      </Field>
                      <Field label="备注">
                        <input className={inputCls} value={form.note}
                          onChange={(e) => setForm({ ...form, note: e.target.value })} />
                      </Field>
                    </div>
                    <div className="flex gap-2">
                      <button type="submit" className={btnPrimary} disabled={busy}>创建</button>
                      <button type="button" className={btnCls} onClick={() => setCreateOpen(false)}>取消</button>
                    </div>
                  </form>
                )}

                <div className="rounded-lg border border-line overflow-hidden">
                  <table className="w-full text-f12">
                    <thead className="bg-soft/80 text-faint text-left">
                      <tr>
                        <th className="px-3 py-2 font-medium">用户</th>
                        <th className="px-3 py-2 font-medium">角色</th>
                        <th className="px-3 py-2 font-medium">状态</th>
                        <th className="px-3 py-2 font-medium">书</th>
                        <th className="px-3 py-2 font-medium">最近登录</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.items.map((u) => (
                        <tr
                          key={u.username}
                          className={`border-t border-line cursor-pointer hover:bg-soft/50 ${
                            selUser?.username === u.username ? 'bg-soft/70' : ''
                          }`}
                          onClick={() => openUser(u.username)}
                        >
                          <td className="px-3 py-2">
                            <div className="font-medium">{u.username}</div>
                            {u.display_name && <div className="text-faint">{u.display_name}</div>}
                          </td>
                          <td className="px-3 py-2">{u.role}</td>
                          <td className="px-3 py-2">{u.status}</td>
                          <td className="px-3 py-2">{u.works_active ?? 0}/{u.works_archived ?? 0}</td>
                          <td className="px-3 py-2 text-faint">{fmtTs(u.last_login_at)}</td>
                        </tr>
                      ))}
                      {users.items.length === 0 && (
                        <tr><td colSpan={5} className="px-3 py-6 text-center text-faint">无用户</td></tr>
                      )}
                    </tbody>
                  </table>
                  <div className="px-3 py-1.5 text-f12 text-faint border-t border-line">共 {users.total} 人</div>
                </div>
              </div>

              <div className="rounded-lg border border-line bg-surface p-3 h-fit sticky top-0">
                {!selUser ? (
                  <div className="text-f12 text-faint py-8 text-center">选择左侧账号查看详情</div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-f14 font-semibold">{selUser.username}</div>
                    <Field label="显示名">
                      <input className={inputCls} value={selUser.display_name || ''}
                        onChange={(e) => setSelUser({ ...selUser, display_name: e.target.value })} />
                    </Field>
                    <Field label="角色">
                      <select className={inputCls} value={selUser.role}
                        onChange={(e) => setSelUser({ ...selUser, role: e.target.value })}>
                        <option value="author">author</option>
                        <option value="admin">admin</option>
                      </select>
                    </Field>
                    <Field label="状态">
                      <select className={inputCls} value={selUser.status}
                        onChange={(e) => setSelUser({ ...selUser, status: e.target.value })}>
                        <option value="active">active</option>
                        <option value="disabled">disabled</option>
                      </select>
                    </Field>
                    <Field label="备注">
                      <textarea className={inputCls} rows={2} value={selUser.note || ''}
                        onChange={(e) => setSelUser({ ...selUser, note: e.target.value })} />
                    </Field>
                    <div className="text-f12 text-faint space-y-0.5">
                      <div>创建：{fmtTs(selUser.created_at)}</div>
                      <div>登录：{fmtTs(selUser.last_login_at)}</div>
                      <div>会话版本：{selUser.session_version}</div>
                      <div>书：活跃 {selUser.works_active ?? 0} / 废弃 {selUser.works_archived ?? 0}</div>
                    </div>
                    <button type="button" className={`${btnPrimary} w-full`} onClick={saveUser} disabled={busy}>保存资料</button>
                    <Field label="重置密码">
                      <input type="password" minLength={6} className={inputCls} value={pwd}
                        onChange={(e) => setPwd(e.target.value)} placeholder="新密码 ≥6" />
                    </Field>
                    <button type="button" className={`${btnCls} w-full inline-flex items-center justify-center gap-1`}
                      onClick={resetPwd} disabled={busy || !pwd}>
                      <KeyRound size={14} /> 重置密码并下线
                    </button>
                    <button type="button" className={`${btnCls} w-full inline-flex items-center justify-center gap-1`}
                      onClick={doForceLogout} disabled={busy}>
                      <LogOut size={14} /> 强制下线
                    </button>
                    <button type="button" className={`${btnCls} w-full text-red-600 inline-flex items-center justify-center gap-1`}
                      onClick={doDeleteUser} disabled={busy}>
                      <UserX size={14} /> 删除账号
                    </button>
                    {Array.isArray(selUser.works) && selUser.works.length > 0 && (
                      <div className="pt-2 border-t border-line">
                        <div className="text-f12 text-faint mb-1">名下书籍</div>
                        <ul className="text-f12 space-y-1 max-h-40 overflow-auto">
                          {selUser.works.map((w) => (
                            <li key={w.slug} className="truncate">
                              {w.archived ? '[废] ' : ''}{w.title || w.slug}
                              <span className="text-faint"> · {w.slug}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {tab === 'works' && (
            <div className="space-y-4">
              <form onSubmit={onCreateWork} className="p-3 rounded-lg border border-line bg-surface grid grid-cols-2 md:grid-cols-4 gap-2 items-end">
                <Field label="书名 *">
                  <input required className={inputCls} value={newWork.title}
                    onChange={(e) => setNewWork({ ...newWork, title: e.target.value })} />
                </Field>
                <Field label="归属账号 *">
                  <input required className={inputCls} value={newWork.owner_user_id}
                    onChange={(e) => setNewWork({ ...newWork, owner_user_id: e.target.value })}
                    placeholder="账号名" />
                </Field>
                <Field label="短标识（可空）">
                  <input className={inputCls} value={newWork.slug}
                    onChange={(e) => setNewWork({ ...newWork, slug: e.target.value })}
                    placeholder="book_xxxx" />
                </Field>
                <button type="submit" className={btnPrimary} disabled={busy}>代建书籍</button>
              </form>

              <div className="p-3 rounded-lg border border-line bg-surface grid grid-cols-2 md:grid-cols-4 gap-2 items-end">
                <Field label="转让短标识">
                  <input className={inputCls} value={transfer.slug}
                    onChange={(e) => setTransfer({ ...transfer, slug: e.target.value })} />
                </Field>
                <Field label="新主人">
                  <input className={inputCls} value={transfer.new_owner}
                    onChange={(e) => setTransfer({ ...transfer, new_owner: e.target.value })} />
                </Field>
                <button type="button" className={btnCls} onClick={doTransfer} disabled={busy}>转让归属</button>
              </div>

              <div className="flex flex-wrap gap-2 items-end">
                <Field label="搜索">
                  <input className={inputCls} value={wq} onChange={(e) => setWq(e.target.value)} />
                </Field>
                <Field label="归属">
                  <input className={inputCls} value={wOwner} onChange={(e) => setWOwner(e.target.value)} placeholder="账号名" />
                </Field>
                <Field label="范围">
                  <select className={inputCls} value={wArch} onChange={(e) => setWArch(e.target.value)}>
                    <option value="all">全部</option>
                    <option value="active">仅活跃</option>
                    <option value="archived">仅废弃</option>
                  </select>
                </Field>
                <button type="button" className={btnCls} onClick={loadWorks}>筛选</button>
              </div>

              <div className="rounded-lg border border-line overflow-hidden">
                <table className="w-full text-f12">
                  <thead className="bg-soft/80 text-faint text-left">
                    <tr>
                      <th className="px-3 py-2">书名</th>
                      <th className="px-3 py-2">slug</th>
                      <th className="px-3 py-2">归属</th>
                      <th className="px-3 py-2">章/字</th>
                      <th className="px-3 py-2">状态</th>
                      <th className="px-3 py-2">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    {works.items.map((w) => (
                      <tr key={w.slug} className="border-t border-line">
                        <td className="px-3 py-2 font-medium max-w-[160px] truncate">{w.title}</td>
                        <td className="px-3 py-2 text-faint font-mono text-[11px]">{w.slug}</td>
                        <td className="px-3 py-2">{w.effective_owner || w.owner_user_id || '—'}</td>
                        <td className="px-3 py-2 text-faint">
                          {w.stats_error ? 'err' : `${w.chapter_count ?? '—'} / ${w.word_count ?? '—'}`}
                        </td>
                        <td className="px-3 py-2">{w.archived ? '废弃' : '活跃'}</td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-1">
                            {!w.archived ? (
                              <button type="button" title="废弃" className={btnCls}
                                onClick={async () => {
                                  if (!confirm(`废弃「${w.title}」？`)) return
                                  try {
                                    await api.adminArchiveWork(w.slug)
                                    await loadWorks()
                                  } catch (e) { setError(e) }
                                }}>
                                <Archive size={12} />
                              </button>
                            ) : (
                              <>
                                <button type="button" title="恢复" className={btnCls}
                                  onClick={async () => {
                                    try {
                                      await api.adminRestoreWork(w.slug)
                                      await loadWorks()
                                    } catch (e) { setError(e) }
                                  }}>
                                  <RotateCcw size={12} />
                                </button>
                                <button type="button" title="永久删除" className={`${btnCls} text-red-600`}
                                  onClick={async () => {
                                    const t = prompt('输入完整书名以确认永久删除：', w.title)
                                    if (t == null) return
                                    try {
                                      await api.adminPurgeWork(w.slug, t)
                                      await loadWorks()
                                    } catch (e) { setError(e) }
                                  }}>
                                  <Trash2 size={12} />
                                </button>
                              </>
                            )}
                            <button type="button" className={btnCls}
                              onClick={() => setTransfer({ slug: w.slug, new_owner: w.effective_owner || '' })}>
                              转让
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {works.items.length === 0 && (
                      <tr><td colSpan={6} className="px-3 py-6 text-center text-faint">无书籍</td></tr>
                    )}
                  </tbody>
                </table>
                <div className="px-3 py-1.5 text-f12 text-faint border-t border-line">共 {works.total} 本</div>
              </div>
            </div>
          )}

          {tab === 'run-logs' && <RunLogsPage />}

          {tab === 'audit' && (
            <div className="rounded-lg border border-line overflow-hidden">
              <table className="w-full text-f12">
                <thead className="bg-soft/80 text-faint text-left">
                  <tr>
                    <th className="px-3 py-2">时间</th>
                    <th className="px-3 py-2">操作者</th>
                    <th className="px-3 py-2">动作</th>
                    <th className="px-3 py-2">目标</th>
                    <th className="px-3 py-2">详情</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.items.map((a) => (
                    <tr key={a.id} className="border-t border-line align-top">
                      <td className="px-3 py-2 text-faint whitespace-nowrap">{fmtTs(a.ts)}</td>
                      <td className="px-3 py-2">{a.actor}</td>
                      <td className="px-3 py-2 font-mono text-[11px]">{a.action}</td>
                      <td className="px-3 py-2">{a.target_type}:{a.target_id}</td>
                      <td className="px-3 py-2 text-faint max-w-[280px] truncate font-mono text-[11px]">
                        {a.detail ? JSON.stringify(a.detail) : '—'}
                      </td>
                    </tr>
                  ))}
                  {audit.items.length === 0 && (
                    <tr><td colSpan={5} className="px-3 py-6 text-center text-faint">暂无审计</td></tr>
                  )}
                </tbody>
              </table>
              <div className="px-3 py-1.5 text-f12 text-faint border-t border-line">共 {audit.total} 条</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AdminConsole
