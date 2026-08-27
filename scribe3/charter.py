"""纲层契约：把卷纲从一段散文变成一份可核对的契约。

前五轮和《万界概率战争》25 章实测撞的是同一堵墙——纲层每一层都是自由文本，
层与层之间没有可验证的接口，模型没有「这一卷该长出什么」的约束，只能原地打转。

契约要求每卷声明三件事，三件都能机器核：

  introduces     这一卷引入哪些新实体
  pays           收哪几条旧线
  knowledge_end  卷末主角必须知道 / 仍不能知道什么

第三条最硬，也最关键：它用限知帧核对，既守红线（「不让柳岸青看见场核坐标」
这种要求第一次变成可自动检查的东西），又让下一卷的章级生成有新起点。

本模块只读 store 的公开方法，不碰 `_query` / `_execute_write`（分层锁）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from scribe3.ontology import canon_oid

# 新鲜度阈值。来自《万界概率战争》实测分段：11-15 章 8.0、16-20 章 2.0、21-25 章 4.0，
# 而卷一开头是 7 个。5.0 是「不倒退回打转」的线，不是文笔判断。
MIN_NEW_ENTITIES_PER_10CH = 5.0

# 关键词集中度**不做门禁**，只作报告信息。
#
# 原本想拿它当判据（25 章时「开-3」占 33% 看着很像打转的证据），实测校准后废掉了：
# 人写的种子设定里「自己」占 62%，模型生成段「柳岸」占 50-70%——**人写和机器写没有区分度**。
# 主角名和核心概念高频出现是长篇的正常形态，不是打转。当时那个 33% 是在人工挑选的
# 实词表下算的，换成自动 top-keyword 就不成立了。
#
# 留一个宽松的报告线，只用来在报告里提一句，不参与 ok 判定。
KEYWORD_SHARE_NOTE = 0.75

#: 只有这三个前缀算「设定长出来的东西」。
#: `plant_promise` 每埋一条线就建一条 `entity_id=promise:xxx` 的命题，id 条条都是新的——
#: 不滤掉，埋得越多新鲜度越高，这个指标就变成伏笔计数器了。
STORY_PREFIXES = ("role:", "place:", "org:")


#: `must_not_know` 每条只能写「那样东西的名字」，提示词要的是二到六字，这里留两字余量。
#: 超过就是写成了句子（「柳岸青看见场核坐标」这种），匹配会被主语和动词稀释，
#: 判不准也判不了——把契约的毛病报回去，别去猜内容对不对。
MAX_FORBID_NAME_LEN = 8


def required_introduces(span_chapters: int) -> int:
    """一卷该点名引入几个新实体。

    必须和 `MIN_NEW_ENTITIES_PER_10CH` 同源。实测教训：契约只要求 3 个/卷、
    判据却按 5 个/10 章（20 章卷 = 10 个）算，模型严格照契约办事——
    点名的三个都引入了，此外一个不多给，于是每卷稳定不合格。
    **契约是地板，模型不会主动超过它；地板定低了，判据再高也没用。**
    """
    return max(3, round(span_chapters / 10 * MIN_NEW_ENTITIES_PER_10CH))


def story_entities(facts) -> set[str]:
    """命题里属于设定本体的实体，排除系统自建的账目命题。"""
    return {f.entity_id for f in facts
            if str(getattr(f, "entity_id", "")).startswith(STORY_PREFIXES)}


class CharterError(ValueError):
    """契约结构不合法。"""


def normalize_charter(raw: Any) -> dict:
    """把模型/人给的契约收成规范结构，缺字段补空，多字段丢掉。

    宽进严出：允许字符串 JSON、允许 introduces 写成裸字符串列表，
    但出口一定是固定形状，下游不用再做防御。
    """
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return _empty_charter()
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as e:
            raise CharterError(f"契约不是合法 JSON：{e}") from e
    if raw is None:
        return _empty_charter()
    if not isinstance(raw, dict):
        raise CharterError(f"契约须是对象，得到 {type(raw).__name__}")

    out = _empty_charter()
    out["duty"] = _strip_echoed_prompt(str(raw.get("duty") or "").strip())

    # oid 就地归位。契约里写 `loc:忘川驿`、章节落库写 `place:忘川驿`，
    # 对账就会判「说要引入却没出现」——东西明明引入了。归不了的保留原样，
    # 交给 `validate_charter` 报出来，不静默丢掉一条引入要求。
    for item in raw.get("introduces") or []:
        if isinstance(item, str):
            oid, why = item.strip(), ""
        elif isinstance(item, dict):
            oid = str(item.get("oid") or item.get("id") or item.get("name") or "").strip()
            why = str(item.get("why") or "").strip()
        else:
            continue
        if oid:
            out["introduces"].append({"oid": canon_oid(oid) or oid, "why": why})

    for item in raw.get("pays") or []:
        text = item.strip() if isinstance(item, str) else str((item or {}).get("text") or "").strip()
        if text:
            out["pays"].append(text)

    ke = raw.get("knowledge_end") or {}
    if isinstance(ke, dict):
        for slot in ("must_know", "must_not_know"):
            for item in ke.get(slot) or []:
                entry = _norm_knowledge_entry(item)
                if entry:
                    out["knowledge_end"][slot].append(entry)

    rng = raw.get("chapter_range")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        try:
            out["chapter_range"] = [int(rng[0]), int(rng[1])]
        except (TypeError, ValueError):
            pass
    return out


# 模型常把字段说明原样抄进值里（实测 10 卷全部以「这一卷要办的那一件事：」开头）。
# 提示词里已经说了不要，这里再兜一层——比每次去调提示词稳。
_ECHOED_PREFIXES = ("这一卷要办的那一件事：", "这一卷要办的那一件事:",
                    "这一卷要办的事：", "要办的那一件事：", "duty：", "duty:")


def _strip_echoed_prompt(text: str) -> str:
    for p in _ECHOED_PREFIXES:
        if text.startswith(p):
            return text[len(p):].strip()
    return text


def _norm_knowledge_entry(item: Any) -> dict | None:
    """知情终态的一条：`key` 是拿去比对属性名的短名，`what` 是给人看的描述。

    旧格式（纯字符串）仍收，`key` 留空、退回模糊匹配——那条路误报率高，
    只用来读旧库，新立的纲一律带 key。
    """
    if isinstance(item, str):
        text = item.strip()
        return {"key": "", "what": text} if text else None
    if isinstance(item, dict):
        key = str(item.get("key") or "").strip()
        what = str(item.get("what") or item.get("text") or "").strip()
        if key or what:
            return {"key": key, "what": what or key}
    return None


def _empty_charter() -> dict:
    return {"duty": "", "introduces": [], "pays": [],
            "knowledge_end": {"must_know": [], "must_not_know": []},
            "chapter_range": None}


def validate_charter(charter: dict, *, strict: bool = True) -> list[str]:
    """返回问题清单，空列表 = 合格。strict=False 只查结构不查内容强度。"""
    c = normalize_charter(charter)
    problems: list[str] = []
    if not c["duty"]:
        problems.append("没写这一卷要办的那一件事（duty）")
    if not strict:
        return problems
    rng = c["chapter_range"]
    span = (int(rng[1]) - int(rng[0]) + 1) if rng else 20
    need = required_introduces(span)
    if len(c["introduces"]) < need:
        problems.append(
            f"这一卷 {span} 章，只引入 {len(c['introduces'])} 个新实体，少于 {need} 个。"
            f"判据是每 10 章 ≥{MIN_NEW_ENTITIES_PER_10CH} 个，契约点名少于这个数，"
            "模型就照少的办——实测每卷稳定不合格")
    for slot in ("must_know", "must_not_know"):
        nokey = [e["what"] for e in c["knowledge_end"][slot] if not e["key"]]
        if nokey:
            problems.append(
                f"{slot} 这几条没给 key，核对只能退回模糊匹配（误报率高）："
                + "、".join(x[:20] for x in nokey))
        longkey = [e["key"] for e in c["knowledge_end"][slot]
                   if e["key"] and len(e["key"]) > MAX_FORBID_NAME_LEN]
        if longkey:
            problems.append(f"{slot} 的 key 要是二到四字的属性名，这几条太长：{'、'.join(longkey)}")
    strays = [i["oid"] for i in c["introduces"] if canon_oid(i["oid"]) is None]
    if strays:
        problems.append(f"这些 oid 的前缀不在本体里（只认 role/place/org）：{'、'.join(strays)}")
    if not c["pays"]:
        problems.append("一条旧线都不收，卷与卷之间不成账")
    if not c["knowledge_end"]["must_know"] and not c["knowledge_end"]["must_not_know"]:
        problems.append("没写卷末知情终态，下一卷拿不到新起点")
    return problems


@dataclass
class CharterAudit:
    """契约核对结果。declared 是纲说的，actual 是库里真有的。"""

    volume_id: str
    chapter_range: tuple[int, int]
    introduces_declared: list[str] = field(default_factory=list)
    introduces_actual: list[str] = field(default_factory=list)
    introduces_missing: list[str] = field(default_factory=list)
    pays_declared: list[str] = field(default_factory=list)
    #: 纲说要收几条，和这一卷实际收掉的更早埋的线数。文本对不上不算错，数目不够才算。
    pays_expected: int = 0
    cross_volume_payoffs: int = 0
    must_know_missing: list[str] = field(default_factory=list)
    must_not_know_violated: list[str] = field(default_factory=list)
    #: 只在命题内容里撞见、属性名没撞上。可能是叙述里提了一嘴，也可能真漏了，交给人看。
    must_not_know_suspect: list[str] = field(default_factory=list)
    #: 契约把它写成了句子而不是名字，判不了。是契约的毛病，不是内容的毛病。
    must_not_know_unusable: list[str] = field(default_factory=list)
    new_entities_per_10ch: float = 0.0
    top_keyword: str = ""
    top_keyword_share: float = 0.0

    @property
    def red_line_broken(self) -> bool:
        """声明主角不该知道、实际却知道了。这是红线，比其他项严重。"""
        return bool(self.must_not_know_violated)

    @property
    def pays_short(self) -> int:
        """还差几条跨卷收线。"""
        return max(0, self.pays_expected - self.cross_volume_payoffs)

    @property
    def ok(self) -> bool:
        """关键词集中度不参与判定，理由见 KEYWORD_SHARE_NOTE 上方注释。"""
        return not (self.introduces_missing or self.pays_short
                    or self.must_know_missing or self.must_not_know_violated
                    or self.new_entities_per_10ch < MIN_NEW_ENTITIES_PER_10CH)

    def report(self) -> str:
        lines = [f"卷 {self.volume_id}（第 {self.chapter_range[0]}-{self.chapter_range[1]} 章）"]
        if self.red_line_broken:
            lines.append("  ✗ 红线：声明不该知道，实际知道了 —— "
                         + "；".join(self.must_not_know_violated))
        if self.must_not_know_suspect:
            lines.append("  ? 疑似：只在命题内容里提到，属性名没有，人看一眼 —— "
                         + "；".join(self.must_not_know_suspect))
        if self.must_not_know_unusable:
            lines.append("  ! 契约这几条写成了句子，判不了红线，改成那样东西的名字 —— "
                         + "；".join(self.must_not_know_unusable))
        if self.introduces_missing:
            lines.append(f"  ✗ 说要引入却没出现：{'、'.join(self.introduces_missing)}")
        if self.pays_short:
            lines.append(f"  ✗ 说要收 {self.pays_expected} 条旧线，"
                         f"实际只收掉 {self.cross_volume_payoffs} 条上一卷之前埋的")
        if self.must_know_missing:
            lines.append(f"  ✗ 卷末该知道却不知道：{'、'.join(self.must_know_missing)}")
        if self.new_entities_per_10ch < MIN_NEW_ENTITIES_PER_10CH:
            lines.append(f"  ✗ 每 10 章只新增 {self.new_entities_per_10ch:.1f} 个实体"
                         f"（要 ≥{MIN_NEW_ENTITIES_PER_10CH}）—— 在打转")
        if self.top_keyword_share > KEYWORD_SHARE_NOTE:
            lines.append(f"  · 提一句：「{self.top_keyword}」出现在 "
                         f"{self.top_keyword_share:.0%} 的命题里（不计入判定）")
        if self.ok:
            lines.append("  ✓ 契约兑现")
        return "\n".join(lines)


def audit_volume(store, volume: dict, hero: str, *,
                 prior_entities: set[str] | None = None) -> CharterAudit:
    """核对一卷：纲说的 vs 库里真有的。

    prior_entities 是这一卷开始前已经出现过的实体，用来判断「新」。
    不传就按 chapter_range 起点之前的命题现算。
    """
    charter = normalize_charter(volume.get("charter"))
    vid = str(volume.get("id") or "")
    rng = charter["chapter_range"] or [1, 0]
    lo, hi = int(rng[0]), int(rng[1])

    audit = CharterAudit(volume_id=vid, chapter_range=(lo, hi))
    audit.introduces_declared = [i["oid"] for i in charter["introduces"]]
    audit.pays_declared = list(charter["pays"])
    if hi < lo:
        return audit

    facts_hi = list(store.facts_at(hi) or [])
    if prior_entities is None:
        prior_entities = story_entities(store.facts_at(lo - 1) or []) if lo > 1 else set()
    in_range = [f for f in facts_hi if lo <= f.valid_from <= hi]

    actual_entities = story_entities(in_range)
    audit.introduces_actual = sorted(actual_entities - prior_entities)
    audit.introduces_missing = [
        oid for oid in audit.introduces_declared
        if not any(oid == e or oid in e or e in oid for e in actual_entities)]

    audit.new_entities_per_10ch = (
        len(actual_entities - prior_entities) / max(hi - lo + 1, 1) * 10)
    audit.top_keyword, audit.top_keyword_share = _top_keyword(in_range)

    # 收线只数「收的是不是更早埋的线」，不比文本。
    #
    # 立纲发生在这些线存在之前，契约里的 pays 必然是模型编的措辞，
    # 跟库里真实的 promise 文本天生对不上——实测十卷全报「说要收却没收」，
    # 而真实收线率是 93%（256 条收了 238 条）。那是判据的错，不是书的错。
    # 卷与卷之间要成账，能客观算的是「这一卷收掉了几条上一卷之前埋的线」。
    audit.cross_volume_payoffs = _cross_volume_payoffs(store, lo, hi)
    audit.pays_expected = len(audit.pays_declared)

    try:
        from scribe3.knowledge import project_frame
        known = list(project_frame(store, hero, hi).facts)
    except Exception:
        known = []

    # 知情终态优先用 `key` 精确比对属性名。
    #
    # 契约里写的是人话，库里存的也是人话，拿长句互相模糊匹配两头都不准：
    # 实测 must_know 报缺失 11 条里 8 条是误报（库里有几乎同义的命题，
    # 只是措辞不同、实词重合不到一半），红线误报过六卷。
    # 带 key 的走精确匹配，不带 key 的（旧契约）才退回模糊，并标明结果不可靠。
    blob = [f"{f.attribute} {f.value}" for f in known]
    attrs = [f.attribute for f in known]

    for want in charter["knowledge_end"]["must_know"]:
        key, what = want["key"], want["what"]
        if key:
            if not any(key == a or _attr_names_forbidden(a, key) for a in attrs):
                audit.must_know_missing.append(what or key)
        elif not any(_loose_match(what, b) for b in blob):
            audit.must_know_missing.append(what)

    for forbid in charter["knowledge_end"]["must_not_know"]:
        key, what = forbid["key"], forbid["what"]
        if key:
            if any(key == a or _attr_names_forbidden(a, key) for a in attrs):
                audit.must_not_know_violated.append(what or key)
            elif any(_loose_match(key, b) for b in blob):
                audit.must_not_know_suspect.append(what or key)
            continue
        # 以下是旧契约的兜底路径。写成句子的判不了：匹配是双向的，
        # 属性名「清算名单」的实词全落在「柳岸青知道忘川驿的清算名单是否包含……」
        # 里就算命中，任何沾边的设定都被判成越界。输入不合格就报契约的毛病。
        if len(what) > MAX_FORBID_NAME_LEN:
            audit.must_not_know_unusable.append(what)
        elif any(_attr_names_forbidden(a, what) for a in attrs):
            audit.must_not_know_violated.append(what)
        elif any(_loose_match(what, b) for b in blob):
            audit.must_not_know_suspect.append(what)
    return audit


def _cross_volume_payoffs(store, lo: int, hi: int) -> int:
    """这一卷收掉了几条本卷开始之前埋的线。

    只数跨卷的。卷内埋卷内收是一章之内的小回环，不构成卷与卷之间的账。
    """
    n = 0
    for p in (store.list_promises() or []):
        pc, sc = p.get("payoff_chapter"), p.get("setup_chapter")
        if pc is None or sc is None:
            continue
        if str(p.get("status") or "").lower() == "open":
            continue
        if lo <= int(pc) <= hi and int(sc) < lo:
            n += 1
    return n


def _loose_match(needle: str, haystack: str) -> bool:
    """契约里写的是人话，库里存的也是人话，没法精确对。

    取 needle 里的实词做交集：过半命中就算兑现。宁可宽一点，
    严格匹配会把「场核坐标」和「坐标」判成两回事，反而逼人去凑词。
    """
    toks = [t for t in _tokens(needle) if len(t) >= 2]
    if not toks:
        return False
    hit = sum(1 for t in toks if t in haystack)
    return hit / len(toks) >= 0.5


def _attr_names_forbidden(attr: str, forbid: str) -> bool:
    """这个属性名说的是不是禁项本身。要求属性名的实词**全部**落在禁项里。

    过半不够。实测：属性名「坐标锁回」（实词「坐标」「锁回」）撞上禁项
    「柳岸青看见场核坐标」，只中「坐标」就算过半，六卷因此误报红线——
    而那条命题的内容是「双锁会不能借柳岸青开关位读取场核坐标」，
    恰恰说明他不知道。属性名是设定的标题，词少、每个都关键，缺一个就不是同一件事。
    """
    toks = [t for t in _tokens(attr) if len(t) >= 2]
    # 只有一个词的属性名太泛，判不了高置信。实测：属性名就叫「坐标」、
    # 内容是「不署名门拒绝输出场核坐标」，撞上禁项「柳岸青看见场核坐标」就报红线——
    # 而这句说的是拿不到。关键词匹配抓不到否定，这类只能降级成疑似交给人看。
    return len(toks) >= 2 and all(t in forbid for t in toks)


# 虚字：含这些字的 2-gram 不当关键词。用 2-gram 而不是 jieba，是因为小说自造词
# （「场核」「死光子」「开-3」）分词器切不准，而 2-gram 天然抓得到；代价是虚词噪声，
# 靠这张表滤掉。
_STOP_CHARS = set("的了在是和与及被把就都也还又要不有这那其之以为所能会可对从向到"
                  "由于而且或但则如若因让给过着们个上下里外前后中已经再只才更最很"
                  "一二三四五六七八九十")


def _tokens(text: str, *, drop_stop: bool = False) -> list[str]:
    """按非中文/字母数字切开，中文再切 2-gram。

    drop_stop=True 时丢掉含虚字的 gram——统计关键词集中度要用，
    否则「的事」「不相」这种会盖过真正的实词。松散匹配则要保留全部，
    因为那里比的是覆盖率不是显著性。
    """
    import re
    chunks = re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9\-]+", str(text))
    toks: list[str] = []
    for c in chunks:
        if re.match(r"[A-Za-z0-9\-]", c):
            toks.append(c.lower())
            continue
        grams = [c] if len(c) <= 2 else [c[i:i + 2] for i in range(len(c) - 1)]
        for g in grams:
            if drop_stop and any(ch in _STOP_CHARS for ch in g):
                continue
            toks.append(g)
    return toks


def _top_keyword(facts: list) -> tuple[str, float]:
    """最集中的那个词占多少命题。25 章时「开-3」占 33%，就是靠这个数看出打转的。"""
    if not facts:
        return "", 0.0
    import collections
    counter: collections.Counter = collections.Counter()
    for f in facts:
        seen = set()
        for tok in _tokens(f"{f.attribute} {f.value}", drop_stop=True):
            if len(tok) >= 2 and tok not in seen:
                seen.add(tok)
                counter[tok] += 1
    if not counter:
        return "", 0.0
    word, n = counter.most_common(1)[0]
    return word, n / len(facts)


def _bible(store) -> str:
    """给模型看的常量：规则、人物、势力。不含情节。"""
    out: list[str] = []
    for r in (store.list_world_rules() or []):
        out.append(f"- 规则《{r.get('name')}》：{r.get('capabilities') or ''}"
                   f"　代价：{str(r.get('cost') or '')[:60]}")
    for c in (store.characters() or []):
        t = getattr(c, "traits", None) or {}
        out.append(f"- 人物 {c.name}：要{str(t.get('surface_goal') or '')[:40]}"
                   f"　怕{str(t.get('fear') or '')[:40]}")
    for f in (store.list_factions() or []):
        out.append(f"- 势力 {f.get('name')}：{str(f.get('public_face') or '')[:50]}")
    return "\n".join(out)


def build_charter_prompt(store, n_volumes: int, total: int) -> str:
    """分卷立纲的提示词。判据只有一条：下一卷必须比上一卷长出新东西。"""
    intent = store.get_intent() or {}
    vols = store.list_volumes() or []
    outline = "\n".join(
        f"卷{v.get('sort_order')}《{v.get('title')}》：{str(v.get('intro') or '')[:80]}"
        for v in vols) or "（还没有卷）"
    used = sorted(story_entities(store.facts_at(99999) or []))
    span = max(1, round(total / max(n_volumes, 1)))
    need = required_introduces(span)

    return f"""你在给一本 {total} 章的长篇分卷立纲，不是写正文，也不是写章纲。

