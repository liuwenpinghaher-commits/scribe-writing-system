import { BRAND_MARK_SVG, PRODUCT_NAME_ZH, PRODUCT_SLUG } from './brand'

/**
 * 顶栏/登录页用的铜炉 mark（透明底矢量 · 赛博霓虹）。
 * size: 像素边长；showWordmark 时右侧显示中文名。
 * layout: "inline"（默认，顶栏）| "stack"（登录页大标 + 文案纵向）
 * glow: 登录大标霓虹光晕
 */
export function BrandMark({
  size = 22,
  showWordmark = false,
  layout = 'inline',
  glow = false,
  className = '',
  wordmarkClassName = '',
}) {
  const mark = (
    <img
      src={BRAND_MARK_SVG}
      width={size}
      height={size}
      alt=""
      draggable={false}
      className="block shrink-0"
      style={{
        width: size,
        height: size,
        ...(glow
          ? {
              filter:
                'drop-shadow(0 0 10px rgba(0, 229, 255, 0.55)) drop-shadow(0 0 22px rgba(255, 45, 149, 0.35))',
            }
          : {}),
      }}
    />
  )

  if (layout === 'stack') {
    return (
      <span
        className={`inline-flex flex-col items-center gap-3 select-none ${className}`}
        data-brand={PRODUCT_SLUG}
        title={PRODUCT_NAME_ZH}
      >
        {mark}
        {showWordmark ? (
          <span className={`font-semibold tracking-tight text-brand leading-none ${wordmarkClassName || 'text-2xl'}`}>
            {PRODUCT_NAME_ZH}
          </span>
        ) : null}
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 select-none shrink-0 ${className}`}
      data-brand={PRODUCT_SLUG}
      title={PRODUCT_NAME_ZH}
    >
      {mark}
      {showWordmark ? (
        <span className={`font-semibold tracking-tight text-brand text-sm leading-none ${wordmarkClassName}`}>
          {PRODUCT_NAME_ZH}
        </span>
      ) : null}
    </span>
  )
}
