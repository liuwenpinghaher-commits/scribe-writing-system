// 时间线「叙事顺序」轴是否可用的诚实判定(#74)。
//
// 双轴(故事编年 / 叙事顺序)只在存在「叙事位 ≠ 故事章」的事件(倒叙/闪回)时才有区别:
//   axis='story'     → 事件横铺坐标 = story_chapter
//   axis='narrative' → 事件横铺坐标 = narrative_position ?? story_chapter
// 若全书没有任何事件设过 narrative_position(或都等于 story_chapter),两轴投影完全一致,
// 切「叙事顺序」是纯空操作。而 UI 手编事件的叙事位入口(patchEventNarrative)本就未接线、
// ingest 也不写该字段 —— 纯 UI 作者的 np 恒 null,死切换会误导「这里有东西可切」。
//
// 故:仅当确有「叙事位 ≠ 故事章」的事件时,才让「叙事顺序」轴可用;否则禁用(诚实,不留死旋钮)。
// 每个事件条目恒带 story_chapter / narrative_position(store.timeline 投影,与 axis 无关),
// 故此判定在任何一次加载(含默认 story 轴)的 items 上都成立,无需先切轴探测。
export function hasNarrativeData(items) {
  if (!Array.isArray(items)) return false
  return items.some((it) => {
    if (it?.kind !== 'event') return false
    const np = it.narrative_position
    if (np == null) return false
    const sc = it.story_chapter ?? it.chapter
    return np !== sc
  })
}
