"""统一上下文与记忆系统 · 类型合同层(Task 2)。

为什么单独一个纯模型文件:这些合同是后续所有环节的公共语言——
Task 3(SurrealDB CAS 存储)、Task 4(Context API)、Task 7(assembler)
都直接 import 这里的类型。保持零依赖(不 import store/llm),
任何一端都能安全引用而不引入循环。

核心不变量:
- ContextSnapshot 必须是"一份完整的语义状态"——focus/route/work 等字段
  齐备才允许构造,不存在"半份上下文"入库的可能。
- context_hash 是【快照身份指纹】:对除 captured_at(墙钟噪声)与 hash
  自身之外的全部字段取 SHA-256——session_id/navigation_id/revision 也
  参与,它们正是"这一份快照"身份的一部分。用途是把每次 LLM 调用/审批
  绑定到具体快照上做过期检测(Task 4 的 409 判定);它不是跨会话/
  跨导航的语义去重键——幂等去重靠 navigation_id(Task 3 的 UNIQUE 索引)。
- ContextSnapshot / ContextFocus 均 frozen(不可变):可变字段会让已算好
  的 hash 与实际内容脱节,击穿指纹合同;任何变化都必须走 model_copy
  产生新对象再重算 hash。
- 乐观并发:写入端携带 expected_revision,失配即抛 StaleContextError,
  由 Task 3 的 CAS 存储消费。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# 焦点类型与前端 DirectoryPane/DetailPane 现有 node/view 命名对齐,
# 新增类型必须同时评估 detail_route 路由与 assembler 的取数路径。
FocusType = Literal[
    "entry", "view", "chapter", "scene", "character", "fact", "event",
    "promise", "motif", "material", "review_issue", "selection",
]

# 与前端四阶段 tab + 演绎阶段对齐(见 ChapterStudio 的 phase 命名)。
PhaseName = Literal["outline", "beats", "deduce", "draft", "final"]
ContextTaskKind = Literal["draft", "final", "grounding", "quality_chapter"]


class ContextRequest(BaseModel):
    """一次创作上下文请求的纯意图合同。

    ``navigation_snapshot_id`` 只是产生请求时所见导航状态的身份引用；它绝不
    承载或复制导航快照正文。内容状态由后续组装器按 request 重新取数，避免把
    已过期的 UI 快照误当作可注入的故事事实。
    """

    model_config = ConfigDict(frozen=True)

    request_id: str
    task_kind: ContextTaskKind
    target_ref: str
    navigation_snapshot_id: str
    work: str
    chapter: int | None = None
    scene_key: str | None = None
    phase: PhaseName | None = None
    actor_role: str | None = None
    pov_character: str | None = None
    story_time_window: str | None = None
    knowledge_cutoff: str | None = None
    author_intent_ref: str | None = None
    quality_contract_revision: str | None = None
    required_slots: tuple[str, ...] = ()
    forbidden_source_kinds: tuple[str, ...] = ()
    budget_profile: str | None = None
    freshness_requirement: str | None = None
    policy_version: str = "generation.v1"


class ContextFocus(BaseModel):
    """用户此刻"看着什么"。type+id 唯一定位;label 不参与路由,但参与
    快照 hash——快照是历史定格,焦点改名后再看就是一份新快照。"""

    # frozen:焦点嵌在快照里,若可原地改 label/id,快照 hash 即失真
    model_config = ConfigDict(frozen=True)

    type: FocusType
    id: str
    label: str = ""
    # 焦点对象自身的版本(如事实卡的修订号),用于块级溯源时判断"过期引用"
    source_revision: str | None = None


class NavigationIntent(BaseModel):
    """前端每次导航发出的意图。expected_revision 携带客户端已知的最新
    revision,服务端 CAS 失配时拒绝——防止两个窗口互相覆盖上下文。"""

    navigation_id: str
    expected_revision: int
    entry: str
    # Pydantic v2 对可变默认值做每实例深拷贝,直接写 [] 是安全的
    directory_path: list[str] = []
    focus: ContextFocus
    detail_route: str
    chapter: int | None = None
    phase: PhaseName | None = None
    focalizer: str | None = None
    # 导航为何发生:决定 assembler 是否需要重算(如 restore 可走缓存)
    reason: Literal["entry", "item", "view", "phase", "focalizer", "restore", "explicit"]


class ContextSnapshot(BaseModel):
    """某一时刻的完整语义状态。不可变(frozen):任何变化都产生新 revision
    的新快照,而不是原地修改——这样主编线程/回放/审计都能引用一个与内容
    永远一致的身份指纹(context_hash)。"""

    # frozen:hash 在构造后固化,若字段可变,指纹与内容会悄悄脱节;
    # with_hash() 用 model_copy(update=...) 生成新实例,与 frozen 兼容
    model_config = ConfigDict(frozen=True)

    session_id: str
    work: str
    revision: int = Field(ge=0)
    thread_id: str
    entry: str
    # tuple 而非 list:frozen 只锁属性赋值,list 仍可原地 append 击穿 hash 合同;
    # Pydantic 自动把 list 输入转 tuple,mode="json" 序列化仍是 JSON 数组,黄金 hash 不变
    directory_path: tuple[str, ...]
    focus: ContextFocus
    detail_route: str
    chapter: int | None
    # 与 NavigationIntent 对齐用同一枚举:快照是要持久化的对象,垃圾 phase 不能入库
    phase: PhaseName | None
    focalizer: str | None
    previous_revision: int | None
    navigation_id: str
    captured_at: datetime
    context_hash: str

    def canonical_payload(self) -> dict:
        """身份指纹的规范载荷:除 captured_at(墙钟噪声)与 hash 自身(自指)
        外全部字段都参与——session_id/navigation_id/revision 正是身份的一部分。"""
        return self.model_dump(exclude={"captured_at", "context_hash"}, mode="json")

    def with_hash(self) -> "ContextSnapshot":
        """算身份指纹:供 LLM 调用/审批绑定做过期检测(Task 4 的 409 判定)。
        不是语义去重键——去重靠 navigation_id(Task 3 的 UNIQUE 索引)。"""
        # sort_keys + 紧凑分隔符 + 不转义中文:保证跨进程/跨版本序列化字节稳定
        raw = json.dumps(
            self.canonical_payload(),
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        )
        return self.model_copy(update={"context_hash": hashlib.sha256(raw.encode()).hexdigest()})


class ContextSource(BaseModel):
    """块级溯源的最小单元:envelope 里每一段文本都能回答"从哪来、
    有没有被限知遮蔽、为什么"。Task 7(assembler)/Task 8/14 消费。"""

    # renderer 必须在选入后回写 digest，故不能 frozen；开启赋值校验防止写回后被
    # 任意字符串篡改成伪造摘要。
    model_config = ConfigDict(validate_assignment=True)

    source_id: str
    source_kind: str
    work: str
    # 限知范式:被遮蔽的来源仍要留痕(masked=True + reason),而不是凭空消失
    masked: bool = False
    reason: str = ""
    revision: str | None = None
    # 仅记录实际选入该 block 的 _Item.text 的 SHA-256，不存正文；用于 manifest
    # 验证来源与实际提示词输入是否一致。None 表示尚未被 renderer 选入。
    content_digest: str | None = None

    @field_validator("content_digest")
    @classmethod
    def validate_content_digest(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("content_digest 必须是 64 位 SHA-256 十六进制摘要")
        return value.lower()


class ContextBlock(BaseModel):
    """envelope 的一个语义分区。name 是固定枚举——assembler 的预算分配、
    前端的折叠展示都按这八类走,不允许自造分区名。"""

    name: Literal[
        "focus", "global", "canonical", "recent",
        "procedural", "reference", "uncertainty", "provenance",
    ]
    text: str
    token_estimate: int = Field(ge=0)
    sources: list[ContextSource]


class ContextEnvelope(BaseModel):
    """一次组装的最终产物:快照 + 分块正文 + 被省略项。
    omitted 记录"预算内放不下/被限知排除"的条目,让裁剪可审计。"""

    snapshot: ContextSnapshot
    blocks: list[ContextBlock]
    total_token_estimate: int = Field(ge=0)
    omitted: list[dict]
    assembled_at: datetime
    # 由 Task 7 assembler 计算,规范化规则(哪些字段参与、如何序列化)届时定义
    envelope_hash: str


class StaleContextError(Exception):
    """CAS 失配:客户端以为的 revision(expected)落后于库里的(actual)。
    latest 可携带服务端最新快照摘要,方便前端直接对齐而不用再发一次读。"""

    # API 层(Task 4)映射 409 时直接透传的稳定错误码
    code = "stale_context"

    def __init__(self, expected: int, actual: int, latest: dict | None = None):
        self.expected = expected
        self.actual = actual
        self.latest = latest
        super().__init__(f"context revision 过期: expected={expected}, actual={actual}")
