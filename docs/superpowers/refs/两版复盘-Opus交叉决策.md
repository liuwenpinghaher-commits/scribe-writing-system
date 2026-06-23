# 两版复盘 · Opus 一手复核与 scribe3 决策

> 本文是对 [scribe2-retrospective.md](scribe2-retrospective.md) 与 [hermes-novel-retrospective.md](hermes-novel-retrospective.md) 两份文档的**复核 + 交叉分析 + 决策层**。
> 前两份由 Sonnet subagent 生成,回答"两个旧系统是什么";本文由 Opus 亲自重读一手源码生成,回答"它们说得准不准、彼此冲突在哪、scribe3 到底该怎么选"。
> 复核日期:2026-06-23。一手阅读范围见文末附录。

---

## 一、为什么要做这次复核

Sonnet subagent 的两份文档是基于源码生成的二手浓缩。这类浓缩有两个固有风险:
1. **具体数字/正则/字段可能转述失真**(幻觉高发区);
2. **单文档视角**——每份只看一个系统,看不到两系统之间的冲突与共性。

Opus 用 1M 上下文一次性吃下两系统的命门源码(scribe2 的 `critique.py`/`writing.py`/`generate.py`/`consistency.py` + hermes-novel 的 5 个 craft 核心文件),做了两件 subagent 做不到的事:**逐条核对技术声明**,以及**跨系统对照判断**。

---

## 二、准确性核实:前两份文档可信度背书

逐条核对了 subagent 文档里所有"硬声明",结论:**scribe2 那份近乎零误差,hermes-novel 那份准确但有 1 处夸大 + 2 处重大遗漏。**

### 2.1 scribe2-retrospective.md —— 全部核实通过

| subagent 声明 | 一手出处 | 判定 |
|---|---|---|
| 8 维 rubric(texture/surprise/emotion_truth/pace/voice/anti_slop/intent_resonance/coherence) | `critique.py:9-18` | ✅ 准确 |
| 评改 threshold = 3.5 | `critique.py:33,110` | ✅ 准确 |
| 去重 n-gram n=8、出现 ≥3 次 | `critique.py:140` | ✅ 准确 |
| 去重最多 2 遍、改写 <原文60% 则弃 | `critique.py:225,236` | ✅ 准确 |
| 评改 max_rounds=1、成对比较 B_better 才采纳 | `critique.py:109-131` | ✅ 准确 |
| 升华句正则 _PURPLE_PATS = 8 条 | `critique.py:180-189`(亲数 8 条) | ✅ 准确 |
| 纪律闸四类违规 + cut_after 截断留 ≥40% | `critique.py:253-259,283` | ✅ 准确 |
| rollup_global cap=1800、首章+最近6章、verbatim 不压缩 | `generate.py:53-64` | ✅ 准确 |
| check_chapter 用 `content[:3000]`、长章后半漏检 | `consistency.py:39` | ✅ 准确(确属真实局限) |
| 力量体系 cost/limitations/trouble_it_causes 注入 | `consistency.py:24-31`、`writing.py:122-131` | ✅ 准确 |

**结论:scribe2 那份文档可直接作为可信参考,无需修订。** 它甚至准确转述了代码注释里"确定性检测对语义违规是瞎的"这种关键判断。

### 2.2 hermes-novel-retrospective.md —— 准确,但需打三个补丁

✅ **核实通过的**:情感词典 15 种(亲数,`emotion-thesaurus.md` 正好 15 条)、身体先行三层 L3 整卷≤3次(`03-body.md:59`)、叙述者 95% 闭嘴每章≤1句(`03-body.md:63-79`)、温度四色冷/暖/锐/杂(`04-temperature.md:21-26`)、硬检 E1-E5 + W1-W11(`hard-checks.md` 完全对应)。

⚠️ **勘误 1(夸大)**:subagent 表格称情感词典每种情感都是"身体信号 + 内部感觉 + **覆盖动作**"三件套。**实际只有前 4 种**(压抑的悲伤/被压住的恐惧/内疚/愤怒)有"覆盖动作"段,**后 11 种没有**(`emotion-thesaurus.md`)。迁移时别假设每种情感都有现成覆盖动作。

❌ **重大遗漏 1(题材污染)**:整套 craft wiki 的 **toolkit 层和示例层是从一本科幻小说《量子幽灵》提炼的**,不是志怪。铁证遍布:情感词典的覆盖动作绑定"**沈默/姜婉**"(科幻角色)、身体先行的示范句"探针测到的不是数据。是**陆远舟**最后三秒的恐惧"(`03-body.md:78`)、温度曲线预规划 yaml 全是"**校准参数/波形图异常/数据面板/食堂酸菜鱼**"(`04-temperature.md:99-107`)。**subagent 却建议"不做修改地注入 scribe3 的 Writer system prompt"——这是错的。** 详见 §4。

❌ **重大遗漏 2(路线冲突)**:见 §3,这是本次复核最重要的发现。

---

## 三、深层发现 A:两系统在"writer 要不要知道审查规则"上路线相反

这是 subagent 两份文档**各说各话、谁也没点破**的根本分歧。

### 3.1 铁证

