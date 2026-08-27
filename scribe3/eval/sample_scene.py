"""Write one ~2000-word scene from shared craft. Eval-only. Never call playbook."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "docs/craft-samples"

# Structural lines both 对照.md / 因文.md / 章法.md agree on.
# No names, props, or plots from either book.
SHARED_CRAFT: tuple[str, ...] = (
    "要人共情，把眼睛交给当场那个人。要人旁观，才站到外头报年号。",
    "要落一个真意，先给反面，再破功。不要上来就掏底牌。",
    "用办事说。开篇先立还在过的日子，不要开篇就报身份、扔钩子。",
    "嘴上要的和真正缺的打架。看见谁办了哪一件，日子怎么变。不要鉴定式人设。",
    "先让人进还在过的日子，再让哪一件闯进来，读完人欠了什么。",
    "不要学：开篇必须一个强钩子、三章交代主线、努力三次失败、黄金三章。",
    "奇事从丢脸的小事里闯进来；当场人还在办事，不要先宣布设定。",
    "人刚把上一场圆成「不算亏」，下一场险不要写成同一桩事追上；让他歇下来时，绊进别人正在办的事。",
    "同一场里换谁闯进来，可以写长。换章号当换章，不要。",
    "翻的是还能不能当回原来过这种日子的人，不是气氛变了。",
    "醒了先叫谁，才是人有没有回来。不要把升级、换地、换身份写成翻。",
)

BANNED_TOKENS: tuple[str, ...] = (
    "乱世铜炉",
    "诡秘之主",
    "胡炭",
    "萱儿",
    "秦苏",
    "胡不为",
    "时闻盂",
    "韩之敬",
    "犀香",
    "周明瑞",
    "克莱恩",
    "廷根",
    "梅丽莎",
    "邓恩",
    "阿兹克",
    "柜上账",
    "皮影",
    "布包",
    "横担",
    "非凡者",
    "源堡",
    "愚者",
    "序列8",
    "占卜家",
    "圣手小青龙",
    "三水村",
    "梧桐村",
    "定马村",
    "鲁恩",
    "赫密斯",
)

_DISALLOWED_GENRE = (
    "不要写成古代武侠、江湖门派、维多利亚风、神秘学、占卜、穿越。",
    "题材必须同时避开两本参照。当代职场、悬疑刑侦、乡土、硬科幻可以。",
)

_HEADING_PROSE = "正文"
_HEADING_EVAL = "自评"


def build_prompt_v4(premise: dict, demo_md: str = "") -> str:
    """Material only. No checklist language."""
    person = premise["person"]
    gap = premise["info_gap"]
    lines = [
        "写一场约两千字的戏。专名自拟。",
        "",
        f"这个人：{person['name']}，{person['age']}岁，{person['job']}。在乎的是：{person['cares']}。",
        f"这件事（今天躲不掉）：{premise['event']}",
        f"怕失去：{premise['fear']}",
        f"题材：{premise['genre']}",
        "",
        f"谁已经知道：{gap['knows']}",
        f"谁还不知道：{gap['does_not_know']}",
        f"谁在瞒：{gap['hides']}",
        "",
        "这场里的人：",
    ]
    for c in premise["cast"]:
        jargon = "、".join(c["jargon"])
        lines.append(
            f"{c['name']}，{c.get('age', '')}，{c['job']}。"
            f"嘴里常有这些词：{jargon}。"
            f"说话的样子：{c.get('speech_habit', '')}。"
            f"总惦记着「{c.get('tic', '')}」，跟眼下这件事没关系，还是会冒出来。"
            f"他绝不会说：{c['never_says']}。"
        )
    props = premise.get("props") or []
    if props:
        lines.append("")
        lines.append(
            "这场里有这些东西：" + "、".join(props) + "。"
            "东西一旦出场，后面得再用上一次，别只摆着。"
        )
    lines.append("")
    lines.append(
        "下面几段是别人书里的对白，连人物心里的嘀咕一起摘了。"
        "只看人怎么开口、心里怎么嘀咕，不要抄专名和情节："
    )
    lines.append("")
    lines.append((demo_md or "").strip())
    lines.append("")
    lines.append(
        "硬限制：核心冲突不要写成账、盘点、清算、对账、欠款、差钱。"
        "不要写成古代武侠江湖，不要维多利亚神秘学占卜。"
    )
    lines.append("")
    lines.append("输出，不要代码块：")
    lines.append("# <短标题>")
    lines.append("## 正文")
    lines.append("<两千字左右，现代汉语>")
    return "\n".join(lines)


_DRAFT_SECTIONS = ("正文", "事实清单", "洞", "岔路")


def build_prompt_draft(premise: dict) -> str:
    """交草稿，不交成品。

    与 v4 的两处关键差别：

    一是**不给对白示范**。示范会让模型往范文上靠，而草稿要的是它自己
    想到哪、想不到哪——尤其是「洞」那一段，给了范例就等于把答案漏了。

    二是**不给 speech_habit / tic / catchphrase**。那三个参数是文笔层的，
    前几轮已证明会被逐条机械执行（`catchphrase: 有文件。` → 原样贴进第一句）。
    草稿本来就不追求对白措辞，索性从生成路径里拿掉。
    """
    person = premise["person"]
    gap = premise["info_gap"]
    cast = "；".join(
        f"{c['name']}（{c.get('age', '')}，{c['job']}）" for c in premise["cast"]
    )
    props = "、".join(premise.get("props") or [])
    return f"""你要交的是一份草稿，不是成品。

