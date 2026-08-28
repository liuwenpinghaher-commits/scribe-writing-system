# 写厚抽取:两处按构造不可满足的缺陷

接 `2026-08-28-ROOTCAUSE-PROMPT.md`。R1+R2 已落(3a724206 / 4bb3b9db / f33cad9e)。
R1 确认真修好了:温贩婆短文写的是这本书的价单和抵押,不是通用人设。
`char_issue_ratio` 仍是 0.737,原因不在短文质量,在下面两处。

**不要重写短文。** 现有 14 段短文内容合格,修完这两处应当能直接抽出字段,
不需要再调一次 LLM 生成短文。

**不要为了过线调阈值。** 下面两处都不是阈值问题,是判据判的东西和它声称判的
东西不是一回事——和先前「悬置显示 cross_open 却判 all_closed」「introduces
判存在不判首现」同一类。

---

## 缺陷一:抽取输出与解析器不对齿(当前真正的阻塞点)

`build_portrait_extract_prompt` 给的是填空模板:

```
他要什么：
他让人付出什么：
```

实测模型返回的是两段裸文本,内容完全正确(逐字取自短文,一段答要什么、一段答
让人付出什么),但**没带标签**。而:

- `parse_codex_payload("character", raw)` 只认 JSON → 返回 `{}`
- `_apply_portrait_extract` 的正则兜底 `re.search(r"他要什么\s*[:：]\s*(.+)")`
  只认标签 → 不命中

两条路都落空,四字段全空,`duty_fields_ready` 判假,记 `llm_thin`。
**闸门根本还没轮到判。** 这也是 R2 四轮重试全部白跑的原因——重试改变不了
输出形态和解析器不对齿。

复现:

```python
from scribe3.codex_generate import parse_codex_payload
two = "她要的不是某一个人立刻死，而是交易成立。\n她会让人付出体温余额。"
parse_codex_payload("character", two)   # {}
```

### 修法(两头都做,任一命中即可)

1. 提示词改成硬性要求带标签输出,把两行标签写成必须原样回显的格式,而不是
   留空让模型填。
2. `_apply_portrait_extract` 增加无标签兜底:正则未命中时,按段落顺序取
   非空段落,第一段作 want、第二段作 pay。仅在 `patch` 与正则都落空时启用。

顺带:提示词对女性角色用「他要什么」,一并改成中性措辞。

---

## 缺陷二:`portrait_grounded` 判的是四字段拼接串

`codex_generate.py:824` `_duty_blob("character", ...)` 把
`surface_goal / deep_need / fear / internal_conflict` 四个字段 `" ".join`
成一串;`portrait_grounded` 去掉空格标点后要求这**一整串是短文的连续子串**。

`surface_goal` 出自短文某一句、`fear` 出自另一句,两段拼起来在原文里不连续。
实测拿短文里的两句原话:

- 单独看 `surface_goal` 是子串 → True
- 单独看 `fear` 是子串 → True
- 拼起来走 `portrait_grounded` → **False**

即模型逐字照抄短文,这道闸照样判失败。

### 修法

`portrait_grounded` 改成**逐字段**对短文判定,不再判拼接串。每个非空字段
单独检查是否落在短文里;全部非空字段都落在短文里才算 grounded。

判定用实词重合而非严格子串——抽取器可能把长句压缩,严格子串会误杀合法压缩。
阈值取「该字段的实词有多数出现在短文中」,具体比例自己定并在提交信息里写明
依据。防的是模型另编,不是防压缩。

`_duty_blob` 若别处还有用,保留;只改 `portrait_grounded` 的判定方式。

---

## 验收(必须按顺序,不许跳)

1. 单测先行:两处各补测。缺陷一测无标签两段输入能抽出字段;缺陷二测两句
   非相邻原话能判 grounded、另编的内容判不 grounded。
2. 只在 `wanjie_v2` 上对现有 14 个空壳重跑写厚,**不生成新短文**(短文已在
   `personality_detail`,直接走抽取)。
3. 报 `char_issue_ratio` 变化。抽 5 个人贴出 `surface_goal` / `fear` 原文,
   人读一遍确认是这本书的内容、不是通用人设。
4. `wanjie_scale` 不动。**不铺 41–200。**

抽取真能落地后再回头做 R3 按批分配。R3 现在仍不动。

如果修完 `char_issue_ratio` 仍不下来,停下报数,不要接着往下改。
