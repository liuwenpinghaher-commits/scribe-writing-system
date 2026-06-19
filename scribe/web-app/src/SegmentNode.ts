import { Node, mergeAttributes } from "@tiptap/core";

// E:自定义 Tiptap 段落节点,携带来源(ai/human),编辑态可视化贡献来源(工程2b §3.3)。
// 行为同 paragraph,但渲染 <p data-by=...>,配合 CSS 着色(AI 淡蓝 / 人工淡绿)。
export const SegmentNode = Node.create({
  name: "segment",
  group: "block",
  content: "inline*",
  defining: true,

  addAttributes() {
    return {
      by: {
        default: "human",
        parseHTML: (el) => el.getAttribute("data-by") || "human",
        renderHTML: (attrs) => ({ "data-by": attrs.by }),
      },
    };
  },

  parseHTML() {
    return [{ tag: "p[data-by]" }];  // 仅带来源标记的段落=segment;普通 p 仍归 StarterKit
  },

  renderHTML({ HTMLAttributes }) {
    return ["p", mergeAttributes(HTMLAttributes, { class: "seg-node" }), 0];
  },
});
