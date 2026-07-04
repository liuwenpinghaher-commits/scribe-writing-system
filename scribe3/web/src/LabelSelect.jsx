import { LABELS, LABEL_META } from './outlineColors'

// 章状态选择器(#70)——卡片墙/大纲表「按状态」色源的生产入口。
//
// 背景:outlineColors.cardColorVar 默认 status 模式读 chapter.label,ChapterCard/Outliner 消费
// LABEL_META[label] 出五值徽章;但前端从无任何 patchChapter({label}) 入口 → 真书章 label 恒 null
// → 「按状态」色彩恒全灰、五值徽章永不出现(已建成的色彩编码不可用,#70)。补此下拉打通生产侧。
//
// 后端契约(migration 044):chapter.label 是 option<string>,ASSERT `NONE 或 idea/draft/revise/done/beat`。
//   · 设值 → 发对应枚举串;
//   · 清空「未设」→ 必须发 null(实测 label:null → 200 清空;label:'' → 500,空串过不了 ASSERT)。
// onChange(nullOrLabel):null=清空,否则为五枚举之一。上层 patchLabel → api.patchChapter(seq,{label})。
export function LabelSelect({ value, onChange, className = '' }) {
  const meta = LABEL_META[value]
  return (
    <select
      value={value || ''}
      // 卡片内:阻止冒泡,避免误触卡片其它点击目标 / 触发 dnd
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => { e.stopPropagation(); const v = e.target.value; onChange?.(v === '' ? null : v) }}
      title="章状态(卡片墙/大纲表「按状态」色源)"
      style={meta ? { color: `var(--color-${meta.token})` } : undefined}
      className={`cursor-pointer bg-transparent outline-none rounded hover:bg-soft/40 transition-colors ${meta ? '' : 'text-faint/50'} ${className}`}
    >
      <option value="">未设</option>
      {LABELS.map((l) => <option key={l} value={l}>{LABEL_META[l].text}</option>)}
    </select>
  )
}
