# scribe3 留白/减法 · 设计

> 设计日期:2026-06-23
> 目标:给 scribe3 加"留白/减法"能力,治 AI 写作的"情绪过饱和/写满"通病。

## 目标

加一条"留白/减法"craft 维度——正面引导主编"该不写的不写",并用确定性 QC 抓"过度解释/过度饱和"的表层信号。这是 hermes-novel 在 35 章实测里自诊的"情绪过饱和"系统性弱点的解药,也是乱世铜炉级与 AI 腔的分水岭。

## 背景

scribe3 的 craft 七引擎(body/temperature/idle/metaphor/subtext/sensory/soak)都在**正面塑造**,但没有"减法"维度。AI 写作通病是"写满"——每个情绪都展开、每条信息都给、每个转折都解释。留白(信息冰山、情绪不解释、删装饰、克制收尾)是高级感的关键。

## 设计(approach B:引擎引导 + 确定性 QC,不单加 LLM 判官)

留白是"质"的东西:深层判断("这里该不该留白")靠**引擎引导** + 已有的 `discipline_check`(LLM)兜底;表层"过度信号"(解释句/情绪标签/比喻密集)靠**确定性扫描**抓。不单加 LLM 饱和度判官(成本 + discipline_check 已能兜底语义级)。

### 一、craft.py 第八引擎 `restraint`(正面引导,主力)

`ENGINES` 加 `"restraint"`:
```python
"restraint": (
    "留白/减法:写满是 AI 通病,该不写的不写比写满更有力。"
    "①信息冰山:前史/设定落笔只露 1/8,读者能推的不写明。"
    "②情绪不解释:给身体/场景,不给「这意味着/他明白了/正是因为」的解说;转折后留一句呼吸,不立即点透。"
    "③删装饰:删了读者不少懂的形容词/比喻 → 删。"
    "④克制收尾:章末冷笔定格,不升华不总结。"
    "⑤一段一焦点:别在一段里塞满所有情绪/信息,留下未说的。"
),
```
配套:`_ZH` 加 `"restraint": "留白"`;`build_craft_block` 的七引擎循环元组改为含 restraint 的八引擎(已用 `for key in _ZH` 则自动覆盖,确认即可)。

### 二、critique.py `find_oversaturation`(确定性检测,辅助)

确定性可测的"过度饱和/解释"表层信号,按**每千字密度**归一化、超**保守阈值**才标记(宁可漏,不滥杀正常解释):

```python
_EXPLAIN = ["这意味着", "也就是说", "换句话说", "正是因为", "说明了", "其实是", "无非是", "不过是", "正因如此"]
_EMO_LABEL = ["愤怒", "悲伤", "恐惧", "绝望", "痛苦", "欣喜", "喜悦", "忧伤", "焦虑", "孤独", "兴奋", "悲痛"]
_SIMILE = ["像", "仿佛", "如同", "宛如", "好似", "犹如"]

def find_oversaturation(text, per_k_explain=3.0, per_k_emo=5.0, per_k_simile=6.0):
    """过度解释/过度饱和检测(每千字密度超阈值)。留白引擎的确定性兜底。"""
    n = len("".join((text or "").split())) or 1
    k = n / 1000.0
    out = []
    for label, words, thr in (("explain", _EXPLAIN, per_k_explain),
                              ("emo_label", _EMO_LABEL, per_k_emo),
                              ("simile", _SIMILE, per_k_simile)):
        cnt = sum(text.count(w) for w in words)
        if k > 0 and cnt / k > thr:
            out.append({"kind": label, "count": cnt, "per_k": round(cnt / k, 1)})
    return out
```
并入 `quality_flags` 第五键 `"oversaturation": find_oversaturation(text)`。

**阈值说明**:初始值保守(解释连接词每千字 >3、情绪标签 >5、比喻 >6),宁可漏报。实测后可在 plan/迭代调。

## 组件

| 文件 | 改动 |
|---|---|
| `scribe3/craft.py` | `ENGINES` 加 `restraint`;`_ZH` 加映射;build_craft_block 覆盖八引擎 |
| `scribe3/critique.py` | 加 `find_oversaturation` + 三个词表常量;`quality_flags` 加 `oversaturation` 键 |
| (自动受益) | 渲染端 `build_craft_block` 注入已含留白引擎;`s3_qc_chapter` 调 `quality_flags` 自动含 oversaturation,无需改 mcp/render |

## 测试策略(TDD)

| 测试 | 断言 |
|---|---|
| `test_craft.py::test_engines_eight_present` | `ENGINES` 含 restraint(键集 8 个);`build_craft_block()` 含"留白" |
| `test_craft.py::test_no_scifi_residue`(既有) | 留白引擎文本无科幻残留(沿用既有黑名单扫描) |
| `test_critique.py::test_oversaturation_explain` | 解释连接词密集文本 → 出 `explain` 项 |
| `test_critique.py::test_oversaturation_emo_label` | 情绪标签密集 → 出 `emo_label` 项 |
| `test_critique.py::test_oversaturation_clean_passes` | 正常克制文本(低密度)→ 空(不误杀) |
| `test_critique.py::test_quality_flags_has_oversaturation` | `quality_flags` 含 `oversaturation` 键 |

## YAGNI(不做)

- 不单加 LLM 饱和度判官(`discipline_check` 已兜底语义级过度解释)。
- 不做留白的前端可视化/单独 MCP 工具(qc 已自动含)。
- 阈值不做 per-work 可配(先用统一保守阈值,需要再说)。

## 不变量 / 风险

- 确定性 QC **保守**:阈值宁可漏报,不滥杀正常解释句/必要情绪词(误杀比漏报更伤)。
- 留白引擎是**题材无关**的通用 craft(进引擎层,不进题材层)。
- 引擎数从 7→8,`build_craft_block`/`test_engines` 需同步(用 `for key in _ZH` 则天然覆盖)。
- **`_SIMILE` 的「像」单字匹配会误抓**「图像/好像/想象/像样」等非比喻。plan 实现时改用更精确模式(如 `像[^,。]{1,10}(一样|般|似的)`)或仅保留 `仿佛/如同/宛如/好似/犹如` 等明确比喻词,把「像」交给保守阈值兜底。测试 `test_oversaturation_clean_passes` 须用含「好像/图像」的正常文本验证不误报。
