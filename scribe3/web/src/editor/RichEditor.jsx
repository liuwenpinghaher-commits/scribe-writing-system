import { useEffect, useRef, useState } from 'react'
import { useEditor, EditorContent, useEditorState } from '@tiptap/react'
import { BubbleMenu } from '@tiptap/react/menus'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import CharacterCount from '@tiptap/extension-character-count'
import { Bold, Italic, Strikethrough, Heading3 } from 'lucide-react'
import { mdToHTML, docToMd } from './markdown'

/**
 * 前置阶段共享富文本内核(大纲/节拍/演绎/草稿)。
 * 从 ProseEditor 提炼:tiptap + StarterKit + Placeholder + CharacterCount;
 * 去掉正文专属的护栏装饰/场景断。进出均为 markdown 字符串(见 ./markdown.js 口径)。
 *
 * props:
 * - value: markdown 字符串(外部真相源)
 * - onChange(md): 每次编辑派发最新 markdown
 * - onBlur(): 失焦(调用方据此落库)
 * - placeholder / ariaLabel: 占位与无障碍名(playwright getByRole('textbox',{name}) 可选中)
 * - editorKey: 变化时重建编辑器实例(切章/切选中项,清 undo 栈)
 * - minimal: 精简模式(节拍单条):低高度、无字数尾栏、无气泡菜单
 */
export function RichEditor({ value, onChange, onBlur, placeholder = '', ariaLabel, editorKey, minimal = false, className = '' }) {
  const [chars, setChars] = useState(0)
  const lastEmit = useRef(value || '')

  const editor = useEditor({
    extensions: [
      // horizontalRule 保留:md 的 --- 载入为 hr,禁掉会被 PM 静默丢弃、保存即永久删除。
      // link/underline 禁掉:docToMd 不序列化这两个 mark,留着会静默丢格式。
      StarterKit.configure({ link: false, underline: false }),
      Placeholder.configure({ placeholder, showOnlyWhenEditable: true }),
      CharacterCount,
    ],
    content: mdToHTML(value),
    immediatelyRender: false,
    shouldRerenderOnTransaction: false,
    editorProps: {
      attributes: {
        class: minimal ? 'tiptap-rich tiptap-rich-mini' : 'tiptap-rich',
        role: 'textbox',
        'aria-multiline': 'true',
        'aria-label': ariaLabel || placeholder,
        spellcheck: 'false',
      },
      handleDOMEvents: {
        compositionstart: (view) => { view.dom.dataset.composing = 'true'; return false },
        compositionend: (view) => { delete view.dom.dataset.composing; return false },
      },
    },
    onUpdate: ({ editor }) => {
      setChars(editor.storage.characterCount.characters())
      const md = docToMd(editor.state.doc)
      lastEmit.current = md
      onChange?.(md)
    },
    onBlur: () => { onBlur?.() },
  }, [editorKey])

  // 外部 value 变化(载章/生成流灌入)→ 仅当与最近一次 emit 不同才 setContent,避免回灌循环
  useEffect(() => {
    if (!editor) return
    if ((value || '') !== lastEmit.current) {
      editor.commands.setContent(mdToHTML(value), { emitUpdate: false })
      lastEmit.current = value || ''
    }
    setChars(editor.storage.characterCount.characters())
  }, [value, editor])

  const sel = useEditorState({
    editor,
    selector: ({ editor }) => editor ? {
      bold: editor.isActive('bold'), italic: editor.isActive('italic'),
      strike: editor.isActive('strike'), h3: editor.isActive('heading', { level: 3 }),
    } : { bold: false, italic: false, strike: false, h3: false },
  })

  if (!editor) return <div className="text-faint text-f13 p-2">编辑器加载中…</div>

  const Bub = ({ on, onClick, title, children }) => (
    <button onMouseDown={(e) => e.preventDefault()} onClick={onClick} title={title} aria-label={title}
      className={`w-7 h-7 grid place-items-center rounded-md transition-colors cursor-pointer ${on ? 'bg-brand text-brandfg' : 'text-ink hover:bg-soft'}`}>{children}</button>
  )

  return (
    <div className={`rich-shell ${minimal ? '' : 'rich-shell-full'} ${className}`}>
      {!minimal && (
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
            <Bub on={sel.h3} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} title="小标题"><Heading3 size={14} /></Bub>
          </div>
        </BubbleMenu>
      )}
      <EditorContent editor={editor} className="rich-content" />
      {!minimal && <div className="shrink-0 pt-1 text-right text-meta text-faint tnum">{chars} 字</div>}
    </div>
  )
}

/**
 * beforeunload 兜底:isDirty() 为真时,关/刷新页面弹浏览器原生提示。
 * 传入读取函数(通常读 ref),不依赖 state 闭包。
 */
export function useUnsavedGuard(isDirty) {
  const fnRef = useRef(isDirty)
  fnRef.current = isDirty
  useEffect(() => {
    const handler = (e) => { if (fnRef.current()) { e.preventDefault(); e.returnValue = '' } }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [])
}
