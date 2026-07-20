"""Creative Context OS 的代码内版本化策略注册表。"""
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from scribe3.context_models import ContextEnvelope


class ContextPolicy(BaseModel):
    """可审计的上下文注入策略。

    策略只在代码注册，不从请求体接受任意策略定义。这样任务类型到策略版本的
    映射是可复现的，也避免调用方把 reference 正文伪装成 canonical 输入。
    """

    model_config = ConfigDict(frozen=True)

    policy_key: str
    version: str
    task_kinds: tuple[
        Literal[
            "draft", "final", "grounding", "quality_chapter",
            "reference_fingerprint", "reference_compare",
        ], ...
    ]
    canonical_source_kinds: tuple[str, ...] = ("canonical",)
    forbidden_source_kinds: tuple[str, ...] = ()
    protocol_versions: tuple[tuple[str, str], ...] = ()

    def safe_payload(self) -> dict:
        """可持久化的策略快照；只有规则与版本，不含提示词或领域正文。"""
        return {
            "policy_key": self.policy_key,
            "version": self.version,
            "task_kinds": list(self.task_kinds),
            "canonical_source_kinds": list(self.canonical_source_kinds),
            "forbidden_source_kinds": list(self.forbidden_source_kinds),
            "protocol_versions": {
                key: value for key, value in self.protocol_versions
            },
        }

    @property
    def schema_hash(self) -> str:
        raw = json.dumps(
            self.safe_payload(), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def for_task(cls, task_kind: str) -> "ContextPolicy":
        try:
            return _TASK_POLICY_REGISTRY[task_kind]
        except KeyError as exc:
            raise ValueError(f"未知 creative context 任务类型: {task_kind}") from exc

    @classmethod
    def by_version(cls, version: str) -> "ContextPolicy":
        try:
            return _POLICY_VERSION_REGISTRY[version]
        except KeyError as exc:
            raise ValueError(f"未知 creative context 策略版本: {version}") from exc

    def validate_envelope(self, envelope: "ContextEnvelope") -> None:
        """拒绝把 reference 来源放进 canonical block 的伪装输入。"""
        for block in envelope.blocks:
            if block.name != "canonical":
                continue
            for source in block.sources:
                if source.source_kind not in self.canonical_source_kinds:
                    raise ValueError(
                        "reference 或其他非 canonical 来源不得冒充 canonical: "
                        f"{source.source_id} ({source.source_kind})"
                    )


GENERATION_V1 = ContextPolicy(
    policy_key="generation",
    version="generation.v1",
    task_kinds=("draft", "final"),
    forbidden_source_kinds=(
        "reference_work_text", "raw_reference_text", "model_inference",
    ),
    protocol_versions=(
        ("context_policy", "creative-context-policy.v2"),
        ("system_instructions", "scribe3-write-system.v1"),
        ("write_protocol", "scribe3-write-protocol.v1"),
        ("secret_guard", "scribe3-secret-guard.v1"),
    ),
)

GROUNDING_V1 = ContextPolicy(
    policy_key="grounding",
    version="grounding.v1",
    task_kinds=("grounding",),
    forbidden_source_kinds=(
        "reference_work_text", "raw_reference_text", "model_inference",
    ),
    protocol_versions=(("grounding_protocol", "scribe3-grounding-review.v1"),),
)

QUALITY_CHAPTER_V1 = ContextPolicy(
    policy_key="quality_chapter",
    version="quality-chapter.v1",
    task_kinds=("quality_chapter",),
    forbidden_source_kinds=(
        "reference_work_text", "raw_reference_text", "model_inference",
        "generation_prompt", "generation_reasoning",
    ),
    protocol_versions=(("quality_protocol", "scribe3-discipline-review.v1"),),
)

REFERENCE_FINGERPRINT_V1 = ContextPolicy(
    policy_key="reference_fingerprint",
    version="reference-fingerprint.v1",
    task_kinds=("reference_fingerprint",),
    canonical_source_kinds=(),
    forbidden_source_kinds=(
        "chapter_prose", "canonical", "generation_prompt",
        "generation_reasoning", "model_inference",
    ),
    protocol_versions=(("fingerprint_protocol", "scribe3-reference-fingerprint.v1"),),
)

REFERENCE_COMPARE_V1 = ContextPolicy(
    policy_key="reference_compare",
    version="reference-compare.v1",
    task_kinds=("reference_compare",),
    forbidden_source_kinds=(
        "reference_work_text", "raw_reference_text",
        "generation_prompt", "generation_reasoning", "model_inference",
    ),
    protocol_versions=(("compare_protocol", "scribe3-reference-compare.v1"),),
)

_POLICY_VERSION_REGISTRY: dict[str, ContextPolicy] = {
    GENERATION_V1.version: GENERATION_V1,
    GROUNDING_V1.version: GROUNDING_V1,
    QUALITY_CHAPTER_V1.version: QUALITY_CHAPTER_V1,
    REFERENCE_FINGERPRINT_V1.version: REFERENCE_FINGERPRINT_V1,
    REFERENCE_COMPARE_V1.version: REFERENCE_COMPARE_V1,
}
_TASK_POLICY_REGISTRY: dict[str, ContextPolicy] = {}
for _policy in _POLICY_VERSION_REGISTRY.values():
    for _task_kind in _policy.task_kinds:
        _TASK_POLICY_REGISTRY[_task_kind] = _policy
