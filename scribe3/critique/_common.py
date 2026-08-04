"""Shared imports and constants for critique package."""
from __future__ import annotations

"""移植自 scribe2/critique.py 的确定性 QC 纯函数(已验证资产)。

跨段复读/排比开头/单字断句/升华句——prompt 规则治不了已生成文本,确定性扫描+定向删才拦得住。
纯函数(无 DB/无网络),作渲染层质检兜底。语义级违规(双高潮/声音崩)是另一路(LLM 判官,后续)。
"""
import bisect
import json
import logging
import re

_log = logging.getLogger("scribe3.critique")

_PUNCT_ONLY = re.compile(r"^[，。！？、；：「」『』“”‘’…—\-\d\s]+$")




















# collector/rewriter 统一切句正则(含省略号 …,与 find_duplicate_lines 口径一致,修 review P2-3)
_INTRA_SENT_SPLIT = re.compile(r"(?<=[。！？…\n])")
_AUTO_REWRITE_AI_TIC_KINDS = {"em_dash", "not_a_but_b", "toxic_pattern", "banned_word"}














_EDGE = re.compile(r'^[\s"\'“”‘’「」『』,，、:：;；…—]+|[\s"\'“”‘’「」『』,，、:：;；…—]+$')
_HAS_CJK = re.compile(r'[一-鿿]')




LUANSHI_PURPLE_SEEDS = [
    r"原来[^。！？\n]{0,30}(就|早就|从一开始|没的选|没得选)",
    r"从[^,，。\n]{1,18}那一刻起",
    r"像[^。！？\n]{0,12}[滴颗][^。！？\n]{0,8}眼泪",
    r"影子[被]?拉得很[长短]",
    r"(有些|有的)[^。！？\n,，]{0,14}(就再也|再也)[^。！？\n]{0,14}",
    r"他知道[，,][^。！？\n]{0,4}(回不去|没的选|不一样了)",
    r"走下去|刀山火海",
]

_PURPLE_PATS = LUANSHI_PURPLE_SEEDS
_PURPLE_RE = [re.compile(p) for p in _PURPLE_PATS]




# 通用 AI 腔硬检(E1/E2,题材无关,来自 hermes-novel hard-checks)
# E2「不是A——是B」结构性扫描,移植自 oh-story check-ai-patterns.js 的
# findNotIsComparisons/findPositiveFlipEnd——原正则 `不是.{1,15}——是` 只认破折号一种变体,
# 真实文本里"不是A而是B/不是A，是B/不是A。是B/不是A是B"同样是伪深刻制造器,须结构性扫。
_STOP_CHARS = set("。！？!?\n")
_SOFT_SEPARATORS = set("，,、；;：:")
_HARD_SEPARATORS = set("。.！!？?")
# 阈值 craft.max_negative_span / craft.max_positive_span 已接设置中心热生效(见 _th 调用点)
# either-or「不是A就是B/也是B」里紧贴的"是"是连词的一部分,不是肯定项系动词;
# 也借此排掉「不是A,也不是B」这种第二个否定段(prev 为"也"时不算翻转)。
_COMPACT_EITHER_OR_PREV = set("不就也")
# 句尾语气/反问助词:"…,是吗/是吧/是嘛"是反问尾巴,不是否定后的肯定翻转。
_TAG_PARTICLES = set("吗吧嘛")
_TRAILING_NOISE = re.compile(r"[\s|\)）】\]]+$")

_WIKI_FLIPS = [
    ("bujin", re.compile(r"不仅[^。！？\n]{1,40}?(?:而且|还)[^。！？\n]{1,40}")),
    ("erfei", re.compile(r"[^。！？\n，,]{1,20}，?而非[^。！？\n]{1,20}")),
    ("yuqishuo", re.compile(r"与其说[^。！？\n]{1,40}?不如说[^。！？\n]{1,40}")),
]










# ==== 方案A任务3:禁用词分级建表(来自 oh-story banned-words.md,已按归位纪律清洗)====
# 归位纪律:①比喻词(仿佛/如同/宛如/好似/犹如)不进表——已在 _SIMILE_WORDS,find_oversaturation 管;
# ②缓缓/微微/轻轻/淡淡 四个副词不进一级词表——它们走后续任务的密度检测,单次出现合法;
# ③不由得/不禁 保留进表(判断/心理类里的"轻度AI腔"信号)。
_BANNED_LEXICON: dict[str, tuple[str, ...]] = {
    "情态类": ("一丝", "一抹", "些许", "几分", "隐约"),
    "动作类": ("深吸一口气", "不禁"),
    "表情类": ("眼中闪过", "嘴角勾起", "眉头微皱", "眉眼低垂", "瞳孔微缩"),
    "心理类": ("心中一动", "心头一震", "心下了然", "心中暗道", "心底泛起", "不由得"),
    "判断类": ("不容置疑", "不容置喙", "不易察觉", "显而易见", "毫无疑问", "不可否认"),
    "形容类": ("闪烁着光芒", "狡黠", "深邃", "凛冽"),
    "过渡类": ("不由自主", "情不自禁", "自然而然"),
}
_CONTEXTUAL_WORDS = ("突然", "好像", "瞬间")   # 二级:仅密度超阈才报
_TOXIC_PATTERNS = [   # oh-story ★★★★/★★★ 毒句式(★★★★★否定翻转已由 find_negation_flips 承担)
    ("wandai", re.compile(r"[，,]带着(?:一种|一丝|几分)?[^，,。！？\n]{2,20}的[^，,。！？\n]{0,6}(?:力量|气息|意味)")),
    ("shengyin_buda", re.compile(r"声音不大[，,]却")),
    ("yanzhong_shanguo", re.compile(r"眼中闪过一丝[^，,。！？\n]{1,8}")),
    ("zuijiao_gouqi", re.compile(r"嘴角勾起一抹[^，,。！？\n]{1,8}")),
    ("xinzhong_yongqi", re.compile(r"心中涌起一股[^，,。！？\n]{1,8}")),
]

