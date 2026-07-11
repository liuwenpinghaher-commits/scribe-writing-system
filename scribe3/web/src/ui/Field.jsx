import { cloneElement, useId } from 'react'

export function Field({ label, description, error, required = false, children }) {
  const id = useId()
  const descriptionId = description ? `${id}-description` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy = [descriptionId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-helper font-medium text-ink">
        {label}{required && <span aria-hidden="true"> *</span>}
      </label>
      {cloneElement(children, {
        id,
        required,
        'aria-describedby': describedBy,
        'aria-invalid': error ? true : undefined,
      })}
      {description && <div id={descriptionId} className="text-meta text-muted">{description}</div>}
      {error && <div id={errorId} role="alert" className="text-meta text-danger">{error}</div>}
    </div>
  )
}