判据只有一条：**下一卷必须比上一卷长出新东西**。

有一次实测是这么砸的：只给了一卷卷纲就去生成 200 章，结果第 14 章起
每章新增实体恒为 0，25 章和 15 章是同一件事的变奏。根因是模型没有新的推进方向可用，
只能在既有元素上反复加细节。你要防的就是这个。

## 北极星
{intent.get('north_star') or ''}

## 红线（越过就是写坏了）
{intent.get('red_lines') or ''}

## 这本书的常量
{_bible(store)}

## 已有的卷
{outline}

## 已经用过的实体（新卷引入的必须不在这个名单里）
{'、'.join(used) or '（空）'}

---

交一个 JSON 对象，不要代码块标记，第一个字符就是 `{{`：

{{
  "volumes": [
    {{
      "sort_order": 1,
      "title": "卷名，三到六字",
      "duty": "这一卷要办的那一件事。一句话，要有具体的人和具体的阻碍。",
      "chapter_range": [起章, 止章],
      "introduces": [
        {{"oid": "role:新人名 / place:新地点 / org:新组织，前缀只能用这三个",
          "why": "这一卷为什么非要他不可"}}
      ],
      "pays": ["这一卷要收掉的、前面卷埋下的线，一句话说清收的是什么"],
      "knowledge_end": {{
        "must_know": [
          {{"key": "二到四字的属性名，会拿去和设定的属性名精确比对",
            "what": "卷末主角必须已经知道的事，一句话，给人看的"}}
        ],
        "must_not_know": [
          {{"key": "二到四字的属性名，比如「场核坐标」「帝真名」",
            "what": "为什么这一卷还不能让他知道"}}
        ]
      }}
    }}
  ]
}}