- **scribe2**:`writing.py:237` 最后一行 `parts.append(CONSTRAINT_BLOCK)`——把反 AI 腔 9 条铁律(show不tell / 禁升华尾句 / **一长串禁用词清单** / 法器三件套 / 知识边界)**全量拼进 writer 的生成 prompt**。writer 写之前就知道所有红线。
- **hermes-novel**:信息屏障是**有意设计**(`hermes-novel-retrospective.md` §3.2)——writer 的输入里**明确排除**"审查标准/批判维度/技法解析";理由白纸黑字:"Writer 不知道审查标准 → 不会写'符合审查规则'的防御性文本"。

**同一个问题,两个系统给了相反答案。** 一个把规则塞满 writer 脑子,一个坚决不让 writer 看见规则。

### 3.2 谁对?Opus 的判断:hermes-novel 的方向更对,但 scribe2 的内容不能丢

把规则清单塞进 writer prompt 有一个隐蔽代价:**writer 会进入"规避模式"而非"创作模式"**。满脑子"别写嘴角勾起、别写一丝、别写命运齿轮"的模型,倾向于写得拘谨、安全、寡淡——它在躲雷,不在塑造语感。hermes-novel 用 35 章验证过这一点(防御性文本)。

但 scribe2 的 CONSTRAINT_BLOCK **内容**(尤其第 7 条法器三件套、第 9 条知识边界)是真有价值的——不能因为放错位置就丢掉。

### 3.3 融合方案:把约束从"事前塞 writer"挪到"事后当 critic 清单"

| 约束类型 | scribe2 现在的位置 | scribe3 应放的位置 |
|---|---|---|
| 正面 craft(show不tell / 双声部 / 节奏 / 法器要有里子) | writer prompt | **改为 hermes-novel 式引擎引导**(正面塑造,不写成禁令) |
| 负面禁令(禁用词清单 / 禁升华句) | writer prompt | **移出 writer,下沉为后置 critic 的检查清单** |
| 知识边界(POV 防穿帮) | writer prompt | **保留在 writer**(这是上下文事实,不是审查规则,writer 必须知道"谁不知道什么") |

核心动作一句话:**`CONSTRAINT_BLOCK` 的"禁用清单"部分应从 `build_writing_context` 里删除,改造成 critic 阶段的确定性检查 + LLM 判官。** 这恰好就是 scribe2 已经有的 `find_purple_prose` / `discipline_check`——它们本就是后置 critic。换句话说,**scribe2 自己把同一批规则既塞了 writer(预防)又做了后置扫描(检测),writer 端那份是冗余且有害的,删掉它,只保留后置扫描。**

这是两系统经验融合后的最优解,任何单份文档都得不出。

---

## 四、深层发现 B:两系统都把"题材特化规则"硬编码进了"通用" craft 层

这是两个系统**共同的隐藏坑**,scribe3 多书架构下会直接爆雷。

### 4.1 题材耦合证据(两系统都有)

| 资产 | 出处 | 绑死的题材 |
|---|---|---|
| _PURPLE_PATS 升华正则 `天地为炉\|万物为铜\|在炉[子火]?里` | scribe2 `critique.py:182` | 乱世铜炉(志怪) |
| CONSTRAINT_BLOCK 法器三件套范例"灵龙镇煞钉/阳铜黑狗血七七四十九天" | scribe2 `writing.py:27` | 志怪 |
| 情感词典覆盖动作"调出数据面板/校准参数" | hermes-novel `emotion-thesaurus.md:33-35` | 量子幽灵(科幻) |
| 温度曲线范例"波形图异常/诡秘之主克莱恩" | hermes-novel `04-temperature.md:87,105` | 科幻/西幻 |

**两个系统都没有把"题材无关的引擎"和"题材特化的实例"分开。** scribe2 的志怪规则混在通用 critique 里;hermes-novel 的科幻实例混在通用 craft 里。

### 4.2 为什么对 scribe3 是硬伤

memory 记载 scribe3 是**多书架构**(按 work_id 隔离,支持跨书品味)。如果把这些题材耦合的资产当通用层注入:
- 写志怪的书,注入了科幻情感词典 → writer 思维里冒出"校准/数据面板",污染志怪冷笔;
- 写科幻的书,注入了 `天地为炉` 升华正则 → 误杀正常文本,或漏检科幻特有的 AI 腔。

### 4.3 分层方案:craft 资产必须拆成"引擎层 / 题材层"两级

```
通用引擎层(题材无关,所有 work 共享)
  · 身体先行三层(L1/L2/L3)
  · 温度曲线(每500字一震,四色,差≥2级)
  · 闲笔(每章≥3,豁免契诃夫之枪)
  · 潜台词(每章≥1)
  · 认知比喻三问(删了少理解什么/来自角色领域/后面别跟解释)
  · 对话三校验(遮名可辨/碰禁句/有脏元素)
  · 通用 AI 腔硬检(E1破折号>5 / E2不是A是B / 副词密度 / 命名情感词)

题材层(per-work,放 SurrealDB 或 per-work skill 配置)
  · 升华句正则(志怪用"天地为炉";科幻用别的)
  · 法器/道具写法(志怪三件套;科幻另一套)
  · 情感词典的"覆盖动作"(必须用本书角色重写,不能用沈默/姜婉)
  · 范文/技法标杆(本书风格指纹)
```

