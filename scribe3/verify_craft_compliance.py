"""工艺优先合规门闩(GATE-A/B/C-Det/D)· 纯领域、零 app import。

契约真源:docs/craft-first-verification-scheme-v3.md(专家团 R1–R5 修订后)。

分层:
  Tier-0  纯 store 查询 — CI 默认、可复现
  Tier-1  复用 find_leaks 等确定性检测
  Tier-2  LLM 对照(本模块不隐式联网;align 入口需显式 complete_fn)

PASS 默认公式(机判):
  GATE-A ∧ GATE-B ∧ C-Det(硬项) ∧ GATE-D_min
  字数 / form_fill / 十维 不进公式。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from typing import Any, Callable, Literal

Verdict = Literal["pass", "warn", "fail", "skip"]
RootCause = Literal[
    "RC-EMPTY-AUX",
    "RC-SKIP-STAGE",
    "RC-NO-INJECT",
    "RC-INJECT-IGNORED",
    "RC-TOOL-FAIL",
    "RC-SCHEMA-WEAK",
    "RC-DETECTOR-BUG",
    "RC-PRODUCT-HOLE",
]

# PASS 公式键(契约测用;禁止塞 word_count / form_fill)
PASS_FORMULA_KEYS = frozenset({"gate_a", "gate_b", "gate_c_det", "gate_d_min"})


@dataclass(frozen=True)
class CraftGateThresholds:
    min_characters: int = 2
    min_motifs: int = 1
    min_open_promises: int = 1
    min_relations: int = 1
    min_facts_or_rules: int = 1
    # 硬:非空;软 warn 字数提示(不单独 fail)
    synopsis_soft_chars: int = 40
    scene_truth_soft_chars: int = 40
    min_beats: int = 3
    bridge_min_beats: int = 1
    beat_cover_ratio: float = 2 / 3
    # C-Det:warn 条数达阈值则整闸 fail(防堆积);0=不把 warn 升 fail
    max_warns_before_fail: int = 3


DEFAULT_THRESHOLDS = CraftGateThresholds()


@dataclass
class CheckResult:
    id: str
    verdict: Verdict
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    root_cause_hint: RootCause | None = None
    hard: bool = True  # hard fail 进 gate.ok; soft 仅 warn


@dataclass
class GateReport:
    gate: Literal["A", "B", "C", "D"]
    work: str
    seq: int | None
    ok: bool
    checks: list[CheckResult] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gate": self.gate,
            "work": self.work,
            "seq": self.seq,
            "ok": self.ok,
            "pass": self.ok,  # 兼容 e2e 脚本
            "checks": [
                {
                    "id": c.id,
                    "ok": c.verdict == "pass",
                    "verdict": c.verdict,
                    "detail": c.detail,
                    "evidence": c.evidence,
                    "root_cause_hint": c.root_cause_hint,
                    "hard": c.hard,
                }
                for c in self.checks
            ],
            "blocking": [c.id for c in self.checks if c.hard and c.verdict == "fail"],
            "rc_hints": list(self.root_causes),
            "degraded": list(self.degraded),
        }


@dataclass
class AlignItem:
    dimension: str
    expected_refs: list[str]
    prose_hits: list[str]
    miss: list[str]
    verdict: Verdict
    root_cause_hint: RootCause | None = None


@dataclass
class ComplianceReport:
    work: str
    seq: int
    gate_b: GateReport | None
    det: GateReport
    align: list[AlignItem]
    ok: bool
    post_check: dict | None = None

    def to_dict(self) -> dict:
        return {
            "work": self.work,
            "seq": self.seq,
            "ok": self.ok,
            "gate_b": self.gate_b.to_dict() if self.gate_b else None,
            "det": self.det.to_dict(),
            "align": [asdict(a) for a in self.align],
            "post_check": self.post_check,
        }


def _thr(t: CraftGateThresholds | None) -> CraftGateThresholds:
    return t or DEFAULT_THRESHOLDS


def _work_name(st) -> str:
    return getattr(st, "db_name", None) or getattr(st, "db", None) or "unknown"


def _strip(s: Any) -> str:
    return (s or "").strip() if isinstance(s, str) else str(s or "").strip()


def _finalize(gate: Literal["A", "B", "C", "D"], st, seq: int | None,
              checks: list[CheckResult], *, max_warns: int = 3) -> GateReport:
    hard_fails = [c for c in checks if c.hard and c.verdict == "fail"]
    warns = [c for c in checks if c.verdict == "warn"]
    ok = not hard_fails
    if max_warns > 0 and len(warns) >= max_warns:
        ok = False
        checks.append(CheckResult(
            id=f"{gate}-WARN-BUDGET",
            verdict="fail",
            detail=f"warn 条数 {len(warns)} ≥ {max_warns}",
            root_cause_hint="RC-SCHEMA-WEAK",
            hard=True,
        ))
        hard_fails = [c for c in checks if c.hard and c.verdict == "fail"]
    rcs: list[str] = []
    for c in checks:
        if c.verdict == "fail" and c.root_cause_hint and c.root_cause_hint not in rcs:
            rcs.append(c.root_cause_hint)
    if not ok and not rcs:
        rcs.append("RC-EMPTY-AUX" if gate == "A" else "RC-SKIP-STAGE")
    return GateReport(
        gate=gate, work=_work_name(st), seq=seq, ok=ok,
        checks=checks, root_causes=rcs,
    )


def _char_has_profile(traits: dict) -> bool:
    appearance = _strip(traits.get("appearance"))
    personality = (
        _strip(traits.get("personality_detail"))
        or (traits.get("personality_tags") or [])
    )
    return bool(appearance or personality)


def _char_has_motive(traits: dict) -> bool:
    for k in ("surface_goal", "deep_need", "fear", "backstory", "internal_conflict"):
        if _strip(traits.get(k)):
            return True
    return False


# ─── GATE-A 书级辅助信息 ───────────────────────────────────────────

def gate_a(st, *, thresholds: CraftGateThresholds | None = None) -> GateReport:
    t = _thr(thresholds)
    checks: list[CheckResult] = []

    intent = st.get_intent() if hasattr(st, "get_intent") else {}
    intent = intent or {}
    missing_intent = [k for k in ("reader_feeling", "emotional_arc", "red_lines")
                      if not _strip(intent.get(k))]
    if missing_intent:
        checks.append(CheckResult(
            "A1", "fail",
            f"intent 缺字段: {','.join(missing_intent)}",
            {"missing": missing_intent}, "RC-EMPTY-AUX"))
    else:
        checks.append(CheckResult("A1", "pass", "intent 三字段非空",
                                  {"intent_keys": list(intent.keys())}))

    chars = st.characters() if hasattr(st, "characters") else []
    rich = [c for c in chars
            if _char_has_profile(c.traits or {}) and _char_has_motive(c.traits or {})]
    if len(chars) < t.min_characters:
        checks.append(CheckResult(
            "A2", "fail",
            f"角色数 {len(chars)} < {t.min_characters}",
            {"count": len(chars)}, "RC-EMPTY-AUX"))
    elif len(rich) < t.min_characters:
        checks.append(CheckResult(
            "A2", "fail",
            f"档案齐全角色 {len(rich)} < {t.min_characters}"
            "（需外貌/性格之一 + 动机/前史/恐惧之一）",
            {"rich": [c.id for c in rich], "all": [c.id for c in chars]},
            "RC-SCHEMA-WEAK"))
    else:
        checks.append(CheckResult(
            "A2", "pass", f"{len(rich)} 名档案齐全角色",
            {"ids": [c.id for c in rich]}))

    # A-ARC 主档缺 Lie — soft only（不进 save hard block）
    try:
        from scribe3 import arc_signals as AS
        missing_lie = []
        for c in chars:
            a = st.char_anchors(c.id) if hasattr(st, "char_anchors") else {}
            if (a.get("lie") or "").strip():
                continue
            imp = ""
            if isinstance(getattr(c, "traits", None), dict):
                imp = str((c.traits or {}).get("importance") or "")
            if AS.is_main_cast_importance(imp):
                missing_lie.append(getattr(c, "name", None) or c.id)
        if missing_lie:
            checks.append(CheckResult(
                "A-ARC", "warn",
                f"主角色缺 Lie 锚 {len(missing_lie)} 人: {', '.join(missing_lie[:5])}",
                {"names": missing_lie}, "RC-EMPTY-AUX", hard=False))
        else:
            checks.append(CheckResult(
                "A-ARC", "pass", "主角色 Lie 锚齐全或无主档", hard=False))
    except Exception as e:
        checks.append(CheckResult(
            "A-ARC", "warn", f"弧光锚检查失败: {e}", hard=False,
            root_cause_hint="RC-DETECTOR-BUG"))

    n_facts = 0
    if hasattr(st, "facts_at"):
        try:
            n_facts = len(st.facts_at(9999) or [])
        except Exception:
            n_facts = 0
    n_rules = 0
    if hasattr(st, "list_world_rules"):
        try:
            n_rules = len(st.list_world_rules() or [])
        except Exception:
            n_rules = 0
    if n_facts + n_rules < t.min_facts_or_rules:
        checks.append(CheckResult(
            "A3", "fail",
            f"命题+世界规则={n_facts + n_rules} < {t.min_facts_or_rules}",
            {"facts": n_facts, "rules": n_rules}, "RC-EMPTY-AUX"))
    else:
        checks.append(CheckResult(
            "A3", "pass", f"facts={n_facts} rules={n_rules}",
            {"facts": n_facts, "rules": n_rules}))

    n_rel = 0
    if hasattr(st, "_all_relations"):
        try:
            n_rel = len(st._all_relations() or [])
        except Exception:
            n_rel = 0
    if n_rel < t.min_relations:
        checks.append(CheckResult(
            "A4", "fail",
            f"角色关系 {n_rel} < {t.min_relations}",
            {"count": n_rel}, "RC-EMPTY-AUX"))
    else:
        checks.append(CheckResult("A4", "pass", f"关系 {n_rel} 条", {"count": n_rel}))

    motifs = st.list_motifs() if hasattr(st, "list_motifs") else []
    named = [m for m in (motifs or []) if _strip(m.get("name"))]
    if len(named) < t.min_motifs:
        checks.append(CheckResult(
            "A5", "fail",
            f"母题 {len(named)} < {t.min_motifs}",
            {"count": len(named)}, "RC-EMPTY-AUX"))
    else:
        checks.append(CheckResult(
            "A5", "pass", f"母题 {len(named)}",
            {"names": [m.get("name") for m in named[:10]]}))

    opens = []
    # 有效 open:status=open 且非 red_herring;abandoned/closed 不计入 A6
    if hasattr(st, "effective_open_promises"):
        opens = st.effective_open_promises() or []
    elif hasattr(st, "open_promises"):
        opens = [p for p in (st.open_promises() or [])
                 if p.get("kind") != "red_herring"]
    elif hasattr(st, "list_promises"):
        opens = [p for p in (st.list_promises() or [])
                 if p.get("status") == "open" and p.get("kind") != "red_herring"]
    valid_p = [p for p in opens
               if _strip(p.get("text")) and p.get("setup_chapter") is not None]
    if len(valid_p) < t.min_open_promises:
        checks.append(CheckResult(
            "A6", "fail",
            f"有效 open 伏笔 {len(valid_p)} < {t.min_open_promises}"
            "（需 text + setup_chapter）",
            {"open": len(opens), "valid": len(valid_p)}, "RC-EMPTY-AUX"))
    else:
        checks.append(CheckResult(
            "A6", "pass", f"open 伏笔 {len(valid_p)}",
            {"sample": [p.get("text", "")[:40] for p in valid_p[:5]]}))

    # A7: brief 可观测 — 有 open 伏笔时 promises 段应能组装
    a7_ok = True
    a7_detail = "skip:无 brief 组装"
    if valid_p and hasattr(st, "max_chapter"):
        try:
            from scribe3.brief import assemble_chapter_brief, promise_directives
            rows = (st.promises_with_lifecycle(max_chapter=st.max_chapter() or 1)
                    if hasattr(st, "promises_with_lifecycle") else valid_p)
            pd = promise_directives(rows)
            has_dir = bool(pd.get("due") or pd.get("open") or pd.get("lines")
                           or pd.get("due_now") or pd.get("upcoming") or pd)
            # promise_directives 返回结构可能是 dict with lists
            nonempty = False
            if isinstance(pd, dict):
                for v in pd.values():
                    if isinstance(v, (list, tuple)) and len(v) > 0:
                        nonempty = True
                        break
                    if isinstance(v, str) and v.strip():
                        nonempty = True
                        break
                    if isinstance(v, (int, float)) and v:
                        nonempty = True
                        break
            a7_ok = nonempty or has_dir or len(valid_p) > 0
            # 更严:至少 list_promises 非空已保证;尝试 assemble
            try:
                br = assemble_chapter_brief(st, max(1, st.max_chapter() or 1))
                sec = (br or {}).get("sections") or br or {}
                prom_sec = sec.get("promises") if isinstance(sec, dict) else None
                a7_detail = f"brief.promises={type(prom_sec).__name__}"
                if prom_sec is None and not nonempty:
                    a7_ok = False
                    a7_detail = "brief 无 promises 段且 directives 空"
            except Exception as e:
                # brief 失败但台账有伏笔 → warn(注入链路洞) 不 hard fail 齐套
                checks.append(CheckResult(
                    "A7", "warn", f"assemble_chapter_brief 失败: {e}",
                    hard=False, root_cause_hint="RC-NO-INJECT"))
                a7_ok = True  # 已记 warn
                a7_detail = "brief_error_warned"
        except Exception as e:
            checks.append(CheckResult(
                "A7", "warn", f"A7 探测失败: {e}",
                hard=False, root_cause_hint="RC-NO-INJECT"))
            a7_ok = True
            a7_detail = "import_error_warned"
    if not any(c.id == "A7" for c in checks):
        if not valid_p:
            checks.append(CheckResult(
                "A7", "fail", "无有效伏笔,注入不可观测",
                root_cause_hint="RC-EMPTY-AUX"))
        elif a7_ok:
            checks.append(CheckResult("A7", "pass", a7_detail))
        else:
            checks.append(CheckResult(
                "A7", "fail", a7_detail, root_cause_hint="RC-NO-INJECT"))

    return _finalize("A", st, None, checks, max_warns=t.max_warns_before_fail)


# ─── GATE-B 章级脚手架 ───────────────────────────────────────────

def _beats_list(ch: dict) -> list:
    beats = ch.get("beats") or []
    if not isinstance(beats, list):
        return []
    out = []
    for b in beats:
        if isinstance(b, dict):
            if _strip(b.get("text")):
                out.append(b)
        elif _strip(b):
            out.append({"text": str(b)})
    return out


def _deduction_map(ch: dict) -> dict[str, dict]:
    deds = ch.get("deductions") or []
    out: dict[str, dict] = {}
    if not isinstance(deds, list):
        return out
    for d in deds:
        if not isinstance(d, dict):
            continue
        # MCP/前端可能写 character_id 或 character(裸名/role:)
        cid = str(d.get("character_id") or d.get("character") or d.get("role") or "")
        if cid and _strip(d.get("prose")):
            out[cid] = d
    return out


def gate_b(st, seq: int, *, thresholds: CraftGateThresholds | None = None,
           chapter_kind: str = "normal",
           stage_journal: dict | None = None) -> GateReport:
    t = _thr(thresholds)
    checks: list[CheckResult] = []
    ch = st.get_chapter(seq) if hasattr(st, "get_chapter") else None
    if not ch:
        checks.append(CheckResult(
            "B0", "fail", f"章 {seq} 不存在", root_cause_hint="RC-SKIP-STAGE"))
        return _finalize("B", st, seq, checks, max_warns=t.max_warns_before_fail)

    syn = _strip(ch.get("synopsis"))
    if not syn:
        checks.append(CheckResult(
            "B1", "fail", "大纲 synopsis 为空", root_cause_hint="RC-SKIP-STAGE"))
    else:
        if len(syn) < t.synopsis_soft_chars:
            checks.append(CheckResult(
                "B1", "warn",
                f"大纲偏短({len(syn)}<{t.synopsis_soft_chars})",
                {"len": len(syn)}, hard=False))
        else:
            checks.append(CheckResult("B1", "pass", f"大纲 {len(syn)} 字",
                                      {"len": len(syn)}))

    beats = _beats_list(ch)
    min_b = t.bridge_min_beats if chapter_kind in ("bridge", "epilogue") else t.min_beats
    if len(beats) < min_b:
        checks.append(CheckResult(
            "B2", "fail",
            f"节拍 {len(beats)} < {min_b} (kind={chapter_kind})",
            {"count": len(beats)}, "RC-SKIP-STAGE"))
    else:
        checks.append(CheckResult("B2", "pass", f"节拍 {len(beats)}",
                                  {"count": len(beats)}))

    truth = _strip(ch.get("scene_truth"))
    if not truth:
        checks.append(CheckResult(
            "B3", "fail", "scene_truth 为空", root_cause_hint="RC-SKIP-STAGE"))
    else:
        if len(truth) < t.scene_truth_soft_chars:
            checks.append(CheckResult(
                "B3", "warn",
                f"场景真相偏短({len(truth)}<{t.scene_truth_soft_chars})",
                {"len": len(truth)}, hard=False))
        else:
            checks.append(CheckResult("B3", "pass", f"scene_truth {len(truth)} 字",
                                      {"len": len(truth)}))

    involved = ch.get("involved_characters") or []
    if not isinstance(involved, list):
        involved = []
    involved = [str(x) for x in involved if x]

    def _char_keys(x: str) -> set[str]:
        """role:沈砚 / 沈砚 互认——MCP 常写裸名,库内 oid 带 role:。"""
        s = str(x or "").strip()
        if not s:
            return set()
        bare = s.split(":", 1)[-1]
        return {s, bare, f"role:{bare}"}

    char_ids: set[str] = set()
    for c in (st.characters() if hasattr(st, "characters") else []):
        char_ids |= _char_keys(getattr(c, "id", "") or "")
        char_ids |= _char_keys(getattr(c, "name", "") or "")
    if not involved:
        checks.append(CheckResult(
            "B4", "fail", "involved_characters 为空",
            root_cause_hint="RC-SKIP-STAGE"))
    else:
        unknown = [i for i in involved if not (_char_keys(i) & char_ids)]
        if unknown:
            checks.append(CheckResult(
                "B4", "fail", f"涉及角色不在书中: {unknown}",
                {"unknown": unknown}, "RC-SCHEMA-WEAK"))
        else:
            checks.append(CheckResult(
                "B4", "pass", f"涉及 {len(involved)} 角色",
                {"ids": involved}))

    dmap = _deduction_map(ch)
    # 投影 map 键也可能是 role: 或裸名
    dmap_keys: set[str] = set()
    for k in dmap:
        dmap_keys |= _char_keys(k)
    missing_ded = [i for i in involved if not (_char_keys(i) & dmap_keys)]
    # MVP: 全部 involved 必须有投影(无 cameo 字段时从严;有 focalizer 时至少焦点必有)
    foc = _strip(ch.get("focalizer"))
    if foc and foc not in dmap and foc in involved:
        checks.append(CheckResult(
            "B5", "fail", f"焦点 {foc} 无限知投影",
            {"focalizer": foc}, "RC-SKIP-STAGE"))
    elif missing_ded:
        checks.append(CheckResult(
            "B5", "fail",
            f"缺投影: {missing_ded}",
            {"missing": missing_ded, "have": list(dmap.keys())},
            "RC-SKIP-STAGE"))
    elif not involved:
        checks.append(CheckResult(
            "B5", "fail", "无角色可投影", root_cause_hint="RC-SKIP-STAGE"))
    else:
        checks.append(CheckResult(
            "B5", "pass", f"{len(dmap)} 条限知投影",
            {"ids": list(dmap.keys())}))

    # B6 grounding: verbatim 优先 — 投影 prose 子串 ⊆ scene_truth 则 pass
    if truth and dmap:
        bad = []
        for cid, d in dmap.items():
            prose = _strip(d.get("prose"))
            # 宽松:至少有一段 ≥8 字的连续片段落在 truth,或整段很短且被包含
            if prose in truth:
                continue
            # 抽前 40 字探针
            probe = prose[:40] if len(prose) > 40 else prose
            if len(probe) >= 8 and probe in truth:
                continue
            # 无 verbatim → warn(非 LLM 路径);hard fail 留给 e2e 可选
            bad.append(cid)
        if bad:
            checks.append(CheckResult(
                "B6", "warn",
                f"投影未 verbatim 钉在 scene_truth: {bad}（LLM grounding 另轨）",
                {"ids": bad}, "RC-INJECT-IGNORED", hard=False))
        else:
            checks.append(CheckResult("B6", "pass", "投影 verbatim 可对齐真相"))
    elif not truth:
        checks.append(CheckResult(
            "B6", "skip", "无 scene_truth,跳过 grounding", hard=False))
    else:
        checks.append(CheckResult(
            "B6", "skip", "无投影可检", hard=False))

    # B6s: 相对 scene_truth_revision 过期的投影（hard=False, 可堆积升 fail）
    from scribe3.deduce_helpers import (
        has_five_layer_headings,
        stale_roles,
        truth_revision,
    )
    rev = truth_revision(ch)
    stale_ids = stale_roles(involved, ch.get("deductions"), rev)
    if stale_ids:
        checks.append(CheckResult(
            "B6s", "warn",
            f"投影相对真相过期: {stale_ids} (rev={rev})",
            {"ids": stale_ids, "truth_revision": rev},
            "RC-INJECT-IGNORED", hard=False))
    elif dmap and truth:
        checks.append(CheckResult(
            "B6s", "pass", f"投影未过期 (rev={rev})",
            {"truth_revision": rev}))
    else:
        checks.append(CheckResult(
            "B6s", "skip", "无可检过期投影", hard=False))

    # B8: 五层标题可检测（缺标题 warn，不硬卡旧散文）
    weak = []
    for cid, d in dmap.items():
        prose = _strip(d.get("prose"))
        if prose and not has_five_layer_headings(prose):
            weak.append(cid)
    if weak:
        checks.append(CheckResult(
            "B8", "warn",
            f"投影缺五层标题: {weak}",
            {"ids": weak}, "RC-SCHEMA-WEAK", hard=False))
    elif dmap:
        checks.append(CheckResult("B8", "pass", "投影五层标题齐全或无投影需检"))
    else:
        checks.append(CheckResult("B8", "skip", "无投影可检五层", hard=False))

    # B7 阶段序:无库内时间戳 → skip(不假绿不假红)
    if stage_journal:
        order = stage_journal.get("order") or []
        need = ["outline", "beats", "deduce"]
        ok_ord = all(x in order for x in need)
        if ok_ord:
            # 检查相对顺序
            idxs = [order.index(x) for x in need]
            if idxs == sorted(idxs):
                checks.append(CheckResult("B7", "pass", "阶段序 journal 合法",
                                          {"order": order}))
            else:
                checks.append(CheckResult(
                    "B7", "fail", f"阶段序错乱: {order}",
                    {"order": order}, "RC-SKIP-STAGE"))
        else:
            checks.append(CheckResult(
                "B7", "fail", f"journal 缺阶段: {order}",
                {"order": order}, "RC-SKIP-STAGE"))
    else:
        checks.append(CheckResult(
            "B7", "skip", "无 stage_journal,库内无阶段时间戳", hard=False))

    return _finalize("B", st, seq, checks, max_warns=t.max_warns_before_fail)


# ─── C-Det 正文确定性合规 ─────────────────────────────────────────

def audit_chapter_det(
    st, seq: int, prose: str | None = None, *,
    focalizer: str | None = None,
    thresholds: CraftGateThresholds | None = None,
    run_leaks: bool = True,
) -> GateReport:
    t = _thr(thresholds)
    checks: list[CheckResult] = []
    ch = st.get_chapter(seq) if hasattr(st, "get_chapter") else None
    if not ch:
        checks.append(CheckResult(
            "C0", "fail", f"章 {seq} 不存在", root_cause_hint="RC-SKIP-STAGE"))
        return _finalize("C", st, seq, checks, max_warns=t.max_warns_before_fail)

    body = prose if prose is not None else _strip(ch.get("prose"))
    if not body:
        checks.append(CheckResult(
            "C0", "fail", "正文为空", root_cause_hint="RC-SKIP-STAGE"))
        return _finalize("C", st, seq, checks, max_warns=t.max_warns_before_fail)

    foc = focalizer if focalizer is not None else _strip(ch.get("focalizer"))

    # C1 find_leaks
    if run_leaks and foc:
        try:
            from scribe3.verify import find_leaks_for_chapter
            leaks = find_leaks_for_chapter(body, st, foc, seq)
            if leaks:
                checks.append(CheckResult(
                    "C1", "fail",
                    f"限知泄露 {len(leaks)} 处",
                    {"leaks": [getattr(x, "marker", None) or str(x) for x in leaks[:5]]},
                    "RC-INJECT-IGNORED"))
            else:
                checks.append(CheckResult("C1", "pass", "find_leaks 清空",
                                          {"focalizer": foc}))
        except Exception as e:
            checks.append(CheckResult(
                "C1", "fail", f"find_leaks 异常: {e}",
                root_cause_hint="RC-DETECTOR-BUG"))
    elif not foc:
        checks.append(CheckResult(
            "C1", "warn", "无 focalizer,跳过泄露检测", hard=False))
    else:
        checks.append(CheckResult("C1", "skip", "run_leaks=False", hard=False))

    # C2 causal — ``causal_complete`` 的空列表仅表示“没有违规”，不能自行区分
    # “无事件”与“已有事件且完整”。先从同一 work-scoped store 读取事件存在性，
    # 防止已完成自动 ingest 的章节被误报为 skip。
    try:
        from scribe3.verify import causal_complete
        events = st.events_at(seq) if hasattr(st, "events_at") else []
        res = causal_complete(st, seq)
        # 兼容不同返回形状
        if isinstance(res, dict):
            if res.get("no_event_data"):
                checks.append(CheckResult(
                    "C2", "skip", "无事件数据,因果不适用", hard=False))
            else:
                viol = res.get("violations") or res.get("issues") or []
                if viol:
                    checks.append(CheckResult(
                        "C2", "fail", f"因果违规 {len(viol)}",
                        {"n": len(viol)}, "RC-SCHEMA-WEAK"))
                else:
                    checks.append(CheckResult("C2", "pass", "因果完整"))
        elif isinstance(res, list):
            if not res:
                if events:
                    checks.append(CheckResult(
                        "C2", "pass", "因果完整", {"events": len(events)}))
                else:
                    checks.append(CheckResult(
                        "C2", "skip", "无事件数据,因果不适用", hard=False))
            else:
                checks.append(CheckResult(
                    "C2", "fail", f"因果违规 {len(res)}",
                    root_cause_hint="RC-SCHEMA-WEAK"))
        else:
            checks.append(CheckResult("C2", "skip", f"未知因果返回: {type(res)}",
                                      hard=False))
    except Exception as e:
        checks.append(CheckResult(
            "C2", "warn", f"causal_complete 失败: {e}",
            hard=False, root_cause_hint="RC-DETECTOR-BUG"))

    # C6 母题 echo 关键词(弱确定);结构化 echo_terms + 遗留 echoes
    from scribe3.motif_craft import parse_echo_terms
    motifs = st.list_motifs() if hasattr(st, "list_motifs") else []
    echo_hits = []
    echo_miss = []
    for m in motifs or []:
        name = _strip(m.get("name"))
        tokens = list(parse_echo_terms(m.get("echoes"), m.get("echo_terms")))
        if name:
            tokens.append(name)
        hit = any(tok and tok in body for tok in tokens)
        # instance 也算
        if not hit and hasattr(st, "list_motif_instances"):
            try:
                inst = st.list_motif_instances(seq) or []
                hit = any(
                    (i.get("motif_id") == m.get("id") or i.get("name") == name)
                    for i in inst)
            except Exception:
                pass
        if hit:
            echo_hits.append(name or m.get("id"))
        else:
            echo_miss.append(name or m.get("id"))
    if motifs and echo_miss and not echo_hits:
        checks.append(CheckResult(
            "C6", "warn",
            f"母题无正文/instance 痕迹: {echo_miss}",
            {"miss": echo_miss}, "RC-INJECT-IGNORED", hard=False))
    elif motifs:
        checks.append(CheckResult(
            "C6", "pass", f"母题命中 {echo_hits or 'instance'}",
            {"hits": echo_hits}))
    else:
        checks.append(CheckResult(
            "C6", "warn", "书中无母题(应在 GATE-A 拦截)", hard=False,
            root_cause_hint="RC-EMPTY-AUX"))

    # C11 节拍覆盖(keyword 粗筛) — soft warn 进主报告, hard 仅当 0 覆盖
    beats = _beats_list(ch or {})
    if beats:
        covered = 0
        for b in beats:
            text = _strip(b.get("text") if isinstance(b, dict) else b)
            # 取最长词块 ≥2 字在 prose 中
            ok_b = False
            for n in (6, 4, 2):
                if len(text) >= n and text[:n] in body:
                    ok_b = True
                    break
            # 也试空格分片
            if not ok_b:
                for tok in text.replace("，", " ").replace("。", " ").split():
                    if len(tok) >= 2 and tok in body:
                        ok_b = True
                        break
            if ok_b:
                covered += 1
        ratio = covered / max(1, len(beats))
        if covered == 0:
            checks.append(CheckResult(
                "C11", "fail",
                f"节拍覆盖 0/{len(beats)}",
                {"covered": 0, "total": len(beats)}, "RC-INJECT-IGNORED"))
        elif ratio < t.beat_cover_ratio:
            checks.append(CheckResult(
                "C11", "warn",
                f"节拍覆盖 {covered}/{len(beats)} < {t.beat_cover_ratio:.0%}",
                {"covered": covered, "total": len(beats)},
                "RC-INJECT-IGNORED", hard=False))
        else:
            checks.append(CheckResult(
                "C11", "pass",
                f"节拍覆盖 {covered}/{len(beats)}",
                {"covered": covered, "total": len(beats)}))
    else:
        checks.append(CheckResult(
            "C11", "warn", "无节拍可对照", hard=False,
            root_cause_hint="RC-SKIP-STAGE"))

    return _finalize("C", st, seq, checks, max_warns=t.max_warns_before_fail)


def audit_chapter(
    st, seq: int, *,
    prose: str | None = None,
    mode: Literal["det", "full"] = "det",
    thresholds: CraftGateThresholds | None = None,
    stage_journal: dict | None = None,
    check_gate_b: bool = True,
) -> ComplianceReport:
    """综合审计。mode=full 预留 LLM align,当前与 det 相同(无隐式联网)。"""
    t = _thr(thresholds)
    gb = gate_b(st, seq, thresholds=t, stage_journal=stage_journal) if check_gate_b else None
    det = audit_chapter_det(st, seq, prose=prose, thresholds=t)
    align: list[AlignItem] = []
    if mode == "full":
        # 无 complete_fn 时仅记 skip,不假绿
        align.append(AlignItem(
            dimension="llm_align",
            expected_refs=[],
            prose_hits=[],
            miss=["complete_fn not provided"],
            verdict="skip",
        ))
    ok = det.ok and (gb.ok if gb is not None else True)
    return ComplianceReport(
        work=_work_name(st), seq=seq, gate_b=gb, det=det, align=align, ok=ok,
    )


# ─── GATE-D 反哺(最小) ───────────────────────────────────────────

def gate_d(st, seq: int, *,
           expect_promise_touch: bool = False,
           thresholds: CraftGateThresholds | None = None) -> GateReport:
    t = _thr(thresholds)
    checks: list[CheckResult] = []

    # D1: 若要求 touch 或存在 due 窗口
    touched = False
    if hasattr(st, "promises_with_lifecycle"):
        try:
            rows = st.promises_with_lifecycle(max_chapter=seq) or []
            for p in rows:
                if p.get("last_refresh_at") == seq:
                    touched = True
                    break
        except Exception as e:
            checks.append(CheckResult(
                "D1", "warn", f"lifecycle 读失败: {e}", hard=False,
                root_cause_hint="RC-DETECTOR-BUG"))
    if expect_promise_touch and not touched:
        checks.append(CheckResult(
            "D1", "fail", f"期望章 {seq} 有伏笔 touch,未检测到",
            root_cause_hint="RC-TOOL-FAIL"))
    elif touched:
        checks.append(CheckResult("D1", "pass", f"章 {seq} 有 promise touch"))
    else:
        checks.append(CheckResult(
            "D1", "skip", "未要求 touch 且未检测到", hard=False))

    # D2 母题 instance — soft
    inst = []
    if hasattr(st, "list_motif_instances"):
        try:
            inst = st.list_motif_instances(seq) or []
        except Exception:
            inst = []
    if inst:
        checks.append(CheckResult("D2", "pass", f"母题 instance {len(inst)}",
                                  hard=False))
    else:
        checks.append(CheckResult(
            "D2", "warn", "本章无 motif_instance", hard=False,
            root_cause_hint="RC-TOOL-FAIL"))

    return _finalize("D", st, seq, checks, max_warns=t.max_warns_before_fail)


def journey_pass(*, gate_a_ok: bool, chapters: list[dict]) -> dict:
    """汇总旅程 PASS。chapters: [{seq, gate_b_ok, gate_c_ok, gate_d_ok}]"""
    ch_ok = all(
        c.get("gate_b_ok") and c.get("gate_c_ok") and c.get("gate_d_ok", True)
        for c in chapters
    ) if chapters else False
    ok = bool(gate_a_ok and ch_ok and chapters)
    return {
        "ok": ok,
        "pass": ok,
        "formula_keys": sorted(PASS_FORMULA_KEYS),
        "gate_a": gate_a_ok,
        "chapters": chapters,
        "forbidden_keys_in_formula": ["word_count", "form_fill_count"],
    }


def classify_root_cause(report: GateReport | ComplianceReport) -> list[str]:
    if isinstance(report, ComplianceReport):
        rcs: list[str] = []
        if report.gate_b:
            rcs.extend(report.gate_b.root_causes)
        rcs.extend(report.det.root_causes)
        # unique preserve order
        out = []
        for r in rcs:
            if r not in out:
                out.append(r)
        return out
    return list(report.root_causes)


def to_jsonable(report: GateReport | ComplianceReport | dict) -> dict:
    if isinstance(report, dict):
        return report
    return report.to_dict()


# ─── 产品门闩:存正文前 ───────────────────────────────────────────

_PROSE_ENFORCE_MIN = 80  # 短占位/空壳不触发;实质正文才拦


def craft_gate_env_enabled() -> bool:
    """SCRIBE3_CRAFT_GATE 默认开启(1);测试 conftest 钉 0。"""
    import os
    v = os.environ.get("SCRIBE3_CRAFT_GATE", "1").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def resolve_create_mode(explicit: str | None = None) -> str:
    """standard | explore。默认 standard；显式 / env SCRIBE3_CREATE_MODE。"""
    import os
    raw = (explicit if explicit is not None else os.environ.get("SCRIBE3_CREATE_MODE")) or "standard"
    m = str(raw).strip().lower()
    return "explore" if m == "explore" else "standard"


def explore_soft_save_enabled() -> bool:
    import os
    v = (os.environ.get("SCRIBE3_EXPLORE_SOFT_SAVE") or "1").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def craft_finalize_env_enabled() -> bool:
    """SCRIBE3_CRAFT_FINALIZE 默认 1；关=危险运维旁路 craft 定稿。"""
    import os
    v = (os.environ.get("SCRIBE3_CRAFT_FINALIZE") or "1").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def thresholds_for_create_mode(mode: str | None = None) -> CraftGateThresholds:
    """explore：max_warns_before_fail=0，禁止 WARN-BUDGET 把 soft 升 hard。"""
    t = CraftGateThresholds()
    if resolve_create_mode(mode) == "explore":
        t = replace(t, max_warns_before_fail=0)
    return t


def _soft_map_gate_report(report: GateReport) -> GateReport:
    """将 hard fail 降为 warn（explore soft-save）；保留 check id/detail。"""
    for c in report.checks:
        if c.verdict == "fail" and c.hard:
            c.verdict = "warn"
            c.hard = False
    # 重算 ok（warn 不拦；max_warns 已在 thresholds 置 0）
    hard_fails = [c for c in report.checks if c.hard and c.verdict == "fail"]
    report.ok = not hard_fails
    return report


def evaluate_craft_finalize_gate(
    st, seq: int, *,
    thresholds: CraftGateThresholds | None = None,
    skip: bool = False,
) -> dict:
    """定稿路径 craft 硬门：GATE-A + 本章 GATE-B。**永不** explore soft 映射。

    danger_draft 不得旁路本函数（仅旁路质控 triage）。
    """
    if skip or not craft_finalize_env_enabled():
        return {
            "allowed": True, "code": "skipped",
            "detail": "craft finalize off or skip",
            "blocking": [], "reports": {},
        }
    # 始终 DEFAULT（或显式 thresholds），含 max_warns=3
    t = _thr(thresholds)
    reports: dict[str, Any] = {}
    ga = gate_a(st, thresholds=t)
    reports["gate_a"] = ga.to_dict()
    gb = gate_b(st, int(seq), thresholds=t)
    reports["gate_b"] = gb.to_dict()
    blocking: list[str] = []
    if not ga.ok:
        blocking.extend(
            c.id for c in ga.checks if c.hard and c.verdict == "fail"
        )
    if not gb.ok:
        blocking.extend(
            c.id for c in gb.checks if c.hard and c.verdict == "fail"
        )
    ok = ga.ok and gb.ok
    return {
        "allowed": bool(ok),
        "code": "ok" if ok else "craft_finalize",
        "detail": (
            "craft finalize gates pass" if ok
            else "定稿要求 GATE-A/B 齐套（explore soft-save 不可旁路）"
        ),
        "blocking": blocking,
        "gate_a": reports["gate_a"],
        "gate_b": reports["gate_b"],
        "reports": reports,
    }


def evaluate_save_craft_gate(
    st, seq: int, prose: str, *,
    skip: bool = False,
    thresholds: CraftGateThresholds | None = None,
    create_mode: str | None = None,
) -> dict:
    """存正文前评估。返回 {allowed, code, detail, reports, warnings?}。

    - skip / 环境关闭 → allowed
    - prose 短于阈值 → allowed(骨架占位)
    - explore + EXPLORE_SOFT_SAVE：A/B hard→warn，max_warns=0，allowed=true + warnings
    - standard：需 GATE-B 硬项;若全书尚无实质正文,另需 GATE-A
    """
    if skip or not craft_gate_env_enabled():
        return {"allowed": True, "code": "skipped", "detail": "craft gate off or skip",
                "reports": {}}
    body = _strip(prose)
    if len(body) < _PROSE_ENFORCE_MIN:
        return {"allowed": True, "code": "short_prose", "detail": f"prose<{_PROSE_ENFORCE_MIN}",
                "reports": {}}

    mode = resolve_create_mode(create_mode)
    explore = mode == "explore" and explore_soft_save_enabled()
    t = thresholds if thresholds is not None else thresholds_for_create_mode(mode)
    t = _thr(t)
    reports: dict[str, Any] = {}
    warnings: list[dict[str, Any]] = []

    # 是否「第一篇实质正文」:其它章均无长 prose
    first_substantial = True
    if hasattr(st, "list_chapters"):
        try:
            for row in st.list_chapters() or []:
                s = row.get("seq")
                if s is None or int(s) == int(seq):
                    continue
                ch = st.get_chapter(int(s)) or {}
                if len(_strip(ch.get("prose"))) >= _PROSE_ENFORCE_MIN:
                    first_substantial = False
                    break
        except Exception:
            first_substantial = False

    if first_substantial:
        ga = gate_a(st, thresholds=t)
        if explore:
            ga = _soft_map_gate_report(ga)
            for c in ga.checks:
                if c.verdict == "warn":
                    warnings.append({"id": c.id, "detail": c.detail, "gate": "A"})
        reports["gate_a"] = ga.to_dict()
        if not ga.ok:
            return {
                "allowed": False,
                "code": "craft_gate_a",
                "detail": "书级辅助信息未齐套,禁止写入实质正文",
                "blocking": [c.id for c in ga.checks if c.hard and c.verdict == "fail"],
                "root_causes": ga.root_causes,
                "reports": reports,
                "create_mode": mode,
            }

    gb = gate_b(st, seq, thresholds=t)
    if explore:
        gb = _soft_map_gate_report(gb)
        for c in gb.checks:
            if c.verdict == "warn":
                warnings.append({"id": c.id, "detail": c.detail, "gate": "B"})
    reports["gate_b"] = gb.to_dict()
    if not gb.ok:
        return {
            "allowed": False,
            "code": "craft_gate_b",
            "detail": "章级脚手架未齐套(大纲/节拍/演绎),禁止接受正文",
            "blocking": [c.id for c in gb.checks if c.hard and c.verdict == "fail"],
            "root_causes": gb.root_causes,
            "reports": reports,
            "create_mode": mode,
        }

    out = {
        "allowed": True,
        "code": "ok_explore_soft" if (explore and warnings) else "ok",
        "detail": (
            "explore soft-save: craft gaps as warnings"
            if (explore and warnings)
            else "craft gates pass"
        ),
        "reports": reports,
        "create_mode": mode,
    }
    if warnings:
        out["warnings"] = warnings
    return out
