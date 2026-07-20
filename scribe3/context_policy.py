"""Creative Context OS 的代码内版本化策略注册表。"""
from __future__ import annotations

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

    version: str
    task_kinds: tuple[Literal["draft", "final"], ...]
    canonical_source_kinds: tuple[str, ...] = ("canonical",)

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
    version="generation.v1",
    task_kinds=("draft", "final"),
)

_POLICY_VERSION_REGISTRY: dict[str, ContextPolicy] = {
    GENERATION_V1.version: GENERATION_V1,
}
_TASK_POLICY_REGISTRY: dict[str, ContextPolicy] = {
    task_kind: GENERATION_V1 for task_kind in GENERATION_V1.task_kinds
}