**判定标准很简单**:一条规则换本书还成立吗?成立→引擎层;不成立→题材层。"身体先行"换什么书都对 → 引擎层。"天地为炉是升华句" → 只对乱世铜炉成立 → 题材层。

这个洞察 subagent 完全没有,但它决定了 scribe3 的 craft 资产该怎么组织。

---

## 五、深层发现 C:scribe2 的"三处重叠"是纵深防御,不是冗余——但有一处该删

同一批"反 AI 腔"规则,scribe2 出现在**三个地方**:
1. `writing.py` CONSTRAINT_BLOCK —— 事前塞 writer(预防)
2. `critique.py` `_PURPLE_PATS` / `find_purple_prose` —— 事后确定性扫描(检测)
3. `domain.py:16` `_SLOP` 词表 + `slop_density` —— 质量度量(打分)

第 2、3 处是**有价值的纵深**:确定性扫描负责"已生成文本里揪出来删",质量度量负责"给这章的 AI 腔密度打个客观分"。两者职责不同,都该留。

但第 1 处(事前塞 writer)如 §3 所述,是**有害冗余**——它没带来额外防护(后置扫描已经兜底),反而把 writer 推进规避模式。**结论:删第 1 处,保留第 2、3 处。**

---

## 六、给 scribe3 的决策清单(可执行)

把三个深层发现 + 两份 subagent 文档的"可直接搬"项,合成 scribe3 的行动清单:

### 必做(纠正旧系统的架构错误)
1. **CONSTRAINT_BLOCK 拆分**:禁用词清单移出 `build_writing_context`,下沉为后置 critic;知识边界、正面 craft 保留但改写成引擎引导语气。(发现 A)
2. **craft 资产分两层**:引擎层(通用)放 `scribe-novel-v2` SKILL.md / 公共注入;题材层(升华正则/法器写法/情感覆盖动作/范文)放 per-work 配置。(发现 B)
3. **清洗 hermes-novel craft 的科幻残留**:迁移情感词典/温度范例/身体示范句时,把"沈默/姜婉/陆远舟/校准/波形图"全部换成本书(志怪)的角色与物象,或抽象成不带角色名的结构。(勘误/发现 B)

### 直接搬(经实战验证,别重新发明)
4. scribe2 五层 QC 闸:确定性去重(`find_repetitions`+`find_structural_repeats`+`find_purple_prose`)→ LLM 纪律闸(`discipline_check` 四类)→ 外科修漏(`fix_leak`)→ 8 维评改(成对比较防退步)→ 一致性(力量体系代价检查)。
5. scribe2 `build_writing_context` 的注入骨架(`writing.py` 全 15 段):相关性过滤角色、POV/非POV 内核私密标记、知识账本、伏笔 beats、母题四位一体、Progressions 时间门、语义召回。这是产出质量的命门。
6. hermes-novel 七大引擎(身体先行/温度曲线/闲笔/认知比喻/潜台词/感官锚定/浸泡)——作为引擎层 craft 注入。
7. hermes-novel 信息屏障原则:critic 不喂细纲(只评文学质量,不评"是否完成任务")。

### 别重复(两系统的弯路)
8. 别用 LLM 压缩全书记忆(身份漂移坑)→ 确定性拼接(scribe2 已对)。
9. 别全量注入所有角色 → 相关性过滤(scribe2 已对)。
10. 别用确定性规则做语义判断(知识泄露/双高潮必须 LLM)。
11. 别把题材规则写死进通用层(发现 B,两系统都犯)。
12. 别把禁令清单塞 writer prompt(发现 A,scribe2 犯)。
13. `check_chapter` 别只检 `[:3000]`(长章后半漏检)→ 分段检或滑窗。
14. `upsert_character` 别走删旧+重建(每次重算嵌入)→ 仅 text 变化才重嵌。

### 补空白(两系统都没有的)
15. **非线性叙事**:两系统都是线性时间锁死,无插叙/环形/多视角。scribe3 若要超越需补。
16. **留白/减法**:hermes-novel 自己诊断出"情绪过饱和"是系统性弱点;scribe2 也无留白机制。

---

## 附录:本次一手阅读范围

**scribe2 源码(全文逐行)**:`critique.py`(356)、`writing.py`(238)、`generate.py`(65)、`consistency.py`(51);`domain.py` _SLOP 段、`mcp.py`/`app.py`/`schema.py` 经 subagent 文档交叉。

**hermes-novel craft(全文逐行)**:`emotion-thesaurus.md`(257)、`craft/engine-overview.md`(120)、`craft/03-body.md`(101)、`craft/04-temperature.md`(109)、`guardrails/hard-checks.md`(137)。

**对照**:两份 subagent retrospective 全文。

*本文所有判定均有源码行号出处,无捏造。与前两份文档的差异之处(勘误、路线冲突、题材耦合、CONSTRAINT_BLOCK 移位)以本文为准。*
