import { useEffect, useId, useRef, useState } from 'react'
import { cn } from '../lib/utils'
import { SelectionQuoteActions } from './SelectionQuoteActions.jsx'
import { openChiefForEmptyField } from '../lib/selAction.js'

/**
 * Notion 式 click-to-edit 文本原语。
 * 读态：无边框、hover 微底；写态：brand 描边；blur/Enter 提交，Esc 取消。
 */
export function EditableText({
  value,
  onCommit,
  type = 'text',
  multiline = false,
  placeholder,
  emptyLabel,
  label,
  description,
  readOnly = false,
  className,
  displayClassName,
  inputClassName,
  id: idProp,
  'aria-label': ariaLabel,
  testId,
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value ?? '')
  const ref = useRef(null)
  const autoId = useId()
  const id = idProp || autoId
  const isEmpty = value == null || value === ''
  const display = value == null || value === '' ? null : String(value)

  useEffect(() => {
    if (!editing) setDraft(value ?? '')
  }, [value, editing])

  useEffect(() => {
    if (editing && ref.current) ref.current.focus()
  }, [editing])

  if (readOnly) {
    return (
      <div className={cn(label ? 'py-2' : '', className)} data-testid={testId}>
        {label && <div className="text-meta text-faint uppercase tracking-wider mb-1">{label}</div>}
        <div className={cn('type-stage whitespace-pre-wrap', displayClassName)}>
          {display || <span className="text-faint">{placeholder || '—'}</span>}
        </div>
      </div>
    )
  }

  const commit = () => {
    setEditing(false)
    let next = draft
    if (type === 'number') {
      const raw = String(draft ?? '').trim()
      if (raw === '') {
        next = null
      } else {
        const n = Number(raw)
        // 拒绝 NaN / ±Infinity;jsdom 对 number 输入非法串可能清空为 ''(见测试)
        if (!Number.isFinite(n)) {
          setDraft(value ?? '')
          return
        }
        next = n
      }
    }
    const prev = type === 'number'
      ? (value === '' || value == null ? null : Number(value))
      : (value ?? '')
    if (next !== prev) onCommit?.(next)
  }

  const cancel = () => {
    setDraft(value ?? '')
    setEditing(false)
  }

  if (isEmpty && !editing) {
    return (
      <div className={cn('py-1.5', className)} data-testid={testId}>
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="text-f12 text-faint hover:text-brand cursor-pointer transition-colors duration-150"
        >
          {emptyLabel || (label ? `+ 添加${label}` : '+ 添加')}
        </button>
      </div>
    )
  }

  if (editing) {
    const editChrome = cn(
      'w-full rounded-lg border border-brand/40 bg-canvas px-3 py-2 type-stage outline-none focus:border-brand',
      inputClassName,
    )
    return (
      <div className={cn('py-2', className)} data-testid={testId} onClick={(e) => e.stopPropagation()}>
        {label && (
          <label htmlFor={id} className="block text-meta text-faint uppercase tracking-wider mb-1">
            {label}
          </label>
        )}
        {description && <div className="text-meta text-faint/60 mb-1.5">{description}</div>}
        {multiline ? (
          <textarea
            ref={ref}
            id={id}
            value={draft}
            rows={4}
            aria-label={ariaLabel || label}
            placeholder={placeholder || (label ? `输入${label}...` : undefined)}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => { if (e.key === 'Escape') cancel() }}
            className={cn(editChrome, 'resize-y')}
          />
        ) : type === 'select' ? null : (
          <input
            ref={ref}
            id={id}
            type={type === 'number' ? 'number' : 'text'}
            value={draft}
            aria-label={ariaLabel || label}
            placeholder={placeholder || (label ? `输入${label}...` : undefined)}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit()
              if (e.key === 'Escape') cancel()
            }}
            className={cn(editChrome, 'h-9 py-0')}
          />
        )}
        <div className="text-meta text-faint/50 mt-0.5">失焦自动保存 · ESC 取消</div>
      </div>
    )
  }

  return (
    <div className={cn('group py-2', className)} data-testid={testId}>
      <div className="flex items-center gap-2 mb-1">
        {label && <span className="text-meta text-faint uppercase tracking-wider">{label}</span>}
        <button
          type="button"
          onClick={() => setEditing(true)}
          aria-label={label ? `编辑${label}` : '编辑'}
          className="text-meta text-brand opacity-0 group-hover:opacity-100 focus-visible:opacity-100 cursor-pointer transition-opacity"
        >
          编辑
        </button>
      </div>
      <div
        role="button"
        tabIndex={0}
        className={cn(
          'type-stage cursor-text hover:bg-soft/30 rounded-md px-2 py-1.5 -mx-1 transition-colors duration-150 whitespace-pre-wrap',
          displayClassName,
        )}
        onClick={() => setEditing(true)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setEditing(true)
          }
        }}
      >
        {display || placeholder || '—'}
      </div>
    </div>
  )
}

