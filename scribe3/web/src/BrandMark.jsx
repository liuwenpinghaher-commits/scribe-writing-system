import { BRAND_MARK_SVG, PRODUCT_NAME_ZH, PRODUCT_SLUG } from './brand'

/**
 * 顶栏/登录页用的铜炉 mark。
 * size: 像素边长；showWordmark 时右侧显示中文名。
 */
export function BrandMark({ size = 22, showWordmark = false, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 select-none shrink-0 ${className}`}
      data-brand={PRODUCT_SLUG}
      title={PRODUCT_NAME_ZH}
    >
      <img
        src={BRAND_MARK_SVG}
        width={size}
        height={size}
        alt=""
        draggable={false}
        className="rounded-[5px] shadow-sm"
      />
      {showWordmark ? (
        <span className="font-semibold tracking-tight text-brand text-sm leading-none">
          {PRODUCT_NAME_ZH}
        </span>
      ) : null}
    </span>
  )
}