草稿的用途是给作者拿去改。所以你要做的是让他改着省事，不是让他读着舒服。
判据只有一条：他改你这份，比他从零写要快。

这个人：{person['name']}，{person['age']}岁，{person['job']}。在乎的是：{person['cares']}。
这件事（今天躲不掉）：{premise['event']}
怕失去：{premise['fear']}
题材：{premise['genre']}
这场里还有：{cast}
这场里有这些东西：{props}

谁已经知道：{gap['knows']}
谁还不知道：{gap['does_not_know']}
谁在瞒：{gap['hides']}

交四样东西，用下面的标题，不要代码块。

# <短标题>

## 正文

八百到一千五百字的骨架。三条死规矩：

- 不许点题。不许在结尾或任何地方总结这件事的意义。
- 不许用比喻。一个都不要。写你看见什么。
- 不许用漂亮句子盖住你没想清楚的地方。想不清楚就用方括号标出来，像这样：
  ［这里缺三五句交代两人过去的关系，我还没想好用哪件事来交代］

环境描写、情绪的细腻刻画、句子的节奏——这些一概不要写，那是作者的活，
你写了他还得拆。省下的字数用在把事情讲清楚上。

## 事实清单

三小节：

- **时间线**：逐条列，精确到能查出矛盾的程度。
- **谁在什么时候知道什么**：每个出场的人一行，分「知道」和「不知道」两栏。
- **这一稿新立的事实**：这场戏之后就成立了、以后不能推翻的东西。

写完自己回头验一遍时间线。对不上的地方直接写出来，不要藏，也不要顺手改圆。

## 洞

你没解决的问题，按要紧程度排，**至少五条**。三类都要找：

- 现实里说不通的。这一类最要紧，一条就能让整个故事塌。
- 你埋了但没收的。
- 你自己也不确定的。

如果你觉得没有洞，那是你没找。

## 岔路

关键选择：你走了哪条、另外还有哪条、你倾向哪条、为什么。

只列真岔路——两条走下去，故事会长成不同的样子，才算真岔路。
三条其实差不多的选项不要列，那是凑数。
"""


def parse_draft(raw: str) -> dict[str, str]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()
    parts: dict[str, str] = {}
    title = ""
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("# ") and current is None and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if current is not None:
                parts[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        parts[current] = "\n".join(buf).strip()
    out = {"title": title, "raw": text}
    for key in _DRAFT_SECTIONS:
        out[key] = parts.get(key, "")
    return out


def build_prompt_v3(premise: dict, rules: tuple[str, ...] | list[str]) -> str:
    """Write first. Checklist later. No 21-section mould."""
    rules = list(rules)[:5]
    person = premise["person"]
    rule_block = "\n".join(f"- {r}" for r in rules)
    return f"""写一场约两千字的戏。不要按格子填。不要模仿任何一本书的故事、腔调或母题。