# ---- find_ai_tics 分级阈值:已接设置中心热生效(craft.banned_density_per_k /
# craft.banned_min_sents / craft.contextual_per_k / craft.contextual_min_hits /
# craft.wandai_block_hits,见函数体首行 _th() 取值,下方文档串沿用旧常量名描述语义)----

# banned_word 句子簇计数的句切分符(与协调审查口径一致:[。！？\n])
_AI_TIC_SENT_DELIM = re.compile(r"[。！？\n]")










# 过度解释/过度饱和(留白引擎的确定性兜底;保守阈值,宁可漏不滥杀)
_EXPLAIN = ["这意味着", "也就是说", "换句话说", "正是因为", "说明了", "其实是", "无非是", "不过是", "正因如此"]
_EMO_LABEL = ["愤怒", "悲伤", "恐惧", "绝望", "痛苦", "欣喜", "喜悦", "忧伤", "焦虑", "孤独", "兴奋", "悲痛"]
_SIMILE_WORDS = ["仿佛", "如同", "宛如", "好似", "犹如"]            # 明确比喻词
_SIMILE_LIKE = re.compile(r"像[^,，。！？\n]{1,10}(一样|般|似的|似地)")  # "像…一样"精确模式,避开"好像/图像"




# ==== 方案A任务7:副词密度 + 句内三段式 + 同义词循环三检测器 ====
# 归位纪律(承接 A3 _BANNED_LEXICON 注释②):微微/淡淡/缓缓/轻轻 四个副词【不进】禁用词表
# ——单次出现是正常修辞,只有密度异常才是 AI 腔信号,故单独走密度检测,report-only。
_ADVERB_WORDS = ("微微", "淡淡", "缓缓", "轻轻")   # oh-story anti-ai-writing 模式2




# 句内顿号三连(维基 rule of three):恰好三项 X、Y、Z(每项 1-6 字)。
# 实现是"先全局切分再判长度",不是局部正则近似——负向环视 (?<!、) 只能保证起点前
# 一字不是顿号,不能保证起点对齐分项边界(多字词场景被击穿:「院里安静、破败、荒凉、
# 死寂。」曾从"破败"第二个字起匹配出「败、荒凉、死寂」,把半个词冒充分项,使四项
# 列举被误报,污染密度门)。全局切分:句读([。！？\n])切句,句内再按逗号/分号切段
# (顿号列表止于逗号,「他带上刀、粮、水，然后出发」逗号前是完整候选序列),每段
# 完整 split("、") 后 len(items)==3 且每项 1-6 字才命中——≥4 项、2 项、超长项都
# 整体不报,不存在"从列表中间截出伪三连"的起点。
_RULE_OF_THREE_SEG_RE = re.compile(r"[^。！？\n，,；;]+")   # 句读+逗号/分号界定的候选段
# 阈值 craft.rule_of_three_item_max 已接设置中心热生效(见 find_rule_of_three 首行 _th 调用)




# rule_of_three 报告门:单句偶尔三连打比方是正常修辞,只有千字密度超阈才谈得上
# "句内三段式滥用"这一 AI 腔信号——故聚合层(quality_flags/quality_issues)只有
# 密度 >craft.rule_of_three_gate_per_k 才整体上报,否则该章不计入(见 _rule_of_three_gated)。




# 同义词循环/精致变异(维基 elegant variation):角色被点名后,后文频繁改用"那男人/
# 少年"等泛称替换指代,过犹不及的"避免重复"手法。泛称表刻意只收 2 字以上的确定性
# 词——不收单字词或过泛词如"男人/女人"(会子串误报,如"那男人"里已含"男人")。
_GENERIC_REFS = ("那男人", "那女人", "少年", "青年", "老者", "主人公", "主角")




# ==== 方案B任务21:水字数确定性信号(rules/story-consistency.md:28 的确定性子集)====
# oh-story 原文列了 5 条水字数信号,其中"全章对话无新信息"/"连续2章无冲突"需要通读
# 语义才能判(无法靠规则/计数确定),不在此实现——已作为附加判据挂进
# build_reasoning_audit_prompt 的"水字数征兆"节,交给 LLM 一并审议。本函数只做可用
# 正则/计数判定的两条确定性子集,全 advisory(report-only,不阻断)。
_FILLER_ACTION_WORDS = ("走", "跑", "抓", "推", "打", "拔", "扑", "跳", "转身", "抬手", "挥")








# ==== 护栏可操作性:问题定位到句(F-05) ====





# 结构重复的句切分:与 find_structural_repeats 同口径([。！？\n]+ 分句 + 去标点边缘),
# 但额外记录每句在原文里的 [start,end)(用 finditer 在原文上扫,边缘去空白后再夹回)。
_SENT_SPLIT = re.compile(r"[。！？\n]+")








