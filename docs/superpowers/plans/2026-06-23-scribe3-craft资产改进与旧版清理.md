# scribe3 craft 资产改进与旧版清理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 hermes-novel 的七大引擎 + 情感词典以"引擎层/题材层分离"落地进 scribe3 渲染管线(渲染端程序化注入 + 浸泡前置),并删除已无价值的 scribe2、hermes-novel 两个旧系统。

**Architecture:** 引擎层(`craft.py` 纯常量,题材无关)程序化注入 `build_render_prompt`;题材层(`craft_rule` per-work 表)主编经 elicitation 可改;浸泡前置(`soak.py`)渲染前产出情感曲线种子词;负面禁令留后置 critic(`critique.py`,并把题材耦合的升华正则拆到题材层)。

**Tech Stack:** Python 3.11、FastMCP、SurrealDB(NS=scribe3)、pytest。依据 spec:`docs/superpowers/specs/2026-06-23-scribe3-craft资产改进与旧版清理-design.md`。

**提交约定(用户红线):** 每个 Task 末尾的 commit 步骤须经作者明确批准后执行;未获批准则只留改动不提交。所有命令在仓库根 `<repo-root>` 下、scribe3 venv 激活后运行。

---

## File Structure

**阶段一(craft 代码)**
- 新建 `scribe3/craft.py` — 引擎层:`ENGINES`(七引擎)+ `PALETTE`(情感词典15种,清洗后)+ `build_craft_block()`
- 新建 `scribe3/soak.py` — 浸泡前置:`build_soak_prompt`/`parse_soak`/`soak`
- 改 `scribe3/critique.py` — 拆 `_PURPLE_PATS`(通用留下/题材移走)+ `find_purple_prose(text, extra_patterns)` + 补 E1/E2 `find_ai_tics` + `quality_flags` 聚合
- 改 `scribe3/render.py` — `build_render_prompt` 加 `craft_block`/`soak_result`;`render` 加 `soak` 开关 + 读 craft_rule
- 新建 `scribe3/migrations/008_craft_rule.surql` — `craft_rule` 表
- 改 `scribe3/store.py` — `add_craft_rule`/`list_craft_rules`/`delete_craft_rule`;`seed_craft_rules`
- 改 `scribe3/ontology.py` — `World.list_craft_rules()` 空实现(鸭子兼容,内存渲染不报错)
- 改 `scribe3/mcp.py` — `s3_emotion_palette` + `s3_craft_rule_list/add/remove` + `WRITE_GATED` 登记
- 改 `scribe3/hermes_skills/scribe-novel-v2/SKILL.md` — craft 段扩展

**测试**
- 新建 `tests/test_craft.py`、`tests/test_soak.py`、`tests/test_craft_rule.py`
- 改 `tests/test_critique.py`、`tests/test_render.py`

**阶段二(验证 + 删除)**
- 真机渲染验证(无新文件)
- 删除:`scribe/`、`写作/hermes-novel/`、`写作/.agents/wiki*`、`~/.scribe/data.db`、清理 `~/.hermes/config.yaml`

---

## 阶段一:craft 代码

### Task 1: craft.py 引擎层(ENGINES + PALETTE + build_craft_block)

**Files:**
- Create: `scribe3/craft.py`
- Test: `scribe3/tests/test_craft.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_craft.py
"""引擎层 craft · 纯函数/纯常量,无 DB 无网络(同 test_critique 范式)。"""
from scribe3.craft import ENGINES, PALETTE, build_craft_block

_SCIFI = ("沈默", "姜婉", "陆远舟", "校准", "波形图", "数据面板", "探针", "数据日志", "酸菜鱼")


def test_engines_seven_present():
    assert set(ENGINES) == {"body", "temperature", "idle", "metaphor", "subtext", "sensory", "soak"}


def test_palette_fifteen_complete():
    assert len(PALETTE) == 15
    for name, e in PALETTE.items():
        assert e["body"], f"{name} 缺身体信号"
        assert e["inner"], f"{name} 缺内部感觉"


def test_no_scifi_residue():
    """craft wiki 是科幻《量子幽灵》提炼,迁移必须清洗(两版复盘发现 B)。"""
    blob = "".join(ENGINES.values()) + "".join(
        "".join(e["body"] + e["inner"]) for e in PALETTE.values())
    for w in _SCIFI:
        assert w not in blob, f"craft.py 残留科幻词:{w}"


def test_build_craft_block_has_engines():
    block = build_craft_block()
    assert "身体先行" in block and "温度曲线" in block and "潜台词" in block


def test_build_craft_block_appends_themed_rules():
    rules = [{"kind": "artifact_craft", "pattern": "法器四件套", "note": "专名+工艺+术数+义理"}]
    block = build_craft_block(rules)
    assert "本书题材规则" in block
    assert "法器四件套" in block and "专名+工艺+术数+义理" in block
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_craft.py -v`
Expected: FAIL,`ModuleNotFoundError: No module named 'scribe3.craft'`

- [ ] **Step 3: 实现 craft.py**

ENGINES 用下面定稿文本(从 `写作/.agents/wiki/craft/engine-overview.md` + `03-body.md`/`04-temperature.md` 萃取精炼,无题材词)。PALETTE 从 `写作/.agents/wiki/toolkit/emotion-thesaurus.md` 逐条搬入(该文件阶段二才删,此刻仍在);**清洗映射**:删每种情感的"覆盖动作"段(归题材层)、把 `沈默/姜婉` 句删除、`校准参数/数据面板/波形图/探针/数据日志/酸菜鱼` 等科幻物删除或换中性。下面给完整 ENGINES + 前 4 种 PALETTE 完整内容作模板,其余 11 种(内疚/震惊/疲惫/孤独/警觉/好奇/释然/犹豫/被背叛/绝望/嫌恶/困惑——共 15)按同样结构与清洗规则从源文件搬入。

