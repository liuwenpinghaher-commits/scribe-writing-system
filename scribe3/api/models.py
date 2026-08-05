"""HTTP/API Pydantic request models (split from app_impl).

Re-exported from ``scribe3.api.app_impl`` for stable monkeypatch/import paths.
"""
from __future__ import annotations

from typing import Any, Optional, List, Dict, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

# 写作附件上限（原在 app_impl；模型拆出后校验器仍引用，须在本模块定义）
_MAX_IMAGES = 6
_MAX_IMG_BYTES = 5 * 1024 * 1024


class SettingPutReq(BaseModel):
    value: object = None


class GatewayFilePutReq(BaseModel):
    id: str
    content: str
    base_sha256: str


class GatewayRestartReq(BaseModel):
    profile: str


class AIRunCreateReq(BaseModel):
    input: str
    instructions: str = ""
    session_id: str | None = None
    conversation_history: list[dict] | None = None
    previous_response_id: str | None = None
    # 章级阶段运行的会话隔离键。旧客户端缺省时保持作品级 runs 兼容行为。
    run_scope: str | None = Field(default=None, pattern=r"^[A-Za-z0-9:_-]{1,120}$")
    # Task 13:发起时的上下文绑定(可选)——供审批前重校验"旧 run 拿着过期焦点写入当前章"。
    # 缺省(存量/旧前端)→ 不记 origin binding,审批不被重校验拦截(现有行为零回归)。
    context_session_id: str | None = None
    context_revision: int | None = Field(default=None, ge=0)


class AIRunApprovalReq(BaseModel):
    approval_id: str | None = None
    choice: str | None = None
    decision: str | None = None
    message: str | None = None
    approved: bool | None = None
    # Task 13:审批当刻声明的上下文(前端从当前快照带上);approve_stale=用户看过"发起时/
    # 当前焦点"两卡后仍决定放行"无关的过期 run"的二次确认令牌。
    context_session_id: str | None = None
    context_revision: int | None = Field(default=None, ge=0)
    approve_stale: bool = False


class ContextSessionCreateReq(BaseModel):
    actor_id: str = "author"
    device_id: str = ""
    # work 可放 body(优先)或 ?work= query;创建后固化进 session 记录
    work: str | None = None
    # P0a:显式绑定某会话线程(切会话=重建 session 绑新线程);缺省=active 默认线程
    thread_id: str | None = None


class ForkThreadReq(BaseModel):
    title: str | None = None


class ThreadCreateReq(BaseModel):
    title: str | None = None


class ThreadPatchReq(BaseModel):
    title: str | None = None
    status: str | None = None


class MemoryPrefetchReq(BaseModel):
    thread_id: str | None = None
    query: str = ""
    k: int = Field(default=24, ge=1, le=200)


class MemoryCaptureTurnReq(BaseModel):
    thread_id: str | None = None
    event_id: str | None = None
    user: str = ""
    assistant: str = ""
    messages: list = Field(default_factory=list)


class MemoryFlushReq(BaseModel):
    thread_id: str | None = None
    reason: str = "manual"


class PendingClaimResolveReq(BaseModel):
    decision: str   # approve | reject
    valid_from: int = 1
    secret: bool = False


class WorkIn(BaseModel):
    title: str


class WorkPurgeReq(BaseModel):
    confirm_title: str


class NarrativeIn(BaseModel):
    narrative_position: int | None = None


class CausalRootIn(BaseModel):
    reason: str


class CausalLinkIn(BaseModel):
    source_event: str
    ctype: str = "enables"


class CharIn(BaseModel):
    name: str
    backstory: str | None = None
    backstory_secret: bool = False
    importance: str | None = None
    appearance: str | None = None
    personality_detail: str | None = None
    personality_tags: list[str] = []
    aliases: list[str] = []
    abilities: str | None = None
    weaknesses: list = []
    surface_goal: str | None = None
    deep_need: str | None = None
    internal_conflict: str | None = None
    fear: str | None = None
    first_appearance: int | None = None


class FactIn(BaseModel):
    entity: str
    attribute: str
    value: str
    valid_from: int = 1
    valid_to: int | None = None
    secret: bool = False
    leak_markers: list[str] = []


class SupersedeIn(BaseModel):
    entity_id: str
    attribute: str
    value: str
    since_chapter: int
    secret: bool = False


class ForgetIn(BaseModel):
    knower_id: str
    proposition_id: str
    until_chapter: int


class PromIn(BaseModel):
    text: str
    setup_chapter: int = 1
    promise_kind: str = "promise"
    # tier 三档兑现窗口:chapter(近场 +1..+3)/arc(卷级 +5..+15)/book(书级 payoff_max=None 永不超期)。
    # 可选:add 时缺省即 chapter;edit 时缺省即保留既有 tier(不发送则 update_promise 不动窗口/层级)。
    tier: str | None = None
    # 悬念存档答案(方案B任务21,rules/story-narrative.md:20):"悬念必须有文档记录的
    # 真实答案"。仅 tier∈{book,arc} 的长期悬念强制(见 add_prom 校验);chapter 级短期
    # 悬念本章内起落即兑现,不强制,向后兼容不传此字段的既有调用方。
    resolution: str | None = None