# ==== 方案B任务18:反谄媚对抗注入 + 统一 Findings Schema ====
# 背景(oh-story story-review/SKILL.md):LLM 评审默认倾向"找亮点、给通过"(谄媚/盖章通过),
# 确定性纠偏是在每个 reviewer prompt 里硬写"你的任务是找问题,不是验证正确性"——
# 用最严苛的标准审视,宁可误报不可漏报。仅对"评审性"prompt(discipline 纪律判官/
# tension 张力评审)注入;build_knowledge_extract_prompt/build_voice_fold_prompt 是
# 抽取/折叠而非评审,不注入(它们的任务本就是"如实抽取",不存在"验证正确性"的谄媚风险)。
ANTI_SYCOPHANCY = "你的任务是找问题,不是验证正确性;以最严苛的标准审视,宁可误报不可漏报。"

# 统一 Findings Schema:后续 reviewer 编排(方案B任务19/21 与 loop 化)公用契约。
# severity 从重到轻 S1(阻断)→S4(建议);category 覆盖九类问题域。
# 现有 parse_discipline/parse_tension_report 的输出**不强改**(向后兼容,各自 caller
# 仍按老字段消费);新消费方(未来的多 reviewer 编排层)用 normalize_findings 清洗
# 各 reviewer 的原始输出,统一成可机器合并排序的一张表。
FINDING_SEVERITIES = ("S1", "S2", "S3", "S4")
FINDING_CATEGORIES = (
    "structure", "character", "prose", "consistency", "platform",
    "factual", "format", "causal", "rule_boundary",
)




_VERDICT_RANK = {"REJECT": 2, "CONCERNS": 1, "APPROVE": 0}






# ==== 方案B任务20:finding-merge 纪律 + degradation→重新生成 ====
# 背景(oh-story story-review/SKILL.md:151/:153):
# ①合并多检测器 finding 时要去重归口——同一位置若同时存在"机械替换"(如标点归一
#   punct_suggestions)与"按功能改写"(如 ai_tics/god_view 等 issue)两条建议,两者冲突,
#   丢弃机械替换那条,只留按功能改写的 issue(机械替换不理解上下文,盲改易破坏语义,
#   按功能改写的判断优先级更高)。
# ②degradation 类(find_degeneration 产出的 type=="degeneration" issue)要精确绑定
#   "重新生成该段"而不是"改写"——对齐 scribe3 已验证的 continue-steer 回炉机制(模型退化
#   是生成过程本身失控,局部改写治标不治本,必须整段回炉重打)。
# 这里的 fix_action(regenerate/rewrite)是 loop 化回炉编排的 severity/action 分流依据
# 之一,与设计文档「blocking→regenerate / advisory→rewrite」的两态合流一致。


# ==== LLM 语义判官(纪律闸)——确定性检测的盲区:双高潮/声音崩/解说倾泻/知识泄露 ====

# Minor(收尾清理批):默认纪律文案单一来源——app.py /post-check 拼继承开放项时
# 也要引用同一段文案(此前是手写字面量副本,有漂移风险)。
DEFAULT_DISCIPLINE_BRIEF = (
    "(默认:乱世铜炉式克制——单一戏剧主线、不偷跑后续章剧情、terse 角色不大段独白、不解说倾泻)")




DISCIPLINE_KINDS = ("double_climax", "voice_collapse", "exposition_dump",
                    "knowledge_leak", "god_view")








# ==== 声音演变折叠(fold_voice_flags:LLM 把开放 flag 折进 voice_profile)====





# ==== 知识账本抽取(定稿时抽"本章谁新知道什么/做了什么",喂单一真相源)====




# ==== M2a: 叙事张力盲评 rubric(对成文单章,LLM 单次合并评审)====





# ==== 方案B任务13b:反转工具箱 rubric + 悬念/伏笔边界
#      (oh-story reversal-toolkit.md 7类反转 + hooks-suspense.md 悬念vs伏笔边界)====

_REVERSAL_TYPES = ("身份反转", "动机反转", "因果反转", "立场反转",
                    "信息差反转", "时间线反转", "道德反转")






