import { Command } from 'cmdk'
import { Library as LibIcon } from 'lucide-react'
import { VIEWS } from './AppRail'
import { OVERLAY_CLASS } from './ui/Dialog.jsx'

function Item({ onSelect, icon: Icon, label }) {
  return (
    <Command.Item onSelect={onSelect} value={label}
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-f13 text-ink cursor-pointer data-[selected=true]:bg-soft">
      {Icon && <Icon size={15} className="text-faint" />}{label}
    </Command.Item>
  )
}

// ⌘K 命令面板:跳视图 / 切书 / 回作品库(借鉴 scribe2 cmdk)。
export function CommandPalette({ open, onClose, works, cur, onView, onSelectWork, onLibrary }) {
  if (!open) return null
  const act = (fn) => { fn(); onClose() }
  return (
    <div className={`${OVERLAY_CLASS} flex items-start justify-center pt-[16vh]`} onClick={onClose}>
      <Command label="命令面板" className="w-full max-w-lg rounded-md border border-line bg-surface shadow-2xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <Command.Input autoFocus placeholder="跳视图 / 切书 / 作品库…"
          className="w-full h-12 px-4 bg-transparent text-f14 text-ink outline-none border-b border-line placeholder:text-faint/60" />
        <Command.List className="max-h-[52vh] overflow-y-auto p-2 [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-meta [&_[cmdk-group-heading]]:text-faint [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider">
          <Command.Empty className="px-3 py-6 text-center text-faint text-f13">无匹配</Command.Empty>
          {cur && (
            <Command.Group heading="视图">
              {VIEWS.map((v) => <Item key={v.key} onSelect={() => act(() => onView(v.key))} icon={v.icon} label={v.label} />)}
            </Command.Group>
          )}
          <Command.Group heading="作品">
            {works.map((w) => <Item key={w.slug} onSelect={() => act(() => onSelectWork(w))} icon={LibIcon} label={w.title} />)}
            <Item onSelect={() => act(onLibrary)} icon={LibIcon} label="作品库…" />
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  )
}
