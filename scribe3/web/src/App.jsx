import React, { useEffect, useState } from 'react'
import * as api from './api.js'

// 写作台 v2 双表面:结构面(设计 fabula)/ 散文面(渲染 sjuzhet)/ 校验面(连贯·反讽)。
// 散文面居中、权重最大(primary)。限知:渲染只吃 focalizer 知识帧,帧外私密进不去。
const C = {
  bg: '#1a1a1e', panel: '#23232a', line: '#34343d', text: '#e8e8ea', dim: '#9a9aa5',
  accent: '#c9a86a', danger: '#d4756b', irony: '#7aa6d4', secret: '#b06b8f',
}
const box = { background: C.panel, border: `1px solid ${C.line}`, borderRadius: 8, padding: 12 }

export default function App() {
  const [chapter, setChapter] = useState(1)
  const [entities, setEntities] = useState([])
  const [focalizer, setFocalizer] = useState('')
  const [facts, setFacts] = useState([])
  const [events, setEvents] = useState([])
  const [frame, setFrame] = useState([])
  const [causal, setCausal] = useState([])
  const [irony, setIrony] = useState([])
  const [prose, setProse] = useState('')
  const [rendering, setRendering] = useState(false)
  const [tick, setTick] = useState(0)        // SSE 变更计数:任一表变 → +1 → 各视图重取
  const [live, setLive] = useState(false)

  // 订阅 NS=scribe3 变更(开一次;改一处处处同步)
  useEffect(() => {
    const es = api.openLive(() => setTick((t) => t + 1))
    es.onopen = () => setLive(true)
    es.onerror = () => setLive(false)
    return () => es.close()
  }, [])

  useEffect(() => {
    api.getEntities().then((es) => {
      setEntities(es)
      const chars = es.filter((e) => e.kind === 'character')
      if (chars.length) setFocalizer((f) => f || chars[0].id)
    })
  }, [tick])

  useEffect(() => {
    api.getFacts(chapter).then(setFacts)
    api.getEvents(chapter).then(setEvents)
    api.getCausal(chapter).then(setCausal)
  }, [chapter, tick])

  useEffect(() => {
    if (!focalizer) return
    api.getFrame(focalizer, chapter).then(setFrame)
    api.getIrony(focalizer, chapter).then(setIrony)
  }, [focalizer, chapter, tick])

  const render = async () => {
    setRendering(true)
    setProse('')
    try {
      const r = await api.postRender(focalizer, chapter)
      setProse(r.prose || '(空)')
    } catch (e) {
      setProse('渲染失败:' + e.message)
    } finally {
      setRendering(false)
    }
  }

  const chars = entities.filter((e) => e.kind === 'character')
  const focName = (chars.find((c) => c.id === focalizer) || {}).name || focalizer

  return (
    <div style={{ background: C.bg, color: C.text, minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      {/* 顶栏 */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '10px 16px', borderBottom: `1px solid ${C.line}` }}>
        <strong style={{ color: C.accent }}>scribe3 · 写作台 v2</strong>
        <span style={{ color: C.dim, fontSize: 13 }}>NS=scribe3 · 限知靠知识帧投影</span>
        <span title={live ? 'LIVE 已连(改一处处处同步)' : 'LIVE 未连'}
          style={{ fontSize: 12, color: live ? '#6db07a' : C.dim }}>● {live ? 'LIVE' : '离线'}</span>
        <span style={{ marginLeft: 'auto' }}>章
          <input type="number" min={1} value={chapter} onChange={(e) => setChapter(+e.target.value || 1)}
            style={{ width: 56, marginLeft: 6, background: C.panel, color: C.text, border: `1px solid ${C.line}`, borderRadius: 4, padding: '2px 6px' }} />
        </span>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '26% 1fr 26%', gap: 12, padding: 12, height: 'calc(100vh - 52px)', boxSizing: 'border-box' }}>
        {/* ── 结构面 fabula ── */}
        <section style={{ ...box, overflow: 'auto' }}>
          <h3 style={{ marginTop: 0, color: C.accent }}>结构面 · fabula</h3>
          <div style={{ color: C.dim, fontSize: 12, margin: '6px 0' }}>本章事件</div>
          {events.length === 0 && <div style={{ color: C.dim }}>(无)</div>}
          {events.map((ev) => (
            <div key={ev.id} style={{ padding: '4px 0', borderBottom: `1px solid ${C.line}` }}>
              <span style={{ color: C.accent }}>[{ev.type}]</span> {ev.id}
              {!ev.goal && <span title="缺目标" style={{ color: C.danger }}> ⚠无目标</span>}
            </div>
          ))}
          <div style={{ color: C.dim, fontSize: 12, margin: '12px 0 6px' }}>本章事实</div>
          {facts.map((f) => (
            <div key={f.id} style={{ padding: '3px 0', fontSize: 13 }}>
              {f.secret && <span title="私密" style={{ color: C.secret }}>🔒 </span>}
              <span style={{ color: C.dim }}>{f.entity}·{f.attribute}:</span>{f.value}
            </div>
          ))}
        </section>

        {/* ── 散文面 sjuzhet(primary)── */}
        <section style={{ ...box, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <h3 style={{ margin: 0, color: C.accent }}>散文面 · sjuzhet</h3>
            <span style={{ color: C.dim, fontSize: 13 }}>视角</span>
            <select value={focalizer} onChange={(e) => setFocalizer(e.target.value)}
              style={{ background: C.panel, color: C.text, border: `1px solid ${C.line}`, borderRadius: 4, padding: '3px 8px' }}>
              {chars.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <button onClick={render} disabled={rendering || !focalizer}
              style={{ marginLeft: 'auto', background: rendering ? C.line : C.accent, color: '#1a1a1e', border: 'none', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: rendering ? 'wait' : 'pointer' }}>
              {rendering ? '渲染中…' : '渲染本场'}
            </button>
          </div>
          <div style={{ color: C.dim, fontSize: 12, margin: '8px 0' }}>
            {focName} 此刻所知（渲染只能用这些，帧外私密写不出）：{frame.map((f) => f.value).join(' · ') || '（空）'}
          </div>
          <div style={{ flex: 1, overflow: 'auto', whiteSpace: 'pre-wrap', lineHeight: 1.9, fontSize: 16, padding: 12, background: C.bg, borderRadius: 6, border: `1px solid ${C.line}` }}>
            {rendering ? <span style={{ color: C.dim }}>渲染中（走 Hermes，doubao 可能较慢）…</span>
              : prose || <span style={{ color: C.dim }}>选视角 → 渲染本场。散文只渲染 {focName} 知道的事。</span>}
          </div>
        </section>

        {/* ── 校验面 ── */}
        <section style={{ ...box, overflow: 'auto' }}>
          <h3 style={{ marginTop: 0, color: C.accent }}>校验面</h3>
          <div style={{ color: C.dim, fontSize: 12, margin: '6px 0' }}>连贯性（因果完整）</div>
          {causal.length === 0 ? <div style={{ color: '#6db07a' }}>✓ 干净</div>
            : causal.map((v, i) => <div key={i} style={{ color: C.danger, fontSize: 13, padding: '3px 0' }}>⚠ {v.event}:{v.reason}</div>)}
          <div style={{ color: C.dim, fontSize: 12, margin: '12px 0 6px' }}>戏剧反讽（读者知 · {focName}不知）</div>
          {irony.length === 0 ? <div style={{ color: C.dim }}>（无）</div>
            : irony.map((f) => <div key={f.id} style={{ color: C.irony, fontSize: 13, padding: '3px 0' }}>◆ {f.value}</div>)}
        </section>
      </div>
    </div>
  )
}