# ==== 方案B任务17:平台留存轴 + S1-S4 裁决(oh-story story-review/references/
#      rubrics/{qidian,fanqie,zhihu}.md 提炼,真实文件已核实存在——非按要点臆造)====
# 背景(主篇3.4):build_tension_rubric_prompt 只有内在戏剧轴,返布尔无严重度无裁决;
# 本节补平台留存轴,输出与 build_reversal_rubric_prompt 同一套统一 FindingsSchema
# (六字段 + severity S1-S4 + category="platform" + verdict,方案B任务18 已备)。
#
# 严肃向定位:平台轴【可选】——只有调用方显式传 platform 才启用本函数;不传 platform
# 时写作/评审主链路完全不受影响。app 端点接线不在本任务(app.py 被 B24 占用):
# TODO(接线,后续任务) 按 work.target_platform 非空才调 build_platform_rubric_prompt,
# 目标端点可挂在 /post-check 之后或独立 /platform-check,当前 critique/brief 层已就绪。
#
# 每平台三块:name(展示名)+ word_range(章字数区间,供 prompt 提示 & platform_deterministic
# 复用)+ deterministic(可用正则/计数判定的口径,列在 prompt 里给 LLM 对齐平台惯例参考,
# 真正的确定性判定见 brief.platform_deterministic)+ llm_axes(需要通读语义才能判的轴,
# 交给 LLM 逐项裁决)。
_PLATFORM_RUBRICS: dict[str, dict] = {
    # 取舍说明(B17 审查):源表 qidian.md 另有「日更支持」词条(大纲支持 4000
    # 字/天节奏),本函数是单章评审 prompt,不适用于跨章日更节奏判定,故此处
    # 有意不纳入——非遗漏。「黄金三章」不在源 qidian.md 表内,已删除,不再固化。
    "qidian": {
        "name": "起点中文网",
        "word_range": (2000, 4000),
        "deterministic": [
            "爽点密度:每 3000 字 ≥1 情绪节点(升级/打脸/获宝),连续 5000 字无情绪节点则 FAIL",
            "钩子密度:每章结尾须有悬念/钩子,连续 3 章结尾无钩子则 FAIL",
        ],
        "llm_axes": [
            "升级节奏:每 50 章应有等级/实力突破,100 章无任何升级为 FAIL",
            "金手指使用:每章提及或使用金手指(系统/戒指/功法),连续 5 章未提及为 FAIL",
            "角色存在感:主角每章须出场并推进,连续 2 章不出场或无推进为 FAIL",
            "追读比预估:章尾钩子+情绪连续性→预估追读比走高;连续 3 章无钩子或情绪断裂则预估走低",
        ],
    },
    "fanqie": {
        "name": "番茄小说",
        "word_range": (1500, 2500),
        "deterministic": [
            "开头吸引力:前 3 段须含冲突/悬念/钩子,纯描写/背景介绍则 FAIL",
            "情绪节点:每 1000 字须有情绪起伏,连续 2000 字情绪平直则 FAIL",
        ],
        "llm_axes": [
            "读者留存:每章结尾须有翻页动力(悬念/反转/新信息),连续 3 章无翻页动力为 FAIL",
            "题材匹配:内容须符合标签类型(如甜宠/逆袭/重生),偏离标签类型超过 3 章为 FAIL",
            "算法友好:短段落、快节奏、高信息密度,大段落/慢节奏/低信息密度为 FAIL",
            "完读率预估:3 章 Hook 有效+节奏不拖→预估完读率走高;前 3 章无 Hook 或连续拖沓则预估走低",
        ],
    },
    "zhihu": {
        "name": "知乎盐言故事",
        "word_range": (8000, 13000),
        "deterministic": [
            "字数控制:8000-13000 字(盐言标准),超出或不足为 FAIL",
            "开头钩子:第一句须含信息量(动作/冲突/悬念),纯描写/背景为 FAIL",
            "格式合规:段落以短为主(有长短/疏密变化)、无空行、对话格式正确,通篇同长度"
            "或连续超长段落/空行/对话标签则 FAIL(逐章可检查)",
        ],
        "llm_axes": [
            "第一人称:全文须用「我」视角(除非多视角设计),否则 FAIL",
            "情绪拉扯:每段须有情绪变化(期待→失望→惊喜等),连续 3 段情绪无变化为 FAIL",
            "反转设计:至少 1 个有效反转(前文有伏笔支撑),无反转或反转无伏笔支撑为 FAIL",
            "结尾余韵:结尾须留有思考空间/情感余韵,完全封闭无回味为 FAIL",
            "完读率/开头跳失率预估:第一句含动作/冲突/悬念→跳失率预估走低、完读率预估走高;"
            "第一句纯描写/背景则跳失率预估走高、完读率预估走低",
        ],
    },
}






# ==== 方案B任务21:5 类推理一致性审计(oh-story consistency-checker.md 第三步
#      "推理型一致性审查")====
# 分工声明:本节与"事实对账"(概念上指具体实体事实——人名/数字/地点等可直接 grep
# 核对的硬事实——是否前后一致)彻底分离:事实对账比的是"具体值对不对",本节审的是
# "规则/因果/代价"这类需要推理才能发现的矛盾——每条前提孤立看都成立,组合起来才
# 暴露矛盾,无法靠字面 grep 揪出,必须交给 LLM 顺着证据链推理。




# ==== M2: 确定性文本质检——整行精确复读 + 叙述层情感直说 ====

# 句子切分:按换行符 + 中文句末标点(。！？…)拆句(带 capture group 保留分隔符)
_SENT_DELIM_CAP = re.compile(r"([。！？…]+)")

# 对话包裹检测:中文弯引号 “”("") 和直角引号 「」(「」)
# 用 Unicode 码点写死避免编辑器保存时字符变形
_DIALOGUE_RE = re.compile(
    r"[“「][^”」]{0,200}[”」]", re.S
)

# 情绪直说正则:叙述层主语 + 情绪动词/词语 + 具体情绪词
_EMOTION_WORD_RE = re.compile(
    r"(?:他|她|它)?(?:感到|觉得|心里|心中|心头)(?:一阵|一)?"
    r"(?:害怕|恐惧|惧|难过|悲伤|愧疚|不忍|心疼|疼痛|高兴|欢喜|愤怒|绝望|紧张|安心|悲痛|痛苦|焦虑|孤独|兴奋|恐慌)"
)

# 直接评语正则:对人物下定性评语
_VERDICT_RE = re.compile(
    r"(?:他|她)(?:其实)?(?:不是|是)(?:个)?(?:坏人|好人|善人|恶人|好角色|坏角色)"
)

# 标签化生理-情感套语(weak 命中,kind=cliche)
_CLICHE_RE = re.compile(
    r"心里像被(?:什么)?(?:揪|攥|堵|压|刺|扎|灼|撕)(?:住|着|了|痛)?"
)

# 方案B任务13:情绪表达4级(oh-story style-craft.md:直写<思想<神态<动作,表达质量阶梯)
# L2 思想转述——用叙述层动词直接转述人物内心念头(而非具体情绪词),同属 telling。
_THOUGHT_REPORT_RE = re.compile(r"(?:心中暗道|心想|心道|暗想|暗忖)")