```python
# scribe3/craft.py
"""引擎层 craft · 题材无关的写作引擎 + 情感词典。
从 hermes-novel craft wiki(写作/.agents/wiki/)萃取,已清洗科幻《量子幽灵》残留。
纯常量/纯函数,无 DB/网络,可离线单测。题材特化(升华正则/法器写法/角色覆盖动作)
不在此——在 craft_rule per-work 表(见 store.py / migrations/008)。
"""
from __future__ import annotations

ENGINES: dict[str, str] = {
    "body": (
        "身体先行:情感的展示顺序永远是 身体→行动→沉默→语言。叙述者不命名情感"
        "(禁「他感到悲伤」)、不解说防御机制、不替读者理解。三层——L1 无意识微动作"
        "(最强,角色自己都不知道在做)＞L2 覆盖动作(用另一行为盖住情绪,暴露防御机制)"
        "＞L3 身体失控(想控制却失败,全卷≤3 次)。叙述者 95% 闭嘴,5% 例外仅用于"
        "「打破读者认知框架」的一句洞察,每章最多 1 句。"
    ),
    "temperature": (
        "温度曲线:每 500 字情绪温度至少变化 1 次(微震即可)。四色——冷(压抑/疏离)、"
        "暖(柔软/怀念)、锐(紧张/对抗)、杂(混乱/失控)。全章温度差≥2 级,不能全冷或全锐。"
        "压抑≠恒温:表面平静时内部仍有微震(手指频率变了/呼吸变了)。三工具:节奏切换"
        "(长短句)、叙事距离跳跃(特写↔远景)、闲笔插入(高压后给读者一口气)。"
    ),
    "idle": (
        "闲笔:每章≥3 个与剧情无关但让世界/角色有温度的具体细节(至少一个世界级、一个角色级)。"
        "必须具体到能画出来。不解释,放在那里就好。豁免契诃夫之枪——闲笔不为推动剧情,是让世界活着。"
    ),
    "metaphor": (
        "认知比喻:每个比喻必须让读者理解一件之前不理解的事,且来自角色的专业领域"
        "(思维惯性冒出来,不是在「用修辞」)。三问——①删了它读者少理解什么?「没什么」→删"
        "(装饰比喻);②来自角色领域吗?否→重写;③后面跟解释句吗?有→删解释(比喻自己会说话)。每章 2-4 个。"
    ),
    "subtext": (
        "潜台词:每章至少 1 处角色实际说的与真正想说的不同。不在叙述中解释潜台词,让读者自己发现。"
        "三模式:屏障对话(心知肚明不说破)、转移话题(避真正想说的、谈无关日常)、物理替代"
        "(用一个动作替代该说的话)。角色避真话时往往谈论无关的日常事物。"
    ),
    "sensory": (
        "感官锚定:每个关键场景至少 1 个非视觉感官(听/触/嗅/温度/本体感觉)。环境承载情感——"
        "不命名情感,让环境说话。2-3 个精准细节＞5 个泛泛细节。反复出场的场景应有稳定的"
        "「感官签名」(读者闻到那股气味就知道身在何处)。"
    ),
    "soak": (
        "浸泡(贯穿全程):始终保持 POV 角色的声音——不是你在写,是角色在经历。"
        "环境、他人、情感都经该角色的感知/人格/防御机制过滤后呈现。"
    ),
}

# 情感词典:15 种,每种 {body:[身体信号], inner:[内部感觉]}。已去角色名/科幻物。
# 本书角色的「覆盖动作」放 craft_rule(kind=cover_action),不在此通用层。
PALETTE: dict[str, dict] = {
    "压抑的悲伤": {
        "body": ["目光短暂移向别处又迅速收回(约半秒)", "手指无意识沿杯沿或桌沿画圈",
                 "呼吸变浅但节奏不变(刻意控制)", "把手边物品摆放得过度整齐",
                 "突然去做一件不紧急的事(擦拭、整理、收拾)", "说话时看着对方的下巴而非眼睛"],
        "inner": ["胸腔里有一块空的位置——不疼,但持续存在", "喉咙微微发紧,没到说不出话的程度",
                  "一种「忘了什么」的模糊不适,追不到源头"],
    },
    "被压住的恐惧": {
        "body": ["瞳孔微微放大", "手指轻微颤抖,精细动作偏移", "咽口水的动作比平时慢",
                 "呼吸从鼻息变成嘴巴微张", "肩膀不自觉抬高一点", "脚趾在鞋里蜷起来(别人看不到)"],
        "inner": ["后脖颈汗毛竖起", "胃部收缩像被攥了一把", "时间变慢——注意力突然极清晰",
                  "皮肤表面有细微的电流感"],
    },
    "内疚": {
        "body": ["回避与相关人的目光", "无意识触碰自己的手腕或后颈", "别人说话时点头过多过快",
                 "主动做补偿性小事(倒水、让位、多担一点)", "相关话题出现时身体微微后倾"],
        "inner": ["想起那件事时腹部有微弱而确定的下坠感", "一种「欠了什么还不了」的背景噪音",
                  "被感谢时比被批评时更不舒服"],
    },
    "愤怒(被压制的)": {
        "body": ["下颌咬紧——太阳穴附近的肌肉跳一下", "手握成拳又刻意松开",
                 "说话语速变慢(不是思考,是在控制)", "眼神变硬、眨眼频率降低", "呼吸变深变重、鼻翼微张"],
        "inner": ["热量从胸口往上涌,停在喉咙", "太阳穴的血管在跳", "一种「被关在笼子里」的压迫感"],
    },
    # —— 其余 11 种:震惊 / 疲惫(深层的) / 孤独 / 警觉 / 好奇 / 释然 / 犹豫 / 被背叛 /
    #    绝望 / 嫌恶 / 困惑 ——
    # 从 写作/.agents/wiki/toolkit/emotion-thesaurus.md 第 5–15 条逐条搬入,
    # 同样只取「身体信号」→body、「内部感觉」→inner,丢弃「覆盖动作」段,
    # 删除任何含 沈默/姜婉/陆远舟/校准/波形图/数据面板/探针/数据日志/酸菜鱼 的句子。
    # (源文件此刻仍在;test_palette_fifteen_complete 会强制 15 种齐全、test_no_scifi_residue 会强制清洗干净)
}


def build_craft_block(rules: list[dict] | None = None) -> str:
    """组装引擎层引导块(注入渲染 prompt);题材层 rules 叠加其后。
    rules: [{kind, pattern, note}] 来自 craft_rule per-work 表。"""
    _ZH = {"body": "身体先行", "temperature": "温度曲线", "idle": "闲笔",
           "metaphor": "认知比喻", "subtext": "潜台词", "sensory": "感官锚定", "soak": "浸泡"}
    lines = ["## 写作引擎(题材无关,渲染时遵守)"]
    for key in ("body", "temperature", "idle", "metaphor", "subtext", "sensory", "soak"):
        lines.append(f"- 【{_ZH[key]}】{ENGINES[key]}")
    if rules:
        lines.append("## 本书题材规则(本作专属)")
        for r in rules:
            note = f" — {r['note']}" if r.get("note") else ""
            lines.append(f"- [{r.get('kind')}] {r.get('pattern')}{note}")
    return "\n".join(lines)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_craft.py -v`
