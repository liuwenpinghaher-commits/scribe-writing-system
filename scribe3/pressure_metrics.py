"""压力后验检测（确定性）· 合同锚定优先 · 抗词表刷绿。"""
from __future__ import annotations

import re
from typing import Any

from scribe3.pressure_drive import (
    beat_pressure_stats,
    pdc_blocking_env_enabled,
    validate_pdc,
)

METRICS_VERSION = "pressure_metrics.v1"

_TIME_MARKS = re.compile(
    r"五更|四更|三更|天没亮|天已经|大亮|日头|过午|偏了|入夜|夜里|昨儿|今儿|"
    r"一整天|坐了一整夜|等了一整天|天快亮|入夜时分"
)
_BEND_MARKS = re.compile(
    r"忽然|片刻|两刻|一息|时间像|记不清过了多久|像过了|不过一袋烟|转眼"
)
_FORCE_VERBS = re.compile(
    r"决定|抉择|捅|插|推开|接了|接下|不能再|要么|若是|咬牙|拦|拒绝|承认|签|按进|嵌进"
)
_DECISION_PAT = re.compile(r"若.{0,12}就|要么.{0,12}要么|不能再|他决定|她决定|我接|接不上也接")
_RITUAL_VERB = re.compile(r"按|启|记|拜|抹|画|蘸|扣")
_PLACE_CAND = re.compile(r"[\u4e00-\u9fff]{2,6}(?:铺|巷|门|库|房|庄|坊|街|口|檐|摊)")


def _norm(s: str) -> str:
    return (
        str(s or "")
        .replace(" ", "")
        .replace("　", "")
        .lower()
    )


def _metric(
    value: Any,
    *,
    tier: str = "n/a",
    detail: str = "",
    anchored: bool = False,
) -> dict:
    return {
        "value": value,
        "tier": tier,
        "detail": (detail or "")[:200],
        "anchored": anchored,
    }


def _place_set(synopsis: str, beats_text: str) -> set[str]:
    blob = f"{synopsis or ''}\n{beats_text or ''}"
    found = set(_PLACE_CAND.findall(blob))
    # 也抽连续 2–4 字块作为弱候选（限量）
    for m in re.finditer(r"[\u4e00-\u9fff]{2,4}", blob):
        t = m.group(0)
        if t.endswith(("的", "了", "着", "和", "与")):
            continue
        if len(found) >= 24:
            break
        found.add(t)
    return found