这个人：{person['name']}，{person['age']}岁，{person['job']}。在乎的是：{person['cares']}。
这件事（今天躲不掉）：{premise['event']}
怕失去：{premise['fear']}
题材：{premise['genre']}

最多五条，写的时候可以忘掉：
{rule_block}

硬限制：核心冲突不许写账、盘点、清算、对账、欠款、差钱。少用「像 / 如同 / 仿佛 / 好似」，宁可写看见什么。对白要像活人：允许废话、跑题、答非所问、被打断、说错再改，不要每句都推进情节。前三百字必须发生一件改不回去的事，不要先铺流程。结尾不要用「不是……而是……」点题。不要古代武侠江湖，不要维多利亚神秘学占卜。

输出，不要代码块：
# <短标题>
## 正文
<两千字左右，现代汉语，专名自拟>
## 自评
只写三句：哪一件事改不回去；哪一句对白是废话或答非所问；哪一句还在用比喻偷懒。没有就写没有。
"""


def build_prompt(genre: str, situation: str) -> str:
    craft = "\n".join(f"- {line}" for line in SHARED_CRAFT)
    avoid = "\n".join(f"- {line}" for line in _DISALLOWED_GENRE)
    return f"""写一场约两千字的戏。只学下面这些结构作法。不要模仿任何一本书的故事或腔调。

题材：{genre}
处境：{situation}

作法：
{craft}

禁区：
{avoid}
- 不要报身份说明书、不要上课、不要主题金句。
- 眼睛跟当场那个人。热切在一件具体的事上，不要靠旁白降温。
- 嘴上要的和真正缺的必须打架，用办事看见，不要剖心独白。
- 先给一个像翻了的假面，再破掉。读完人欠着什么。

输出格式，不要包代码块：
# <短标题>
## {_HEADING_PROSE}
<两千字左右的小说正文，现代汉语，专名自拟>
## {_HEADING_EVAL}
逐条对照上面的作法，每条点出正文里的哪一句做到了；没做到就写没做到。不要空夸。
"""


def parse_sample(raw: str) -> dict[str, str]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()
    parts: dict[str, str] = {}
    current = None
    buf: list[str] = []
    title = ""
    for line in text.splitlines():
        if line.startswith("# ") and current is None and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            if current is not None:
                parts[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        parts[current] = "\n".join(buf).strip()
    return {
        "title": title,
        "prose": parts.get(_HEADING_PROSE, ""),
        "self_eval": parts.get(_HEADING_EVAL, ""),
        "raw": text,
    }


def assert_no_banned(text: str) -> None:
    hits = [t for t in BANNED_TOKENS if t in (text or "")]
    if hits:
        raise ValueError(f"banned tokens leaked: {hits}")


def write_sample(
    dest: Path,
    *,
    genre: str,
    situation: str,
    prose: str,
    self_eval: str,
    calls: int,
    tokens: int,
    provider: str,
    title: str = "",
) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    heading = title or dest.stem
    body = f"""# {heading}

> **不作任何闸的证据。** 不进 Surreal，不上现网，不 overlay 已删的书。作者读完说像/不像即可。评测侧产物。

- 题材：{genre}
- 处境：{situation}
- 通道：{provider}
- 调用：{calls} 次
- 粗估 token：{tokens}

## 正文

{prose.strip()}

## 自评

{self_eval.strip()}
"""
    dest.write_text(body, encoding="utf-8")
    return dest


def write_candidate(
    dest: Path,
    *,
    premise: dict,
    prose: str,
    title: str,
    provider: str,
    monitor_md: str = "",
) -> Path:
    """候选稿。没有自评段——上一轮的自评只是在复述检查项。"""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f"""# {title or dest.stem}