Expected: PASS(5 passed)。若 `test_palette_fifteen_complete` 失败=11 种没搬全;若 `test_no_scifi_residue` 失败=清洗没干净。

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/craft.py scribe3/tests/test_craft.py
git commit -m "feat(craft): 引擎层 craft.py(七引擎+情感词典15种,清洗科幻残留)"
```

---

### Task 2: soak.py 浸泡前置

**Files:**
- Create: `scribe3/soak.py`
- Test: `scribe3/tests/test_soak.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_soak.py
"""浸泡前置 · 渲染前产出情感曲线种子词(意识流丢弃)。用 fake complete_fn,不连网。"""
from scribe3.scenario import luanshi_leak_world
from scribe3.soak import build_soak_prompt, parse_soak, soak


def test_soak_prompt_in_focalizer_voice_and_limited():
    w = luanshi_leak_world()
    p = build_soak_prompt(w, 1, "role:老道")
    assert "流云观皂衣道士" in p, "soak 以视角角色身份"
    assert "治眼" not in p, "soak 也受限知约束:不含他人私密"


def test_parse_soak_extracts_cot():
    reply = '随便一段意识流……{"emotion_arc":"戒备→贪念","turn":"看清那颗丹时","seed_words":["潮","锈","贪"]}'
    r = parse_soak(reply)
    assert r["emotion_arc"] == "戒备→贪念"
    assert r["turn"] == "看清那颗丹时"
    assert r["seed_words"] == ["潮", "锈", "贪"]


def test_parse_soak_bad_json_safe():
    r = parse_soak("模型只吐了散文没有 JSON")
    assert r == {"emotion_arc": "", "turn": "", "seed_words": []}


def test_soak_calls_model():
    w = luanshi_leak_world()
    def fake(prompt, **kw):
        return '{"emotion_arc":"冷→锐","turn":"拔刀","seed_words":["铁","血"]}'
    r = soak(w, 1, "role:老道", fake)
    assert r["seed_words"] == ["铁", "血"]
```

- [ ] **Step 2: 运行确认失败**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_soak.py -v`
Expected: FAIL,`ModuleNotFoundError: No module named 'scribe3.soak'`

- [ ] **Step 3: 实现 soak.py**

```python
# scribe3/soak.py
"""浸泡前置 · 渲染前让模型以 focalizer 身份进入状态,产出情感曲线种子词。
意识流文本本身丢弃(只为进入角色),只解析 CoT 结构化产出带进正式渲染。
受限知约束:soak prompt 只用 focalizer 知识帧内的事实。"""
from __future__ import annotations

import json
import re

from scribe3.knowledge import project_frame


def build_soak_prompt(world, chapter: int, focalizer: str) -> str:
    foc = world.entity(focalizer)
    name = foc.name if foc else focalizer
    frame = project_frame(world, focalizer, chapter)
    facts = "、".join(f"{f.attribute}:{f.value}" for f in frame.facts[:8]) or "(此刻暂无已知)"
    return (
        f"你就是【{name}】。写前浸泡一次(产出只为进入状态,不进正文)。\n"
        f"你此刻只知道:{facts}——别人的私密心思你一概不知,不得提及。\n"
        "先在心里以你的身份过一遍这一场,然后只输出一行 JSON:\n"
        '{"emotion_arc":"本场情感 起点→终点(各3-5字)",'
        '"turn":"情感转折发生的具体时刻(一句话)",'
        '"seed_words":["本场情绪种子词3-5个"]}'
    )


def parse_soak(reply: str) -> dict:
    m = re.search(r"\{.*\}", reply or "", re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            return {"emotion_arc": (d.get("emotion_arc") or "").strip(),
                    "turn": (d.get("turn") or "").strip(),
                    "seed_words": [str(x) for x in (d.get("seed_words") or [])][:5]}
        except Exception:
            pass
    return {"emotion_arc": "", "turn": "", "seed_words": []}


def soak(world, chapter: int, focalizer: str, complete_fn) -> dict:
    """渲染前置:调一次模型拿情感曲线种子词。complete_fn(prompt)->str。"""
    return parse_soak(complete_fn(build_soak_prompt(world, chapter, focalizer)))
```

- [ ] **Step 4: 运行确认通过**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_soak.py -v`
Expected: PASS(4 passed)

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/soak.py scribe3/tests/test_soak.py
git commit -m "feat(craft): soak.py 浸泡前置(情感曲线种子词,受限知约束)"
```

---

### Task 3: critique.py 拆题材正则 + 补 E1/E2

**Files:**
- Modify: `scribe3/critique.py:49-78`(`_PURPLE_PATS` / `find_purple_prose` / `quality_flags`)
- Test: `scribe3/tests/test_critique.py`(追加)

- [ ] **Step 1: 写失败测试(追加到 test_critique.py 末尾)**

```python
# 追加到 scribe3/tests/test_critique.py
from scribe3.critique import find_ai_tics, find_purple_prose


def test_purple_generic_stays():
    """通用升华句(跨题材)仍被抓。"""
    assert find_purple_prose("他知道,回不去了。")


def test_purple_themed_via_extra_patterns():
    """题材升华句(天地为炉)不再硬编码,经 extra_patterns 注入才命中。"""
    text = "炉火映脸,天地为炉,万物为铜。"
    assert not find_purple_prose(text), "题材正则已移出通用层,默认不命中"
    assert find_purple_prose(text, extra_patterns=[r"天地为炉|万物为铜"]), "题材正则经注入命中"


def test_find_ai_tics_em_dash_abuse():
    """E1:全章破折号 > 5。"""
    text = "他——她——它——你——我——他们——又来了"
    hits = find_ai_tics(text)
    assert any(h["kind"] == "em_dash" for h in hits)


def test_find_ai_tics_not_a_but_b():
    """E2:不是A——是B 句式。"""
    hits = find_ai_tics("那不是恐惧——是渴望。")
    assert any(h["kind"] == "not_a_but_b" for h in hits)


def test_quality_flags_includes_ai_tics():
    flags = quality_flags("那不是恐惧——是渴望。")
    assert "ai_tics" in flags
```

