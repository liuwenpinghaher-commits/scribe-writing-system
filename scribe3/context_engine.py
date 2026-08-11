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

    def __init__(
        self,
        store,
        retriever=None,
        *,
        retrieval_out: dict | None = None,
        token_budget: int | None = None,
        block_budgets: dict | None = None,
    ):
        # novel-first：显式传入 envelope 预算（None → context_budget flag 默认 10k）
        from scribe3.context_budget import resolve_assembler_budgets
        tb, bb = resolve_assembler_budgets(token_budget, block_budgets)
        self._assembler = ContextAssembler(
            store, retriever, token_budget=tb, block_budgets=bb,
        )
        self.token_budget = tb
        self.block_budgets = bb
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
        render: Callable[
            [ContextEnvelope],
            str | tuple[str, tuple["ContextSource", ...]],
        ],
    ) -> CreativeContextCompilation:
        """组装、裁决、渲染最终输入，然后一次性建立并持久 Manifest。"""
        from scribe3.context_models import ContextSource

        policy = ContextPolicy.for_task(request.task_kind)
        if request.policy_version != policy.version:
            raise ValueError("请求任务类型与策略版本不匹配")
        merged_forbidden = tuple(dict.fromkeys(
            policy.forbidden_source_kinds + request.forbidden_source_kinds
        ))
        request = request.model_copy(update={
            "forbidden_source_kinds": merged_forbidden,
        })
        envelope = self._assembler.assemble(
            snapshot,
            query,
            mode,
            retrieval_out=self._retrieval_out,
            forbidden_source_kinds=request.forbidden_source_kinds,
        )
        self._validate_request(request, snapshot, envelope)
        policy.validate_envelope(envelope)

        rendered = render(envelope)
        supplemental_sources: tuple[ContextSource, ...] = ()
        if (
            isinstance(rendered, tuple) and len(rendered) == 2
            and isinstance(rendered[0], str)
            and isinstance(rendered[1], tuple)
        ):
            rendered_input, supplemental_sources = rendered
        else:
            rendered_input = rendered
        if not isinstance(rendered_input, str):
            raise TypeError("render 必须返回字符串或 (字符串, supplemental_sources)")
        if not all(isinstance(source, ContextSource) for source in supplemental_sources):
            raise TypeError("supplemental_sources 必须全部是 ContextSource")
        if any(source.work != request.work for source in supplemental_sources):
            raise ValueError("supplemental source work 与请求不一致")
        forbidden_supplemental = sorted({
            source.source_kind for source in supplemental_sources
            if source.source_kind in request.forbidden_source_kinds
        })
        if forbidden_supplemental:
            raise ValueError(
                "supplemental source kind 被 Policy forbidden: "
                + ", ".join(forbidden_supplemental)
            )
        manifest = build_context_manifest(
            request, policy, envelope, rendered_input, supplemental_sources,
        )
        self._context_store.save_manifest(manifest)
        return CreativeContextCompilation(
            request=request,
            envelope=envelope,
            manifest=manifest,
            rendered_input=rendered_input,
        )


__all__ = ["CreativeContextCompilation", "CreativeContextEngine"]