硬要求：

- 一共 {n_volumes} 卷，章号连续覆盖 1 到 {total}，不许有缺口或重叠。
- 每卷 `introduces` **至少 {need} 个新实体**（按每 10 章 {MIN_NEW_ENTITIES_PER_10CH:.0f} 个算，
  一卷 {span} 章），且 oid 不许出现在上面「已经用过的实体」里。
  这是全书能往前走的唯一保证——不引入新东西就是原地打转。
  实测过一次少给的后果：契约只点名 3 个，模型就正好只引入那 3 个，一个不多，
  整卷每 10 章新增 1.5 个，和没有卷纲时差不多。**你写几个，就只会有几个。**
  **前缀只能是 `role:` / `place:` / `org:`**，别的前缀系统认不出来、存进去也关联不上。
- 每卷 `pays` 至少一条，收的必须是前面卷埋下的线。第一卷可以收种子里立的。
  核对时数的是「这一卷收掉了几条本卷之前埋的线」，所以别把本卷刚埋的算进来。
- `knowledge_end` 两栏都要有，会被拿去和限知帧逐条对，写不实会被查出来。
- **`key` 必须是二到四字的属性名**，像「场核坐标」「炉主身份」「帝真名」。
  核对时拿它和设定的属性名精确比。写成句子就对不上——
  上一版全写成「柳岸青知道××」这样的长句，结果 must_know 误报八条、红线误报六卷。
  写这一卷相关设定的属性名时，也要用同一个 key，两边才对得上。