> **候选稿，等作者挑。** 不作任何闸的证据，不进 Surreal，不上现网。
> 下面的分布对照是只读监控，不是评分；离参照近不等于写得好。

- 题材：{premise['genre']}
- 抽签：{premise['id']}
- 通道：{provider}

## 正文

{prose.strip()}

{monitor_md.strip()}
""",
        encoding="utf-8",
    )
    return dest


def generate_candidates(
    *,
    premise: dict,
    complete_fn,
    demo_md: str,
    n: int = 3,
    out_dir: Path | None = None,
    round_tag: str = "v5",
    provider: str = "coding",
) -> list[dict]:
    """同一处境写 n 篇，交作者挑一篇。

    拒绝采样比规则约束有效得多：模型在自己的分布里采样，人来挑，
    挑出来的那篇连同落选的一篇存成偏好对（见 `scribe3.eval.prefs`）。
    每篇独立调用，互不看见彼此，避免第二篇往第一篇上靠。
    """
    from scribe3.eval.prose_check import check_prose, format_report

    out_dir = Path(out_dir) if out_dir else SAMPLES / round_tag
    prompt = build_prompt_v4(premise, demo_md=demo_md)
    out: list[dict] = []
    for i in range(1, n + 1):
        parsed = parse_sample(complete_fn(prompt))
        assert_no_banned(parsed["prose"])
        md_stub = f"## 正文\n\n{parsed['prose']}"
        report = check_prose(md_stub, premise)
        dest = write_candidate(
            out_dir / f"{round_tag}-{premise['id']}-c{i}.md",
            premise=premise,
            prose=parsed["prose"],
            title=parsed["title"],
            provider=provider,
            monitor_md=format_report(report),
        )
        out.append({"path": str(dest), "title": parsed["title"], "metrics": report["metrics"]})
    return out


def generate_sample(
    *,
    genre: str,
    situation: str,
    complete_fn,
    dest: Path | None = None,
    provider: str = "coding",
) -> dict:
    prompt = build_prompt(genre, situation)
    assert_no_banned(prompt)
    raw = complete_fn(prompt)
    parsed = parse_sample(raw)
    blob = (parsed["prose"] or "") + "\n" + (parsed["self_eval"] or "")
    if not parsed["prose"].strip():
        raise ValueError("sample missing 正文")
    if not parsed["self_eval"].strip():
        raise ValueError("sample missing 自评")
    assert_no_banned(blob)
    tokens = max(1, len(prompt + raw) // 2)
    out = dest or (SAMPLES / f"A1-{genre}.md")
    write_sample(
        out,
        genre=genre,
        situation=situation,
        prose=parsed["prose"],
        self_eval=parsed["self_eval"],
        calls=1,
        tokens=tokens,
        provider=provider,
        title=parsed["title"] or out.stem,
    )
    return {
        "path": str(out),
        "title": parsed["title"],
        "calls": 1,
        "tokens": tokens,
        "provider": provider,
        "chars": len(re.sub(r"\s+", "", parsed["prose"])),
    }


def main(argv: list[str] | None = None) -> dict:
    p = argparse.ArgumentParser()
    p.add_argument("--genre", default="当代职场")
    p.add_argument(
        "--situation",
        default="夜班盘点差了三百块，店长说账不平谁也别走。",
    )
    p.add_argument("--out", default="")
    p.add_argument("--provider", default="coding")
    args = p.parse_args(argv)
    if args.provider == "hermes":
        from scribe3.llm import hermes_complete

        def complete_fn(prompt: str) -> str:
            return hermes_complete(prompt, max_tokens=4096, temperature=0.7, timeout=180)

        provider = "hermes"
    else:
        raise SystemExit(
            "sample_scene default provider is coding; pass complete_fn in-process "
            "or --provider hermes only when you mean to spend tonglu tokens"
        )
    dest = Path(args.out) if args.out else SAMPLES / f"A1-{args.genre}.md"
    return generate_sample(
        genre=args.genre,
        situation=args.situation,
        complete_fn=complete_fn,
        dest=dest,
        provider=provider,
    )


if __name__ == "__main__":
    print(main())
