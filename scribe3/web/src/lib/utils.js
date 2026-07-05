import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
export const cn = (...a) => twMerge(clsx(a))

// 章号输入校验:必须是 ≥1 的有限整数值(1-based 故事时间轴)。
// 后端 character_relation.since_chapter 有 `ASSERT $value >= 1`,proposition.valid_from
// 语义同样 1-based —— 前端旧守卫仅拦 `=== ''`,输入 0/负数直穿到后端触发 500(批D 审查 Minor①)。
// 空串 / null / 非数字 / <1 一律非法,统一在此判定,四处生产入口(建/演变关系·超越命题·新建命题)共用。
export const isChapterNum = (x) =>
  x !== '' && x != null && Number.isFinite(Number(x)) && Number(x) >= 1
