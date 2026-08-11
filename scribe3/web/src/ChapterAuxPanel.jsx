import { useEffect, useState } from 'react'
import { api } from './api'
import { Tabs } from './ui/Tabs'
import { BriefPanel } from './BriefPanel'
import { FramePanel } from './FramePanel'
import { NorthStarPanel } from './NorthStarPanel'
import { ExperiencePressurePanel } from './ExperiencePressurePanel'

// 章节辅助面板:简报/关联/评分卡/经验复盘 是"读着写"的辅助资料,不是章的写作阶段。
// 产品名锁定(IA):评分卡≠作品意图;经验复盘≠力学合同 pressure_drive。
// tab 受控/非受控双模见历史注释;onSelectNode 透传关联跳转。
const AUX_TAB_KEYS = new Set(['brief', 'frame', 'northstar', 'pressure'])
export function ChapterAuxPanel({ seq, initialTab, tab: tabProp, onTabChange, onSelectNode }) {
  const [tabState, setTabState] = useState(() => (AUX_TAB_KEYS.has(initialTab) ? initialTab : 'brief'))
  // 受控判定:tab prop 是合法 key 即受控(受控下 initialTab 不参与,内部 state 只为非受控兜底)
  const controlled = AUX_TAB_KEYS.has(tabProp)
  const tab = controlled ? tabProp : tabState
  const setTab = (next) => {
    if (!controlled) setTabState(next)
    onTabChange?.(next)
  }
  // C1:关联页需要本章限知视角——挂载语境不传章 meta,面板自拉(左栏惯例,见 studioDocks:57-72):
  // api.chapter 取 focalizer,s3-live 的 chapter 变更重拉(顶栏改视角存稿后不按库中旧视角渲);
  // fail-soft:拉不到时降级为空 focalizer(FramePanel 显全知空态),不崩面板。
  const [focalizer, setFocalizer] = useState('')
  const [chars, setChars] = useState([])
  useEffect(() => {
    if (seq == null) { setFocalizer(''); return undefined }
    let cancelled = false
    const pull = () => api.chapter(seq)
      .then((ch) => { if (!cancelled) setFocalizer(ch?.focalizer || '') })
      .catch(() => { if (!cancelled) setFocalizer('') })
    pull()
    const onLive = (e) => {
      const d = e?.detail || {}
      if ((d.table || d.tb) !== 'chapter') return
      // 有 id 且指向其他章 → 跳过
      if (d.id && seq != null) {
        const m = String(d.id).match(/chapter[:：]?(\d+)/i)
        if (m && Number(m[1]) !== Number(seq)) return
      }
      pull()
    }
    window.addEventListener('s3-live', onLive)
    return () => {
      cancelled = true
      window.removeEventListener('s3-live', onLive)
    }
  }, [seq])
  // 角色候选(FramePanel 的视角切换 options):书级数据,挂载拉一次即可
  // (宿主 ErrorBoundary key 含 seq,切章重挂本组件时自然重拉)。
  useEffect(() => {
    let cancelled = false
    api.entities()
      .then((es) => { if (!cancelled) setChars((Array.isArray(es) ? es : []).filter((e) => e.kind === 'character')) })
      .catch(() => { if (!cancelled) setChars([]) })
    return () => { cancelled = true }
  }, [])
  const items = [
    { value: 'brief', label: '简报' },
    { value: 'frame', label: '关联' },
    { value: 'northstar', label: '评分卡', title: '机器评分卡 · 与顶栏「作品意图」不是同一物' },
    { value: 'pressure', label: '经验复盘', title: '经验六格/问诊 · 与写路径力学合同不是同一物' },
  ]
  // 栏3 内容区适配:内容套一层宽松 max-w 居中(超宽屏不贴边拉满),Tabs 与内容同一约束对齐;
  // BriefPanel/FramePanel/NorthStarPanel 内部不动,自适应可用宽度。
  return (
    <div className="flex h-full min-h-0 flex-col px-4 pb-4">
      {!controlled && (
        <div className="mx-auto w-full max-w-[96rem] shrink-0 pt-4">
          <Tabs ariaLabel="章节辅助" value={tab} onValueChange={setTab} items={items} />
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-auto pt-3">
        <div className="mx-auto w-full max-w-[96rem]">
          {tab === 'brief' && <BriefPanel seq={seq} />}
          {tab === 'frame' && (
            <FramePanel
              chapter={seq}
              focalizer={focalizer}
              focalizerOptions={chars}
              onSelectNode={onSelectNode}
            />
          )}
          {tab === 'northstar' && <NorthStarPanel seq={seq} />}
          {tab === 'pressure' && <ExperiencePressurePanel seq={seq} />}
        </div>
      </div>
    </div>
  )
}