def measure_pressure(
    prose: str,
    contract: dict | None = None,
    *,
    synopsis: str = "",
    beats_text: str = "",
    chapter_pressure: int | None = None,
) -> dict:
    """对正文 + 可选合同跑 P0 指标，产出 findings。

    severity 默认 advisory；仅 env BLOCKING 且压力≥4 时部分 kind 可 blocking。
    """
    prose = prose or ""
    present = bool(contract) and isinstance(contract, dict) and contract.get("status") != "missing"
    v = validate_pdc(contract) if present else {"ok": None, "errors": [], "warnings": []}
    metrics: dict[str, dict] = {}
    findings: list[dict] = []

    try:
        cp = int(chapter_pressure if chapter_pressure is not None else (contract or {}).get("chapter_pressure") or 0)
    except (TypeError, ValueError):
        cp = 0

    # --- irreversible_anchored ---
    if present:
        irrev = contract.get("irreversible") if isinstance(contract.get("irreversible"), dict) else {}
        ev = str(irrev.get("evidence_must_show") or "").strip()
        if len(ev) >= 2:
            hit = ev in prose or _norm(ev) in _norm(prose)
            metrics["irreversible_anchored"] = _metric(
                hit, tier="light" if hit else "heavy",
                detail=f"evidence={'命中' if hit else '未命中'}:{ev[:40]}",
                anchored=True,
            )
            if not hit:
                findings.append(_finding(
                    "irreversible_anchored",
                    f"不可逆痕迹未在正文出现：须含「{ev}」",
                    severity=_sev("irreversible_anchored", cp),
                ))
        else:
            metrics["irreversible_anchored"] = _metric(None, tier="n/a", detail="无 evidence", anchored=True)
    else:
        metrics["irreversible_anchored"] = _metric(None, tier="n/a", detail="无合同", anchored=False)

    # --- fork_signal ---
    if present:
        fork = contract.get("fork") if isinstance(contract.get("fork"), dict) else {}
        choice = str(fork.get("choice") or "").strip()
        core = choice[:8] if choice else ""
        by_core = bool(core) and (core in prose or _norm(core) in _norm(prose))
        by_pat = bool(_DECISION_PAT.search(prose))
        ok = by_core or by_pat
        metrics["fork_signal"] = _metric(
            ok, tier="light" if ok else "mid",
            detail=f"core={by_core} pat={by_pat}",
            anchored=True,
        )
        if not ok:
            findings.append(_finding(
                "fork_signal",
                "岔路信号弱：未见选择核心词或决策句式",
                severity="advisory",
            ))
    else:
        metrics["fork_signal"] = _metric(None, tier="n/a", detail="无合同", anchored=False)

    # --- ritual_overuse ---
    ritual_count = 0
    if present:
        rq = contract.get("ritual_quota") if isinstance(contract.get("ritual_quota"), dict) else {}
        cls = str(rq.get("class") or "").strip()
        lex = rq.get("ritual_lexicon") if isinstance(rq.get("ritual_lexicon"), list) else []
        terms = [cls] + [str(x) for x in lex if str(x).strip()]
        terms = [t for t in terms if t]
        # 按句计完整形态近似：class 词与完成动词同句共现；同段多次则累加
        for para in re.split(r"\n\s*\n", prose):
            if not para.strip():
                continue
            for sent in re.split(r"[。！？；\n]", para):
                s = sent.strip()
                if not s:
                    continue
                has_term = any(t in s for t in terms) if terms else False
                has_verb = bool(_RITUAL_VERB.search(s))
                if has_term and has_verb:
                    ritual_count += 1
                # 「再…记门/再按」等复读信号额外计次
                if has_term and ("再" in s or "又" in s):
                    ritual_count += 1
        max_full = int(rq.get("max_full") or 1)
        over = ritual_count > max_full
        metrics["ritual_overuse"] = _metric(
            ritual_count,
            tier="heavy" if ritual_count >= max_full + 2 else ("mid" if over else "light"),
            detail=f"fullish={ritual_count} max={max_full}",
            anchored=True,
        )
        if over:
            findings.append(_finding(
                "ritual_overuse",
                f"仪式「{cls or '未命名'}」完整形态约 {ritual_count} 次，超过配额 {max_full}",
                severity=_sev("ritual_overuse", cp, heavy=ritual_count >= max_full + 2),
            ))
    else:
        metrics["ritual_overuse"] = _metric(0, tier="n/a", detail="无合同", anchored=False)

    # --- motif_overheat_local ---
    caps = (contract or {}).get("motif_intensity_caps") if present else None
    if isinstance(caps, list) and caps:
        over_terms = []
        for c in caps:
            if not isinstance(c, dict):
                continue
            term = str(c.get("term") or "")
            try:
                mx = int(c.get("max_mentions") or 0)
            except (TypeError, ValueError):
                mx = 0
            if not term or mx <= 0:
                continue
            cnt = prose.count(term)
            if cnt > mx:
                over_terms.append(f"{term}:{cnt}>{mx}")
        metrics["motif_overheat_local"] = _metric(
            len(over_terms),
            tier="mid" if over_terms else "light",
            detail=";".join(over_terms) or "ok",
            anchored=True,
        )
        for t in over_terms:
            findings.append(_finding("motif_overheat_local", f"意象超 cap：{t}", severity="advisory"))
    else:
        metrics["motif_overheat_local"] = _metric(None, tier="n/a", detail="无 caps", anchored=False)

    # --- time_linear_flag ---
    tmarks = len(_TIME_MARKS.findall(prose))
    bends = len(_BEND_MARKS.findall(prose))
    linear = tmarks >= 3 and bends == 0
    metrics["time_linear_flag"] = _metric(
        linear,
        tier="mid" if linear else "light",
        detail=f"time_marks={tmarks} bend={bends}",
        anchored=False,
    )
    if linear:
        findings.append(_finding(
            "time_linear_flag",
            f"时间刻度词 {tmarks} 处且无弯曲信号，疑似匀速流水账",
            severity="advisory",
        ))

    # --- spatial_inventory ---
    places = _place_set(synopsis, beats_text)
    # 也从 prose 自身抽门/巷类
    places |= set(_PLACE_CAND.findall(prose[:2000]))
    sents = [s.strip() for s in re.split(r"[。！？\n]", prose) if s.strip()]
    run = 0
    max_run = 0
    inventory_hit = False
    for s in sents:
        has_place = any(p in s for p in places) if places else bool(_PLACE_CAND.search(s))
        has_force = bool(_FORCE_VERBS.search(s))
        if has_place and not has_force:
            run += 1
            max_run = max(max_run, run)
            if run >= 3:
                inventory_hit = True
        else:
            run = 0
    metrics["spatial_inventory"] = _metric(
        max_run,
        tier="mid" if inventory_hit else "light",
        detail=f"max_place_run={max_run} places={len(places)}",
        anchored=False,
    )
    if inventory_hit:
        findings.append(_finding(
            "spatial_inventory",
            f"连续≥3 句地点/巷志铺陈且无推力动词（最长 {max_run}）",
            severity="advisory",
        ))

    # --- event_pace_cv (advisory) ---
    lens = [len(p.replace("\n", "")) for p in re.split(r"\n\s*\n", prose) if p.strip()]
    if len(lens) >= 3:
        mean = sum(lens) / len(lens)
        var = sum((x - mean) ** 2 for x in lens) / len(lens)
        cv = (var ** 0.5) / mean if mean else 0.0
    else:
        cv = None
    low_cv = cv is not None and cv < 0.35 and cp >= 4
    metrics["event_pace_cv"] = _metric(
        cv,
        tier="mid" if low_cv else ("light" if cv is not None else "n/a"),
        detail=f"cv={cv:.3f}" if cv is not None else "n/a",
        anchored=False,
    )
    if low_cv:
        findings.append(_finding(
            "event_pace_cv",
            f"高压章段长 CV={cv:.2f}<0.35，事件节拍过匀（仅 advisory）",
            severity="advisory",
        ))

    # --- beat_pressure_var ---
    stats = beat_pressure_stats(contract if present else None)
    metrics["beat_pressure_var"] = _metric(
        stats.get("var"),
        tier="light" if stats.get("var") is not None else "n/a",
        detail=f"span={stats.get('span')} n={stats.get('n')}",
        anchored=True,
    )

    return {
        "version": METRICS_VERSION,
        "contract_present": present,
        "validate": v,
        "metrics": metrics,
        "findings": findings,
        "literary_claim_ban": "machine≠literary≥9.5; human_pass_rule_met never from this module",
    }


def _sev(kind: str, chapter_pressure: int, *, heavy: bool = False) -> str:
    """默认 advisory；BLOCKING env 且压力≥4 时部分 kind 可 blocking。"""
    if not pdc_blocking_env_enabled():
        return "advisory"
    if chapter_pressure < 4:
        return "advisory"
    if kind == "irreversible_anchored":
        return "blocking"
    if kind == "ritual_overuse" and heavy:
        return "blocking"
    return "advisory"


def _finding(kind: str, message: str, *, severity: str = "advisory") -> dict:
    return {
        "type": "pressure",
        "message": message,
        "text": message,
        "range": None,
        "meta": {"kind": kind, "severity": severity},
    }


def pressure_should_block(findings: list[dict], *, chapter_pressure: int) -> bool:
    """是否应升为 finalize blocking（需 triage 白名单配合）。"""
    if not pdc_blocking_env_enabled():
        return False
    if chapter_pressure < 4:
        return False
    for f in findings or []:
        if f.get("type") != "pressure":
            continue
        meta = f.get("meta") if isinstance(f.get("meta"), dict) else {}
        if meta.get("severity") == "blocking":
            return True
    return False
