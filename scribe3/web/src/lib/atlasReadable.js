/**
 * 图谱可读面纯函数：空态、列表分组、默认章切片。
 * 不碰 React / Sigma。图谱只回答「到第 N 章，谁知道什么」。
 */
import { atlasNavType, propositionListLabel, SECRET_PLACEHOLDER } from './atlasNodeDetail.js'

/** 传入 chapter prop 时默认切到该章；无 prop 才全书（显式选）。 */
export function defaultSliceChapter(chapterProp) {
  const n = Number(chapterProp)
  return Number.isFinite(n) && n > 0 ? n : null
}

export function listNodeLabel(node) {
  if (!node) return ''
  if (node.secret) return SECRET_PLACEHOLDER
  const t = atlasNavType(node)
  if (t === 'proposition') {
    return propositionListLabel({
      id: node.id,
      peerId: node.id,
      label: node.label,
      secret: !!node.secret,
      type: 'proposition',
    })
  }
  const lab = String(node.label || '').trim()
  if (lab && !lab.startsWith('fact:')) return lab
  return node.id || ''
}

/**
 * 角色 / 命题 / 其它。命题主文案用人话，禁止 fact: 当标题。
 */
export function groupAtlasNodes(nodes) {
  const characters = []
  const propositions = []
  const others = []
  for (const n of nodes || []) {
    const t = atlasNavType(n)
    const row = { ...n, listLabel: listNodeLabel(n) }
    if (t === 'character') characters.push(row)
    else if (t === 'proposition') propositions.push(row)
    else others.push(row)
  }
  return { characters, propositions, others }
}

/**
 * 空图原因。有节点不算空。
 * kind: loading | no_chars | no_knows | no_rels | empty
 */
export function atlasEmptyKind(raw, chars = []) {
  if (!raw) return 'loading'
  const nodes = raw.nodes || []
  const edges = raw.edges || []
  if (nodes.length > 0) return null
  if (!(chars || []).length) return 'no_chars'
  const knows = edges.filter((e) => e.rel === 'knows').length
  const rels = edges.filter((e) => e.rel && e.rel !== 'knows').length
  if (!knows && !rels) return 'no_knows'
  if (!knows) return 'no_knows'
  if (!rels) return 'no_rels'
  return 'empty'
}

export function atlasEmptyCopy(kind) {
  if (kind === 'no_chars') {
    return {
      title: '还没有角色进图',
      body: '设定库里还没有可作中心的人。先立一个角色，或写一章让正文反哺。',
      hint: '打开设定',
    }
  }
  if (kind === 'no_knows') {
    return {
      title: '还没抽到知情边',
      body: '这个中心还没有「谁知道什么」。写完一章并过正文反哺后，知情命题才会进图。',
      hint: '去写一章',
    }
  }
  if (kind === 'no_rels') {
    return {
      title: '还没录入关系',
      body: '知情边有了，但角色之间还没有关系边。可在设定里补，或继续写让正文抽出。',
      hint: '打开设定',
    }
  }
  if (kind === 'empty') {
    return {
      title: '该角色暂无邻域',
      body: '当前切片里看不到邻居。换个人当中心，或把章切片改到已写过的章。',
      hint: '',
    }
  }
  if (kind === 'error') {
    return {
      title: '图谱加载失败',
      body: '再试一次。还不行就换章切片，或先打开设定看人是否还在。',
      hint: '重试',
    }
  }
  return {
    title: '加载子图…',
    body: '',
    hint: '',
  }
}
