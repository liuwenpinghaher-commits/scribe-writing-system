"""Creative Context OS 的输出留痕合同；刻意不包含模型输出正文。"""
from __future__ import annotations

from datetime import datetime, timezone
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContextOutcomeTrace(BaseModel):
    """一次模型执行与其实际输入三元组的不可变窄留痕。"""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome_id: str
    request_id: str
    manifest_id: str
    actual_input_hash: str
    status: str
    provider: str | None = None
    model: str | None = None
    provider_request_id: str | None = None
    usage: dict[str, int | float] | None = None
    output_hash: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("manifest_id", "actual_input_hash", "output_hash")
    @classmethod
    def validate_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("摘要必须是 64 位 SHA-256 十六进制值")
        return value.lower()
