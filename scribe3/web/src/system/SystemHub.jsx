import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { PLANES, CRAFT_COMMON_KEYS, IMPACT_HINTS } from './planes'
import { SettingField } from '../settings/SettingField'
import { BookSection } from '../settings/BookSection'
import { PrefsSection } from '../settings/PrefsSection'
import { AuditSection } from '../settings/AuditSection'
import { GatewaySection } from '../settings/GatewaySection'
import AdminConsole from '../admin/AdminConsole'
import { Btn } from '../ui.jsx'

/**
 * 系统中心：App 级全页（KD-Mount）。无书可开；依赖 work 的区 disabled。
 */
export function SystemHub({
  work,
  works = [],
  isAdmin = false,
  initialSection = null,
  onSelectWork,
  onExit,
}) {
  const visiblePlanes = useMemo(
    () => PLANES.filter((p) => !p.adminOnly || isAdmin),
    [isAdmin],
  )
  const [planeId, setPlaneId] = useState(visiblePlanes[0]?.id || 'writing')
  const plane = visiblePlanes.find((p) => p.id === planeId) || visiblePlanes[0]
  const [sectionId, setSectionId] = useState(
    initialSection || plane?.sections?.[0]?.id || 'book',
  )
  const [items, setItems] = useState(null)
  const [usage, setUsage] = useState(null)
  const [skills, setSkills] = useState(null)
  const [skillBody, setSkillBody] = useState(null)
  const [mcp, setMcp] = useState(null)
  const [gw, setGw] = useState(null)
  const [dataHealth, setDataHealth] = useState(null)
  const [tables, setTables] = useState(null)
  const [tableRows, setTableRows] = useState(null)
  const [lessons, setLessons] = useState(null)
  const [err, setErr] = useState(null)

  const sections = plane?.sections || []
  const section = sections.find((s) => s.id === sectionId) || sections[0]

  useEffect(() => {
    if (!sections.find((s) => s.id === sectionId)) {
      setSectionId(sections[0]?.id)
    }
  }, [planeId, sections, sectionId])

  const reloadSettings = useCallback(() => {
    api.settings()
      .then((r) => setItems(r.settings || []))
      .catch((e) => setErr(e?.message || '设置加载失败'))
  }, [])

  useEffect(() => { reloadSettings() }, [reloadSettings])

  useEffect(() => {
    api.aiUsage?.().then(setUsage).catch(() => setUsage(null))
  }, [])

  // section loaders
  useEffect(() => {
    setErr(null)
    if (section?.id === 'skills') {
      api.craftSkills?.().then((r) => setSkills(r.skills || r || [])).catch((e) => setErr(String(e?.message || e)))
    }
    if (section?.id === 'mcp') {
      api.mcpCatalog?.().then((r) => setMcp(r)).catch((e) => setErr(String(e?.message || e)))
    }
    if (section?.id === 'hermes' || section?.id === 'health') {
      api.gatewayStatus?.().then(setGw).catch(() => setGw(null))
    }
    if (section?.id === 'surreal' && work) {
      api.dataHealth?.(work).then(setDataHealth).catch((e) => setDataHealth({ ok: false, detail: String(e) }))
      if (isAdmin) {
        api.adminDataTables?.(work).then((r) => setTables(r.tables || [])).catch(() => setTables([]))
      }
    }
    if (section?.id === 'evolution' && work) {
      api.promotableLessons?.(work).then((r) => setLessons(r.lessons || r.rows || r || [])).catch(() => setLessons([]))
    }
  }, [section?.id, work, isAdmin])

  const byCat = (c) => (items || []).filter((i) => i.category === c)
  const craftItems = byCat('craft')
  const craftCommon = craftItems.filter((i) => CRAFT_COMMON_KEYS.has(i.key))
  const craftAdvanced = craftItems.filter((i) => !CRAFT_COMMON_KEYS.has(i.key))
  const needsWork = !!section?.needsWork
  const workMissing = needsWork && !work

  const onChanged = () => reloadSettings()

  const renderSettingsList = (list, { advanced } = {}) => (
    <div className="space-y-2" data-testid={advanced ? 'craft-advanced' : 'craft-common'}>
      {(list || []).map((it) => (
        <div key={it.key}>
          {IMPACT_HINTS[it.key] && (
            <div className="text-meta text-faint mb-0.5 px-1">{IMPACT_HINTS[it.key]}</div>
          )}
          <SettingField item={it} onChanged={onChanged} />
        </div>
      ))}
      {!list?.length && <div className="text-f13 text-faint">本区暂无设置项</div>}
    </div>
  )

  let main = null
  if (workMissing) {
    main = (
      <div className="p-8 text-f13 text-faint" data-testid="system-hub-need-work">
        本区依赖当前作品。请在顶部选择一本书，或从作品库打开后再来。
      </div>
    )
  } else if (section?.id === 'book') {
    main = <BookSection work={work} />
  } else if (section?.id === 'prefs') {
    main = <PrefsSection work={work} />
  } else if (section?.id === 'craft') {
    main = (
      <div className="p-5 space-y-6" data-testid="system-hub-craft">
        <div>
          <h4 className="text-f13 font-medium text-ink mb-2">常用</h4>
          {renderSettingsList(craftCommon)}
        </div>
        <div>
          <h4 className="text-f13 font-medium text-ink mb-2">进阶</h4>
          <p className="text-meta text-faint mb-2">检索权重与半衰期等；误改可能影响召回。</p>
          {renderSettingsList(craftAdvanced, { advanced: true })}
        </div>
      </div>
    )
  } else if (section?.id === 'skills') {
    main = (
      <div className="p-5" data-testid="system-hub-skills">
        <p className="text-f12 text-faint mb-3">仓库技法库（craft_skills）；全文只读。增删改请改仓库 md 后部署。</p>
        <ul className="space-y-2">
          {(skills || []).map((s) => (
            <li key={s.slug || s.name}>
              <button
                type="button"
                className="text-left w-full rounded-lg border border-line px-3 py-2 hover:bg-soft cursor-pointer"
                onClick={() => api.craftSkill?.(s.slug).then((r) => setSkillBody(r.content || r)).catch((e) => setErr(String(e)))}
              >
                <div className="text-f13 font-medium text-ink">{s.name || s.slug}</div>
                <div className="text-meta text-faint">{s.desc || s.slug}</div>
              </button>
            </li>
          ))}
        </ul>
        {skillBody && (
          <pre className="mt-4 p-3 rounded-lg bg-canvas border border-line text-f12 whitespace-pre-wrap max-h-96 overflow-auto">{skillBody}</pre>
        )}
      </div>
    )
  } else if (section?.id === 'mcp') {
    const tools = mcp?.tools || []
    const reads = tools.filter((t) => !t.write_gated)
    const writes = tools.filter((t) => t.write_gated)
    main = (
      <div className="p-5" data-testid="system-hub-mcp">
        <p className="text-f12 text-faint mb-3">共 {mcp?.count ?? tools.length} 个 s3_* 工具。写工具需审批（WRITE_GATED）。</p>
        <h4 className="text-f13 font-medium mb-2">读 / 召回（{reads.length}）</h4>
        <ul className="text-f12 space-y-1 mb-4 max-h-48 overflow-auto">
          {reads.map((t) => <li key={t.name} className="font-mono text-ink">{t.name}<span className="text-faint ml-2 font-sans">{t.doc}</span></li>)}
        </ul>
        <h4 className="text-f13 font-medium mb-2">写（待批 {writes.length}）</h4>
        <ul className="text-f12 space-y-1 max-h-48 overflow-auto">
          {writes.map((t) => <li key={t.name} className="font-mono text-ink">{t.name}</li>)}
        </ul>
      </div>
    )
  } else if (section?.id === 'health') {
    main = (
      <div className="p-5 space-y-4" data-testid="system-hub-health">
        {usage?.cap && (
          <div className="rounded-lg border border-line p-3 text-f13">
            今日 LLM：{usage.cap.used_today}
            {usage.cap.unlimited ? ' · 不限' : ` / ${usage.cap.cap}`}
          </div>
        )}
        <div>
          <h4 className="text-f13 font-medium mb-2">网关状态</h4>
          <div className="space-y-1">
            {(gw?.gateways || []).map((g) => (
              <div key={g.name} className="flex items-center gap-2 text-f13">
                <span className={`inline-block h-2 w-2 rounded-full ${g.online ? 'bg-ok' : 'bg-line'}`} />
                <span>{g.name}</span>
                <span className="text-meta text-faint">{g.profile}</span>
              </div>
            ))}
          </div>
        </div>
        <p className="text-meta text-faint">更细的上下文溯源请在写作台打开「上下文检查器」。</p>
      </div>
    )
  } else if (section?.id === 'evolution') {
    main = (
      <div className="p-5" data-testid="system-hub-evolution">
        <p className="text-f12 text-faint mb-3">可升格教训（promotable）。治理以只读入口为主；写入仍走既有审批路径。</p>
        {Array.isArray(lessons) && lessons.length === 0 && (
          <div className="text-f13 text-faint">暂无 promotable lessons（空态正常）。</div>
        )}
        <ul className="space-y-2">
          {(lessons || []).slice(0, 40).map((L, i) => (
            <li key={L.id || i} className="rounded-lg border border-line px-3 py-2 text-f13">
              {L.text || L.kind || JSON.stringify(L).slice(0, 120)}
            </li>
          ))}
        </ul>
      </div>
    )
  } else if (section?.id === 'hermes') {
    main = (
      <div className="p-5" data-testid="system-hub-hermes">
        <GatewaySection items={byCat('gateway').filter((i) => isAdmin || i.audience === 'author')} onChanged={onChanged} />
      </div>
    )
  } else if (section?.id === 'models') {
    main = (
      <div className="p-5 space-y-4" data-testid="system-hub-models">
        {usage?.cap && (
          <div className="rounded-lg border border-line p-3 text-f13">
            今日已用 {usage.cap.used_today}{usage.cap.unlimited ? ' · 不限' : ` / 日帽 ${usage.cap.cap}`}
          </div>
        )}
        {renderSettingsList(byCat('llm').filter((i) => isAdmin || i.audience !== 'admin'))}
        {!isAdmin && (
          <p className="text-meta text-faint">日帽等管理员项已隐藏；author 可改模型名与超时。</p>
        )}
      </div>
    )
  } else if (section?.id === 'surreal') {
    main = (
      <div className="p-5 space-y-4" data-testid="system-hub-surreal">
        <div className="rounded-lg border border-line p-3 text-f13">
          健康 · work=<code className="text-meta">{work}</code>
          {' '}
          <span className={dataHealth?.ok ? 'text-ok' : 'text-danger'}>
            {dataHealth == null ? '加载中…' : dataHealth.ok ? 'OK' : '异常'}
          </span>
          <div className="text-meta text-faint mt-1">{dataHealth?.detail}</div>
        </div>
        {isAdmin && (
          <>
            <h4 className="text-f13 font-medium">表白名单（只读）</h4>
            <div className="flex flex-wrap gap-2">
              {(tables || []).map((tb) => (
                <button
                  key={tb.id}
                  type="button"
                  className="rounded-lg px-3 py-1.5 text-f12 border border-line hover:bg-soft cursor-pointer"
                  onClick={() => api.adminDataRows?.(tb.id, work).then((r) => setTableRows(r)).catch((e) => setErr(String(e)))}
                >
                  {tb.label || tb.id}
                </button>
              ))}
            </div>
            {tableRows && (
              <pre className="text-f11 p-3 rounded-lg bg-canvas border border-line max-h-64 overflow-auto">
                {JSON.stringify(tableRows.rows || tableRows, null, 2).slice(0, 4000)}
              </pre>
            )}
          </>
        )}
        {!isAdmin && <p className="text-meta text-faint">表浏览器仅管理员可见。</p>}
      </div>
    )
  } else if (section?.id === 'connection') {
    main = <div className="p-5" data-testid="system-hub-connection">{renderSettingsList(byCat('connection'))}</div>
  } else if (section?.id === 'flags') {
    main = <div className="p-5" data-testid="system-hub-flags">{renderSettingsList(byCat('flags'))}</div>
  } else if (section?.id === 'accounts') {
    main = isAdmin ? <AdminConsole onExit={onExit} hasWork={!!work} /> : <div className="p-8 text-faint">需要管理员</div>
  } else if (section?.id === 'audit') {
    main = <div className="p-5"><AuditSection /></div>
  } else {
    main = <div className="p-8 text-faint">选择左侧分区</div>
  }

  return (
    <div className="h-full flex flex-col min-h-0 bg-canvas" data-testid="system-hub">
      <header className="shrink-0 border-b border-line px-4 py-2 flex items-center gap-3 flex-wrap">
        <h2 className="type-section text-ink">系统中心</h2>
        <label className="text-f12 text-faint flex items-center gap-2">
          作品
          <select
            className="rounded-md border border-line bg-surface px-2 py-1 text-f13 text-ink"
            data-testid="system-hub-work"
            value={work || ''}
            onChange={(e) => onSelectWork?.(e.target.value || null)}
          >
            <option value="">（未选书）</option>
            {(works || []).map((w) => (
              <option key={w.slug} value={w.slug}>{w.title || w.slug}</option>
            ))}
          </select>
        </label>
        <div className="flex-1" />
        <Btn variant="ghost" size="sm" onClick={onExit} data-testid="system-hub-exit">返回</Btn>
      </header>
      <div className="flex-1 min-h-0 flex">
        <nav className="w-48 shrink-0 border-r border-line bg-surface/50 overflow-y-auto p-2" aria-label="系统中心平面">
          {visiblePlanes.map((p) => (
            <div key={p.id} className="mb-3">
              <button
                type="button"
                className={`w-full text-left px-2 py-1.5 rounded-md text-f13 font-medium cursor-pointer ${
                  planeId === p.id ? 'bg-soft text-brand' : 'text-ink hover:bg-soft'
                }`}
                onClick={() => { setPlaneId(p.id); setSectionId(p.sections[0]?.id) }}
              >
                {p.label}
              </button>
              {planeId === p.id && (
                <ul className="mt-1 ml-1 space-y-0.5">
                  {p.sections.map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        className={`w-full text-left px-2 py-1 rounded-md text-f12 cursor-pointer ${
                          sectionId === s.id ? 'bg-brand/10 text-brand' : 'text-faint hover:text-ink hover:bg-soft'
                        }`}
                        onClick={() => setSectionId(s.id)}
                      >
                        {s.label}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </nav>
        <div className="flex-1 min-h-0 overflow-y-auto">
          {err && <div className="m-4 text-f13 text-danger" role="alert">{err}</div>}
          {!items && section?.id === 'craft' ? (
            <div className="p-8 text-faint">加载设置…</div>
          ) : main}
        </div>
      </div>
    </div>
  )
}