- [ ] **Step 2: 运行确认失败**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_critique.py -v`
Expected: FAIL — `ImportError: cannot import name 'find_ai_tics'`,且 `test_purple_themed_via_extra_patterns` 失败(当前 `天地为炉` 仍硬编码命中)。

- [ ] **Step 3: 修改 critique.py**

把 `_PURPLE_PATS` 里题材耦合的一条(`天地为炉|万物为铜|在炉[子火]?里`)删除(它移入 craft_rule 种子,Task 5);`find_purple_prose` 加 `extra_patterns` 参数;新增 `find_ai_tics`;`quality_flags` 聚合。改 `scribe3/critique.py`:

```python
# 49-59 行:_PURPLE_PATS 删掉题材那条(天地为炉),只留通用 7 条
_PURPLE_PATS = [
    r"原来[^。！？\n]{0,30}(就|早就|从一开始|没的选|没得选)",
    r"从[^,，。\n]{1,18}那一刻起",
    r"像[^。！？\n]{0,12}[滴颗][^。！？\n]{0,8}眼泪",
    r"影子[被]?拉得很[长短]",
    r"(有些|有的)[^。！？\n,，]{0,14}(就再也|再也)[^。！？\n]{0,14}",
    r"他知道[，,][^。！？\n]{0,4}(回不去|没的选|不一样了)",
    r"走下去|刀山火海",
]
_PURPLE_RE = [re.compile(p) for p in _PURPLE_PATS]


def find_purple_prose(text: str, extra_patterns: list[str] | None = None) -> list[dict]:
    """升华/抒情/主题直陈句:替读者下结论、硬塞命运隐喻——冷笔大忌。生成后扫描+删。
    通用正则跨题材;题材专属升华句经 extra_patterns 注入(来自 craft_rule purple_regex)。"""
    pats = list(_PURPLE_RE) + [re.compile(p) for p in (extra_patterns or [])]
    out: list[dict] = []
    for s in re.split(r"(?<=[。！？\n])", text or ""):
        st = s.strip()
        if st and any(rx.search(st) for rx in pats):
            out.append({"phrase": st[:30], "kind": "purple"})
    return out


# 通用 AI 腔硬检(E1/E2,题材无关,来自 hermes-novel hard-checks)
_NOT_A_BUT_B = re.compile(r"不是.{1,15}——是")


def find_ai_tics(text: str) -> list[dict]:
    """E1 破折号全章>5;E2 「不是A——是B」句式(LLM 最常见的伪深刻制造器)。"""
    out: list[dict] = []
    dash = (text or "").count("——")
    if dash > 5:
        out.append({"kind": "em_dash", "count": dash})
    for m in _NOT_A_BUT_B.finditer(text or ""):
        out.append({"kind": "not_a_but_b", "phrase": m.group(0)})
    return out
```

并把 `quality_flags`(72-78 行)改为:

```python
def quality_flags(text: str, extra_patterns: list[str] | None = None) -> dict:
    """聚合四类确定性质检(渲染层兜底)。extra_patterns 来自本书 craft_rule purple_regex。"""
    return {
        "repetition": find_repetitions(text),
        "structural": find_structural_repeats(text),
        "purple": find_purple_prose(text, extra_patterns),
        "ai_tics": find_ai_tics(text),
    }
```

- [ ] **Step 4: 运行确认通过(含原有测试不回归)**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_critique.py -v`
Expected: PASS(原 4 + 新 5 = 9 passed)

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/critique.py scribe3/tests/test_critique.py
git commit -m "refactor(craft): 升华正则拆题材层(天地为炉移出通用)+ 补E1/E2 AI腔硬检"
```

---

### Task 4: craft_rule 表 + store CRUD + 题材种子

**Files:**
- Create: `scribe3/migrations/008_craft_rule.surql`
- Modify: `scribe3/store.py`(类内追加 craft_rule 方法,约 286 行 motif 区附近)
- Test: `scribe3/tests/test_craft_rule.py`

- [ ] **Step 1: 写失败测试**

```python
# scribe3/tests/test_craft_rule.py
"""题材层 craft_rule · per-work 升华正则/法器写法/角色覆盖动作。用 store fixture(真临时库)。"""


def test_craft_rule_add_list(store):
    store.add_craft_rule("purple_regex", "天地为炉|万物为铜", "乱世铜炉升华句")
    rules = store.list_craft_rules()
    assert any(r["pattern"] == "天地为炉|万物为铜" for r in rules)
    assert all({"kind", "pattern", "note"} <= set(r) for r in rules)


def test_craft_rule_delete(store):
    store.add_craft_rule("artifact_craft", "法器四件套", "专名+工艺+术数+义理")
    rid = store.list_craft_rules()[0]["id"]
    store.delete_craft_rule(rid)
    assert not store.list_craft_rules()


def test_seed_craft_rules_luanshi(store):
    """首书种子:乱世铜炉的升华正则(8条)+法器四件套。"""
    store.seed_craft_rules()
    rules = store.list_craft_rules()
    kinds = {r["kind"] for r in rules}
    assert "purple_regex" in kinds and "artifact_craft" in kinds
    assert any("天地为炉" in r["pattern"] for r in rules)
```

- [ ] **Step 2: 运行确认失败**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_craft_rule.py -v`
Expected: FAIL — `AttributeError: 'SurrealStore' object has no attribute 'add_craft_rule'`

- [ ] **Step 3a: 建 migration**

```surql
-- scribe3/migrations/008_craft_rule.surql
-- 题材层 craft 规则(per-work):升华正则/法器写法/角色覆盖动作。
-- 引擎层(craft.py)题材无关、所有书共享;题材特化规则在此,主编经 elicitation 可改。
DEFINE TABLE IF NOT EXISTS craft_rule SCHEMALESS;
DEFINE FIELD IF NOT EXISTS kind ON craft_rule TYPE string;     -- purple_regex|artifact_craft|cover_action
DEFINE FIELD IF NOT EXISTS pattern ON craft_rule TYPE string;
DEFINE FIELD IF NOT EXISTS note ON craft_rule TYPE option<string>;
```

- [ ] **Step 3b: store.py 追加方法(在 `delete_motif` 之后,约 286 行)**

