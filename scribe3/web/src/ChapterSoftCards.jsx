/**
 * 章侧 soft 卡片：precheck / literary distill / storyline inject 预览（H5）
 */
import { useState } from 'react'
import { api } from './api'
import { Btn } from './ui.jsx'

function Card({ title, children, testId }) {
  return (
    <div
      className="rounded-lg border border-line bg-canvas p-3 space-y-2"
      data-testid={testId}
    >
      <div className="text-f12 font-medium text-ink">{title}</div>
      {children}
    </div>
  )
}

export function ChapterSoftCards({ seq, work, synopsis, beats }) {
  const [precheck, setPrecheck] = useState(null)
  const [distill, setDistill] = useState(null)
  const [inject, setInject] = useState(null)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')

  const runPrecheck = async () => {
    setBusy('precheck')
    setErr('')
    try {
      const body = {
        seq: Number(seq),
        synopsis: synopsis || '',
        beats: beats || [],
      }
      let r
      if (typeof api.softPrecheck === 'function') {
        r = await api.softPrecheck(body, work)
      } else {
        r = await api.post('/soft-precheck', body)
      }
      setPrecheck(r)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || 'precheck 失败')
    } finally {
      setBusy('')
    }
  }

  const runDistill = async () => {
    setBusy('distill')
    setErr('')
    try {
      const text = synopsis || ''
      let r
      if (typeof api.literaryDistill === 'function') {
        r = await api.literaryDistill({ text, seq: Number(seq) }, work)
      } else {
        r = await api.post('/literary-distill', { text, seq: Number(seq) })
      }
      setDistill(r)
    } catch (e) {
      // 端点可能未挂：本地启发式降级
      const t = String(synopsis || '').trim()
      setDistill({
        surface: 'local_fallback',
        summary: t ? t.slice(0, 200) + (t.length > 200 ? '…' : '') : '（无梗概可蒸馏）',
        note: e?.message || 'API 不可用 · 本地截断',
      })
    } finally {
      setBusy('')
    }
  }

  const runInject = async () => {
    setBusy('inject')
    setErr('')
    try {
      const body = {
        focus_seq: Number(seq),
        chapters: [{ seq: Number(seq), synopsis: synopsis || '' }],
      }
      let r
      if (typeof api.storylineInjectPreview === 'function') {
        r = await api.storylineInjectPreview(body, work)
      } else {
        r = await api.post('/storyline/inject-preview', body)
      }
      setInject(r)
    } catch (e) {
      setErr(e?.body?.detail || e?.message || 'inject 预览失败')
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="space-y-2" data-testid="chapter-soft-cards">
      <div className="text-f12 font-medium text-faint">质量 soft · 预检 / 蒸馏 / 故事线注入</div>
      {err && <div className="text-f11 text-warn">{err}</div>}
      <div className="grid gap-2 sm:grid-cols-3">
        <Card title="Soft 预检" testId="soft-card-precheck">
          <Btn size="sm" disabled={!!busy} onClick={runPrecheck} data-testid="soft-precheck-run">
            {busy === 'precheck' ? '…' : '运行'}
          </Btn>
          {precheck && (
            <pre className="text-f11 text-faint whitespace-pre-wrap max-h-32 overflow-auto">
              {JSON.stringify(precheck, null, 0).slice(0, 600)}
            </pre>
          )}
        </Card>
        <Card title="文学蒸馏" testId="soft-card-distill">
          <Btn size="sm" disabled={!!busy} onClick={runDistill} data-testid="soft-distill-run">
            {busy === 'distill' ? '…' : '近章梗概'}
          </Btn>
          {distill && (
            <div className="text-f11 text-ink leading-relaxed">
              {distill.summary || distill.text || distill.distill || JSON.stringify(distill).slice(0, 300)}
            </div>
          )}
        </Card>
        <Card title="故事线注入预览" testId="soft-card-inject">
          <Btn size="sm" disabled={!!busy} onClick={runInject} data-testid="soft-inject-run">
            {busy === 'inject' ? '…' : '预览'}
          </Btn>
          {inject && (
            <pre className="text-f11 text-faint whitespace-pre-wrap max-h-32 overflow-auto">
              {(inject.text || inject.segment || JSON.stringify(inject)).toString().slice(0, 600)}
            </pre>
          )}
        </Card>
      </div>
    </div>
  )
}

export default ChapterSoftCards
