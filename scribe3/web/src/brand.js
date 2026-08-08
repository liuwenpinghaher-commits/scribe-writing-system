/**
 * 产品品牌常量（铜炉 / tonglu）
 *
 * - 对用户可见中文名：铜炉
 * - 代码、包名、配置键、日志、API 英文语境：tonglu（拼音，全小写）
 * - 历史标识 scribe3 / SCRIBE3_* 仍可能出现在部署路径与环境变量中，见 docs/brand/README.md
 */

export const PRODUCT_NAME_ZH = '铜炉'
export const PRODUCT_SLUG = 'tonglu'
/** 英文语境短名（与 slug 一致） */
export const PRODUCT_NAME_EN = 'tonglu'
export const PRODUCT_TAGLINE = '长篇写作工作台'
export const PRODUCT_TITLE = `${PRODUCT_NAME_ZH} · ${PRODUCT_TAGLINE}`

/** 公开静态资源路径（Vite public/） */
export const BRAND_MARK_SVG = '/brand/tonglu-mark.svg'
/** 浅色圆角底版（apple-touch 等需不透明场景） */
export const BRAND_MARK_APP_SVG = '/brand/tonglu-mark-app.svg'
export const BRAND_MARK_IMG = '/brand/tonglu-mark.jpg'
export const BRAND_LOCKUP_IMG = '/brand/tonglu-lockup.jpg'
