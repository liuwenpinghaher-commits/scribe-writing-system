// 50k 验收用叙事圣经（与 craft_first 灰契线一致，扩成 18 章弧）
// 仅用于提示词模板；真实落库必须走 MCP 审批。

export const NOVEL = {
  genre: '都市悬疑 / 契约代价',
  reader_feeling: '压抑中见一线热',
  emotional_arc: '隐瞒到对质到共担代价',
  red_lines: '不美化私刑；不无代价开挂；不切换上帝全知',
  characters: [
    { name: '沈砚', appearance: '右手有茧', deep_need: '查清灰契', role: '主角/追索者' },
    { name: '老道', appearance: '灰袍', deep_need: '守炉', role: '知情者/对抗' },
    { name: '陆晚', appearance: '耳后细疤', deep_need: '还清旧账', role: '第三方视角/中盘 POV' },
  ],
  relation: '沈砚与老道：竞争兼互相利用',
  world_rule: '灰契立契后必有代价，不可无故解除；代价以血温与灰印显现',
  faction: { name: '守炉会', goal: '垄断灰契解释权', method: '口传与禁录' },
  item: { name: '灰契残页', power: '能唤起立契记忆碎片', cost: '持有者体温下降' },
  term: { name: '契血', definition: '立契时渗入纸纹的血温痕迹' },
  motif: { name: '灰契', theme: '契约代价', echoes: '灰印/契血/炉灰' },
  promises: [
    { text: '灰契会反噬立契人', setup_chapter: 1 },
    { text: '守炉会藏着第二份契底', setup_chapter: 3 },
    { text: '陆晚耳后疤与契血同源', setup_chapter: 5 },
  ],
}

