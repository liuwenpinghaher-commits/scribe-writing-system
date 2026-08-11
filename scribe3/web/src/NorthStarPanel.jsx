// 评分卡面板(产品名锁定「评分卡」· IA KD-IA-3):双级 scorecard,三分栏展示——
// constraints / advisory_scores / fulfillment。绝不合成总分。
// 与顶栏「作品意图」(intent:main)不是同一物——旧称「北极星」易混。
// 数据刷新走 /live SSE:BinderLayout 广播 s3-live,不自开 EventSource。
import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, BookOpen, Gauge, ShieldCheck, Target } from 'lucide-react'
import { api } from './api'
import { Empty, Skeleton, Tag } from './ui'

const GRADE_TONE = { light: 'ok', medium: 'brand', heavy: 'danger' }

// 硬约束一行:null=不可判(N/A,如实展示,绝不当 0 假绿);0=在区间;>0=违规数。
function Constraint({ label, value, naText }) {
  const na = value === null || value === undefined
  const bad = !na && value > 0
  return (
    <div className="flex items-center justify-between py-1 text-f12">
      <span className="text-ink">{label}</span>
      {na
        ? <span className="text-faint">{naText || 'N/A'}</span>
        : <span className={`inline-flex items-center gap-1.5 ${bad ? 'text-danger' : 'text-ok'}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${bad ? 'bg-danger' : 'bg-ok'}`} />
            {value}
          </span>}
    </div>
  )
}

function Pane({ icon: I, title, tone, children }) {
  return (
    <div className="mb-3.5 last:mb-0 pb-2.5 border-b border-line/50 last:border-0">
      <div className={`flex items-center gap-1.5 text-meta uppercase tracking-wider mb-1.5 ${tone || 'text-faint'}`}>
        <I size={12} className="shrink-0" />{title}
      </div>
      {children}
    </div>
  )
}

function Dim({ label, main, sub, warn }) {
  return (
    <div className="py-1 text-f12 flex items-start justify-between gap-2">
      <span className="text-ink shrink-0">{label}</span>
      <span className={`text-right ${warn ? 'text-warn' : 'text-faint'}`}>{main}{sub && <div className="text-meta text-faint">{sub}</div>}</span>
    </div>
  )
}

