import { useEffect, useRef, useState } from 'react'
import { useEditor, EditorContent, useEditorState } from '@tiptap/react'
import { BubbleMenu } from '@tiptap/react/menus'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import CharacterCount from '@tiptap/extension-character-count'
import Focus from '@tiptap/extension-focus'
import { Bold, Italic, Strikethrough, Copy, Target, RotateCcw, Sparkles } from 'lucide-react'
import { SceneBreak } from './SceneBreak'

const esc = (s) => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

// 纯文本 ↔ TipTap:段落 \n\n 隔;「* * *」/「***」行 → 场景分隔节点。
function toHTML(text) {
  const blocks = (text || '').split(/\n{2,}/)
  if (blocks.length <= 1) {
    return (text || '').split('\n').map((l) => {
      const t = l.trim()
      if (t === '* * *' || t === '***') return '<hr data-scene-break>'
      return `<p>${esc(l) || '<br>'}</p>`
    }).join('') || '<p></p>'
  }
  return blocks.map((b) => {
    const t = b.trim()
    if (t === '* * *' || t === '***') return '<hr data-scene-break>'
    return `<p>${esc(b)}</p>`
  }).join('')
}
function toText(editor) {
  const parts = []
  editor.state.doc.forEach((node) => {
    parts.push(node.type.name === 'sceneBreak' ? '* * *' : node.textContent)
  })
  return parts.join('\n\n')
}

// PM 位置 → prose 字符串偏移。必须与 toText 同口径:
// 顶层块以 \n\n 相连,sceneBreak 序列化为 '* * *',段落用 node.textContent。
// 段落内文本始于 nodeStart+1(开标记占 1 位),据此把 PM 位置折算到块内文本偏移。
function pmPosToProseOffset(doc, pmPos) {
  let offset = 0
  let result = null
  let pos = 0   // 每个顶层节点前的 PM 位置
  doc.forEach((node) => {
    if (result !== null) { pos += node.nodeSize; return }
    const serialized = node.type.name === 'sceneBreak' ? '* * *' : node.textContent
    const nodeStart = pos
    const nodeEnd = pos + node.nodeSize
    if (pmPos <= nodeStart) {
      // 位置落在本块之前的块边界:偏移即当前累积值
      result = offset
    } else if (pmPos < nodeEnd) {
      if (node.type.name === 'sceneBreak') {
        // atom 节点内部无文本;落在其上 → 取块起始偏移
        result = offset
      } else {
        // 段落内:文本始于 nodeStart+1,折算块内偏移并夹取
        const inBlock = Math.max(0, Math.min(serialized.length, pmPos - (nodeStart + 1)))
        result = offset + inBlock
      }
    } else {
      // 位置在本块之后:累加本块序列化长度 + 块间分隔符 \n\n
      offset += serialized.length + 2
    }
    pos = nodeEnd
  })
  return result === null ? offset : result
}