- `must_not_know` 里点名的东西要一直留在这一栏，直到该翻开的那一卷。
- 卷与卷之间要有升级关系：后一卷的处境必须是前一卷 `knowledge_end` 造成的，
  不能是同一处境换个说法。
- `duty` 直接写内容，不要把「这一卷要办的那一件事：」这句抄进去。
"""


def parse_charters(raw: str) -> list[dict]:
    """把模型返回解析成规范化的卷契约列表。"""
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j < 0:
        raise CharterError(f"没找到 JSON 对象，开头是：{text[:120]}")
    data = json.loads(text[i:j + 1])
    out = []
    for v in (data.get("volumes") or []):
        c = normalize_charter(v)
        c["sort_order"] = int(v.get("sort_order") or 0)
        c["title"] = str(v.get("title") or f"卷{c['sort_order']}")
        out.append(c)
    return out


def generate_charters(store, n_volumes: int, total: int, complete, *,
                      retries: int = 1) -> tuple[list[dict], list[str]]:
    """立纲并把 `validate_charter` 当门：不合格就把问题清单退给模型重写。

    没有这道门时，写成句子的 must_not_know 直接落了库，一直到逐卷对账才炸出来，
    而那时 200 章已经铺完了。立纲只花一次调用，在这儿拦住最便宜。

    `complete` 是 `(prompt) -> str`。返回 (契约, 仍未解决的问题)。
    """
    prompt = build_charter_prompt(store, n_volumes, total)
    charters: list[dict] = []
    problems: list[str] = []
    for attempt in range(retries + 1):
        charters = parse_charters(complete(prompt))
        if not charters:
            raise CharterError("模型没给出任何卷")
        problems = [f"卷{c['sort_order']}《{c['title']}》：{p}"
                    for c in charters for p in validate_charter(c)]
        if not problems or attempt == retries:
            break
        prompt = (build_charter_prompt(store, n_volumes, total)
                  + "\n\n## 上一版被打回，逐条改掉再交\n"
                  + "\n".join(f"- {p}" for p in problems)
                  + "\n\n只改这些问题，其余保持不变。")
    return charters, problems


def persist_charters(store, charters: list[dict], total: int) -> dict:
    """按 sort_order 落库：已有的卷更新契约，没有的新建。"""
    existing = {int(v.get("sort_order") or 0): v for v in (store.list_volumes() or [])}
    n_new = n_upd = 0
    for c in charters:
        so, title = c["sort_order"], c["title"]
        body = {k: c[k] for k in ("duty", "introduces", "pays",
                                  "knowledge_end", "chapter_range")}
        if so in existing:
            store.update_volume(existing[so]["id"], {"charter": body, "intro": c["duty"]})
            n_upd += 1
        else:
            vid = store.add_volume(title, sort_order=so, intro=c["duty"])
            store.update_volume(vid, {"charter": body})
            n_new += 1
    store.set_intent({"book_charter": {"total_chapters": total, "n_volumes": len(charters)}})
    return {"volumes": len(charters), "new": n_new, "updated": n_upd}


def freshness(store, lo: int, hi: int) -> dict:
    """不带契约也能算的两个数——25 章撞墙时看的就是这两个。"""
    facts = [f for f in (store.facts_at(hi) or []) if lo <= f.valid_from <= hi]
    prior = story_entities(store.facts_at(lo - 1) or []) if lo > 1 else set()
    new_ents = story_entities(facts) - prior
    word, share = _top_keyword(facts)
    return {"chapters": (lo, hi), "facts": len(facts),
            "new_entities": sorted(new_ents),
            "new_entities_per_10ch": len(new_ents) / max(hi - lo + 1, 1) * 10,
            "top_keyword": word, "top_keyword_share": share}