class AdvanceIn(BaseModel):
    payoff_chapter: int


class ClueIn(BaseModel):
    note: str
    chapter: int


class RuleIn(BaseModel):
    name: str
    category: str = "magic"
    source: str | None = None
    capabilities: list = []
    cost: str | None = None
    limitations: list = []
    exceptions: list = []
    scope: str = "global"
    established_chapter: int | None = None
    note: str | None = None


class MotifIn(BaseModel):
    name: str
    theme: str = ""
    echoes: str = ""
    unfolding: str = ""
    echo_terms: list[str] | None = None
    phase: str | None = None
    tier: str | None = None
    scope: str | None = None


class MaterialIn(BaseModel):
    title: str
    body: str | None = None
    kind: str = "note"
    tags: list[str] = []
    source: str | None = None
    ref_tags: list[str] = []
    summary: str | None = None
    pinned: bool = False
    origin: str | None = None  # 兼容旧请求；作者 REST 创建由服务端强制为 manual


class MaterialPatch(BaseModel):
    title: str | None = None
    body: str | None = None
    kind: str | None = None
    tags: list[str] | None = None
    source: str | None = None
    ref_tags: list[str] | None = None
    summary: str | None = None
    pinned: bool | None = None
    archived: bool | None = None


class SessionClipIn(BaseModel):
    """作者选区/会话摘录。仅 snippet|note；source 可空(服务端补会话来源)。"""
    body: str
    title: str | None = None
    kind: str = "snippet"
    source: str | None = None
    scope_label: str | None = None
    chapter_seq: int | None = None
    origin_label: str | None = None
    summary: str | None = None
    ref_tags: list[str] | None = None


class ImportCommitReq(BaseModel):
    items: list[dict]


class MaterialReferenceIn(BaseModel):
    chapter: int = Field(ge=1)
    dimension: str | None = None
    reason: str | None = None


class IntentIn(BaseModel):
    reader_feeling: str = ""
    emotional_arc: str = ""
    red_lines: str = ""
    overdue_threshold: int | None = None
    total_word_goal: int | None = None   # 整稿目标字数;None → 前端回退默认 100000
    daily_word_goal: int | None = None   # 每日目标字数;None → 不显示每日进度


class IntentGoalsIn(BaseModel):
    """工程配额-only:整稿/每日字数目标、逾期阈值。禁止叙事北极星字段。"""
    total_word_goal: int | None = None
    daily_word_goal: int | None = None
    overdue_threshold: int | None = None


class ImageModel(BaseModel):
    data: str
    type: str

    @field_validator("type")
    @classmethod
    def _mime_ok(cls, v: str) -> str:
        if v not in _ALLOWED_MIME:
            raise ValueError(f"unsupported mime: {v}")
        return v

    @field_validator("data")
    @classmethod
    def _size_ok(cls, v: str) -> str:
        import base64
        try:
            raw = base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("invalid base64")
        if len(raw) > _MAX_IMG_BYTES:
            raise ValueError("image too large")
        return v


class ChatWriteReq(BaseModel):
    msg: str
    chapter: int = 1
    focalizer: str = ""
    images: list[ImageModel] = []
    seed_words: list[str] = []   # 浸泡产出的情绪种子词(由前端可选传入),注入写作 prompt
    phase: str = ""              # 阶段角色(Phase0-BE2):plan|draft|final;空=现状不变
    short_mode: bool = False     # 方案B任务16:短篇模式——跳过 build_craft_block 的
                                  # ENGINES["restraint"](留白/克制)注入
    # Task 4:上下文绑定字段一律 optional——契约不硬断存量调用方(1270 项测试/旧前端/
    # loop/pilot)。强制校验挂 SCRIBE3_CONTEXT_SNAPSHOT_V1:开关开 + 字段缺失/过期 → 4xx;
    # 开关关(默认)→ 完全忽略,行为不变。见 context_service.ContextService.enforce。
    context_session_id: str | None = None
    context_revision: int | None = Field(default=None, ge=0)
    context_hash: str | None = Field(default=None, min_length=64, max_length=64)
    thread_id: str | None = None   # Task 6:主编线程归属(一 work 一连续线程)
    focus: dict | None = None      # Task 6:本轮焦点标签(切焦点不切线程,焦点只作每轮标签)

    @field_validator("images")
    @classmethod
    def _count_ok(cls, v: list) -> list:
        if len(v) > _MAX_IMAGES:
            raise ValueError(f"too many images (max {_MAX_IMAGES})")
        return v


