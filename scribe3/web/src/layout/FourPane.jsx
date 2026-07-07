// 四区骨架(阶段2):上=顶栏 / 左=总纲领树 / 中=详情 / 右=主编。
// 本阶段先立骨架 + feature flag 并存旧布局,验证四区布局与分流成立;
// 真实组件(ProjectTree/ObjectFrame/ChiefDock)在阶段3逐一接入(逐类型回归,不一次改太多)。
export function FourPane({ work, sel, onSel }) {
  return (
    <div className="h-full flex flex-col bg-canvas">
      {/* 上:整个应用的操作(TopBar 阶段2后续接;此处占位) */}
      <div className="h-11 shrink-0 border-b border-line flex items-center gap-3 px-4 text-f12">
        <span className="font-bold text-brand">✍ 四区布局 v2</span>
        <span className="text-faint">顶栏(TopBar 待接) · 作品:{work}</span>
      </div>
      <div className="flex-1 min-h-0 flex">
        {/* 左:一列总纲领树 */}
        <div className="w-[220px] shrink-0 border-r border-line p-4 text-f12 text-faint bg-surface/40">
          <div className="font-semibold text-ink mb-2">左 · 总纲领树</div>
          手稿 / 设定库 / 素材库<br/><span className="text-faint/60">(阶段3 接 ProjectTree)</span>
        </div>
        {/* 中:详情 */}
        <div className="flex-1 min-w-0 p-4 text-f12 text-faint">
          <div className="font-semibold text-ink mb-2">中 · 具体信息(详情/编辑)</div>
          选中对象后经 ObjectFrame 渲染<br/><span className="text-faint/60">(阶段3 接现有详情组件)</span>
        </div>
        {/* 右:主编 */}
        <div className="w-[290px] shrink-0 border-l border-line p-4 text-f12 text-faint bg-surface/40">
          <div className="font-semibold text-ink mb-2">右 · 主编</div>
          主编对话(常驻)+ 参考/校验/存档<br/><span className="text-faint/60">(阶段3-4 接 ChiefDock)</span>
        </div>
      </div>
    </div>
  )
}