# 7 对引号(对齐 oh-story stripQuoted):台词/弹幕复沓是体裁常态,复读/排比/结构检测只判叙述层。
# 与 _DIALOGUE_RE(仅“”「」两对,供 find_emotion_telling 用)分开维护——语义不同、互不影响。
_QUOTED_SPANS = [re.compile(p, re.S) for p in (
    r"「[^」]*」", r"『[^』]*』", r"【[^】]*】",
    r"“[^”]*”", r"‘[^’]*’", r'"[^"]*"', r"'[^']*'",
)]






# ==== 方案A任务4:上帝视角/解释腔检测器(find_god_view)====
# 纯静态语言指纹,与 verify.py 的 find_leaks(知识帧 fact-leak 检测,判"角色说出其视角
# 不可能知道的信息")分工不同——那里查的是知识账本语义,这里只查字面句式。
# 归位纪律:①"这意味着/正是因为"已在 _EXPLAIN(find_oversaturation 管),此处只收
# "之所以…是因为";②"原来…"已被 LUANSHI_PURPLE_SEEDS[0] 部分覆盖,此处不再收。
_GOD_VIEW_PATTERNS = [   # oh-story anti-ai-writing 模式8 + 总结/升华句式,纯语言层
    ("god_spoiler", re.compile(r"(她|他)不知道的是|殊不知|多年以后|冥冥之中|仿佛预示着")),
    ("explain_causality", re.compile(r"之所以[^。！？\n]{1,30}(?:，)?是因为")),
    ("summarize", re.compile(r"(?:他|她)(?:终于明白|这才意识到|这才明白)|此刻[，,](?:他|她)")),
    # sublimation 只锚"行首(容忍全角/半角/Tab 缩进)开头的整句"——刻意收窄防误伤:
    # 句中出现"这一刻/这就是"(如"爱情在这一刻绽放")是合法叙述,不报;
    # 段首起句的"这一刻，…。/这就是…。"才是升华式盖棺陈词(宁可漏不滥杀)。
    ("sublimation", re.compile(r"^[ 　\t]*(?:这一刻|这就是)[^。！？\n]{2,30}[。！？]", re.M)),
]








_ONOMAT_LINE = re.compile(r"^[咔笃啪嗒砰咚哗叮当吱嘎咯吧噗嘀嗡][——\-—.。…、，！]*$")






_WATCH_MAP = {"一更": 1, "二更": 2, "两更": 2, "三更": 3, "四更": 4, "五更": 5}








# ==== 方案A任务5:模型退化检测(find_degeneration,移植自 oh-story
# skills/story-deslop/scripts/check-degeneration.js)====
# 弱模型/长程生成典型退化指纹,模型自己发现不了,靠确定性扫描+定向重写才拦得住:
#   - 复读/打转(verbatim repetition):长句反复出现,或紧邻整行一字不差重复;
#   - 占位/拒绝语泄漏:作为AI/我无法继续/此处省略/乱码/英文 AI 腔;
#   - 工程词泄漏:细纲/情节点/本章/下一章 等写作流水线术语漏进正文;
#   - 中途截断:正文末尾未以句末/收尾标点结束。
# report-only,不改文本;kind 与阈值常量均与 JS 源逐字对照。

# 复读阈值(逐字移植 JS 源):长句(可见字数≥REPEAT_MIN_LEN)出现≥REPEAT_MIN_COUNT 次判
# 为打转(sentence_loop);紧邻整行重复(可见字数≥ADJACENT_MIN_LEN)判为即时循环
# (adjacent_repeat)。短句/弹幕/对话刷屏豁免——通俗网文的排比/复沓/弹幕是体裁正常手法。
REPEAT_MIN_LEN = 12
REPEAT_MIN_COUNT = 3
ADJACENT_MIN_LEN = 8

# 可见字符集(逐字移植 JS visibleLength):中文 + 全角字母数字 + 半角字母数字。
_DEGEN_VISIBLE_RE = re.compile(r"[一-鿿Ａ-ｚA-Za-z0-9]")




# 占位/拒绝语泄漏:hard=任何行都判(正文里永不合法);soft=仅"非对话叙述行"判(角色台词
# 里可能合法,如"对不起,我无法答应你"是正常对话)。对话行判定:该行剥引号后剩余可见
# 字符数 <2(近乎整行都是台词/物件名,叙述几乎为零)。均为 blocking(与 JS 一致:
# findPlaceholders 无论 hard/soft,命中一律 severity='blocking')。
_DEGEN_PLACEHOLDER_PATTERNS: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(
        r'作为(一个)?(AI|人工智能|大?语言模型|智能助手|聊天助手)'
        r'(?=[，,。、；;：:！!？?\s）)」』"】]|我|无法|不能|没法|$)'
    ), "refusal", False),
    (re.compile(r"�"), "mojibake", True),
    (re.compile(r"^(Sure|Certainly|Here'?s|As an AI|I (?:cannot|can't|am unable|apologize))"),
     "english_ai", True),
    (re.compile(r"[（(](此处|以下|这里|下文|后续)?\s*(省略|略)(去|过)?[^）)]{0,10}[）)]"),
     "placeholder", True),
    (re.compile(r"(未完待续|TODO|占位符|placeholder)"), "placeholder", True),
    (re.compile(
        r"我(无法|不能)(继续(写|创作|生成|下去)|生成(内容|文本|正文)?|创作|续写|完成(这个|本)?(章|篇|创作|请求))"
    ), "refusal", False),
]

