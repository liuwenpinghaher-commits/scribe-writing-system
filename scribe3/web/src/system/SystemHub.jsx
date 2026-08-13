import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { PLANES, CRAFT_COMMON_KEYS, IMPACT_HINTS, GATE_LABEL } from './planes'
import { NODES, EDGES, SEQ_STEPS } from './mapGraph.js'
import { MODULES } from './moduleCatalog.js'
import { TASKS } from './taskCatalog.js'
import { SettingField } from '../settings/SettingField'
import { BookSection } from '../settings/BookSection'
import { PrefsSection } from '../settings/PrefsSection'
import { AuditSection } from '../settings/AuditSection'
import { GatewaySection } from '../settings/GatewaySection'
import AdminConsole from '../admin/AdminConsole'
import { Btn } from '../ui.jsx'

/**
 * 系统中心 + 活地图默认首页（控制面 KD-M2）。
 * 无书可开；依赖 work 的区 disabled。
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
  const defaultSection = initialSection || 'map'
  const [planeId, setPlaneId] = useState(() => {
    if (initialSection === 'accounts' && isAdmin) return 'ops'
    return 'writing'
  })
  const plane = visiblePlanes.find((p) => p.id === planeId) || visiblePlanes[0]
  const [sectionId, setSectionId] = useState(defaultSection)
  const [items, setItems] = useState(null)
  const [usage, setUsage] = useState(null)
  const [skills, setSkills] = useState(null)
  const [skillBody, setSkillBody] = useState(null)
  const [moves, setMoves] = useState(null)
  const [moveBody, setMoveBody] = useState(null)
  const [methods, setMethods] = useState(null)
  const [methodBody, setMethodBody] = useState(null)
  const [panels, setPanels] = useState(null)
  const [bannedLex, setBannedLex] = useState(null)
  const [checkSel, setCheckSel] = useState(() => new Set())
  const [mcp, setMcp] = useState(null)
  const [mcpFilter, setMcpFilter] = useState('all')
  const [showRawNames, setShowRawNames] = useState(false)
  const [gw, setGw] = useState(null)
  const [dataHealth, setDataHealth] = useState(null)
  const [tables, setTables] = useState(null)
  const [tableRows, setTableRows] = useState(null)
  const [lessons, setLessons] = useState(null)
  const [moduleId, setModuleId] = useState(null)
  const [taskId, setTaskId] = useState(TASKS[0]?.id)
  const [err, setErr] = useState(null)

  const sections = plane?.sections || []
  const section = sections.find((s) => s.id === sectionId) || sections[0]

  useEffect(() => {
    if (!sections.find((s) => s.id === sectionId)) {
      setSectionId(sections[0]?.id || 'map')
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

  useEffect(() => {
    setErr(null)
    const sid = section?.id
    if (sid === 'map' || sid === 'health' || sid === 'hermes') {
      api.gatewayStatus?.().then(setGw).catch(() => setGw(null))
    }
    if (sid === 'map' || sid === 'health') {
      api.aiUsage?.().then(setUsage).catch(() => setUsage(null))
    }
    if ((sid === 'map' || sid === 'surreal') && work) {
      api.dataHealth?.(work).then(setDataHealth).catch((e) => setDataHealth({ ok: false, detail: String(e?.message || e) }))
      if (isAdmin && sid === 'surreal') {
        api.adminDataTables?.(work).then((r) => setTables(r.tables || [])).catch(() => setTables([]))
      }
    }
    if (sid === 'skills') {
      api.craftSkills?.().then((r) => setSkills(r.skills || r || [])).catch((e) => setErr(String(e?.message || e)))
      api.storyMoves?.().then((r) => setMoves(r.moves || [])).catch(() => setMoves([]))
      api.authorMethods?.().then((r) => setMethods(r.methods || [])).catch(() => setMethods([]))
      api.authorPanels?.().then(setPanels).catch(() => setPanels(null))
      api.craftBannedLexicon?.().then(setBannedLex).catch(() => setBannedLex(null))
    }
    if (sid === 'mcp') {
      api.mcpCatalog?.().then(setMcp).catch((e) => setErr(String(e?.message || e)))
    }
    if (sid === 'evolution' && work) {
      api.promotableLessons?.(work).then((r) => setLessons(r.lessons || r.rows || r || [])).catch(() => setLessons([]))
    }
  }, [section?.id, work, isAdmin])

  const byCat = (c) => (items || []).filter((i) => i.category === c)
  const byKey = useMemo(() => {
    const m = {}
    for (const it of items || []) m[it.key] = it
    return m
  }, [items])
  const craftItems = byCat('craft')
  const craftCommon = craftItems.filter((i) => CRAFT_COMMON_KEYS.has(i.key))
  const craftAdvanced = craftItems.filter((i) => !CRAFT_COMMON_KEYS.has(i.key))
  const needsWork = !!section?.needsWork
  const workMissing = needsWork && !work
  const onChanged = () => reloadSettings()

  const goSection = (id, planeHint, opts = {}) => {
    if (planeHint) setPlaneId(planeHint)
    else {
      for (const p of visiblePlanes) {
        if (p.sections.some((s) => s.id === id)) {
          setPlaneId(p.id)
          break
        }
      }
    }
    setSectionId(id)
    // Map clicks pass keepModule so the config page still shows the module banner.
    if (!opts.keepModule) setModuleId(null)
  }

  /** Map/module clicks stay in Hub config — never onExit to writing app. */
  const onNodeActivate = (node) => {
    const mod = MODULES.find((m) => m.id === node.id)
    const section = node.configSection || mod?.configSection
    const plane = node.configPlane || mod?.configPlane
    setModuleId(node.id)
    if (section) goSection(section, plane, { keepModule: true })
  }

  const onStepActivate = (step) => {
    if (step.action === 'section' && step.section) {
      goSection(step.section, step.plane)
      if (step.filter) setMcpFilter(step.filter)
    }
  }

  const renderSettingsList = (list, testid) => (
    <div className="space-y-2" data-testid={testid}>
      {(list || []).map((it) => (
        <div key={it.key}>
          {IMPACT_HINTS[it.key] && (
            <div className="text-meta text-faint mb-0.5 px-1">{IMPACT_HINTS[it.key]}</div>
          )}
          <SettingField item={it} onChanged={onChanged} />
        </div>
      ))}
      {!list?.length && <div className="text-f13 text-faint">本区暂无设置项或无权查看</div>}
    </div>
  )

  const ObserveStrip = () => (
    <div className="flex flex-wrap gap-3 text-f12 border border-line rounded-lg p-3 bg-surface/40" data-testid="system-hub-observe">
      <span>
        网关：
        {(gw?.gateways || []).map((g) => (
          <span key={g.name} className="inline-flex items-center gap-1 mr-2">
            <span className={`inline-block h-2 w-2 rounded-full ${g.online ? 'bg-ok' : 'bg-line'}`} />
            {g.name}
          </span>
        ))}
        {!gw && <span className="text-faint">—</span>}
      </span>
      {usage?.cap && (
        <span>今日 LLM：{usage.cap.used_today}{usage.cap.unlimited ? ' · 不限' : ` / ${usage.cap.cap}`}</span>
      )}
      <span>
        故事库：
        {!work ? '选书后可见' : dataHealth == null ? '…' : dataHealth.ok ? '健康' : '异常'}
      </span>
      <span className="text-faint">上下文检查器请在写作台打开（返回后使用）。</span>
    </div>
  )

  const MapHome = () => (
    <div className="p-5 space-y-5" data-testid="system-hub-map">
      <div>
        <h3 className="text-f14 font-medium text-ink mb-1">铜炉运转图</h3>
        <p className="text-f12 text-faint mb-3">
          点模块进入该模块在系统中心内的配置/说明（不跳进写作应用）。顶栏「返回」才回到写作台。
        </p>
        <div className="rounded-lg border border-line bg-canvas p-4 overflow-x-auto" data-testid="system-hub-arch-map">
          <svg viewBox="0 0 480 280" className="w-full max-w-xl h-auto" role="img" aria-label="系统模块架构图">
            {EDGES.map(([a, b]) => {
              const na = NODES.find((n) => n.id === a)
              const nb = NODES.find((n) => n.id === b)
              if (!na || !nb) return null
              return (
                <line key={`${a}-${b}`} x1={na.x + 50} y1={na.y + 18} x2={nb.x + 50} y2={nb.y + 18}
                  stroke="currentColor" className="text-line" strokeWidth="1.5" />
              )
            })}
            {NODES.map((n) => (
              <g key={n.id}>
                <rect x={n.x} y={n.y} width={100} height={36} rx={8}
                  className="fill-surface stroke-line" strokeWidth="1" />
                <foreignObject x={n.x} y={n.y} width={100} height={36}>
                  <button type="button"
                    className="w-full h-full text-f12 text-ink hover:text-brand cursor-pointer"
                    data-testid={`map-node-${n.id}`}
                    aria-label={n.label}
                    onClick={() => onNodeActivate(n)}
                  >
                    {n.label}
                  </button>
                </foreignObject>
              </g>
            ))}
          </svg>
        </div>
      </div>

      <div data-testid="system-hub-seq">
        <h4 className="text-f13 font-medium mb-2">写一章时序</h4>
        <div className="flex flex-wrap gap-2">
          {SEQ_STEPS.map((s) => (
            <button key={s.id} type="button"
              data-testid={`map-step-${s.id}`}
              className="rounded-full border border-line px-3 py-1 text-f12 hover:bg-soft cursor-pointer"
              onClick={() => onStepActivate(s)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="system-hub-module-cards">
        {MODULES.map((m) => (
          <button key={m.id} type="button"
            className="text-left rounded-lg border border-line p-3 hover:bg-soft cursor-pointer"
            data-testid={`module-card-${m.id}`}
            onClick={() => {
              setModuleId(m.id)
              if (m.configSection) goSection(m.configSection, m.configPlane, { keepModule: true })
            }}
          >
            <div className="text-f13 font-medium text-ink">{m.label}</div>
            <div className="text-f12 text-faint mt-1 line-clamp-2">{m.purpose}</div>
          </button>
        ))}
      </div>

      <ObserveStrip />

      <div className="flex flex-wrap gap-2">
        <Btn variant="soft" size="sm" onClick={() => goSection('tasks')}>任务旋钮</Btn>
        <Btn variant="soft" size="sm" onClick={() => goSection('mcp')}>能力注册表</Btn>
        <Btn variant="soft" size="sm" onClick={() => goSection('health')}>健康</Btn>
      </div>

      {moduleId && (
        <ModulePane id={moduleId} health={dataHealth} work={work} onClose={() => setModuleId(null)}
          onGoSection={goSection} />
      )}
    </div>
  )

  function ModulePane({ id, health, work: w, onClose, onGoSection }) {
    const m = MODULES.find((x) => x.id === id)
    if (!m) return null
    return (
      <div className="rounded-lg border border-brand/30 bg-brand/5 p-4 space-y-2 mb-4" data-testid="system-hub-module-pane">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="text-meta text-brand">模块配置</div>
            <h4 className="text-f14 font-medium text-ink">{m.configTitle || m.label}</h4>
          </div>
          <button type="button" className="text-f12 text-faint cursor-pointer shrink-0" onClick={onClose}>收起说明</button>
        </div>
        <p className="text-f13"><strong>作用：</strong>{m.purpose}</p>
        <p className="text-f13"><strong>怎么运转：</strong>{m.flow}</p>
        <p className="text-f13"><strong>在此可配：</strong>{m.can}</p>
        <p className="text-f13 text-faint"><strong>不会：</strong>{m.cannot} 点地图只进控制面配置，不进写作应用。</p>
        {id === 'story' && (
          <p className="text-f12">健康：{!w ? '请先选书' : health?.ok ? 'OK' : health?.detail || '—'}</p>
        )}
        <p className="text-meta text-warn">无「执行写工具」；世界写须经主编审批。返回写作台请用顶栏「返回」。</p>
        {m.configSection && (
          <Btn size="sm" variant="soft" onClick={() => onGoSection(m.configSection, m.configPlane)}>
            已在下方显示：{m.configTitle || m.label}
          </Btn>
        )}
      </div>
    )
  }

  const TaskControls = () => {
    const task = TASKS.find((t) => t.id === taskId) || TASKS[0]
    const list = (task?.keys || []).map((k) => byKey[k]).filter(Boolean)
    return (
      <div className="p-5 space-y-4" data-testid="system-hub-tasks">
        <p className="text-f12 text-faint">按任务拧旋钮（精确 settings 键）。作者可改工艺/部分模型；admin 键由门禁拒绝。</p>
        <div className="flex flex-wrap gap-2">
          {TASKS.map((t) => (
            <button key={t.id} type="button"
              className={`rounded-full px-3 py-1 text-f12 border cursor-pointer ${taskId === t.id ? 'border-brand text-brand bg-brand/10' : 'border-line'}`}
              onClick={() => setTaskId(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
        {renderSettingsList(list, 'task-knobs-list')}
      </div>
    )
  }

  const CapabilityRegistry = () => {
    const tools = mcp?.tools || []
    const domains = mcp?.domains || []
    const counts = mcp?.counts_by_gate || {}
    const filtered = mcpFilter === 'all' ? tools : tools.filter((t) => t.gate === mcpFilter)
    return (
      <div className="p-5 space-y-4" data-testid="system-hub-capability-registry">
        <p className="text-f12 text-faint">
          AI 能力说明书（只读）。共 {mcp?.count ?? 0} 工具；
          世界写须审批 {counts.world_write_gated ?? mcp?.write_gated_total ?? '—'}；
          存稿 {counts.manuscript_save ?? 0}；入库 {counts.ingest ?? 0}；只读 {counts.read ?? 0}。
          <strong className="text-ink"> 无「执行」按钮。</strong>
        </p>
        <div className="flex flex-wrap gap-2 text-f12">
          {['all', 'world_write_gated', 'manuscript_save', 'ingest', 'read'].map((g) => (
            <button key={g} type="button"
              className={`rounded-full px-2 py-0.5 border cursor-pointer ${mcpFilter === g ? 'border-brand text-brand' : 'border-line text-faint'}`}
              onClick={() => setMcpFilter(g)}
            >
              {g === 'all' ? '全部' : (GATE_LABEL[g] || g)}
            </button>
          ))}
          <label className="ml-2 flex items-center gap-1 cursor-pointer">
            <input type="checkbox" checked={showRawNames} onChange={(e) => setShowRawNames(e.target.checked)} />
            显示 s3_ 名
          </label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2" data-testid="capability-domains">
          {domains.map((d) => (
            <div key={d.domain} className="rounded-lg border border-line p-3">
              <div className="text-f13 font-medium">{d.label}</div>
              <div className="text-meta text-faint">
                读 {d.read_count ?? (d.read_tools || []).length}
                {d.channel === 'world_write' || (d.write_tools || []).length
                  ? ` · 写(待批) ${d.write_gated_count ?? (d.write_tools || []).length}`
                  : ''}
                {d.gate_note ? ` · ${GATE_LABEL[d.gate_note] || d.gate_note}` : ''}
              </div>
              {showRawNames && (
                <div className="mt-1 font-mono text-f11 text-faint break-all">
                  {[...(d.read_tools || []), ...(d.write_tools || [])].slice(0, 12).join(' ')}
                </div>
              )}
            </div>
          ))}
        </div>

        {showRawNames && (
          <ul className="text-f12 space-y-1 max-h-64 overflow-auto font-mono" data-testid="capability-raw-list">
            {filtered.map((t) => (
              <li key={t.name}>
                <span className="text-ink">{t.name}</span>
                <span className="text-faint ml-2 font-sans">{GATE_LABEL[t.gate] || t.gate}</span>
                {t.doc && <span className="text-faint ml-2 font-sans">{t.doc}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    )
  }

  let main = null
  if (workMissing) {
    main = (
      <div className="p-8 text-f13 text-faint" data-testid="system-hub-need-work">
        本区依赖当前作品。请在顶部选择一本书。
      </div>
    )
  } else if (section?.id === 'map') {
    main = <MapHome />
  } else if (section?.id === 'book') {
    main = <BookSection work={work} />
  } else if (section?.id === 'prefs') {
    main = <PrefsSection work={work} />
  } else if (section?.id === 'tasks') {
    main = <TaskControls />
  } else if (section?.id === 'craft') {
    main = (
      <div className="p-5 space-y-6" data-testid="system-hub-craft">
        <div>
          <h4 className="text-f13 font-medium text-ink mb-2">常用</h4>
          {renderSettingsList(craftCommon, 'craft-common')}
        </div>
        <div>
          <h4 className="text-f13 font-medium text-ink mb-2">进阶</h4>
          {renderSettingsList(craftAdvanced, 'craft-advanced')}
        </div>
      </div>
    )
  } else if (section?.id === 'skills') {
    const layerGroups = {}
    for (const m of methods || []) {
      const k = m.layer || 'catalog'
      if (!layerGroups[k]) layerGroups[k] = []
      layerGroups[k].push(m)
    }
    main = (
      <div className="p-5 space-y-4" data-testid="system-hub-skills">
        <p className="text-f12 text-faint">技法 = 落笔纪律；招式 = 本意×绕法。句子处方在写路径八引擎，不做成卡。</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="skills-three-cols">
          <div data-testid="skills-col-craft">
            <h4 className="text-f13 font-medium mb-2">技法</h4>
            <ul className="space-y-2">
              {(skills || []).map((s) => (
                <li key={s.slug || s.name}>
                  <button type="button" className="text-left w-full rounded-lg border border-line px-3 py-2 hover:bg-soft cursor-pointer"
                    onClick={() => api.craftSkill?.(s.slug).then((r) => { setSkillBody(r.content || r); setMoveBody(null); setMethodBody(null) }).catch((e) => setErr(String(e)))}>
                    <div className="text-f13 font-medium">{s.name || s.slug}</div>
                    <div className="text-meta text-faint">{s.desc || s.slug}</div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div data-testid="skills-col-moves">
            <h4 className="text-f13 font-medium mb-2">招式</h4>
            <ul className="space-y-2">
              {(moves || []).map((c) => (
                <li key={c.slug}>
                  <button type="button" className="text-left w-full rounded-lg border border-line px-3 py-2 hover:bg-soft cursor-pointer"
                    onClick={() => { setMoveBody(c); setSkillBody(null); setMethodBody(null) }}>
                    <div className="text-f13 font-medium">{c.name}</div>
                    <div className="text-meta text-faint">{c.formula?.arrow || c.one_liner}</div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div data-testid="skills-col-catalog">
            <h4 className="text-f13 font-medium mb-2">编目（{(methods || []).length}）</h4>
            <div className="max-h-80 overflow-auto space-y-2">
              {Object.entries(layerGroups).map(([layer, rows]) => (
                <div key={layer}>
                  <div className="text-meta text-faint px-1">{layer}</div>
                  {rows.map((m) => (
                    <button key={m.id} type="button" className="text-left w-full rounded-md border border-line/60 px-2 py-1.5 mb-1 hover:bg-soft cursor-pointer"
                      onClick={() => api.authorMethod?.(m.id).then((r) => { setMethodBody(r.content || ''); setSkillBody(null); setMoveBody(null) }).catch((e) => setErr(String(e)))}>
                      <div className="text-f12">{m.title}</div>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
        {skillBody && <pre className="p-3 rounded-lg bg-canvas border border-line text-f12 whitespace-pre-wrap max-h-96 overflow-auto" data-testid="skill-body">{typeof skillBody === 'string' ? skillBody : JSON.stringify(skillBody)}</pre>}
        {moveBody && (
          <div className="p-3 rounded-lg bg-canvas border border-line text-f12 space-y-1" data-testid="move-body">
            <div className="font-medium">{moveBody.name} · {moveBody.formula?.arrow}</div>
            <div>直线病：{moveBody.straight_line}</div>
            <div>{moveBody.usage}</div>
          </div>
        )}
        {methodBody && <pre className="p-3 rounded-lg bg-canvas border border-line text-f12 whitespace-pre-wrap max-h-96 overflow-auto" data-testid="method-body">{methodBody}</pre>}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="author-panels">
          <div className="rounded-lg border border-line p-3">
            <h4 className="text-f13 font-medium mb-2">质量清单（勾选不进生成）</h4>
            <ul className="space-y-1">
              {(panels?.checklist || []).map((it) => (
                <li key={it.id}>
                  <label className="flex items-center gap-2 text-f12 cursor-pointer">
                    <input type="checkbox" checked={checkSel.has(it.id)} onChange={() => {
                      const n = new Set(checkSel)
                      if (n.has(it.id)) n.delete(it.id); else n.add(it.id)
                      setCheckSel(n)
                    }} />
                    {it.label}
                  </label>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-line p-3 text-f12 space-y-2">
            <div><span className="font-medium">钩类型</span>：{(panels?.hook_types || []).map((h) => h.label).join(' / ')}</div>
            <div><span className="font-medium">开篇</span>
              <ul className="list-disc pl-4">{(panels?.opening || []).map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
            <div><span className="font-medium">大纲</span>
              <ul className="list-disc pl-4">{(panels?.outline || []).map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
            <div><span className="font-medium">日更</span>
              <ul className="list-disc pl-4">{(panels?.daily || []).map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
            <div><span className="font-medium">回炉</span>
              <ul className="list-disc pl-4">{(panels?.revision || []).map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
          </div>
        </div>
        {bannedLex && (
          <p className="text-meta text-faint" data-testid="banned-lexicon-link">
            禁词只读：{bannedLex.source} · {bannedLex.count} 类（不进技法正文）
          </p>
        )}
      </div>
    )
  } else if (section?.id === 'mcp') {
    main = <CapabilityRegistry />
  } else if (section?.id === 'health') {
    main = (
      <div className="p-5 space-y-4" data-testid="system-hub-health">
        <ObserveStrip />
        <p className="text-meta text-faint">更细的上下文溯源请返回写作台打开「上下文检查器」。</p>
      </div>
    )
  } else if (section?.id === 'evolution') {
    main = (
      <div className="p-5" data-testid="system-hub-evolution">
        <p className="text-f12 text-faint mb-3">可升格教训（只读入口）。</p>
        {Array.isArray(lessons) && lessons.length === 0 && <div className="text-f13 text-faint">暂无 promotable lessons。</div>}
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
        {renderSettingsList(byCat('llm').filter((i) => isAdmin || i.audience !== 'admin'), 'llm-settings')}
      </div>
    )
  } else if (section?.id === 'surreal') {
    main = (
      <div className="p-5 space-y-4" data-testid="system-hub-surreal">
        <div className="rounded-lg border border-line p-3 text-f13">
          健康 · work=<code className="text-meta">{work}</code>{' '}
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
                <button key={tb.id} type="button"
                  className="rounded-lg px-3 py-1.5 text-f12 border border-line hover:bg-soft cursor-pointer"
                  onClick={() => api.adminDataRows?.(tb.id, work).then((r) => setTableRows(r)).catch((e) => setErr(String(e)))}>
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
    main = <div className="p-5">{renderSettingsList(byCat('connection'), 'connection-settings')}</div>
  } else if (section?.id === 'flags') {
    main = <div className="p-5">{renderSettingsList(byCat('flags'), 'flags-settings')}</div>
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
              <button type="button"
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
                      <button type="button"
                        className={`w-full text-left px-2 py-1 rounded-md text-f12 cursor-pointer ${
                          sectionId === s.id ? 'bg-brand/10 text-brand' : 'text-faint hover:text-ink hover:bg-soft'
                        }`}
                        onClick={() => { setSectionId(s.id); setModuleId(null) }}
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
          {moduleId && section?.id !== 'map' && (
            <div className="px-5 pt-4">
              <ModulePane
                id={moduleId}
                health={dataHealth}
                work={work}
                onClose={() => setModuleId(null)}
                onGoSection={goSection}
              />
            </div>
          )}
          {main}
        </div>
      </div>
    </div>
  )
}
