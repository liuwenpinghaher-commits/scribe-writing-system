/**
 * Benchmark 参考库（O32 · advisory 模板 · 落盘持久 · 不自动写正文）
 */
import { useEffect, useState } from 'react'
import { api } from '../api'
import { Btn } from '../ui.jsx'

export function BenchmarkLibrary() {
  const [items, setItems] = useState([])
  const [title, setTitle] = useState('')
  const [notes, setNotes] = useState('')
  const [err, setErr] = useState('')

  const load = async () => {
    setErr('')
    try {
      const j = typeof api.benchmarks === 'function'
        ? await api.benchmarks()
        : await api.get('/benchmarks')
      setItems(j.items || [])
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '加载失败')
    }
  }

  useEffect(() => { load() }, [])

  const add = async () => {
    try {
      if (typeof api.benchmarkUpsert === 'function') {
        await api.benchmarkUpsert({ title, notes, tags: ['advisory'] })
      } else {
        await api.post('/benchmarks', { title, notes, tags: ['advisory'] })
      }
      setTitle('')
      setNotes('')
      load()
    } catch (e) {
      setErr(e?.body?.detail || e?.message || '保存失败')
    }
  }

  return (
    <div className="p-4 space-y-3" data-testid="benchmark-library">
      <h2 className="font-semibold">Benchmark / 参考库</h2>
      <p className="text-xs opacity-60">仅 advisory 模板，不会自动写入章正文。</p>
      {err && <div className="text-amber-700 text-sm">{err}</div>}
      <div className="flex flex-col gap-2 max-w-md">
        <input className="border rounded px-2 py-1" placeholder="标题" value={title} onChange={(e) => setTitle(e.target.value)} />
        <textarea className="border rounded px-2 py-1" placeholder="笔记" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <Btn onClick={add}>添加</Btn>
      </div>
      <ul className="text-sm space-y-1">
        {items.map((it) => (
          <li key={it.id} className="border-b border-black/5 py-1">
            <strong>{it.title}</strong>
            <div className="opacity-70 text-xs">{it.notes}</div>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default BenchmarkLibrary