# 工程词泄漏(逐字移植):tier1=纯写作流水线术语,正文里几乎永不合法;tier2=章节结构/
# 歧义词,角色在故事内真实阅读/讨论"第X章"、或故事内系统/界面用语时属例外,恒 advisory
# 交人/LLM 判。tier1 命中若落在对话行(引号内)降级 advisory——写手/编剧题材角色可能
# 真讨论创作;tier2 恒 advisory。
_DEGEN_META_TIER1_RE = re.compile(r"细纲|情节点|卷纲|功能标签|目标情绪|字数目标|章首钩子|章尾钩子")
_DEGEN_META_TIER2_RE = re.compile(
    r"第[一二三四五六七八九十百千万两0-9]+章|本章|这一章|上一章|下一章|上章|下章|前一章|后一章|前文|后文|伏笔|读者|任务描述"
)
# 标题行(如"第一章 桥下")属"正文标题行"而非泄漏,排除对首个内容行的误判(移植自 JS
# findMetaLeak 里的首行标题豁免逻辑,check-degeneration.js:278-282)。
_DEGEN_TITLE_RE = re.compile(r"^第[一二三四五六七八九十百千万两0-9]+章")

# 截断判定:全文最后一个非空行须以句末/收尾标点结束,否则疑似中途被切断(advisory——
# 与 JS 的 blocking 不同,此处按方案A任务5要求降级,交人/LLM 判)。
_DEGEN_TRUNCATED_END_RE = re.compile(r'[。！？…”」』"]$')


















# ==== 方案A任务6:句长方差/burstiness 检测器(find_rhythm_uniformity)====
# GPTZero/DetectGPT/Binoculars 公认头号 AI 破绽:句长分布异常均匀("节拍器")——
# 人类文本天然 bursty(长短句剧烈交替),LLM 默认输出句长收敛。确定性量化,report-only。
#
# 阈值已用 tools/calibrate_rhythm.py 真机标定回填(2026-07-04):经 REST 拉取本机三本已
# 存在库、已人工/流程验收过质量的作品(book_bfd18b78「铜炉试炼·三轮验证」5章、
# book_c256380e「纸命」双POV 4章、main「乱世铜炉·设定参照」18章)共 27 章正文,
# 逐章跑检测器取 CV / mean_adj_ratio 分位数:
#   CV             P10=0.517  P50=0.591  P90=0.776
#   mean_adj_ratio P10=0.550  P50=0.616  P90=0.754
# 取 P10(约 10% 已验收章节比该值更"均匀")作为新地板值——用回填后阈值复核这 27 章,
# 2/27(book_bfd18b78 第1章、main 第18章)恰好落在 P10 边界以下被判 uniform,
# 与"P10=约一成样本比该值更均匀"的定义相符,非阈值算错;report-only/advisory 性质,
# 该假阳性率可接受。样本仅 27 章,后续语料增长应重跑脚本复核阈值。
_RHYTHM_MIN_SENTS = 20     # 句数下限:样本太少 CV 波动大,不判(避免短章误报)
_RHYTHM_CV_FLOOR = 0.517   # 变异系数(sigma/mean)低于此值视为"过于均匀"
_RHYTHM_ADJ_FLOOR = 0.550  # 相邻句长差绝对值均值 / 句长均值,低于此值视为"缺乏突变"




# ==== 方案A任务8:整章 AI 味定档聚合(aggregate_ai_grade)+ 7-Gate 骨架 ====
# 把 quality_flags 的分项确定性命中,聚合成"可决策的章级结论"——写作闭环回炉触发依据。
# report-only,不改文本。指标口径与 7-Gate 映射均来自 oh-story story-deslop SKILL.md
# 附录§H.2。
#
# 三档阈值真机标定(2026-07-04,真机冒烟修复配套):用 tools/calibrate_ai_grade.py
# 拉取 :3321 当时在库的全部 4 个 work / 27 章正文(book_5ce0a5c4 无正文跳过,实取
# book_bfd18b78×5 + book_c256380e×4 + main×18 = 27 章)跑 P50/P90/P99 分位:
#   banned_density        P50=0.40 P90=0.60 P99=2.23 max=2.29
#   parallel_run(修复后)  P50=0.00 P90=4.00 P99=4.00 max=4.00
#   psych_ratio           P50=0.00 P90=0.00 P99=0.69 max=0.93
#   dialogue_tag_density  P50=0.00 P90=0.22 P99=0.86 max=1.02
#   repeat_density        P50=0.00 P90=1.35 P99=1.88 max=1.92
# ①banned_density/③psych_ratio/④dialogue_tag_density 三项真机分布远低于原有临时
# 阈值(P99 均未触及原 medium 上界),维持原值不变——原临时值本就够宽松,标定
# 只是确认,不是巧合(main ch5/ch12 各自密集复读"一丝/隐约""突然"4 次,banned_density
# 落在 medium 属真实命中,不是误判,对应下方"6 个达标章大多 light、最多个别
# medium"验收里被允许的"个别 medium")。
# ②parallel_run 与⑥repeat_density 两项按 P90 上侧回填,是本次真机冒烟修复的
# 主体——27 章样本里既有完整叙事章也有短篇设定/存根章(全零指标拉低分位),
# 单纯照抄全库 P99/P90 数值会让样本里最长、最"像小说"的达标章(纸命 ch1-4,
# 6774~8965 字)因为文本更长、天然多出几处不打眼的短语复现/惯用连排,反而卡在
# 分位线上——不是它们有问题,是全库分位数被大量存根章拉低。故在 P90 数值基础上
# 留足余量,以"6 个已人工验收章节(纸命 ch1-4、main ch5/ch12)大多 light、最多
# 个别 medium"为验收标准复核过:
#   _AI_GRADE_PARALLEL_LIGHT/_MEDIUM 3,5→5,7:parallel_run 语义修复后(见下方
#     ②parallel_run 计算处注释)真机连排最大值稳定在 3~4(P90=P99=max=4),原
#     light<3 门槛比 find_parallelism 自身 min_run=3 的探测下限还低,等于"只要
#     测到任何排比就至少 medium"——把 4/6 达标章卡在 medium。新阈值 light<5 让
#     真机全部已知连排值(0/3/4)落 light,medium(5~7)/heavy(>7)留给真正超出
#     已验收样本上限的排比堆砌(反向验证见 tests/test_critique.py 的
#     TestAiGrade::test_heavy_reverse_smoke,8 连排比判 heavy)。
#   _AI_GRADE_REPEAT_LIGHT/_MEDIUM 1.0,2.0→2.0,3.0:达标章千字复读密度实测
#     1.09~1.92,原 medium 下界 1.0 太严,4/6 达标章因此常年卡 medium;新
#     light<2.0 覆盖真机全部已知值(max=1.92),medium(2.0~3.0)/heavy(>3.0)
#     留给真正密集复读的文本。
_AI_GRADE_BANNED_LIGHT, _AI_GRADE_BANNED_MEDIUM = 1.0, 3.0        # ①千字禁用词密度
_AI_GRADE_PARALLEL_LIGHT, _AI_GRADE_PARALLEL_MEDIUM = 5, 7        # ②排比/结构复读最大连排数
_AI_GRADE_PSYCH_LIGHT, _AI_GRADE_PSYCH_MEDIUM = 2.0, 5.0          # ③情感直说占句子数百分比
_AI_GRADE_DIALOGUE_LIGHT, _AI_GRADE_DIALOGUE_MEDIUM = 2.0, 4.0    # ④千字对话腔标记密度
_AI_GRADE_REPEAT_LIGHT, _AI_GRADE_REPEAT_MEDIUM = 2.0, 3.0        # ⑥千字复读密度
_AI_GRADE_HEAVY_GATE_COUNT = 4    # oh-story"4+ Gate 有问题=重度",命中≥此数强制 heavy

