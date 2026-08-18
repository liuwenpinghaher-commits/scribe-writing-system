"""Final/write assembly: story constraints + ban list. Zero craft/PALETTE/quota."""
from __future__ import annotations

from typing import Any

BAN_LIST = (
    "章末升华/感悟收尾（「他知道」「他明白」「一切才刚刚开始」）。",
    "同类比喻连续两段出现。",
    "元叙述（「命运」「选择」「代价」不进叙述层，除非角色说出口）。",
    "复述排演的叙述原句（对话若已是声口对的原句可保留）。",
    "泄露禁止拆穿的事。",
)


def _field(contract: dict[str, Any], name: str) -> str:
    fields = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    node = fields.get(name) if isinstance(fields.get(name), dict) else {}
    return str(node.get("text") or "").strip()


def assemble_final_prompt(ctx: dict[str, Any]) -> str:
    """Shipped Final generator prompt. Draft is the sole blueprint."""
    from scribe3.playbook.prompts import final_generate

    contract = ctx.get("contract") or {}
    built = {
        "draft_text": ctx.get("draft_text") or (ctx.get("draft") or {}).get("text") or "",
        "goal_text": _field(contract, "goal"),
        "choice_text": _field(contract, "choice"),
        "decision_text": _field(contract, "decision"),
        "hook_text": _field(contract, "hook"),
        "cost_text": _field(contract, "cost"),
        "deduction_json": ctx.get("deduction_json") or ctx.get("deduction") or {},
        "forbidden_reveal": ctx.get("forbidden_reveal") or [],
        "prev_prose_tail": ctx.get("prev_prose_tail") or "",
        "voice_anchor_block": ctx.get("voice_anchor_block") or "",
        "codex_recall": ctx.get("codex_recall") or "",
    }
    return final_generate(built)


def assemble_ban_block() -> str:
    return "【禁止清单】\n" + "\n".join(f"- {x}" for x in BAN_LIST)
