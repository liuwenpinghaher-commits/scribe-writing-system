import { useEffect, useRef, useState } from 'react'
import { api } from '../../api'
import { targetNodeToSelection } from '../../layout/targetNavigation'
import { focusChiefWithSeed } from '../../lib/chiefSeed.js'

// 范围有效 = [from, to) 两个有限数且 to > from。causal 等来源会给 [0,0] 占位,
// 那不是真范围:不渲染(旧版把它显示成 "0-0" 假范围)、也不参与定位核对。
function validRange(range) {
  return Array.isArray(range) && range.length === 2
    && range.every((n) => Number.isFinite(n)) && range[1] > range[0]
}

// Task 10 Step 5:校验详情只给真实控制。
//   · 定位:先用当前正文核对范围,正文已变化(范围越界)就不跳错误范围,给出恢复路径;
//     无定位目标(如"本章总览")直接不渲染定位按钮,不再静默吞点击。
//   · 修复:必须有真实 onFix handler 才渲染(旧版没有 handler 时伪装成定位)。
//   · 重新检查:真实调用 /issues(后端每次即算即返 = 重跑确定性检测),
//     拿到该命中的最新数据(range/reason)后恢复可定位;命中消失则如实说明。
export function IssueDetail({ node, onLocate, onFix, onRecheck }) {
  // fresh:重新检查后的最新命中数据,优先于节点自带 payload(DetailPane 按 node.id 挂 key,切命中会重建组件)
  const [fresh, setFresh] = useState(null)
  // notice:定位/重查的失败与恢复状态。state: idle|checking|stale|gone|error
  const [notice, setNotice] = useState({ state: 'idle', msg: '' })
  // unmount 守卫:async handler 回来时组件可能已卸载(切命中/切栏),避免 setState on unmounted。
  // 与本目录 Promise/Motif 面板 effect 里的 `let alive` 同向,只是这里的 async 在事件回调、故用 ref。
  const aliveRef = useRef(true)
  useEffect(() => { aliveRef.current = true; return () => { aliveRef.current = false } }, [])
  const issue = fresh || node?.payload || node || {}
  const range = validRange(issue.range) ? issue.range : null
  const busy = notice.state === 'checking'
  // 能否定位由真实换算决定 —— 与 FourPaneShell.handleNavigateToObject 同源
  // (targetNodeToSelection):换算不出导航目标的按钮不渲染,而不是点了没反应。
  const locatable = Boolean(onLocate && issue.target_node && targetNodeToSelection(issue.target_node))
  const canRecheck = issue.id != null && issue.chapter != null

  const doLocate = async () => {
    // 定位前用当前正文核对范围:范围越界说明正文已变化,拒绝定位到错误范围。
    if (range && issue.chapter != null) {
      setNotice({ state: 'checking', msg: '' })
      let prose = null
      try {
        const ch = await api.chapter(issue.chapter)
        prose = typeof ch?.prose === 'string' ? ch.prose : null
      } catch {
        // 正文暂不可读 ≠ 已变化:不据此误报;仍按章定位(编辑器层还有"失配丢弃"兜底,不会标错)。
        prose = null
      }
      if (!aliveRef.current) return
      if (prose != null && range[1] > prose.length) {
        setNotice({ state: 'stale', msg: '正文已变化,重新检查后再定位。' })
        return
      }
    }
    setNotice({ state: 'idle', msg: '' })
    onLocate?.(issue.target_node)
  }

  const doRecheck = async () => {
    onRecheck?.(issue)   // 上层有真实协同 handler 时同步告知(缺省无副作用)
    setNotice({ state: 'checking', msg: '' })
    try {
      const r = await api.issues(issue.chapter)
      if (!aliveRef.current) return
      const hit = (Array.isArray(r?.issues) ? r.issues : []).find((it) => it.id === issue.id)
      if (hit) {
        setFresh(hit)
        setNotice({ state: 'idle', msg: '' })
      } else {
        setNotice({ state: 'gone', msg: '重新检查后该命中已不存在,可能已修复。' })
      }
    } catch (e) {
      if (!aliveRef.current) return
      setNotice({ state: 'error', msg: e?.body?.detail || e?.message || '重新检查失败' })
    }
  }

  return (
    <div className="h-full overflow-auto bg-canvas px-6 py-6">
      <div className="mx-auto max-w-[52rem] space-y-4">
        <div>
          <div className="mb-1 text-f12 text-faint">能力工作台</div>
          <h2 className="type-section text-ink">校验详情</h2>
        </div>
        <section className="rounded-lg border border-line bg-surface p-4">
          <div className="mb-1 text-f14 font-semibold text-ink">{issue.title || node?.label || '校验命中'}</div>
          <div className="mb-3 flex flex-wrap gap-2 text-meta text-faint">
            {issue.source && <span>{issue.source}</span>}
            {issue.severity && <span>{issue.severity}</span>}
            {issue.chapter != null && <span>第 {issue.chapter} 章</span>}
            {range && <span>{range[0]}-{range[1]}</span>}
          </div>
          {issue.reason && <p className="text-f13 leading-7 text-ink">{issue.reason}</p>}
          {issue.suggested_action && (
            <div className="mt-3 rounded-md bg-soft px-3 py-2">
              <div className="mb-1 text-meta font-semibold text-faint">修复建议</div>
              <p className="text-f12 leading-6 text-fore">{issue.suggested_action}</p>
            </div>
          )}
          {(notice.state === 'stale' || notice.state === 'gone' || notice.state === 'error') && (
            <div role="alert" className="mt-3 rounded-md border border-danger/30 bg-danger/5 px-3 py-2 text-f12 text-danger">
              {notice.msg}
            </div>
          )}
          {(locatable || onFix || canRecheck) && (
            <div className="mt-4 flex gap-2">
              {locatable && (
                <button type="button" onClick={doLocate} disabled={busy}
                  className="rounded-md border border-brand/40 px-3 py-1.5 text-f12 text-brand hover:bg-brand/10 disabled:opacity-50">
                  定位
                </button>
              )}
              {/* 待接线:全仓暂无生产 onFix 传入(DetailPane 只传 onLocate/onRecheck),
                  此分支当前生产不可达——留接口不留假按钮,避免"修复是活功能"的错觉。 */}
              {onFix && (
                <button type="button" onClick={() => onFix(issue)}
                  className="rounded-md border border-line px-3 py-1.5 text-f12 text-ink hover:bg-soft">
                  修复
                </button>
              )}
              {canRecheck && (
                <button type="button" onClick={doRecheck} disabled={busy}
                  className="rounded-md border border-line px-3 py-1.5 text-f12 text-faint hover:text-ink disabled:opacity-50">
                  {busy ? '检查中…' : '重新检查'}
                </button>
              )}
              <button
                type="button"
                data-testid="issue-seed-chief"
                onClick={() => {
                  const title = issue.title || '校验命中'
                  const reason = issue.reason || issue.message || ''
                  const act = issue.suggested_action || '请按约束改写本章相关段落。'
                  focusChiefWithSeed(
                    `请根据校验命中修订第 ${issue.chapter ?? '?'} 章：\n`
                    + `· ${title}\n· ${reason}\n· 建议：${act}\n`
                    + '先只读核实正文，再提出可审批的改写；未获批准不得声称已落库。',
                  )
                }}
                className="rounded-md border border-brand/40 px-3 py-1.5 text-f12 text-brand hover:bg-brand/10"
              >
                让主编处理
              </button>
            </div>
          )}
          {/* 无定位/重查时仍可种子主编 */}
          {!(locatable || onFix || canRecheck) && (
            <div className="mt-4">
              <button
                type="button"
                data-testid="issue-seed-chief"
                onClick={() => {
                  focusChiefWithSeed(
                    `请处理校验：${issue.title || ''}\n${issue.reason || ''}\n${issue.suggested_action || ''}`,
                  )
                }}
                className="rounded-md border border-brand/40 px-3 py-1.5 text-f12 text-brand hover:bg-brand/10"
              >
                让主编处理
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