```python
    # --- 题材层 craft 规则(per-work)---
    def add_craft_rule(self, kind: str, pattern: str, note: str = "") -> None:
        self._execute_write(
            "CREATE craft_rule SET kind=$k, pattern=$p, note=$n",
            {"k": kind, "p": pattern, "n": note})

    def list_craft_rules(self) -> list[dict]:
        return self._query("SELECT meta::id(id) AS id, kind, pattern, note FROM craft_rule")

    def delete_craft_rule(self, rid: str) -> None:
        self._execute_write("DELETE type::record('craft_rule',$r)", {"r": rid})

    def purple_patterns(self) -> list[str]:
        """本书升华正则(喂 critique.find_purple_prose 的 extra_patterns)。"""
        return [r["pattern"] for r in self.list_craft_rules() if r["kind"] == "purple_regex"]

    def seed_craft_rules(self) -> None:
        """首书(乱世铜炉系)种子:scribe2 实战的升华正则8条 + 法器四件套。幂等(已有则跳过)。"""
        if self.list_craft_rules():
            return
        for p in ["天地为炉|万物为铜|在炉里", r"原来.{0,30}(就|早就|从一开始)",
                  r"从.{1,18}那一刻起", r"像.{0,12}[滴颗].{0,8}眼泪", "影子被拉得很长",
                  r"(有些|有的).{0,14}(就再也|再也)", r"他知道[，,].{0,4}(回不去|不一样了)",
                  "走下去|刀山火海"]:
            self.add_craft_rule("purple_regex", p, "乱世铜炉升华句(scribe2实证)")
        self.add_craft_rule(
            "artifact_craft",
            "法器/法术首次出场须四件套:专名+工艺工序+术数+义理(至少齐3项)",
            "范例:灵龙镇煞钉·阳铜黑狗血七七四十九天炼成·三百六十支围太极阵·画井为狱镇魂锁煞")
```

- [ ] **Step 4: 运行确认通过**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_craft_rule.py -v`
Expected: PASS(3 passed)

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/migrations/008_craft_rule.surql scribe3/store.py scribe3/tests/test_craft_rule.py
git commit -m "feat(craft): craft_rule per-work 表 + CRUD + 乱世铜炉题材种子"
```

---

### Task 5: ontology.World 鸭子兼容 + render 注入 craft/soak

**Files:**
- Modify: `scribe3/ontology.py`(World 末尾,约 124 行加 `list_craft_rules`)
- Modify: `scribe3/render.py:31-75`(`build_render_prompt` + `render`)
- Test: `scribe3/tests/test_render.py`(改+追加)

- [ ] **Step 1: 改/写测试**

把现有 `test_render_feeds_clean_prompt_to_model`(render 现默认会多调一次 soak)改为显式 `soak=False` 隔离;并新增 craft/soak 注入断言。改 `scribe3/tests/test_render.py`:

```python
# 改现有 test_render_feeds_clean_prompt_to_model 的 render 调用为 soak=False:
    out = render(w, 1, "role:老道", complete_fn=fake_complete, soak=False)

# 末尾追加:
from scribe3.craft import build_craft_block


def test_prompt_injects_craft_block():
    w = luanshi_leak_world()
    p = build_render_prompt(w, 1, "role:老道", craft_block=build_craft_block())
    assert "写作引擎" in p and "身体先行" in p, "渲染 prompt 含引擎层 craft"


def test_prompt_injects_soak_seeds():
    w = luanshi_leak_world()
    sr = {"emotion_arc": "戒备→贪念", "turn": "看清那颗丹", "seed_words": ["潮", "锈", "贪"]}
    p = build_render_prompt(w, 1, "role:老道", soak_result=sr)
    assert "情感曲线" in p and "戒备→贪念" in p and "潮" in p


def test_craft_does_not_break_limited_pov():
    """load-bearing:craft/soak 注入后,老道视角仍不含焦三私密。"""
    w = luanshi_leak_world()
    sr = {"emotion_arc": "", "turn": "", "seed_words": ["雨", "刀"]}
    p = build_render_prompt(w, 1, "role:老道", craft_block=build_craft_block(), soak_result=sr)
    assert "治眼" not in p and "攒钱给老娘" not in p


def test_render_runs_soak_then_renders():
    """soak=True:complete_fn 先被 soak 调一次、再被渲染调一次;最终输出是渲染结果。"""
    w = luanshi_leak_world()
    calls = []
    def fake(prompt, **kw):
        calls.append(prompt)
        if "浸泡" in prompt:
            return '{"emotion_arc":"冷→锐","turn":"拔刀","seed_words":["铁"]}'
        return "雨砸在乱葬岗的烂泥上。"
    out = render(w, 1, "role:老道", complete_fn=fake, soak=True)
    assert out == "雨砸在乱葬岗的烂泥上。"
    assert len(calls) == 2 and "铁" in calls[1], "soak 种子词进了渲染 prompt"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_render.py -v`
Expected: FAIL — `build_render_prompt() got an unexpected keyword argument 'craft_block'`

- [ ] **Step 3a: ontology.py World 加空实现(124 行末尾)**

```python
    def list_craft_rules(self) -> list[dict]:
        """内存 World 无题材层(鸭子兼容 render);真库由 SurrealStore 覆盖。"""
        return []
```

- [ ] **Step 3b: 改 render.py**

`build_render_prompt` 签名加 `craft_block`/`soak_result`,在事件之后、`_CONSTRAINT` 之前插入;`render` 加 `soak` 开关并读 craft_rule。改 `scribe3/render.py`:

