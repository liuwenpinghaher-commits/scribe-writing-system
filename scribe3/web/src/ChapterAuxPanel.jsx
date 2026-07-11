import { useEffect, useState } from 'react'
import { api } from './api'
import { Tabs } from './ui/Tabs'
import { BriefPanel } from './BriefPanel'
import { FramePanel } from './FramePanel'
import { NorthStarPanel } from './NorthStarPanel'

// 章节辅助面板(Task 7):简报/关联/北极星是"读着写"的辅助资料,不是章的写作阶段——
// 从章阶段页签移入右栏,选中章时经 RightDock 的「章节辅助」capability 挂载。
// 签名只收 { seq }:RightDock 无 work 形参,面板走全局 WORK(与左栏 FramePanel 同惯例,
// 见 studioDocks 左栏 caps;2026-07-11 裁决:FramePanel 省略 work prop,不碰在途 FourPaneShell)。
// 点行导航:onSelectNode 不传——RightDock 语境无导航回调通道,FramePanel 内为可选链 no-op
// (FramePanel.jsx:595 `onSelectNode?.(…)`);接线留待 Task 8 右栏作用域。
export function ChapterAuxPanel({ seq }) {
  const [tab, setTab] = useState('brief')
  // C1:关联页需要本章限知视角——RightDock 不传章 meta,面板自拉(左栏惯例,见 studioDocks:57-72):
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
    const onLive = (e) => { if ((e?.detail?.table || e?.detail?.tb) === 'chapter') pull() }
    window.addEventListener('s3-live', onLive)
    return () => {
      cancelled = true
      window.removeEventListener('s3-live', onLive)
    }
  }, [seq])
  // 角色候选(FramePanel 的视角切换 options):书级数据,挂载拉一次即可
  // (RightDock 的 ErrorBoundary key 含 seq,切章重挂本组件时自然重拉)。
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
    { value: 'northstar', label: '北极星' },
  ]
  return (
    <div className="flex h-full min-h-0 flex-col p-3">
      <Tabs ariaLabel="章节辅助" value={tab} onValueChange={setTab} items={items} />
      <div className="min-h-0 flex-1 overflow-auto pt-3">
        {tab === 'brief' && <BriefPanel seq={seq} />}
        {tab === 'frame' && <FramePanel chapter={seq} focalizer={focalizer} focalizerOptions={chars} />}
        {tab === 'northstar' && <NorthStarPanel seq={seq} />}
      </div>
    </div>
  )
}