/** 带分区分隔的字段壳（section 顶部分割线） */
export function EditableField({ section, children, className, ...p }) {
  return (
    <div className={cn(section ? 'mt-3 pt-3 border-t border-line/60' : '', className)}>
      {children ?? <EditableText {...p} />}
    </div>
  )
}

/** 只读展示：纯文本，无边框假输入盒 */
export function ReadOnlyText({
  label,
  value,
  section,
  placeholder = '—',
  emptyHint,
  testId,
  className,
  scopeLabel,
  /** 空字段「聊聊」时的条目名（角色名等） */
  entityLabel,
  /** 空字段写入时的字段键（可选，进主编话术） */
  fieldKey,
  /** 覆盖默认空字段动作；false 关闭空字段按钮 */
  emptyAsk = true,
  emptyAskLabel = '聊聊怎么写',
  onEmptyAsk,
}) {
  const display = Array.isArray(value)
    ? (value.length ? value.join('、') : null)
    : (value == null || value === '' ? null : String(value))
  const body = (
    <div className="type-stage whitespace-pre-wrap min-h-[1.25rem]">
      {display || <span className="text-faint">{emptyHint || placeholder}</span>}
    </div>
  )
  const askEmpty = () => {
    if (typeof onEmptyAsk === 'function') {
      onEmptyAsk({ label, fieldKey, entityLabel })
      return
    }
    openChiefForEmptyField({
      entityLabel: entityLabel || scopeLabel || '当前条目',
      fieldLabel: label || fieldKey || '该字段',
      fieldKey,
    })
  }
  const showEmptyAsk = !display && emptyAsk !== false && (onEmptyAsk || label || fieldKey)
  return (
    <div
      className={cn(`py-2 ${section ? 'mt-3 pt-3 border-t border-line/60' : ''}`, className)}
      data-testid={testId || undefined}
    >
      {label && <div className="text-meta text-faint uppercase tracking-wider mb-1">{label}</div>}
      {/* 有正文：划选聊/改；空字段：显式「聊聊怎么写」指定这一项进主编 */}
      {display
        ? (
          <SelectionQuoteActions scopeLabel={scopeLabel || label || '设定字段'}>
            {body}
          </SelectionQuoteActions>
        )
        : (
          <div className="flex items-start gap-2 flex-wrap min-w-0">
            <div className="min-w-0 flex-1">{body}</div>
            {showEmptyAsk && (
              <button
                type="button"
                data-testid={testId ? `${testId}-empty-ask` : 'readonly-empty-ask'}
                onClick={askEmpty}
                className="shrink-0 h-7 px-2 rounded-md text-f12 text-brand hover:bg-brand/10 cursor-pointer whitespace-nowrap"
                title={`指定「${label || fieldKey || '该字段'}」到主编对话`}
              >
                {emptyAskLabel}
              </button>
            )}
          </div>
        )}
    </div>
  )
}