```python
def build_render_prompt(world: World, chapter: int, focalizer: str,
                        craft_block: str = "", soak_result: dict | None = None) -> str:
    """按 focalizer 的知识帧拼限知渲染 prompt。帧外事实绝不出现。
    craft_block(引擎层+题材层)与 soak 种子词插在事件之后、渲染纪律之前。"""
    frame = project_frame(world, focalizer, chapter)
    foc = world.entity(focalizer)
    foc_name = foc.name if foc else focalizer

    lines = [f"# 把下面的事件写成小说正文(限知视角:{foc_name})",
             f"以【{foc_name}】的限知视角,把下列既定事件写成一段小说散文。直接写正文,别解释。",
             "",
             f"## {foc_name} 此刻所知(这是你能用的全部事实,帧外之事他不知道):"]
    if frame.facts:
        for f in frame.facts:
            subj = world.entity(f.entity_id)
            nm = subj.name if subj else f.entity_id
            lines.append(f"- {nm}·{f.attribute}:{f.value}")
    else:
        lines.append("-(空:此视角暂无已知事实)")

    lines += ["", "## 本章要发生的事件(按此渲染):"]
    for ev in _events_at(world, chapter):
        parts = "、".join(
            (world.entity(v).name if world.entity(v) else v)
            for v in ev.participants.values()
        )
        where = world.entity(ev.location).name if ev.location and world.entity(ev.location) else (ev.location or "")
        lines.append(f"- [{ev.type}] {parts}" + (f" 于{where}" if where else ""))

    if craft_block:
        lines += ["", craft_block]
    if soak_result and (soak_result.get("seed_words") or soak_result.get("emotion_arc")):
        seeds = "、".join(soak_result.get("seed_words") or [])
        arc = soak_result.get("emotion_arc") or ""
        turn = soak_result.get("turn") or ""
        lines += ["", "## 本场情感设计(浸泡产出,据此把握情绪曲线,不要写进正文)"]
        if arc:
            lines.append(f"- 情感曲线:{arc}")
        if turn:
            lines.append(f"- 转折时刻:{turn}")
        if seeds:
            lines.append(f"- 情绪种子词:{seeds}")

    lines += ["", _CONSTRAINT]
    return "\n".join(lines)


def render(world: World, chapter: int, focalizer: str,
           complete_fn: Callable[..., str] | None = None,
           max_tokens: int | None = None, timeout: float | None = None,
           soak: bool = True) -> str:
    """渲染一章一视角:浸泡→限知 prompt(含 craft)→complete_fn→sjuzhet。默认走 Hermes。"""
    if complete_fn is None:
        from scribe3.llm import hermes_complete
        complete_fn = hermes_complete
    from scribe3.craft import build_craft_block
    rules = world.list_craft_rules() if hasattr(world, "list_craft_rules") else None
    craft_block = build_craft_block(rules)
    soak_result = None
    if soak:
        from scribe3.soak import soak as run_soak
        soak_result = run_soak(world, chapter, focalizer, complete_fn)
    prompt = build_render_prompt(world, chapter, focalizer,
                                 craft_block=craft_block, soak_result=soak_result)
    kw: dict = {}
    if max_tokens:
        kw["max_tokens"] = max_tokens
    if timeout is not None:
        kw["timeout"] = timeout
    return complete_fn(prompt, **kw)
```

- [ ] **Step 4: 运行确认通过(全量,防回归)**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_render.py scribe3/tests/test_craft.py scribe3/tests/test_soak.py -v`
Expected: PASS(原 render 测试 + 新 4 条 + craft/soak 全绿)

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/ontology.py scribe3/render.py scribe3/tests/test_render.py
git commit -m "feat(craft): render 注入引擎层+题材层craft+浸泡种子词(限知不破)"
```

---

### Task 6: MCP 工具 s3_emotion_palette + s3_craft_rule_*

**Files:**
- Modify: `scribe3/mcp.py`(读工具区加 palette/list;写门控区加 craft_rule add/remove;`WRITE_GATED` 登记)
- Test: `scribe3/tests/test_mcp.py`(追加)

- [ ] **Step 1: 写失败测试(追加)**

```python
# 追加到 scribe3/tests/test_mcp.py
from scribe3 import mcp as m


def test_emotion_palette_list_and_query():
    names = m.s3_emotion_palette.fn("")
    assert isinstance(names, list) and "压抑的悲伤" in names
    one = m.s3_emotion_palette.fn("压抑的悲伤")
    assert one["body"] and one["inner"]


def test_craft_rule_gated_in_write_set():
    assert "s3_craft_rule_add" in m.WRITE_GATED
    assert "s3_craft_rule_remove" in m.WRITE_GATED
    assert "s3_craft_rule_list" not in m.WRITE_GATED
    assert "s3_emotion_palette" not in m.WRITE_GATED
```

> 注:`s3_emotion_palette` 是只读纯数据工具,`.fn` 是 FastMCP 包装下的原函数(同仓 test_mcp 既有调用方式)。写工具的批准链已由 `test_mcp_elicit.py` 覆盖,这里只断言门控登记。

- [ ] **Step 2: 运行确认失败**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_mcp.py -k "palette or craft_rule" -v`
Expected: FAIL — `AttributeError: module 'scribe3.mcp' has no attribute 's3_emotion_palette'`

- [ ] **Step 3a: WRITE_GATED 登记(mcp.py:30-31)**

```python
WRITE_GATED = {"s3_add_character", "s3_add_fact", "s3_add_event", "s3_record_knowledge",
               "s3_plant_promise", "s3_advance_promise", "s3_ingest_chapter",
               "s3_craft_rule_add", "s3_craft_rule_remove"}
```

- [ ] **Step 3b: 读工具(加在 s3_qc_chapter 之后,约 130 行)**

```python
@mcp.tool(annotations=_RO)
def s3_emotion_palette(emotion: str = "") -> list | dict:
    """情感词典(引擎层,题材无关):空参返回15种情感名;带参返回该情感的身体信号/内部感觉。
    渲染某情感时查取 2-3 个身体信号编织进叙述(show 不 tell 的命门)。"""
    from scribe3.craft import PALETTE
    if not emotion:
        return list(PALETTE)
    return PALETTE.get(emotion, {})


@mcp.tool(annotations=_RO)
def s3_craft_rule_list() -> list[dict]:
    """列本书题材层 craft 规则(升华正则/法器写法/角色覆盖动作)。"""
    return _store.list_craft_rules()
```

- [ ] **Step 3c: 写工具(加在 s3_record_knowledge 之后,约 227 行)**

```python
@mcp.tool(annotations=_RW)
async def s3_craft_rule_add(ctx: Context, kind: str, pattern: str, note: str = "") -> dict:
    """加一条本书题材 craft 规则(写,待批)。kind=purple_regex|artifact_craft|cover_action。"""
    ok = await _ask(ctx, f"加题材规则 [{kind}] {pattern}")
    return commit_if_approved("s3_craft_rule_add", ok,
                              lambda: _store.add_craft_rule(kind, pattern, note))


@mcp.tool(annotations=_RW)
async def s3_craft_rule_remove(ctx: Context, rule_id: str) -> dict:
    """删一条本书题材 craft 规则(写,待批)。"""
    ok = await _ask(ctx, f"删题材规则 {rule_id}")
    return commit_if_approved("s3_craft_rule_remove", ok,
                              lambda: _store.delete_craft_rule(rule_id))