export function NorthStarPanel({ seq, scope }) {
  const [ch, setCh] = useState(undefined)     // undefined=加载中,null=失败/无
  const [book, setBook] = useState(undefined)

  const load = useCallback(() => {
    if (seq != null) api.northStarChapter(seq).then(setCh).catch(() => setCh(null))
    api.northStarBook().then(setBook).catch(() => setBook(null))
  }, [seq])

  useEffect(() => { setCh(undefined); setBook(undefined); load() }, [load])
  useEffect(() => {
    let timer = null
    const h = (e) => {
      const d = e?.detail || {}
      const t = d.table
      // 变更表已知且与面板无关 → 跳过;格式未知(无 table 字段)→ 保守重取
      if (t && !['chapter', 'chapter_scorecard', 'promise', 'lesson'].includes(t)) return
      // 章级评分卡：有 id 且能解析出其他章号 → 跳过
      if (t === 'chapter' && seq != null && d.id) {
        const m = String(d.id).match(/chapter[:：]?(\d+)/i)
        if (m && Number(m[1]) !== Number(seq)) return
      }
      clearTimeout(timer)
      timer = setTimeout(load, 800)
    }
    window.addEventListener('s3-live', h)
    return () => { clearTimeout(timer); window.removeEventListener('s3-live', h) }
  }, [load, seq])

  const c = ch?.constraints
  const a = ch?.advisory_scores
  const f = ch?.fulfillment
  const degraded = ch?.degraded || []

  return (
    <div data-testid="scorecard-panel">
      <p className="mb-2 text-meta text-faint" title="与顶栏作品意图不是同一物" data-testid="scorecard-readonly-hint">
        评分卡（机器只读 · 硬约束/软参考/目的达成）· <strong className="font-medium text-ink">不是可写 SSOT</strong>
        · 改读者感受/红线请用顶栏「作品意图」· 缺大纲/节拍请去章阶段让主编写，勿「生成评分卡」
      </p>
      {/* ===== 章级 ===== */}
      {scope !== 'book' && (
        seq == null ? <Empty>未选章</Empty> : ch === undefined ? <Skeleton /> : ch === null ? (
          <Empty>本章暂无评分卡（无正文或加载失败）</Empty>
        ) : (
          <>
            {degraded.length > 0 && (
              <div className="mb-2 flex items-center gap-1.5 rounded-md border border-warn/30 bg-warn/10 px-2 py-1 text-meta text-warn">
                <AlertTriangle size={11} className="shrink-0" />
                检测降级:{degraded.join('、')}(没查≠没病,人工过目)
              </div>
            )}
            <Pane icon={ShieldCheck} title={`第 ${seq} 章 · 硬约束 setpoint(违规=0 为在区间)`}>
              <Constraint label="限知泄露 leaks" value={c?.leaks} naText="全知章 N/A" />
              <Constraint label="模型退化 blocking" value={c?.degeneration_blocking} />
              <Constraint label="因果违规 qc_causal" value={c?.qc_causal === -1 ? null : c?.qc_causal} naText="无事件数据(-1 哨兵)" />
              <Constraint label="伏笔超期" value={c?.promise_overdue} />
            </Pane>
            <Pane icon={Gauge} title="软参考(只提示,不门禁)">
              <div className="flex items-center gap-2 py-1 text-f12">
                <span className="text-ink">AI 味定档</span>
                {a?.ai_grade
                  ? <Tag tone={GRADE_TONE[a.ai_grade.grade] || 'faint'}>{a.ai_grade.grade}{a.ai_grade.gates_hit?.length ? ` · Gate ${a.ai_grade.gates_hit.join('/')}` : ''}</Tag>
                  : <span className="text-faint">降级,无数据</span>}
              </div>
              {a?.qc_breakdown && (
                <div className="text-meta text-faint">
                  {Object.entries(a.qc_breakdown).map(([k, v]) => `${k}:${v}`).join(' · ')}
                </div>
              )}
            </Pane>
            <Pane icon={Target} title="目的达成 fulfillment(验「做没做」,不验好坏)">
              {f?.status === 'active' ? (
                <>
                  <div className="flex flex-wrap gap-1.5 py-1">
                    <Tag tone="ok">达成 {f.achieved}</Tag>
                    <Tag tone={f.carried ? 'danger' : 'faint'}>滚动 {f.carried}</Tag>
                    <Tag tone="faint">计划 {f.planned}</Tag>
                    <Tag tone="faint">放弃 {f.waived}</Tag>
                  </div>
                  {f.alert && (
                    <div className="text-meta text-amber-600 flex items-center gap-1">
                      <AlertTriangle size={11} />连续 {f.carried_chain_max} 章未达成:目的与实际写作脱节,该修目的还是修稿,人来定
                    </div>
                  )}
                </>
              ) : (
                <div className="text-meta text-faint">{f?.note || '未登记目的合同'}</div>
              )}
            </Pane>
          </>
        )
      )}

      {/* ===== 书级 ===== */}
      <Pane icon={BookOpen} title="书级四维(不合成总分;全绿≠书好,裁决在人)" tone="text-brand">
        {book === undefined ? <Skeleton /> : book === null ? (
          <Empty>书级数据加载失败</Empty>
        ) : (
          <>
            <Dim label="张弛分布"
                 main={book.tension?.no_data ? (book.tension?.degraded ? '计算失败(degraded)' : '无节拍标注数据') : (book.tension?.findings?.length ? `${book.tension.findings.length} 处失衡` : '无失衡')}
                 warn={!!book.tension?.findings?.length} />
            <Dim label="伏笔回收率"
                 main={book.promise_recovery?.no_data ? (book.promise_recovery?.degraded ? '计算失败(degraded)' : '无伏笔数据') : (book.promise_recovery?.rate == null ? '—' : `${Math.round(book.promise_recovery.rate * 100)}%`)}
                 sub={book.promise_recovery?.no_data ? '' : `开 ${book.promise_recovery.open} · 收 ${book.promise_recovery.payoff} · 超期 ${book.promise_recovery.overdue}`}
                 warn={(book.promise_recovery?.overdue || 0) > 0} />
            <Dim label="跨章矛盾密度"
                 main={book.contradiction_density?.no_data ? (book.contradiction_density?.degraded ? '计算失败(degraded)' : '无正文数据') : `${(book.contradiction_density?.per_10k ?? 0).toFixed(2)} / 万字`}
                 sub="仅自比趋势,不可对标外部基准" />
            <Dim label="目的达成率"
                 main={book.fulfillment?.no_data ? (book.fulfillment?.degraded ? '计算失败(degraded)' : '未启用目的合同') : (book.fulfillment?.rate == null ? '—' : `${Math.round(book.fulfillment.rate * 100)}%`)}
                 sub={book.fulfillment?.no_data ? '' : `欠账 ${book.fulfillment.carried_backlog} · 放弃 ${book.fulfillment.waived}(链尾去重口径)`}
                 warn={(book.fulfillment?.carried_backlog || 0) > 0} />
            <Dim label="因果欠账存量" main={book.causal_debt_total ?? '—'} warn={(book.causal_debt_total || 0) > 0} />
            {book.style_diversity && !book.style_diversity.no_data && (
              <div className="mt-1 pt-1 border-t border-line">
                <Dim label="文体多样性"
                     main={book.style_diversity.insufficient_window
                       ? `样本 ${book.style_diversity.profiles_n} 章(不足告警窗口,非"无漂移")`
                       : (book.style_diversity.alerts?.length ? `${book.style_diversity.alerts.length} 条告警` : '无单调化迹象')}
                     warn={!!book.style_diversity.alerts?.length} />
                {(book.style_diversity.alerts || []).map((al, i) => (
                  <div key={i} className="text-meta text-amber-600 mt-0.5">{al.detail}</div>
                ))}
              </div>
            )}
          </>
        )}
      </Pane>
    </div>
  )
}
