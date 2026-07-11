"""Task 10 · 记忆的三时态投影与生命周期判定(纯逻辑,零 DB / 零重依赖)。

三时态(计划 Task 10 Step 3,逐条固定):
  · system_time    —— created_at / updated_at / invalid_at:系统何时记录、更正、失效。
  · story_time     —— valid_from / valid_to:事实在故事世界第几章成立(故事真值)。
  · knowledge_time —— known_from / known_to + focalizer:某聚焦角色何时【可以知道】;
                      真相成立 ≠ 角色知道,二者必须分开投影(限知红线)。
  · episodic 另有 observed_at:仅表示用户/主编何时说过,不代表内容为真——【不参与】可见性判定。

focalizer 是【投影参数】,不是 memory_item 存储字段(MVP 决策,理由见下):
  visible / resolve_temporal_view 的 focalizer 只决定"是否叠加限知视角"——
    focalizer=None → 全知 / 故事真值视角,只按 story_time 投影;
    focalizer 非空 → 在 story_time 之上【叠加】knowledge_time 门(该聚焦角色此刻能否知道)。
  记忆行本身不区分"这条 known 是关于谁的"(known_from/to 已表达"聚焦角色何时知道"),
  故不给 memory_item 加 focalizer 归属列——最小改动、不引未被测试消费的字段。

⚠⚠ I-2 限知红线守卫(严禁误用,后来者必读)⚠⚠
  focalizer=None 是【上帝 / 作者视角】——它【不】叠加 knowledge_time 门,故 known_from=20
  的"第20章才被揭示"的记忆,在第 5 章 focalizer=None 下【也会命中】(这是规格 Step 1 锁死的
  "focalizer=None → 故事真值"语义,不可改)。因此:
    · resolve_temporal_view(默认 focalizer=None)【绝不可】直接用作限知写作 prompt 的组装源——
      否则未来章节才被知道的记忆会剧透倒灌进早章,违限知保守红线;
    · 面向写作 prompt 的记忆检索【必须】走 memory_bm25 / memory_vector / memory_graph 通道
      (那里的读者/发现时间门 known_from/to 恒开、不看 focalizer,天然防剧透),或
      resolve_temporal_view 时【显式传入当前聚焦角色 focalizer】开启限知门。
  同一对 known_from/to 承载两种投影用途,不要混淆:
    · 检索管线(memory_bm25/vector/graph、store._memory_known_at)把它当【读者/发现时间·剧透门】,
      恒开、不接受 focalizer——保证任何检索都不倒灌未来揭示;
    · resolve_temporal_view / visible 把它当【可选的角色限知视角】——仅在传 focalizer 时才叠加。
  两处边界数值口径完全一致(半开区间,见下),差别只在"门是否恒开"。

章号语义统一为【半开区间】[from, to):from<=chapter 且 (to 为空或 to>chapter);
from/to 为空 = 该端无界(fail-open);chapter=None = 讨论模式,不做时态过滤。
本模块的边界口径与 store._memory_known_at 同源(后者已下沉委托到 known_at)。
"""
from __future__ import annotations

from typing import Any, Iterable

_ACTIVE = "active"


def _get(memory: Any, name: str):
    """记忆既可能是 DB 行 dict,也可能是带属性的对象——统一取字段。"""
    if isinstance(memory, dict):
        return memory.get(name)
    return getattr(memory, name, None)


def _within(frm, to, chapter) -> bool:
    """半开区间 [frm, to) 命中判定。chapter=None → 不过滤(fail-open)。
    story_time 与 knowledge_time 共用这一套边界语义。"""
    if chapter is None:
        return True
    if frm is not None and frm > chapter:
        return False
    if to is not None and to <= chapter:
        return False
    return True


def known_at(known_from, known_to, chapter) -> bool:
    """knowledge_time 门:聚焦角色在第 chapter 章能否知道该记忆。"""
    return _within(known_from, known_to, chapter)


def story_valid_at(valid_from, valid_to, chapter) -> bool:
    """story_time 门:该事实在第 chapter 章的故事世界是否成立(故事真值)。"""
    return _within(valid_from, valid_to, chapter)


def visible(memory, chapter, focalizer=None) -> bool:
    """(chapter, focalizer) 下该记忆是否可见:
    ① 只有 active 记忆可见——superseded / invalid 一律不可见(审计留库,检索与投影都排除);
    ② story_time 门恒生效(故事真值);
    ③ focalizer 非空时【叠加】knowledge_time 门(限知视角:真相成立 ≠ 角色知道)。

    ⚠ focalizer=None 是上帝/作者视角(不叠限知门)——严禁把它的结果直接喂给限知写作 prompt,
      会剧透倒灌未来揭示;写作 prompt 检索走 bm25/vector/graph 通道或显式传 focalizer(见模块顶注)。"""
    status = _get(memory, "status") or _ACTIVE
    if status != _ACTIVE:
        return False
    if not story_valid_at(_get(memory, "valid_from"), _get(memory, "valid_to"), chapter):
        return False
    if focalizer is not None and not known_at(
            _get(memory, "known_from"), _get(memory, "known_to"), chapter):
        return False
    return True


def resolve_temporal_view(memories: Iterable, chapter, focalizer=None) -> list:
    """把一批记忆按 (chapter, focalizer) 投影为可见子集(纯过滤,保持入参顺序)。

    ⚠ 默认 focalizer=None = 上帝/作者视角(不叠 knowledge_time 限知门)——此结果【不可】直接
      用作限知写作 prompt 的组装源(会把未来章节才被知道的记忆剧透进早章)。写作 prompt 检索
      须走 memory_bm25/vector/graph 通道(剧透门恒开)或此处显式传当前聚焦角色 focalizer。"""
    return [m for m in memories if visible(m, chapter, focalizer)]