export function ProseEditor({ value, onChange, chapterKey, placeholder = '开始写本章……', focusMode = false, onDiscuss }) {
  const [chars, setChars] = useState(0)
  const [recovered, setRecovered] = useState(null)
  const lastEmit = useRef(value || '')
  const draftTimer = useRef(null)
  const dkey = `s3-draft-${chapterKey || 'x'}`

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ horizontalRule: false }),
      Placeholder.configure({ placeholder, showOnlyWhenEditable: true }),
      CharacterCount,
      Focus.configure({ className: 'has-focus', mode: 'deepest' }),
      SceneBreak,
    ],
    content: toHTML(value),
    immediatelyRender: false,
    shouldRerenderOnTransaction: false,
    editorProps: {
      attributes: { class: 'tiptap-prose', spellcheck: 'false' },
      handleDOMEvents: {
        compositionstart: (view) => { view.dom.dataset.composing = 'true'; return false },
        compositionend: (view) => { delete view.dom.dataset.composing; return false },
      },
    },
    onUpdate: ({ editor }) => {
      setChars(editor.storage.characterCount.characters())
      const txt = toText(editor)
      lastEmit.current = txt
      onChange?.(txt)
      clearTimeout(draftTimer.current)
      draftTimer.current = setTimeout(() => { if (txt.trim()) localStorage.setItem(dkey, txt) }, 1000)
    },
  }, [chapterKey])

  // 外部 value 变化(载章 / render 灌入)→ 仅当与当前不同才 setContent,避免回灌循环
  useEffect(() => {
    if (!editor) return
    if ((value || '') !== lastEmit.current) {
      editor.commands.setContent(toHTML(value), { emitUpdate: false })
      lastEmit.current = value || ''
      setChars(editor.storage.characterCount.characters())
    }
    // 防丢草稿:本地草稿比落库内容更新且非空 → 提示恢复
    const d = localStorage.getItem(dkey)
    setRecovered(d && d.trim() && d !== (value || '') ? d : null)
  }, [value, editor, dkey])

  const sel = useEditorState({
    editor,
    selector: ({ editor }) => editor ? {
      bold: editor.isActive('bold'), italic: editor.isActive('italic'), strike: editor.isActive('strike'),
    } : { bold: false, italic: false, strike: false },
  })

  const restore = () => {
    if (!editor || !recovered) return
    editor.commands.setContent(toHTML(recovered))
    lastEmit.current = recovered; onChange?.(recovered); setRecovered(null)
  }
  const discard = () => { localStorage.removeItem(dkey); setRecovered(null) }

  if (!editor) return <div className="text-faint text-sm p-4">编辑器加载中…</div>
  const Bub = ({ on, onClick, title, children }) => (
    <button onMouseDown={(e) => e.preventDefault()} onClick={onClick} title={title}
      className={`w-7 h-7 grid place-items-center rounded-md transition-colors cursor-pointer ${on ? 'bg-brand text-white' : 'text-ink hover:bg-soft'}`}>{children}</button>
  )

  return (
    <div className={`tiptap-shell ${focusMode ? 'focus-mode' : ''}`}>
      {recovered && (
        <div className="mb-3 rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 flex items-center gap-2 text-[13px]">
          <RotateCcw size={14} className="text-warn shrink-0" />
          <span className="text-ink flex-1">发现上次未保存的草稿。</span>
          <button onClick={restore} className="px-2 py-0.5 rounded text-brand hover:bg-soft text-[12px] cursor-pointer">恢复</button>
          <button onClick={discard} className="px-2 py-0.5 rounded text-faint hover:bg-soft text-[12px] cursor-pointer">丢弃</button>
        </div>
      )}
      <BubbleMenu editor={editor} options={{ placement: 'top', offset: 8 }}
        shouldShow={({ editor, state, from, to }) => {
          if (!editor.isEditable || state.selection.empty || from === to) return false
          if (state.selection.constructor.name === 'NodeSelection') return false
          return true
        }}>
        <div className="flex items-center gap-0.5 rounded-lg border border-line bg-surface p-1 shadow-lg">
          <Bub on={sel.bold} onClick={() => editor.chain().focus().toggleBold().run()} title="加粗"><Bold size={14} /></Bub>
          <Bub on={sel.italic} onClick={() => editor.chain().focus().toggleItalic().run()} title="斜体"><Italic size={14} /></Bub>
          <Bub on={sel.strike} onClick={() => editor.chain().focus().toggleStrike().run()} title="删除线"><Strikethrough size={14} /></Bub>
          <div className="w-px h-5 bg-line mx-0.5" />
          <Bub onClick={() => { const { from, to } = editor.state.selection; navigator.clipboard?.writeText(editor.state.doc.textBetween(from, to, '\n')) }} title="复制选区"><Copy size={14} /></Bub>
          {onDiscuss && (
            <>
              <div className="w-px h-5 bg-line mx-0.5" />
              <button onMouseDown={(e) => e.preventDefault()} title="让主编改这段"
                onClick={() => {
                  const { from: pmFrom, to: pmTo } = editor.state.selection
                  // prose 字符串与 toText 同口径;偏移由同口径转换器折算,text 直接从该串切片 → 三者必然自洽
                  const proseStr = toText(editor)
                  const from = pmPosToProseOffset(editor.state.doc, pmFrom)
                  const to = pmPosToProseOffset(editor.state.doc, pmTo)
                  onDiscuss({ text: proseStr.slice(from, to), from, to })
                }}
                className="h-7 px-2 inline-flex items-center gap-1 rounded-md text-[12px] text-brand hover:bg-soft cursor-pointer transition-colors"><Sparkles size={13} />改这段</button>
            </>
          )}
          <span className="px-1.5 text-[11px] text-faint tnum inline-flex items-center gap-1"><Target size={11} />{Math.abs(editor.state.selection.to - editor.state.selection.from)}</span>
        </div>
      </BubbleMenu>
      <EditorContent editor={editor} />
      <div className="mt-2 text-right text-[11px] text-faint tnum">{chars} 字</div>
    </div>
  )
}