```

- [ ] **Step 4: 运行确认通过**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_mcp.py -v`
Expected: PASS(原有 + 新 2 条全绿)

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/mcp.py scribe3/tests/test_mcp.py
git commit -m "feat(craft): MCP s3_emotion_palette(读)+s3_craft_rule_*(写待批)"
```

---

### Task 7: SKILL.md craft 段扩展 + qc 接题材正则

**Files:**
- Modify: `scribe3/hermes_skills/scribe-novel-v2/SKILL.md:34-37`(写作纪律段)
- Modify: `scribe3/mcp.py`(`s3_qc_chapter` 接本书 purple_patterns)
- Test: 手动 + 复用 test_mcp(下方)

- [ ] **Step 1: 写失败测试(追加 test_mcp.py)**

```python
def test_qc_chapter_uses_themed_purple(store, monkeypatch):
    """s3_qc_chapter 把本书 craft_rule 的题材升华正则喂给 find_purple_prose。"""
    from scribe3 import mcp as m
    store.seed_craft_rules()
    store.save_chapter(1, "炉火映脸,天地为炉,万物为铜。")
    m.set_store(store)
    flags = m.s3_qc_chapter.fn(1)
    assert flags["purple"], "题材升华句(天地为炉)应被本书正则抓到"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_mcp.py -k qc_chapter_uses_themed -v`
Expected: FAIL（`s3_qc_chapter` 当前不传题材正则,`天地为炉` 已从通用层移走 → purple 为空）

- [ ] **Step 3a: 改 s3_qc_chapter(mcp.py:124-129)**

```python
@mcp.tool(annotations=_RO)
def s3_qc_chapter(seq: int) -> dict:
    """对某章正文跑确定性 QC(复读/排比/升华/AI腔)——渲染层兜底。
    升华检测叠加本书题材正则(craft_rule purple_regex)。"""
    from scribe3.critique import quality_flags
    ch = _store.get_chapter(seq)
    if not ch:
        return {}
    extra = _store.purple_patterns() if hasattr(_store, "purple_patterns") else None
    return quality_flags(ch["prose"], extra_patterns=extra)
```

- [ ] **Step 3b: 改 SKILL.md 写作纪律段(34-37 行替换)**

```markdown
## 写作纪律(craft · 引擎层题材无关,渲染端已程序化注入 `scribe3/craft.py`)
渲染前先**浸泡**(`soak`):以 focalizer 身份过一遍本场,定情感曲线+种子词。落笔守七引擎:
- **身体先行**:情感经 身体→行动→沉默→语言;不命名情感;L3 失控全卷≤3 次;叙述者 95% 闭嘴。
- **温度曲线**:每 500 字一震,冷/暖/锐/杂,全章温差≥2 级;压抑≠恒温。
- **闲笔**每章≥3(豁免契诃夫之枪);**潜台词**每章≥1;**认知比喻**来自角色领域、后不跟解释;**感官锚定**每场≥1 非视觉感官。
- 需要某情感的身体信号时查 `s3_emotion_palette`(选 2-3 个编织,勿堆砌)。
- show 不 tell;冷笔动作收尾,不喊升华口号;单一戏剧主线,不双高潮、不偷跑后续章;用了力量必付代价。
- 本书题材规则(升华句/法器写法)见 `s3_craft_rule_list`;负面禁令由 `s3_qc_chapter` 后置兜底,不必写时分心。
```

- [ ] **Step 4: 运行确认通过**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/test_mcp.py -v`
Expected: PASS

- [ ] **Step 5: 提交(经作者批准)**

```bash
git add scribe3/mcp.py "scribe3/hermes_skills/scribe-novel-v2/SKILL.md" scribe3/tests/test_mcp.py
git commit -m "feat(craft): qc接本书题材正则 + SKILL.md craft段扩展(引擎/浸泡/词典)"
```

---

### Task 8: 阶段一全量回归 + 首书种子落库

**Files:** 无新增(集成校验)

- [ ] **Step 1: 全量测试**

Run: `cd "<repo-root>" && python -m pytest scribe3/tests/ -v`
Expected: 全绿(含原有所有测试 + 本期新增 test_craft/test_soak/test_craft_rule + 改动的 test_critique/test_render/test_mcp)。任何红=回归,先修。

- [ ] **Step 2: 给主书 main 落题材种子(一次性,连真库)**

scribe3 真库须在跑(`~/.surrealdb/surreal` 或既有实例,`SCRIBE3_SURREAL_URL` 默认 `ws://127.0.0.1:8001/rpc`)。

```bash
cd "<repo-root>" && python -c "
from scribe3.store import SurrealStore
s = SurrealStore(ns='scribe3', db='main'); s.apply_schema(); s.seed_craft_rules()
print('craft_rule 种子:', len(s.list_craft_rules()), '条'); s.close()
"`
```
Expected: 打印 `craft_rule 种子: 9 条`(8 升华正则 + 1 法器四件套)。

- [ ] **Step 3: 提交(经作者批准)**

```bash
git add -A scribe3/
git commit -m "test(craft): 阶段一全量回归绿 + 主书 craft 题材种子落库"
```

---

## 阶段二:真机验证 + 删除旧版

### Task 9: 真机渲染验证(craft 生效 + 限知不破)

**Files:** 无(真机冒烟)

- [ ] **Step 1: 渲染一章,人工核验**

Hermes 与 scribe3 真库在跑。渲染主书第 1 章老道视角:

```bash
cd "<repo-root>" && python -c "
from scribe3.store import SurrealStore
from scribe3.render import build_render_prompt, render
s = SurrealStore(ns='scribe3', db='main'); s.apply_schema()
# 先看注入:prompt 应含引擎层 + 题材规则、且不含他人私密
p = build_render_prompt(s, 1, 'role:老道',
      __import__('scribe3.craft', fromlist=['build_craft_block']).build_craft_block(s.list_craft_rules()))