_GRADE_ORDER = {"light": 0, "medium": 1, "heavy": 2}

# 对话腔调标记:引号收尾紧跟极短"XX说/XX道"型提示语(如「……」他说。/「……」淡淡道,)
_AI_GRADE_DIALOGUE_TAG_RE = re.compile(r"[”」]\s*[^\n。！？]{0,6}(说|道)[。，]")






# ==== 方案A任务9(计划A最后一项):标点归一建议生成器(report-only)====
# 移植自 oh-story story-deslop/scripts/normalize-punctuation.js 的
# choosePauseReplacement 上下文判定——但那是全仓唯一会 fs.writeFileSync 落盘改写
# 正文的脚本;scribe3 守 report-only 纪律,这里只出"建议"清单,不动原文一个字符。
#
# 范围刻意收窄到 JS 里"会真正改写成中文标点"的三种确定性情形:
#   ① numeric_range: 数字/汉字数字区间 X——Y(或 X—Y / X--Y)→ 建议"到";
#   ② ellipsis:      句中 ……/ASCII ...(非数字区间)→ 建议"。"或"，"(上下文判定,见下);
#   ③ double_hyphen:  半角双连字符 --(非数字区间)→ 建议"——"或删除(句首/引号后)。
#   ④ 【未移植】JS 原版的冒号分支(前瞻后文出现"因为/原来/答案"等词 → 建议"："):
#     那是改写器语义(替标点重排句子的语气),前瞻词表在中文叙述里误报面大
#     ("因为"作普通连词满地都是),scribe3 守 report-only 纪律宁可漏不滥报,刻意不做。
# 单独出现、不落入以上三类的 ——/—(如纯粹的插入语破折号)刻意不报——那是
# find_ai_tics 的 em_dash 密度门(见 quality_flags["ai_tics"] 里 "kind":"em_dash")
# 已经覆盖的信号,本函数重复上报只会制造噪声;两者可能同位置命中的去重合并
# 留给计划B任务20(finding-merge)按 "kind"+"range" 做,故此处每条建议都带 kind。
_PUNCT_PAUSE_RE = re.compile(r"…+|\.{3,}|——|—|--+")
# 数字区间的"数字"按 oh-story 原意扩展到汉字数字(JS 原版只认 ASCII \d,三——五
# 这种汉字数字区间在中文小说里更常见,故此处一并收纳,不是 JS 的字面直译)。
_PUNCT_DIGIT_RE = re.compile(r"[0-9〇一二三四五六七八九十百千万]")
_PUNCT_OPENING_DELIM_RE = re.compile(r"[「『（(“‘]")
_PUNCT_CLOSING_QUOTE_RE = re.compile(r"[”」』]")
_PUNCT_SENTENCE_END_RE = re.compile(r"[，,。.!！?？;；:：…]")








# ===== 时间线检测器第一刀(遗留处置批次三,ConStory 对照:Timeline 6 子类原仅 2 窄点)=====
# report-only:产出只走 advisory 通道,永不进 blocking(宪法:停机判据只挂确定性项,
# 时间语义歧义多——回忆/对话/闪回都合法,第一刀宁窄勿滥)。