/** 18 章骨架：title / brief / focalizer / plan hints */
export function chapterPlan(seq) {
  const plans = {
    1: {
      title: '夜访棺材铺',
      focalizer: '沈砚',
      brief: '沈砚夜访棺材铺逼问灰契，老道只给半句，灰印意象起',
      synopsis: '沈砚夜访棺材铺逼问灰契来历；老道只给半句；腕内侧灰印发烫；压抑中见热。',
      beats: '推门—对质—缄口',
      scene_truth: '老道知道灰契真相但出于守炉顾虑只给碎片线索；沈砚只见灰印发热与半句对白。',
    },
    2: {
      title: '契血的气味',
      focalizer: '沈砚',
      brief: '沈砚追踪契血气味进入旧巷，发现守炉会标记',
      synopsis: '沈砚循契血气味进入旧巷，发现守炉会留下的禁录标记，冲突升级。',
      beats: '追踪—发现标记—被迫撤离',
      scene_truth: '标记对沈砚可见为灰粉符号；他尚不知守炉会内部层级。',
    },
    3: {
      title: '第二份契底',
      focalizer: '沈砚',
      brief: '沈砚听说存在第二份契底，第一次埋下守炉会秘密伏笔',
      synopsis: '茶馆闲话里漏出第二份契底；沈砚决定潜入会册室。',
      beats: '听闻—验证—立誓潜入',
      scene_truth: '沈砚只得到传闻级信息；契底是否存在尚未证实。',
    },
    4: {
      title: '会册室',
      focalizer: '沈砚',
      brief: '潜入会册室失败，付出体温下降的代价',
      synopsis: '潜入失败，触碰灰契残页导致体温骤降；灰契反噬初现。',
      beats: '潜入—触物—反噬',
      scene_truth: '残页真实存在；反噬以生理代价呈现，非旁白说教。',
    },
    5: {
      title: '耳后的疤',
      focalizer: '陆晚',
      brief: '陆晚 POV：耳后疤与契血同源的暗示',
      synopsis: '陆晚视角：她耳后疤在靠近炉灰时发热，回忆碎片闪回。',
      beats: '发热—闪回—决意接触沈砚',
      scene_truth: '陆晚不知道沈砚全部动机；她只知自己的疤与炉有关。',
    },
    6: {
      title: '临时同盟',
      focalizer: '沈砚',
      brief: '沈砚与陆晚短暂结盟，交换不完整信息',
      synopsis: '两人交换半真半假信息，同盟脆弱。',
      beats: '会面—交换—猜疑',
      scene_truth: '双方各有隐瞒；读者可知双方信息差。',
    },
    7: {
      title: '炉边守夜',
      focalizer: '老道',
      brief: '老道 POV：守炉的真实理由',
      synopsis: '老道守夜，回忆为何禁止完整契底流传。',
      beats: '守夜—回忆—拒绝开门',
      scene_truth: '老道知完整规则；不向沈砚展示。',
    },
    8: {
      title: '假契',
      focalizer: '沈砚',
      brief: '出现假契干扰，沈砚差点误判',
      synopsis: '市井出现假契，沈砚差点按假线索行动。',
      beats: '发现假契—鉴别—愤怒',
      scene_truth: '假契来源不明；沈砚鉴别能力有限。',
    },
    9: {
      title: '代价清单',
      focalizer: '陆晚',
      brief: '陆晚整理已知代价清单，推进主题',
      synopsis: '陆晚列出所有可见代价，意识到同盟必须共担。',
      beats: '罗列—推演—约见',
      scene_truth: '清单只含她可见事实。',
    },
    10: {
      title: '会审',
      focalizer: '沈砚',
      brief: '守炉会对沈砚非正式会审',
      synopsis: '会审施压；沈砚拒不交残页。',
      beats: '传唤—质问—拒交',
      scene_truth: '会审目的是夺解释权。',
    },
    11: {
      title: '灰印蔓延',
      focalizer: '沈砚',
      brief: '灰印从腕蔓延至臂，身体代价加重',
      synopsis: '身体危机迫使沈砚重新评估对质时机。',
      beats: '蔓延—求医—被拒',
      scene_truth: '医不知契；只能治表。',
    },
    12: {
      title: '裂炉',
      focalizer: '老道',
      brief: '炉现裂痕，老道第一次动摇',
      synopsis: '炉裂；老道动摇是否继续隐瞒。',
      beats: '裂痕—动摇—传信',
      scene_truth: '老道仍不全盘托出。',
    },
    13: {
      title: '三方对质',
      focalizer: '沈砚',
      brief: '沈砚、老道、陆晚三方对质',
      synopsis: '对质中信息差部分闭合，新冲突开启。',
      beats: '对质—部分真相—新冲突',
      scene_truth: '每人仍有保留。',
    },
    14: {
      title: '契底现形',
      focalizer: '陆晚',
      brief: '第二份契底局部现形',
      synopsis: '契底一角现形，指向共担代价的规则。',
      beats: '现形—解读—分裂',
      scene_truth: '解读不完全正确。',
    },
    15: {
      title: '反噬高峰',
      focalizer: '沈砚',
      brief: '灰契反噬高峰，沈砚濒临失控',
      synopsis: '反噬高峰；陆晚以疤共鸣分担部分代价。',
      beats: '失控—共鸣—暂缓',
      scene_truth: '分担真实有效但有限。',
    },
    16: {
      title: '守炉会分裂',
      focalizer: '老道',
      brief: '守炉会内部分裂',
      synopsis: '强硬派要销毁契底；老道选择站队。',
      beats: '分裂—站队—护送',
      scene_truth: '老道站队有私心与公义混合。',
    },
    17: {
      title: '共担仪式',
      focalizer: '沈砚',
      brief: '三人尝试共担代价的仪式',
      synopsis: '仪式不完美成功，灰印稳定但未消失。',
      beats: '准备—仪式—余波',
      scene_truth: '无开挂；代价仍在。',
    },
    18: {
      title: '未尽的热',
      focalizer: '沈砚',
      brief: '收束：压抑中一线热，开放式但兑现主伏笔',
      synopsis: '主伏笔兑现：反噬规则被三人共同承担；新问题留白。',
      beats: '兑现—告别—一线热',
      scene_truth: '开放式结局但不烂尾主线。',
    },
  }
  if (plans[seq]) return { seq, ...plans[seq] }
  // 扩展章：在 18 以外时用模板
  return {
    seq,
    title: `续章${seq}`,
    focalizer: seq % 3 === 0 ? '陆晚' : seq % 3 === 1 ? '沈砚' : '老道',
    brief: `第${seq}章推进未解决冲突并完成有后果场景`,
    synopsis: `第${seq}章：冲突推进、代价加重、信息差部分闭合。`,
    beats: '起—承—转',
    scene_truth: `焦点人物限知；不泄露他人秘密。`,
  }
}

export function stagePrompt(seq, phase, plan) {
  const hints = {
    大纲: `synopsis 至少80字：${plan.synopsis}`,
    节拍: `beats：${plan.beats}`,
    演绎: `scene_truth≥80字：${plan.scene_truth}；involved_characters 含相关角色；每人 deductions prose 非空；focalizer=${plan.focalizer}`,
  }
  return (
    `第${seq}章当前在「${phase}」阶段，title=${plan.title}。` +
    `请用 s3_patch_chapter_plan 写入（${hints[phase]}）。` +
    '需我审批。未获批准不得声称已落库。'
  )
}

export function prosePrompt(seq, plan, minLen) {
  return [
    `请按第${seq}章已批准的大纲/节拍/演绎，写完整正文草稿提案卡。`,
    `title=${plan.title}；限知焦点=${plan.focalizer}；${plan.brief}。`,
    `净文至少${minLen}汉字；必须有具体对白、感官与选择后果。`,
    '严格限知：不得写出焦点人物不可能知道的他人秘密。',
    '承接前章已定稿事实；用动作推进；提案卡交付，不要只聊天。',
  ].join('')
}

export function repairPrompt(seq, failedDetail, minLen) {
  return (
    `第${seq}章质量审阅未通过：${failedDetail}。` +
    '请先且只用 s3_get_chapter 读取完整现稿，保留既有情节与限知，不得改成提纲。' +
    `然后用提案卡或 s3_save_chapter 提交完整修订正文，净文仍不少于${minLen}字。` +
    '需我审批；未获批准不得声称已落库。'
  )
}