class LoopChapterReq(BaseModel):
    chapter: int
    focalizer: str = ""
    msg: str = ""            # 可选驱动语;默认"按简报写第N章正文"
    phase: str = "final"
    short_mode: bool = False


class ChapterCreateReq(BaseModel):
    title: str | None = None
    volume: str | None = None


class ChapterArchiveReq(BaseModel):
    reason: str | None = None


class RestoreVersionReq(BaseModel):
    """从 chapter_version 恢复正文,或直接用 prose 覆盖(前端已取过版本全文时)。"""
    version_id: str | None = None
    prose: str | None = None
    label: str = "从存档恢复"
    # 恢复历史稿默认仍重抽知识(与当前正文对齐);仅运维逃生可关。
    reingest: bool = True


class ReorderReq(BaseModel):
    volume: str | None = None   # 目标卷裸 id;None = 未分卷区
    order: list[int]            # 该卷内章 seq 的新顺序(全量)


class ChapterMetaReq(BaseModel):
    synopsis: str | None = None
    volume: str | None = None   # 卷裸 id 或 None(置未分卷)
    label: str | None = None
    title: str | None = None
    beats: list | None = None   # 节拍:[{text, done?}, ...](Phase0-BE2 四阶段)
    scene_truth: str | None = None          # 场景真相(全知)
    involved_characters: list | None = None # 涉及角色 id
    deductions: list | None = None          # [{character_id, character_name, prose}]
    purpose_text: str | None = None         # 北极星任务6:一句话章节目的
    deltas: list | None = None              # 北极星任务6:delta 清单(登记时校验+预演)

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value):
        if value is None:
            return value
        allowed = {"draft", "revise", "done", "idea", "beat"}
        if value not in allowed:
            raise ValueError("label 必须是 draft、revise、done、idea 或 beat")
        return value


class DeductionGroundingReq(BaseModel):
    candidate: str
    character_id: str = ""


class VolumeReq(BaseModel):
    title: str = ""
    sort_order: int = 0
    intro: str | None = None
    color: str | None = None


class VolumePatchReq(BaseModel):
    title: str | None = None
    sort_order: int | None = None
    intro: str | None = None
    color: str | None = None


class SaveChapterReq(BaseModel):
    seq: int
    prose: str
    title: str = ""
    focalizer: str | None = None
    # 工艺门闩逃生:工具/测试/明确跳过;默认受 SCRIBE3_CRAFT_GATE 约束
    skip_craft_gate: bool = False
    # 定稿门闩(门A/KR1):blocking 默认禁落 final;显式危险草稿旁路(默认关)
    danger_draft: bool = False
    # 测试/工具逃生;生产勿开。默认受 SCRIBE3_FINALIZE_GATE 约束
    skip_finalize_gate: bool = False


class CheckpointReq(BaseModel):
    prose: str
    label: str = ""
    kind: str = "checkpoint"   # checkpoint | final
    qc: dict = {}


class CheckReq(BaseModel):
    prose: str
    focalizer: str = ""
    short_mode: bool = False  # 方案B任务16:短篇模式——透传给 aggregate_ai_grade,


class PostCheckReq(BaseModel):
    prose: str
    focalizer: str = ""
    brief: str = ""
    short_mode: bool = False  # 方案B任务16:短篇模式——直写情绪+审判金句合法,


class DraftCheckReq(BaseModel):
    prose: str
    focalizer: str = ""


class SaveDraftReq(BaseModel):
    prose: str
    summary: str = ""


class ImportChapterItem(BaseModel):
    seq: int
    prose: str


class ImportReq(BaseModel):
    chapters: list[ImportChapterItem]


class SelectChapterReq(BaseModel):
    chapter: int
    force: bool = False       # 非关键章硬要出候选(作者主权;默认拦,N 倍成本只花刀刃)
    msg: str = ""             # 可选驱动语补充


class SelectFinalizeReq(BaseModel):
    chapter: int
    version_id: str
    reason_axis: str = "其他"
    reason_text: str


class SelectLightReq(BaseModel):
    chapter: int
    msg: str = ""


class SelectLightPickReq(BaseModel):
    chapter: int
    version_id: str | None = None
    strategy: str | None = None


class PilotStepReq(BaseModel):
    seq: int
    mode: str = "manual"     # manual | run(run 由 /pilot/run 循环使用)
    steer: str = ""          # 追加/更新作者意图(写入 pilot_steer)


class IdeaIn(BaseModel):
    text: str


class IdeaResolveReq(BaseModel):
    id: str


class PilotDismissReq(BaseModel):
    seq: int


class PilotApproveReq(BaseModel):
    seq: int
    expect_state: str = ""   # 审查 P1-1:知情背书——前端携带条目状态,错位 409 防误触终选


class PilotRunReq(BaseModel):
    start_seq: int
    until_seq: int