_SEASON_FAMILIES = {
    "春": ("初春", "早春", "暮春", "开春", "入春", "春日", "春夜", "阳春"),
    "夏": ("盛夏", "仲夏", "初夏", "入夏", "夏日", "夏夜", "酷暑", "三伏"),
    "秋": ("初秋", "深秋", "晚秋", "入秋", "秋日", "秋夜", "秋凉"),
    "冬": ("隆冬", "深冬", "初冬", "寒冬", "入冬", "冬日", "冬夜", "数九", "腊月"),
}
_SEASON_RE = re.compile("|".join(w for ws in _SEASON_FAMILIES.values() for w in ws))
_SEASON_OF = {w: fam for fam, ws in _SEASON_FAMILIES.items() for w in ws}

# 时辰粗档(升序;只收叙述常用词,单字"晨/夜"不收防误报)
_TIME_STEPS = [
    (1, ("拂晓", "黎明", "五更", "天蒙蒙亮")),
    (2, ("清晨", "早晨", "一大早")),
    (3, ("上午", "日上三竿")),
    (4, ("晌午", "正午")),
    (5, ("午后", "过午")),
    (6, ("黄昏", "傍晚", "日暮", "夕阳", "落日")),
    (7, ("掌灯", "入夜", "天黑", "天擦黑")),
    (8, ("夜里", "夜深")),
    (9, ("深夜", "半夜", "三更", "子时")),
]
_TIME_RE = re.compile("|".join(w for _, ws in _TIME_STEPS for w in ws))
_TIME_STEP_OF = {w: n for n, ws in _TIME_STEPS for w in ws}

# 回忆/追述豁免(句内命中即豁免该句的时间标记)与跨日衔接(倒流判定的重置词)
_MEMORY_RE = re.compile(r"想起|记得|回忆|忆起|去年|那年|往年|当年|旧年|儿时|从前|早年")
_DAY_BREAK_RE = re.compile(r"次日|翌日|翌晨|次晨|第二天|隔天|转天|天亮|天明|一觉|睡醒|醒来"
                           r"|三天后|数日后|几天后|翌年|过了[一两三几]?[天日夜]")

_SENT_BOUND = "。!?!?\n"

__all__ = ['ADJACENT_MIN_LEN', 'ANTI_SYCOPHANCY', 'DEFAULT_DISCIPLINE_BRIEF', 'DISCIPLINE_KINDS', 'FINDING_CATEGORIES', 'FINDING_SEVERITIES', 'LUANSHI_PURPLE_SEEDS', 'REPEAT_MIN_COUNT', 'REPEAT_MIN_LEN', '_ADVERB_WORDS', '_AI_GRADE_BANNED_LIGHT', '_AI_GRADE_BANNED_MEDIUM', '_AI_GRADE_DIALOGUE_LIGHT', '_AI_GRADE_DIALOGUE_MEDIUM', '_AI_GRADE_DIALOGUE_TAG_RE', '_AI_GRADE_HEAVY_GATE_COUNT', '_AI_GRADE_PARALLEL_LIGHT', '_AI_GRADE_PARALLEL_MEDIUM', '_AI_GRADE_PSYCH_LIGHT', '_AI_GRADE_PSYCH_MEDIUM', '_AI_GRADE_REPEAT_LIGHT', '_AI_GRADE_REPEAT_MEDIUM', '_AI_TIC_SENT_DELIM', '_AUTO_REWRITE_AI_TIC_KINDS', '_BANNED_LEXICON', '_CLICHE_RE', '_COMPACT_EITHER_OR_PREV', '_CONTEXTUAL_WORDS', '_DAY_BREAK_RE', '_DEGEN_META_TIER1_RE', '_DEGEN_META_TIER2_RE', '_DEGEN_PLACEHOLDER_PATTERNS', '_DEGEN_TITLE_RE', '_DEGEN_TRUNCATED_END_RE', '_DEGEN_VISIBLE_RE', '_DIALOGUE_RE', '_EDGE', '_EMOTION_WORD_RE', '_EMO_LABEL', '_EXPLAIN', '_FILLER_ACTION_WORDS', '_GENERIC_REFS', '_GOD_VIEW_PATTERNS', '_GRADE_ORDER', '_HARD_SEPARATORS', '_HAS_CJK', '_INTRA_SENT_SPLIT', '_MEMORY_RE', '_ONOMAT_LINE', '_PLATFORM_RUBRICS', '_PUNCT_CLOSING_QUOTE_RE', '_PUNCT_DIGIT_RE', '_PUNCT_ONLY', '_PUNCT_OPENING_DELIM_RE', '_PUNCT_PAUSE_RE', '_PUNCT_SENTENCE_END_RE', '_PURPLE_PATS', '_PURPLE_RE', '_QUOTED_SPANS', '_REVERSAL_TYPES', '_RHYTHM_ADJ_FLOOR', '_RHYTHM_CV_FLOOR', '_RHYTHM_MIN_SENTS', '_RULE_OF_THREE_SEG_RE', '_SEASON_FAMILIES', '_SEASON_OF', '_SEASON_RE', '_SENT_BOUND', '_SENT_DELIM_CAP', '_SENT_SPLIT', '_SIMILE_LIKE', '_SIMILE_WORDS', '_SOFT_SEPARATORS', '_STOP_CHARS', '_TAG_PARTICLES', '_THOUGHT_REPORT_RE', '_TIME_RE', '_TIME_STEPS', '_TIME_STEP_OF', '_TOXIC_PATTERNS', '_TRAILING_NOISE', '_VERDICT_RANK', '_VERDICT_RE', '_WATCH_MAP', '_WIKI_FLIPS', '_log', 'annotations', 'bisect', 'json', 'logging', 're']
