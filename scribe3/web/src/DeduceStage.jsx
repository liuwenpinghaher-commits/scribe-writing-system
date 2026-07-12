import { useEffect, useRef, useState } from 'react'
import { Sparkles, Loader2, MessagesSquare } from 'lucide-react'
import { api } from './api'
import { useDeduceSel } from './deduceContext'
import { useStageProposal, useChiefSlot, ProposalBar } from './ChiefSlotContext'
import { useToast } from './ui/Toast.jsx'
import { Btn } from './ui.jsx'
import { RichEditor, useUnsavedGuard } from './editor/RichEditor.jsx'

// Task 4:话术引用截断——chiefIntent 只是预填输入框,长演绎全文引用会塞爆(spec §4 要点4)。
const QUOTE_MAX = 400
const truncateQuote = (s) => {
  const t = (s || '').trim()
  return t.length > QUOTE_MAX ? t.slice(0, QUOTE_MAX) + '…' : t
}

// 演绎中区:据当前选中(truth 或 character_id)显示/编辑/生成并失焦落库。
// work 由 ChapterStudio 透传(实例 key=work,值稳定):卸载兜底 flush 钉死目标书,防切书写错书(F6,同 F1/F5)。
export function DeduceStage({ seq, meta, onSaved, work }) {
  const toast = useToast()
  const { selected, setSelected } = useDeduceSel()
  const { setChiefIntent } = useChiefSlot()
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const chars = meta?.chars || []
  const cur = selected === 'truth'
    ? { name: '场景真相', prose: meta?.scene_truth || '' }
    : (meta?.deductions || []).find((d) => d.character_id === selected)
      || { character_id: selected, character_name: (chars.find((c) => c.id === selected) || {}).name || selected, prose: '' }
  // 工作态 ref:持当前 selected/seq/text/dirty,完全脱离 state 闭包,切换/落库时机都拿最新值。
  const workRef = useRef({ selected, seq, text: '', dirty: false })

  // persistFor:用捕获的旧 sel/sq/val 落库,不读可能已变的 state/props。返回是否成功,供调用方恢复 dirty 重试。
  // 角色分支读最新 chapter 再合并 deductions,避免用过期 meta 覆盖其他角色投影。
  const persistFor = async (sel, sq, val) => {
    try {
      if (sel === 'truth') {
        // 传 work:切书卸载 flush 走全局 WORK 会把本书场景真相写进别的书(F6,同 OutlineTab/BeatsTab 钉书)
        await api.patchChapter(sq, { scene_truth: val }, work)
      } else {
        const ch = await api.chapter(sq, work)                 // 读最新且钉住目标书,避免 meta 过期覆盖别的角色/读错书
        const others = (ch?.deductions || []).filter((d) => d.character_id !== sel)
        const name = (meta?.chars?.find((c) => c.id === sel) || {}).name
          || (ch?.deductions || []).find((d) => d.character_id === sel)?.character_name || sel
        await api.patchChapter(sq, { deductions: [...others, { character_id: sel, character_name: name, prose: val }] }, work)
      }
      onSaved?.()
      return true
    } catch (e) {
      toast(e?.body?.detail || '演绎保存失败,请重试', { tone: 'danger' })
      return false
    }
  }

  // 切换(选中项/切章):进入时 workRef 仍持旧 selected/seq/text;若 dirty 先把旧的 flush 掉,再载新的。
  // alive 取消令牌:persist 在途时目标再变(A→B→C),旧 effect 续体不得 setText/写 workRef,
  // 否则旧目标内容回灌且后续编辑错写到中间目标。
  // flush 失败 → 不覆盖 workRef 旧值,恢复 dirty,并把选中态回滚到旧目标(标题与编辑器不分叉,可重试)。
  useEffect(() => {
    let alive = true
    const flushThenLoad = async () => {
      const w = workRef.current
      let flushed = null   // 本次成功 flush 的 {sel, sq, val}
      if (w.dirty) {
        const { selected: sel, seq: sq, text: val } = w
        w.dirty = false
        const ok = await persistFor(sel, sq, val)
        if (!alive) {
          // 目标又变了:最新 effect 已按 dirty=false 加载新目标,此处绝不回写 workRef(否则错置)。
          if (!ok) console.warn('[deduce] flush 失败且目标已再切换,该次未保存内容无法自动恢复', sel, sq)
          return
        }
        if (!ok) {
          workRef.current = { selected: sel, seq: sq, text: val, dirty: true }
          // 回滚选中项到旧目标(切章失败无法回滚章导航,编辑器停在未保存内容,失焦/再切换可重试)
          if (sq === seq && sel !== selected) setSelected(sel)
          return
        }
        flushed = { sel, sq, val }
      }
      // 载入新目标;若新目标恰是刚成功 flush 的同一目标(回滚重试成功路径),用刚保存的值,防 stale meta 回灌
      const v = (flushed && flushed.sel === selected && flushed.sq === seq) ? flushed.val : (cur.prose || '')
      setText(v)
      workRef.current = { selected, seq, text: v, dirty: false }
    }
    flushThenLoad()
    return () => { alive = false }
  }, [selected, seq]) // eslint-disable-line

  // 失焦 flush:从 workRef 读实时值(不读 state 闭包),与切换 flush 同一落库口径。
  // 失败且仍停在同一目标 → 恢复 dirty 可重试(已切走则由 flushThenLoad 分支兜)。
  const blur = () => {
    const w = workRef.current
    if (!w.dirty) return
    const { selected: sel, seq: sq, text: val } = w
    w.dirty = false
    persistFor(sel, sq, val).then((ok) => {
      const c = workRef.current
      if (!ok && c.selected === sel && c.seq === sq) c.dirty = true
    })
  }
  useUnsavedGuard(() => workRef.current.dirty)

  // 卸载(切阶段)前 flush 兜底:blur 不一定先于卸载触发(键盘/程序化切换)。
  // 卸载后无法 await/重试,fire-and-forget;失败除 persistFor 的 danger toast 外再 console.warn 留痕。
  useEffect(() => () => {
    const w = workRef.current
    if (w.dirty) {
      w.dirty = false
      persistFor(w.selected, w.seq, w.text)
        .then((ok) => { if (!ok) console.warn('[deduce] 卸载 flush 保存失败', w.selected, w.seq) })
    }
  }, []) // eslint-disable-line

  // 块二:接主编 stageProposal —— phase='deduce' 且 seq/target(truth 或角色)全匹配才显示,
  // 防切章/切目标错落。落进编辑器置 dirty,走上面失焦/切换/卸载的健壮保存。
  const { pending, clear } = useStageProposal('deduce', seq, selected)
  const fillPending = () => {
    if (!pending) return
    setText(pending.content)
    workRef.current = { selected, seq, text: pending.content, dirty: true }
    clear(); toast('已填入,失焦自动存')
  }
  const appendPending = () => {
    if (!pending) return
    const w = workRef.current
    const base = (w.selected === selected && w.seq === seq) ? w.text : text
    const next = (base ? base + '\n\n' : '') + pending.content
    setText(next)
    workRef.current = { selected, seq, text: next, dirty: true }
    clear(); toast('已追加,失焦自动存')
  }

  // Task 4:条目级「聊这条/改这条」——当前演绎目标(truth 或角色)话术经 chiefIntent 预填进右栏,
  // 落地复用既有 fillPending(=替换当前目标 prose,零新落地逻辑,详见 Step 1 核实)。
  const targetName = selected === 'truth' ? '场景真相' : cur.character_name
  // 内容为空(或纯空白)时禁用入口:空引号话术没有讨论/改稿对象,只会让主编猜。
  const noProse = !text.trim()
  const notifyChief = () => { try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ } }
  const chatCur = () => {
    if (noProse) return
    setChiefIntent({ phase: 'deduce', seq, text: `就本章「${targetName}」的演绎和你聊聊(先不改):「${truncateQuote(text)}」\n` })
    notifyChief()
  }
  const editCur = () => {
    if (noProse) return
    setChiefIntent({ phase: 'deduce', seq, text: `把本章「${targetName}」这条演绎改一下,直接给出改后的完整演绎:「${truncateQuote(text)}」` })
    notifyChief()
  }

  const gen = () => {
    setBusy(true); let acc = ''
    const instr = selected === 'truth'
      ? `写第${seq}章这一场的「场景真相」:全知冷叙,客观上真正发生了什么,含角色们察觉不到的隐藏机制。据本章大纲/节拍/设定(含私密)。只输出真相正文。`
      : `以「${cur.character_name}」截至第${seq}章的限知,写他这一场的限知投影,分五个小标题:看到/听到、知道、以为(误读)、做了/说了、没察觉的;每个小标题用 markdown 三级标题(### 标题)独立起行。据场景真相与他的限知帧,只含他所知所感。`
    // 后端写作流事件:proposal_start → proposal_chunk（逐段文本，用于流式预览）→ proposal（完整稿）。
    // 兼容纯 delta 流。全部累进到 acc，完成后落库。
    api.chatWrite(instr, {
      // phase='deduce':后端据此注入场景真相(投影从同一真相派生的物理保证,断头修复#5)
      chapter: seq, phase: 'deduce', focalizer: selected === 'truth' ? '' : selected,
      onProposalStart: () => { acc = ''; setText('') },
      onProposalChunk: (c) => { acc += (c?.text ?? c ?? ''); setText(acc) },
      onDelta: (d) => { acc += d; setText(acc) },
      onProposal: (p) => { acc = p.prose ?? p.text ?? acc; setText(acc) },
      onDone: () => {
        setBusy(false); const v = acc.trim()
        if (v) { persistFor(selected, seq, v); workRef.current = { selected, seq, text: v, dirty: false } }
      },
      onError: (e) => { setBusy(false); toast('演绎失败:' + e, { tone: 'danger' }) },  // 不动 text,保留已有内容
    })
  }

  return (
    <div
      data-testid="deduce-stage"
      className="w-full max-w-[min(1120px,calc(100%-48px))] mx-auto px-6 py-6 h-full flex flex-col min-h-0"
    >
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-f14 font-semibold text-ink">{selected === 'truth' ? '场景真相 · 全知' : `${cur.character_name} · 限知投影`}</h3>
        <Btn variant="ghost" size="sm" onClick={chatCur} disabled={noProse}
          title={noProse ? '就这条演绎和主编讨论(该演绎还没有内容)' : '就这条演绎和主编讨论'}
          aria-label="就这条演绎和主编讨论" className="ml-auto">
          <MessagesSquare size={13} />聊这条
        </Btn>
        <Btn variant="ghost" size="sm" onClick={editCur} disabled={noProse}
          title={noProse ? '让主编改这条演绎(该演绎还没有内容)' : '让主编改这条演绎'}
          aria-label="让主编改这条演绎">
          <Sparkles size={13} />改这条
        </Btn>
        <Btn variant="primary" size="sm" onClick={gen} disabled={busy}>
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}{busy ? '演绎中…' : '生成'}
        </Btn>
      </div>
      {pending && (
        <ProposalBar
          text={`主编生成了「${selected === 'truth' ? '场景真相' : cur.character_name}」的内容(${pending.content.replace(/\s/g, '').length} 字)。`}
          actions={[{ label: '填入', variant: 'primary', onClick: fillPending }, { label: '追加', onClick: appendPending }]}
          onDismiss={clear}
        />
      )}
      <RichEditor value={text} editorKey={`${seq}|${selected}`}
        ariaLabel={selected === 'truth' ? '场景真相' : '限知投影'}
        onChange={(md) => { setText(md); workRef.current.text = md; workRef.current.dirty = true }} onBlur={blur}
        placeholder={selected === 'truth' ? '这一场客观真正发生了什么(全知,含隐藏机制)…' : '看到/听到 · 知道 · 以为(误读) · 做了/说了 · 没察觉的'}
        className="flex-1 min-h-0 w-full" />
      <div className="text-f12 text-faint mt-2">失焦自动存;所有角色投影都从「场景真相」派生,保持一致。</div>
    </div>
  )
}