assert '身体先行' in p and '写作引擎' in p, 'craft 未注入'
print('[OK] craft 注入;prompt 长度', len(p))
s.close()
"`
```
Expected: 打印 `[OK] craft 注入`。**人工再读 prompt 确认**:含七引擎、含本书题材规则、不含任何其他角色私密。

- [ ] **Step 2: 实跑一次带浸泡的渲染(连 Hermes)**

```bash
cd "<repo-root>" && python -c "
from scribe3.store import SurrealStore
from scribe3.render import render
s = SurrealStore(ns='scribe3', db='main'); s.apply_schema()
out = render(s, 1, 'role:老道')   # soak=True 默认:先浸泡后渲染
print(out[:400]); s.close()
"`
```
Expected: 输出一段散文(非元叙述)。**人工核验**:身体先行/克制收尾的痕迹、无明显 AI 腔、不含他人私密。若 doubao 限流报错,重试或确认 Hermes :8643 在跑。

- [ ] **Step 3: 验收闸(不通过则停,回阶段一修)**

确认全部为真后才进 Task 10:
- [ ] `pytest scribe3/tests/` 全绿
- [ ] prompt 含引擎层 + 题材层,human-read 无他人私密
- [ ] 真机渲染出散文且 craft 痕迹可见

---

### Task 10: 删除旧版(不可逆 · 逐项确认后执行)

**Files:** 删除 `scribe/`、`写作/hermes-novel/`、`写作/.agents/wiki*`、`~/.scribe/data.db`;改 `~/.hermes/config.yaml`

> **强制前置**:Task 9 验收闸三项全绿。每个删除子步骤执行前向作者复述将删什么、确认后再删。九原渡 32 章随 `scribe/out/` 一并删、不留档(作者 2026-06-23 决定)。

- [ ] **Step 1: 删前快照(可回滚保险)**

```bash
cd "<repo-root>" && git rev-parse HEAD && git status --short
du -sh scribe/ "~/Downloads/写作/hermes-novel" "~/Downloads/写作/.agents" ~/.scribe 2>/dev/null
```
Expected: 记录当前 HEAD(scribe/ 删除走 git,可 `git revert`/`checkout` 找回代码;数据库 data.db 删除不可逆)。

- [ ] **Step 2: 删 scribe2 代码(git 追踪,用 git rm)**

```bash
cd "<repo-root>" && git rm -r scribe/ && git status --short | head
```
Expected: 143 个追踪文件 staged for deletion;`scribe/out/`、`scribe/vendor/`(gitignore)随目录一并消失。

- [ ] **Step 3: 删 hermes-novel(独立 repo 内,直接 rm)**

```bash
rm -rf "~/Downloads/写作/hermes-novel" \
       "~/Downloads/写作/.agents/wiki" \
       "~/Downloads/写作/.agents/wiki-backup-v3"
ls "~/Downloads/写作/" | head    # 确认开源副本/备份仍在
```
Expected: hermes-novel 与 craft wiki 消失;`novel-engine/book-genesis-master/备份` 等**保留**。

- [ ] **Step 4: 删 scribe2 库数据(不可逆)**

```bash
rm -rf ~/.scribe/data.db && ls -la ~/.scribe 2>/dev/null
```
Expected: scribe2 的 SurrealDB(NS=scribe)数据删除。scribe3 数据(NS=scribe3,独立)不受影响。

- [ ] **Step 5: 清理 Hermes 全局 config 对旧版的引用**

编辑 `~/.hermes/config.yaml`:删 `skills.external_dirs` 下的两行(scribe2/hermes-novel skills 路径)、删 `mcp_servers.scribe2` 块。改后校验:

```bash
grep -n "scribe2\|hermes-novel\|写作/hermes\|scribe/scribe2" ~/.hermes/config.yaml || echo "[OK] 全局 config 已无旧版引用"
hermes --profile scribe3 skills list 2>/dev/null | grep -E "scribe|novel" | head
```
Expected: `[OK] 全局 config 已无旧版引用`;profile scribe3 skills 仍只有 `scribe-novel-v2`(Task 前已是此状态)。

- [ ] **Step 6: 删除后回归(确保 scribe3 不依赖被删项)**

```bash
cd "<repo-root>" && python -m pytest scribe3/tests/ -v 2>&1 | tail -20
```
Expected: 全绿。`migrate.py`/`test_migrate.py` 若依赖 scribe2 库会失败——确认 migrate 仅连 NS 不依赖 `scribe/` 目录(已核:`migrate.py` 连 SurrealDB,不 import scribe2 代码);若 test_migrate 连旧库则按需 skip 并记录。

- [ ] **Step 7: 提交(经作者批准)**

```bash
cd "<repo-root>" && git add -A
git commit -m "chore: 删除 scribe2 + hermes-novel 旧系统(craft 已提取进 scribe3,九原渡不留档)"
```

---

## Self-Review

**1. Spec coverage**(逐节核对 spec → task):
- 引擎层 `craft.py`(ENGINES/PALETTE/build_craft_block)→ Task 1 ✓
- 浸泡 `soak.py` → Task 2 ✓
- 负面禁令下沉 critic + E1/E2 → Task 3 ✓
- 题材层 `craft_rule` 表 + 种子(升华正则8条+法器四件套)→ Task 4 ✓
- render 注入 craft_block + soak + 限知不破 → Task 5 ✓
- MCP `s3_emotion_palette` + `s3_craft_rule_*` + WRITE_GATED → Task 6 ✓
- SKILL.md 扩展 + qc 接题材正则 → Task 7 ✓
- 科幻清洗(去沈默/姜婉/校准…)→ Task 1 `test_no_scifi_residue` 强制 ✓
- 迁移(craft wiki→craft.py)→ 融入 Task 1(源文件阶段二才删,可参照)✓
- 验证(真机渲染 craft 生效)→ Task 9 ✓
- 删除(scribe2/hermes-novel/data.db/config,九原渡不留档,保留开源副本)→ Task 10 ✓
- 测试 9 条断言 → 散落 Task 1-6,均有对应 test ✓

**2. Placeholder scan:** PALETTE 仅 4/15 种逐字列出,其余 11 种以"从 emotion-thesaurus.md 第5-15条按清洗映射搬入"指示——源文件阶段二才删、此刻在仓,且 `test_palette_fifteen_complete`+`test_no_scifi_residue` 强制完整与清洗,非 TBD 占位。其余步骤均含完整代码与确切命令。

**3. Type consistency:** `build_craft_block(rules)` / `find_purple_prose(text, extra_patterns)` / `quality_flags(text, extra_patterns)` / `soak(world,ch,foc,fn)->{emotion_arc,turn,seed_words}` / `build_render_prompt(...,craft_block,soak_result)` / `render(...,soak)` / store `add_craft_rule/list_craft_rules/delete_craft_rule/purple_patterns/seed_craft_rules` 在各 task 间签名一致;`craft_rule.kind ∈ {purple_regex,artifact_craft,cover_action}` 全程统一。
