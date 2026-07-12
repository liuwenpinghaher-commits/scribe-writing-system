import { useState } from 'react'

// 各偏好键的真实判定语义以消费点为准(核对表见 Task 15 交付报告):
//   s3-theme      App.jsx:14        `localStorage.getItem('s3-theme') || 'light'` 后 `theme === 'dark'` 才挂 dark class
//   s3.layout.v2  layoutFlag.js:3   `storage.getItem('s3.layout.v2') !== '0'`(未设=开,四栏默认)
//   scribe3:guardOn WriteLayout.jsx:129 `localStorage.getItem('scribe3:guardOn') !== '0'`(未设=开)
//   scribe3:serif   WriteLayout.jsx:148 `localStorage.getItem('scribe3:serif') === '1'`(未设=关)
// isOn 直接照搬各消费点的判定表达式,switch 初始态与实际生效状态保证一致。
const PREFS = [
  { key: 's3-theme', label: '深色主题',
    isOn: (v) => v === 'dark', toggle: (on) => (on ? 'dark' : 'light') },
  { key: 's3.layout.v2', label: '四栏布局(关=旧三栏)', hint: '刷新后生效',
    isOn: (v) => v !== '0', toggle: (on) => (on ? '1' : '0') },
  // guardOn/serif 消费点(WriteLayout.jsx:129/148)是 useState 惰性初始化读取,
  // 已挂载的写作台不会热生效——如实标注,别让作者以为开关坏了。
  { key: 'scribe3:guardOn', label: '写作护栏默认开启', hint: '切书或刷新后生效',
    isOn: (v) => v !== '0', toggle: (on) => (on ? '1' : '0') },
  { key: 'scribe3:serif', label: '正文衬线字体', hint: '切书或刷新后生效',
    isOn: (v) => v === '1', toggle: (on) => (on ? '1' : '0') },
]

// 脉搏维度中文名——与 PulseBar.jsx 的 DIM_LABEL 保持一致(补 stuck,PulseBar 该维无固定文案)。
const DIM_LABEL = {
  promise: '伏笔', arc: '弧光', relation: '关系',
  tension: '张力', causal: '因果', quality: '质量', stuck: '卡文',
}

function PrefRow({ item, onChanged }) {
  const val = localStorage.getItem(item.key)
  const on = item.isOn(val)
  const flip = () => {
    const next = !on
    localStorage.setItem(item.key, item.toggle(next))
    window.dispatchEvent(new CustomEvent('s3-pref-changed', { detail: { key: item.key } }))
    onChanged()
  }
  return (
    <div className="flex items-center gap-3 border-b border-line py-3">
      <div className="flex-1 min-w-0">
        <div className="text-f13 text-ink">{item.label}</div>
        {item.hint && <div className="text-meta text-faint mt-0.5">{item.hint}</div>}
      </div>
      <button role="switch" aria-checked={on} aria-label={item.label} onClick={flip}
        className={`h-5 w-9 rounded-full transition-colors cursor-pointer shrink-0 ${on ? 'bg-brand' : 'bg-line'}`}>
        <span className={`block h-4 w-4 rounded-full bg-surface transition-transform ${on ? 'translate-x-4' : 'translate-x-0.5'}`} />
      </button>
    </div>
  )
}

function MuteList({ work, onChanged }) {
  const w = work || 'main'
  const prefix = `s3.pulse.mute.${w}.`
  // 用 length+key(i) 而非 Object.keys(localStorage) 枚举:标准 Storage 接口两种
  // 方式在真实浏览器里等价,但测试环境(vitest.setup.js)的内存 mock 只实现了
  // 前者(Object.keys 枚举出的是 getItem/setItem 等方法名,不是存的键),用
  // length+key 两边都能跑。
  const dims = []
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i)
    if (k && k.startsWith(prefix) && localStorage.getItem(k) === '1') dims.push(k.slice(prefix.length))
  }
  const clear = (dim) => { localStorage.removeItem(prefix + dim); onChanged() }
  return (
    <div className="mt-2">
      <div className="text-f13 font-medium text-ink mb-2">脉搏静音清单</div>
      {dims.length === 0
        ? <div className="text-f13 text-faint">无静音项</div>
        : dims.map((dim) => (
          <div key={dim} className="flex items-center gap-2 text-f13 py-1.5 border-b border-line/50 last:border-0">
            <span className="text-ink">{DIM_LABEL[dim] || dim}</span>
            <button className="ml-auto text-meta text-brand cursor-pointer" onClick={() => clear(dim)}>解除静音</button>
          </div>
        ))}
    </div>
  )
}

// 个人偏好:纯本地(localStorage)开关清单,不落库、不按书隔离(除脉搏静音——它本身按书记键)。
// 每个开关切换即时生效并派发 s3-pref-changed,供 App.jsx 等热切消费点监听(如主题免刷新)。
export function PrefsSection({ work }) {
  // tick 只用于强制重渲染(PrefRow/MuteList 每次渲染都直读 localStorage,不持有内部状态)。
  const [, setTick] = useState(0)
  const bump = () => setTick((t) => t + 1)
  return (
    <div data-testid="prefs-section">
      <div className="mb-4">
        {PREFS.map((item) => <PrefRow key={item.key} item={item} onChanged={bump} />)}
      </div>
      <MuteList work={work} onChanged={bump} />
    </div>
  )
}
