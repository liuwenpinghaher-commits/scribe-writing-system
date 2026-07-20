"""Creative Context OS 的统一编译入口。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from scribe3.context_assembler import ContextAssembler
from scribe3.context_manifest import ContextManifest, build_context_manifest
from scribe3.context_models import ContextEnvelope, ContextRequest, ContextSnapshot
from scribe3.context_policy import ContextPolicy
from scribe3.context_store import ContextStore


@dataclass(frozen=True)
class CreativeContextCompilation:
    """一次统一编译的内存结果；正文只在当前调用内存中存在。"""

    request: ContextRequest
    envelope: ContextEnvelope
    manifest: ContextManifest
    rendered_input: str


class CreativeContextEngine:
    """复用既有 ``ContextAssembler`` 编译并持久化窄 Manifest。"""

    def __init__(self, store, retriever=None, *, retrieval_out: dict | None = None):
        self._assembler = ContextAssembler(store, retriever)
        self._context_store = ContextStore(store)
        self._retrieval_out = retrieval_out

    @staticmethod
    def _validate_request(
        request: ContextRequest,
        snapshot: ContextSnapshot,
        envelope: ContextEnvelope,
    ) -> None:
        if request.work != snapshot.work:
            raise ValueError("请求 work 与导航快照不一致")
        if request.navigation_snapshot_id != snapshot.navigation_id:
            raise ValueError("请求未绑定当前导航快照")

        blocks = {block.name: block for block in envelope.blocks}
        missing = [
            slot for slot in request.required_slots
            if slot not in blocks or not blocks[slot].text.strip()
        ]
        if missing:
            raise ValueError(f"必需 context slot 缺失: {', '.join(missing)}")

        forbidden = set(request.forbidden_source_kinds)
        leaked = sorted({
            source.source_kind
            for block in envelope.blocks
            for source in block.sources
            if source.source_kind in forbidden
        })
        if leaked:
            raise ValueError(f"禁用 context 来源仍在 envelope 中: {', '.join(leaked)}")

    def compile(
        self,
        request: ContextRequest,
        snapshot: ContextSnapshot,
        query: str,
        mode: str,
        render: Callable[[ContextEnvelope], str],
    ) -> CreativeContextCompilation:
        """组装、裁决、渲染最终输入，然后一次性建立并持久 Manifest。"""
        policy = ContextPolicy.for_task(request.task_kind)
        envelope = self._assembler.assemble(
            snapshot,
            query,
            mode,
            retrieval_out=self._retrieval_out,
            forbidden_source_kinds=request.forbidden_source_kinds,
        )
        self._validate_request(request, snapshot, envelope)
        policy.validate_envelope(envelope)

        rendered_input = render(envelope)
        if not isinstance(rendered_input, str):
            raise TypeError("render 必须返回最终 system instructions 字符串")
        manifest = build_context_manifest(request, policy, envelope, rendered_input)
        self._context_store.save_manifest(manifest)
        return CreativeContextCompilation(
            request=request,
            envelope=envelope,
            manifest=manifest,
            rendered_input=rendered_input,
        )


__all__ = ["CreativeContextCompilation", "CreativeContextEngine"]
