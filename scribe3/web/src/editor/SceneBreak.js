import { Node, nodeInputRule, mergeAttributes } from '@tiptap/core'

// 小说场景分隔节点:`***` 或 `* * *` 或 `---` 一行 → 居中的「* * *」。
// atom 叶子节点(内部无可编辑文本);命令插入后随一个段落,避免光标卡在文末。
export const SceneBreak = Node.create({
  name: 'sceneBreak',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  parseHTML() {
    return [{ tag: 'hr[data-scene-break]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['hr', mergeAttributes(HTMLAttributes, { 'data-scene-break': '' })]
  },
  addCommands() {
    return {
      setSceneBreak: () => ({ chain }) =>
        chain().insertContent({ type: this.name }).run(),
    }
  },
  addInputRules() {
    return [nodeInputRule({ find: /^\s*(?:\*\s?\*\s?\*|---)\s*$/, type: this.type })]
  },
})
