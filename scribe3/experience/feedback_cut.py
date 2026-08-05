"""外部读感导入 + 可删段建议(不自动删文)。"""
from __future__ import annotations

import hashlib
import re
from typing import Any

# 章号: #3 或 第3章 或 ch3
_CH_RE = re.compile(
    r"^(?:#{1,3}\s*)?(?:第\s*(\d+)\s*章|ch(?:apter)?\s*(\d+)|(\d+)\s*[:：.、)])\s*",
    re.I,
)


def parse_feedback_markdown(text: str) -> list[dict[str, Any]]:
    """解析 beta 风格 Markdown 为反馈项。

    支持:
    ```
    ## 第3章
    - 这里节奏慢
    第5章: 结尾假
    ch2 我不懂动机
    ```
    """
    text = text or ""
    items: list[dict[str, Any]] = []
    current_seq: int | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in ("---", "***"):
            continue
        m = _CH_RE.match(line)
        if m:
            nums = [g for g in m.groups() if g]
            current_seq = int(nums[0]) if nums else current_seq
            rest = line[m.end():].strip()
            if rest:
                items.append(_fb_item(current_seq, rest))
            continue
        # 无章头则挂当前章或 0
        body = line.lstrip("-*• ").strip()
        if body:
            items.append(_fb_item(current_seq, body))
    return items


def _fb_item(seq: int | None, body: str) -> dict[str, Any]:
    body = body[:300]
    sid = "fb-" + hashlib.sha1(f"{seq}:{body}".encode()).hexdigest()[:10]
    return {
        "id": sid,
        "seq": seq,
        "body": body,
        "question": f"外部读感(第{seq if seq is not None else '?'}章):{body[:80]}",
    }


def suggest_cut_candidates(prose: str, *, max_items: int = 12) -> list[dict[str, Any]]:
    """启发式可删建议:复读句、过长解释段。零自动写回。"""
    prose = prose or ""
    out: list[dict[str, Any]] = []
    # 整句复读
    try:
        from scribe3.critique import find_duplicate_lines
        for h in (find_duplicate_lines(prose) or [])[:8]:
            out.append({
                "kind": "duplicate_line",
                "text": str(h.get("text") or h.get("line") or h)[:80],
                "detail": "整句复读,可考虑删一处",
                "auto_delete": False,
            })
    except Exception:
        pass
    # 连续同段起笔
    lines = [ln.strip() for ln in prose.splitlines() if ln.strip()]
    seen: dict[str, int] = {}
    for ln in lines:
        key = ln[:12]
        if len(key) < 4:
            continue
        seen[key] = seen.get(key, 0) + 1
    for key, n in sorted(seen.items(), key=lambda x: -x[1]):
        if n < 3:
            continue
        out.append({
            "kind": "anaphora_run",
            "text": key,
            "detail": f"以相同开头出现约 {n} 次,检查是否可合并/删减",
            "auto_delete": False,
        })
        if len(out) >= max_items:
            break
    # 解释腔提示(弱)
    for m in re.finditer(r"这(意味着|说明了|正是因为)[^。]{4,40}。", prose):
        out.append({
            "kind": "explainer",
            "text": m.group(0)[:60],
            "detail": "疑似解释句,可考虑留给读者推断",
            "auto_delete": False,
        })
        if len(out) >= max_items:
            break
    for c in out:
        c["auto_delete"] = False
    return out[:max_items]
