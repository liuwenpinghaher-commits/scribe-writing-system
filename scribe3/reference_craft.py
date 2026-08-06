"""把作者批准的参考指纹编译为生成可用、不可仿写的技法摘要。"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from scribe3.context_models import ContextSource
from scribe3.quality.store import QualityStore, ReferenceFingerprintRecord


_UNSAFE_MECHANISM = re.compile(
    r"(?:模仿|仿写|复刻|照搬|复制|套用|原句|句式|角色名|专名|书名|地名|人名)",
)
_QUOTED_TEXT = re.compile(r"[《》〈〉\"“”‘’]")
_MAX_MECHANISM_CHARS = 140


@dataclass(frozen=True)
class ReferenceCraftBrief:
    """安全投影不保留作品名、原文、证据或不可复制项。"""

    fingerprint_id: str
    revision: int
    mechanism_ids: tuple[str, ...]
    text: str

    def context_source(self, work: str) -> ContextSource:
        return ContextSource(
            source_id=f"reference_fingerprint:{self.fingerprint_id}",
            source_kind="reference_craft",
            work=work,
            revision=f"reference-craft.v1:{self.revision}",
            content_digest=sha256(self.text.encode("utf-8")).hexdigest(),
        )


def _safe_mechanisms(
    record: ReferenceFingerprintRecord, *, reference_title: str = "",
) -> tuple[str, ...]:
    raw = record.fingerprint.get("transferable_mechanisms") or []
    prohibited = {
        str(value).strip()
        for value in (record.fingerprint.get("non_copyable_elements") or [])
        if isinstance(value, str) and len(value.strip()) >= 2
    }
    if reference_title.strip():
        prohibited.add(reference_title.strip())
    approved: list[str] = []
    for value in raw:
        if not isinstance(value, str):
            continue
        mechanism = " ".join(value.split()).strip()
        if not mechanism or len(mechanism) > _MAX_MECHANISM_CHARS:
            continue
        if _UNSAFE_MECHANISM.search(mechanism) or _QUOTED_TEXT.search(mechanism):
            continue
        if any(term in mechanism for term in prohibited):
            continue
        if mechanism not in approved:
            approved.append(mechanism)
    return tuple(approved)


def selected_reference_work_ids_from_contract(
    store, work: str,
) -> frozenset[str] | None:
    """从当前作品**最新已批准**质量合同读取 reference_targets 绑定。

    - ``None``：无已批准合同，或合同未配置任何 reference_targets → 写路径注入
      **全部**已批准标尺（可测默认）。
    - ``frozenset``：仅注入 targets 中出现的 ``reference_work_id``（与已批准指纹
      求交后可能为空 → 不注入）。
    """
    quality = QualityStore(store)
    rows = store._query(
        "SELECT contract_id, revision FROM quality_contract_revision "
        "WHERE work=$work AND approved=true ORDER BY revision DESC LIMIT 1",
        {"work": work},
    )
    if not rows:
        return None
    try:
        contract = quality.get_contract(
            str(rows[0]["contract_id"]), int(rows[0]["revision"]),
        )
    except (ValueError, TypeError, KeyError):
        return None
    targets = tuple(contract.reference_targets or ())
    if not targets:
        return None
    ids = {
        str(t.reference_work_id).strip()
        for t in targets
        if getattr(t, "reference_work_id", None) and str(t.reference_work_id).strip()
    }
    return frozenset(ids) if ids else frozenset()


def approved_craft_briefs(
    store,
    work: str,
    *,
    reference_work_ids: frozenset[str] | None = None,
) -> tuple[ReferenceCraftBrief, ...]:
    """只投影当前作品最新且已批准的指纹；无批准即不注入。

    ``reference_work_ids`` 为 ``None`` 时不额外过滤；为集合时仅保留 id 命中的标尺。
    """
    quality = QualityStore(store)
    records = quality.approved_reference_fingerprints(work)
    if reference_work_ids is not None:
        records = tuple(
            r for r in records if r.reference_work_id in reference_work_ids
        )
    titles = quality.reference_titles(work)
    briefs: list[ReferenceCraftBrief] = []
    for record in records:
        mechanisms = _safe_mechanisms(
            record, reference_title=titles.get(record.reference_work_id, ""),
        )
        if not mechanisms:
            continue
        mechanism_ids = tuple(
            sha256(f"{record.fingerprint_id}:{index}:{mechanism}".encode("utf-8")).hexdigest()[:16]
            for index, mechanism in enumerate(mechanisms, start=1)
        )
        lines = [
            "\n\n## 经作者批准的参考技法（仅迁移方法，不得仿写）",
            "这些是抽象创作机制，不是故事事实；仅在当前作品中使用。",
        ]
        lines.extend(
            f"- 机制 {mechanism_id}: {mechanism}"
            for mechanism_id, mechanism in zip(mechanism_ids, mechanisms)
        )
        lines.append("- 红线：不得复用参考作品的角色名、专名、情节、措辞或句式；必须以本书正典、人物和冲突重新发明。")
        briefs.append(ReferenceCraftBrief(
            fingerprint_id=record.fingerprint_id,
            revision=record.revision,
            mechanism_ids=mechanism_ids,
            text="\n".join(lines),
        ))
    return tuple(briefs)


def craft_briefs_for_write(store, work: str) -> tuple[ReferenceCraftBrief, ...]:
    """写路径唯一入口：契约有 reference_targets 则只注选中标尺，否则全部已批准。"""
    selected = selected_reference_work_ids_from_contract(store, work)
    return approved_craft_briefs(store, work, reference_work_ids=selected)


def render_craft_briefs(briefs: tuple[ReferenceCraftBrief, ...]) -> str:
    """纯函数验收入口；生产路径逐条登记 source，以保留单指纹溯源。"""
    return "".join(brief.text for brief in briefs)
