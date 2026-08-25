/**
 * 时间线可读面：按章分组、空态、首屏窗口。
 * 不碰 vis。时间线只回答「事在何时」。
 */
import { jumpWindowForChapter } from './timelineCraft.js'

export function itemChapter(raw) {
  const n = Number(raw?.story_chapter ?? raw?.chapter)
  return Number.isFinite(n) && n > 0 ? n : 0
}

export function itemLabel(raw) {
  if (!raw) return ''
  return String(raw.label || raw.event_type || raw.refs?.relation || raw.id || '').trim()
}

export function catOfKind(kind) {
  if (kind === 'event') return 'event'
  if (kind === 'arc') return 'arc'
  if (kind === 'promise_setup') return 'promise'
  if (kind === 'relation_start') return 'relation'
  if (kind === 'faction_event') return 'faction'
  return null
}

/** 按章分组，章号升序。不点轴也能答「第 N 章有什么」。 */
export function groupTimelineItems(items) {
  const map = new Map()
  for (const it of items || []) {
    const cat = it.cat || catOfKind(it.raw?.kind || it.kind)
    if (!cat) continue
    const raw = it.raw || it
    const ch = itemChapter(raw)
    if (!map.has(ch)) map.set(ch, [])
    map.get(ch).push({ raw, cat, label: itemLabel(raw), chapter: ch })
  }
  return [...map.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([chapter, rows]) => ({ chapter, rows }))
}

/**
 * 有 chapter 时首屏跟当前章（N-5…N+5），不要默认书末 50 章。
 * 无 chapter 才退回末窗，由调用方用 max 去拉。
 */
export function bootWindowForChapter(chapter) {
  const n = Number(chapter)
  if (!Number.isFinite(n) || n < 1) return null
  return jumpWindowForChapter(n)
}

/** kind: loading | no_events | empty_window | error | null */
export function timelineEmptyKind({ data, hasContent, error, loading } = {}) {
  if (error) return 'error'
  if (loading && !data) return 'loading'
  if (data && !hasContent) {
    const n = (data.items || []).length
    if (n === 0) return 'no_events'
    return 'empty_window'
  }
  return null
}

export function timelineEmptyCopy(kind) {
  if (kind === 'no_events') {
    return {
      title: '还没有事件',
      body: '先写一章并过正文反哺，事件、伏笔条才会上轴。',
    }
  }
  if (kind === 'empty_window') {
    return {
      title: '这窗里是空的',
      body: '当前章附近没有条目。拖轴、点「全览」，或换到已写过的章。',
    }
  }
  if (kind === 'error') {
    return {
      title: '时间线加载失败',
      body: '再试一次。还不行就换章窗口。',
    }
  }
  return { title: '加载时间线…', body: '' }
}
