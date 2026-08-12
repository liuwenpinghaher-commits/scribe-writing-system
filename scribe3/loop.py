"""北极星方案任务4 · 修复环编排层(蓝图 §3-①):生成 → 确定性检测 → severity 三分流。

定位:检测→定档链路(/post-check + merge_findings fix_action + PipelineJournal)早已在库,
本模块补最后一厘米——**消费检测结果去触发再生成**的执行器。纯编排、依赖注入:
generate/post_check/persist_version/finalize 全部由调用方(app.py 端点)绑定真实现,
本模块零 app/store import,可用 stub 全覆盖测试。

三分流(蓝图 §3-①,判据全部来自外部信号,LLM rubric 分不参与收敛判定):
  blocking  → 自动 regenerate,硬上限 2 轮(初写 1 次 + 回炉 ≤2 次);
              2 轮仍 blocking → needs_human 标记后停,正文不落库不 ingest,待人裁决。
  advisory  → 绝不自动重写(宪法条款,保护作者声音):留草稿版本 + rewrite 建议清单
              待批;正文不自动落库不 ingest,人批后走既有链路(D-010)。
  pass      → finalize(正文落库 + 留 final 版 + 同步 ingest 反哺)。

调研采纳(台账 D-009):回炉反馈=CRITIC 式外部工具信号;findings→负面约束用
「检测器名+违例引文+祈使式约束」三元组模板,不倾倒原始 JSON(Guardrails/Instructor
先例);第 2 轮附带上轮失败摘要,禁止同 prompt 复跑(防同质化);journal 每步骤
start/complete 留痕带 attempt 幂等键(Temporal append-only 语义)。
"""
from __future__ import annotations

import logging

_log = logging.getLogger("scribe3.loop")

MAX_REGEN_ROUNDS = 2   # regenerate 硬上限(蓝图定案;Self-Refine Δ5.0→0.9→0.9,首轮拿走绝大部分收益)

# pass 门的关键检测 stage:任何一个降级都不得宣 pass(诚实降级,没查≠没病)。
# leaks 有独立 leaks_degraded 旗;quality_issues 喂判据②(degeneration issue 的来源,
# P0门审查 P1-4)、aggregate_ai_grade 喂判据③——两者降级时 pass 不可信。
_PASS_CRITICAL_STAGES = ("aggregate_ai_grade", "quality_issues")

# 遗留处置 2-B(D-025 自定口径):短文本密度类信号置信度警示。
_SHORT_TEXT_MIN_CHARS = 500          # 低于此可见字数,仅密度类证据的 heavy 降 advisory
_NON_DENSITY_GATES = {"B", "D", "F", "G"}    # 句式套路/节奏结构/升华/god_view(计数与形态类)
_NON_DENSITY_INDICATORS = ("parallel_run", "rhythm_uniform")   # 计数/verdict 类指标


# Story / Style / Redline 分桶骨架（PR-6a · KD-NQ-7；PR-6c deliver 卡消费计数）
_BUCKET_NAMES = ("redline", "story", "style")
_STORY_KINDS = frozenset({
    "park_stroll",
    "spatial_inventory",
    "time_linear_flag",
    "progress_zero_advance",
    "progress_stairs_anchored",
    "location_grind_run",
    "retreat_no_cost",
    "irreversible_anchored",
    "fork_signal",
    "ritual_overuse",
    "drama_beats_incomplete",
    "main_channel_idle_ratio",
    "event_pace_cv",
})
_REDLINE_TYPES = frozenset({"leak", "degeneration", "discipline"})
_STYLE_TYPES = frozenset({
    "punct", "ai_grade", "short_text_low_confidence", "setting", "structure_style",
})


def normalize_bucket_counts(buckets: dict | None) -> dict[str, int]:
    """将 triage.buckets（list 或已是 int）规范为三项计数。

    PR-6c · deliver pilot_card.buckets 契约：
      ``{"redline": int, "story": int, "style": int}``
    缺键 / 非法值 → 0；不抛。
    """
    out = {k: 0 for k in _BUCKET_NAMES}
    if not isinstance(buckets, dict):
        return out
    for k in _BUCKET_NAMES:
        v = buckets.get(k)
        if isinstance(v, list):
            out[k] = len(v)
        elif isinstance(v, bool):
            out[k] = 0
        elif isinstance(v, (int, float)):
            out[k] = max(0, int(v))
        elif isinstance(v, dict):
            c = v.get("count", v.get("n"))
            if isinstance(c, (int, float)) and not isinstance(c, bool):
                out[k] = max(0, int(c))
    return out


def bucket_counts_from_triage(triage_out: dict | None) -> dict[str, int] | None:
    """若 triage 返回含 buckets，产出三项计数；否则 None（调用方可不写卡字段）。"""
    if not isinstance(triage_out, dict) or "buckets" not in triage_out:
        return None
    return normalize_bucket_counts(triage_out.get("buckets"))


def _triage_bucket_for(iss: dict | None, *, is_block: bool = False) -> str:
    """将 issue / blocking 条目归入 redline | story | style。"""
    if not iss:
        return "style"
    t = str(iss.get("type") or iss.get("detector") or "")
    meta = iss.get("meta") if isinstance(iss.get("meta"), dict) else {}
    kind = str(meta.get("kind") or iss.get("kind") or "")
    # 话语层连载 findings → story（禁止落入 style 默认桶）
    if t.startswith("discourse."):
        return "story"
    if t in ("leak", "find_leaks") or kind == "leak" or t == "degeneration" or t == "find_degeneration":
        return "redline"
    if t in ("discipline", "findings_schema") and is_block:
        return "redline"
    if t == "pressure" or t == "pressure_metrics" or kind in _STORY_KINDS:
        return "story"
    if t in _STYLE_TYPES or t == "aggregate_ai_grade" or kind in ("ai_grade_heavy", "ai_grade"):
        return "style"
    if is_block and t in _REDLINE_TYPES:
        return "redline"
    # 默认：blocking 偏 story（含 park_stroll 等 pressure 投影），advisory 偏 style
    return "story" if is_block else "style"


def triage(post: dict) -> dict:
    """把 /post-check 响应按 severity 三分流。返回
    {"verdict": "blocking"|"advisory"|"pass", "blocking": [...], "advisory_count": int,
     "degraded_stages": [...], "leaks": [...], "buckets": {redline, story, style}}。

    blocking 判据(蓝图 §3-① 四项 + PR-6a park_stroll):
      ① find_leaks 非空(限知泄露,本体公证处判定)
      ② issues 里 type=="degeneration" 且 meta.severity=="blocking"(模型退化指纹)
      ③ ai_grade.grade=="heavy"(整章 AI 味定档,确定性文本统计聚合)
      ④ issues 里 meta.severity=="S1"(FindingsSchema 阻断档,悲观合流产物)
      ⑤ type=="pressure" 且 meta.severity=="blocking"（含 park_stroll / spatial 升档；
         默认 PARK_STROLL_BLOCKING=0 时 measure 产出 advisory，不进本桶）
    pass 门(假绿防护):leaks_degraded 或关键检测 stage 降级 → 最高只能 advisory,
    绝不把"没查到"当"没病"。
    """
    from scribe3.review.blocking import is_blocking_issue as _is_blocking_issue
    blocking: list[dict] = []
    buckets: dict[str, list] = {"redline": [], "story": [], "style": []}
    leaks = post.get("leaks") or []
    for lk in leaks:
        item = {"detector": "find_leaks", "kind": "leak",
                "quote": str((lk or {}).get("marker") or lk)[:60],
                "note": (f"帧外私密破绽词(fact="
                         f"{((lk or {}).get('fact_id') or '?')})")[:120]}
        blocking.append(item)
        buckets["redline"].append(item)
    # KD-14: ALL issue types go solely through is_blocking_issue (accepts S1|BLOCKING).
    # Do not special-case degeneration/pressure then exclude them — normalize→S1 must still block.
    # PR-6a: pressure + meta.severity=blocking（含 park_stroll）已由 is_blocking_issue 覆盖。
    _detector_by_type = {
        "degeneration": "find_degeneration",
        "pressure": "pressure_metrics",
        "discipline": "findings_schema",
        "llm_review": "findings_schema",
        "leak": "find_leaks",
    }
    for iss in post.get("issues") or []:
        if not _is_blocking_issue(iss):
            continue
        meta = iss.get("meta") or {}
        t = iss.get("type") or iss.get("kind") or "S1"
        kind = meta.get("kind") or t
        item = {
            "detector": _detector_by_type.get(t, "findings_schema"),
            "kind": kind,
            "quote": str(iss.get("text") or "")[:60],
            "note": str(iss.get("message") or "")[:120],
        }
        blocking.append(item)
        # pressure（含 park_stroll）→ story；泄露/退化 → redline
        if t == "pressure" or kind == "park_stroll":
            bname = "story"
        else:
            bname = _triage_bucket_for(iss, is_block=True)
        buckets[bname].append(item)
    grade = (post.get("ai_grade") or {}).get("grade")
    _short_low_conf = None
    if grade == "heavy":
        ag = post.get("ai_grade") or {}
        gates = ag.get("gates_hit") or []
        # 遗留处置 2-B:短文本(<500 可见字)上密度类信号分母过小,单发命中即爆表
        # (P2 真机:400 字三候选全灭)。heavy 证据全为密度类(Gate A/C/E 由千字密度/
        # 占比档位驱动)→ 降 advisory 并显式标注;含任何非密度证据(Gate B/D/F/G 或
        # parallel_run/rhythm_uniform 指标自身 heavy)→ 照常 blocking。
        ind = ag.get("indicators") or {}
        vis = post.get("visible_chars")
        _non_density = (any(g in _NON_DENSITY_GATES for g in gates)
                        or any((ind.get(x) or {}).get("tier") == "heavy"
                               for x in _NON_DENSITY_INDICATORS))
        if isinstance(vis, int) and vis < _SHORT_TEXT_MIN_CHARS and not _non_density:
            _short_low_conf = (f"短文本置信度警示:可见 {vis} 字 < {_SHORT_TEXT_MIN_CHARS},"
                               f"heavy 仅由密度类信号构成(Gate {'/'.join(gates) or '无'}),"
                               f"降为待批——阈值为自定口径,待真实短章数据标定")
        else:
            item = {"detector": "aggregate_ai_grade", "kind": "ai_grade_heavy",
                    "quote": "", "note": f"整章 AI 味定档 heavy(命中 Gate {'/'.join(gates)})"}
            blocking.append(item)
            buckets["style"].append(item)

    degraded_stages = list(post.get("degraded_stages") or [])
    leaks_degraded = bool(post.get("leaks_degraded"))
    # advisory 清单本体(蓝图 §3-①:"rewrite 建议清单呈给作者",不能只给数量)——
    # 复用 issues/punct_suggestions 的 range 数据,人批时可定位原文。
    # 注:type=="leak" 的 issue 是顶层 leaks 的同事另一投影(post-check F-05 兼容层),
    # 已作 blocking 承载,不再进待批清单——防同一处泄密双重计数(P0 门真机发现)。
    advisory_items = ([{"type": i.get("type"), "message": i.get("message"),
                        "text": (str(i.get("text") or ""))[:60], "range": i.get("range"),
                        "meta": i.get("meta")}
                       for i in (post.get("issues") or [])
                       if not _is_blocking_issue(i) and i.get("type") != "leak"]
                      + [{"type": "punct", "message": str(s.get("message") or "标点建议"),
                          "text": (str(s.get("text") or ""))[:60], "range": s.get("range")}
                         for s in (post.get("punct_suggestions") or [])])
    if _short_low_conf:
        # 2-B:降档必须显式可见——作者要知道"没拦"是因为置信度不足,不是稿子没问题
        advisory_items.append({"type": "short_text_low_confidence",
                               "message": _short_low_conf, "text": "", "range": None})

    # R2：structure_style 仅 advisory（永不 blocking）
    _ss = post.get("structure_style") if isinstance(post.get("structure_style"), dict) else None
    if _ss:
        if _ss.get("ending_formula_hit"):
            advisory_items.append({
                "type": "structure_style",
                "message": "章末公式感（短句+意象回扣）· advisory，可改收束结构",
                "text": str((_ss.get("ending_formula") or {}).get("line") or "")[:60],
                "range": None,
                "meta": {"kind": "ending_formula", "severity": "advisory"},
            })
        if _ss.get("isomorphism_hit"):
            runs = _ss.get("paragraph_isomorphism") or []
            n = runs[0].get("count") if runs else 3
            advisory_items.append({
                "type": "structure_style",
                "message": f"连续段同构 run（≥{n}）· advisory，建议轮换段型",
                "text": str((runs[0].get("sample") if runs else "") or "")[:60],
                "range": None,
                "meta": {"kind": "paragraph_isomorphism", "severity": "advisory"},
            })
        try:
            sp = float(_ss.get("simile_like_per_1k") or 0)
            if sp >= 8.0:
                advisory_items.append({
                    "type": "structure_style",
                    "message": f"「像」密度约 {sp}/千字偏高 · advisory",
                    "text": "",
                    "range": None,
                    "meta": {"kind": "simile_density", "severity": "advisory"},
                })
        except Exception:
            pass

    # Week-1 话语层：顶键 findings → advisory_items（story 桶；永不 blocking）
    _da = post.get("discourse_advisory") if isinstance(post.get("discourse_advisory"), dict) else None
    if _da:
        for f in _da.get("findings") or []:
            if not isinstance(f, dict):
                continue
            t = str(f.get("type") or "")
            if not t.startswith("discourse."):
                t = f"discourse.{t}" if t else "discourse.unknown"
            advisory_items.append({
                "type": t,
                "message": str(f.get("message") or "")[:160],
                "text": "",
                "range": None,
                "meta": {
                    **(f.get("meta") if isinstance(f.get("meta"), dict) else {}),
                    "severity": "advisory",
                    "not_a_kpi": True,
                    "source": "discourse_advisory",
                },
            })

    # F7 · open 伏笔未 touch → soft advisory（永不 blocking；需 post 带 prose + open_promises）
    try:
        _op = post.get("open_promises") or post.get("promises")
        _pr = post.get("prose") or post.get("text") or ""
        if _op and _pr:
            from scribe3.promise_touch_soft import open_promise_touch_advisories
            for a in open_promise_touch_advisories(
                _pr, _op if isinstance(_op, list) else [],
                chapter_skip_mark=bool(post.get("promise_skip_chapter")),
            ):
                advisory_items.append({
                    "type": "promise.untouched",
                    "message": str(a.get("message") or "")[:160],
                    "text": str(a.get("text") or "")[:60],
                    "range": None,
                    "meta": {
                        "severity": "advisory",
                        "blocking": False,
                        "promise_id": a.get("promise_id"),
                        "source": "promise_touch_soft",
                    },
                })
    except Exception:
        pass

    # advisory → buckets（不改 verdict 逻辑）
    for a in advisory_items:
        buckets[_triage_bucket_for(a, is_block=False)].append(a)

    if blocking:
        verdict = "blocking"
    else:
        if leaks_degraded or any(s in degraded_stages for s in _PASS_CRITICAL_STAGES):
            # 降级不 pass:关键检测没跑成,合成一条清单项,人工过目
            degraded_names = ((["leaks"] if leaks_degraded else [])
                              + [s for s in degraded_stages if s in _PASS_CRITICAL_STAGES])
            advisory_items.append({"type": "degraded", "range": None, "text": "",
                                   "message": f"关键检测降级({','.join(degraded_names)}):"
                                              f"没查≠没病,须人工过目"})
            buckets["style"].append(advisory_items[-1])
        # setting(实体登记提醒)不拦截 pass(D-013,P0 门真机发现):它指向"去登记
        # 实体"而非"改稿",且 pass 后的 ingest 本就做实体抽取入待批,拦截只会让
        # 几乎每章卡人;提示仍随 advisory_items 返回,不丢信息。
        gating = [i for i in advisory_items if i.get("type") != "setting"]
        verdict = "advisory" if gating else "pass"
    return {"verdict": verdict, "blocking": blocking,
            "advisory_count": len(advisory_items), "advisory_items": advisory_items,
            "degraded_stages": degraded_stages, "leaks": leaks,
            "buckets": buckets}


def _is_blocking_issue(iss: dict) -> bool:
    """Backward-compatible alias → scribe3.review.blocking.is_blocking_issue (KD-14)."""
    from scribe3.review.blocking import is_blocking_issue
    return is_blocking_issue(iss)


def build_regen_constraints(blocking: list[dict], next_attempt: int,
                            prior_summary: str = "") -> str:
    """把 blocking findings 压缩成负面约束段,追加进**完整组装链**的 instructions 尾部
    (绝不另起简化 prompt——历史教训:每新开一个注入点都泄露过一次)。
    每条=「检测器名 + 违例引文 + 祈使式负面约束」三元组;第 2 轮起附带上轮失败摘要,
    保证两轮 prompt 不同(D-009:禁止同 prompt 同参复跑)。"""
    if not blocking:
        return ""
    imper = {
        "find_leaks": "重写时该私密只许以疑惧/误判/物象暗示存在,任何直说或破绽词一律删除",
        "find_degeneration": "重写该段,句式换开,禁止复读/占位语/工程词/中途截断",
        "findings_schema": "按批注消除该硬伤,保持叙事意图不变",
        "aggregate_ai_grade": "按简报文风重写,拆掉被命中的套路句式,句长错落、情绪走物象",
    }
    # PSC：pressure_metrics 按 finding.kind 分支（换阶/换场）；禁止同地原地兑锚
    imper_by_kind = {
        "progress_stairs_anchored": (
            "换场或换阶写入台阶证据；禁止同地重复犹豫/感官原地补词兑锚"
        ),
        "progress_zero_advance": (
            "本章须至少落地一格代价或决策台阶；禁止只磨痕迹不挪局面"
        ),
        "irreversible_anchored": (
            "换场写入不可逆痕迹证据；禁止同句型原地补词"
        ),
        "location_grind_run": (
            "压缩同地连续主戏；须尽早付代价、换场或安静落地台阶证据"
        ),
        "retreat_no_cost": (
            "退可以，须代价/决策/不可逆落地；禁止原状空转退回"
        ),
        "fork_signal": "岔路须可见选择措辞与后果之一，勿只堆内心戏",
        "motif_overheat_local": "压缩同意象连刷，改峰段或换场",
        "ritual_quota_exceeded": "仪式再写须变形，禁止同一记门完整复读",
        "time_linear_flag": "压时间刻度，允许弯曲/悬置，禁止匀速流水账",
        # PR-6a：公园散步组合
        "park_stroll": (
            "砍巷志流水与匀速日夜铺陈；须落地代价/决策/不可逆或明确转折，禁止公园散步式巡礼"
        ),
        "spatial_inventory": (
            "压缩连续地点/巷志铺陈；插入推力动作或换场推进，禁止无主戏巡礼"
        ),
        "drama_beats_incomplete": (
            "补全场景节拍的目标/冲突/转折；高压章禁止空转闲笔充节拍"
        ),
    }
    lines = [f"## 上稿被确定性检测打回(即将进行第 {next_attempt} 轮重写)",
             "以下约束优先级高于本轮用户指令与大纲中与之冲突的部分;"
             "若约束与叙事意图根本冲突,宁可留疑而不违规(遗留处置 1-C #12)。",
             "以下硬伤必须全部消除;未列出的部分保持原有叙事意图与质感,不要整体翻新:"]
    for b in blocking[:12]:   # 量控:防超长 findings 稀释组装链其余强制项
        q = f"「{b['quote']}」" if b.get("quote") else ""
        det = b.get("detector")
        # kind 只读 triage 已填的 b["kind"]，禁止二次解析 note
        kind = b.get("kind")
        if det == "pressure_metrics":
            tip = imper_by_kind.get(kind) or "消除该硬伤（换阶或换场，禁原地补词）"
        else:
            tip = imper.get(det, "消除该硬伤")
        lines.append(
            f"- [{det}] {b.get('note') or kind or ''}{q}——{tip}。"
        )
    if len(blocking) > 12:
        lines.append(f"-(另有 {len(blocking) - 12} 条同类硬伤,一并按上述要求处理)")
    if prior_summary:
        lines.append(f"上一轮失败摘要(勿重蹈):{prior_summary}")
    return "\n".join(lines)


def _round_summary(blocking: list[dict]) -> str:
    kinds = {}
    for b in blocking:
        kinds[b.get("detector") or "?"] = kinds.get(b.get("detector") or "?", 0) + 1
    return "、".join(f"{k}×{v}" for k, v in kinds.items())


def run_chapter_loop(*, chapter: int, generate, post_check, persist_version,
                     finalize, journal, max_rounds: int = MAX_REGEN_ROUNDS) -> dict:
    """每章一循环的执行器。

    generate(attempt:int, constraints:str) -> str      本轮章稿散文(attempt=0 初写)
    post_check(prose:str) -> dict                      /post-check 同构响应
    persist_version(prose, attempt, verdict) -> str    旧稿留版本(回炉不覆盖),回版本 id
    finalize(prose) -> dict                            pass 分支:正文落库+ingest 反哺
    journal: PipelineJournal                           每步 start/complete 留痕(attempt 幂等键)

    返回 {"verdict": "pass"|"advisory"|"needs_human", "chapter", "rounds": [...],
          "advisory_count", "degraded_stages", ...}。
    """
    rounds: list[dict] = []
    constraints = ""
    prose = ""
    tri: dict = {"verdict": "advisory", "blocking": [], "advisory_count": 0,
                 "degraded_stages": []}
    for attempt in range(0, max_rounds + 1):
        stage_gen = f"ch{chapter}_a{attempt}_generate"
        journal.start_stage(stage_gen)
        prose = generate(attempt, constraints)
        journal.complete_stage(stage_gen)

        # P0门审查 P1-1:稿一落地立刻留版(在 post_check 之前)——检测环节任何异常
        # 都不再吞掉一次昂贵的 LLM 生成;verdict 后补进 rounds 与 journal stage 名。
        vid = None
        try:
            vid = persist_version(prose, attempt, "raw")
        except Exception as e:
            _log.warning("loop ch%s attempt%s 留版失败(继续): %s", chapter, attempt, e)

        stage_chk = f"ch{chapter}_a{attempt}_post_check"
        journal.start_stage(stage_chk)
        post = post_check(prose)
        journal.complete_stage(stage_chk)

        tri = triage(post)
        # P2-5:verdict 也落 journal——审计"哪章回炉几轮、每轮判了什么"不再只在
        # HTTP 响应里;细节理由(findings)在版本库+响应。
        vstage = f"ch{chapter}_a{attempt}_verdict_{tri['verdict']}"
        journal.start_stage(vstage)
        journal.complete_stage(vstage)
        rounds.append({"attempt": attempt, "verdict": tri["verdict"],
                       "version_id": vid,
                       "blocking_summary": _round_summary(tri["blocking"]),
                       "blocking": tri["blocking"][:24],   # P2-7 响应帽(prompt 侧另有 12 条帽)
                       "advisory_count": tri["advisory_count"],
                       "advisory_items": (tri.get("advisory_items") or [])[:20],   # 量控
                       "degraded_stages": tri["degraded_stages"]})
        if tri["verdict"] != "blocking":
            break
        if attempt >= max_rounds:
            break
        constraints = build_regen_constraints(
            tri["blocking"], next_attempt=attempt + 1,
            prior_summary=f"第 {attempt} 稿硬伤:{_round_summary(tri['blocking'])}")

    result = {"chapter": chapter, "rounds": rounds,
              "advisory_count": tri["advisory_count"],
              "advisory_items": (tri.get("advisory_items") or [])[:20],   # 待批清单本体
              "degraded_stages": tri["degraded_stages"]}
    if tri["verdict"] != "pass" and rounds and rounds[-1]["version_id"] is None:
        # P0门审查 P1-2:非 pass 分支版本库是唯一存储,留版失败时稿本体随响应返回,
        # 作者可手工拷走——绝不静默丢一次生成(pass 分支有 finalize 落库兜底)。
        result["prose_unsaved"] = prose
    if tri["verdict"] == "pass":
        stage_ing = f"ch{chapter}_ingest"
        journal.start_stage(stage_ing)
        ing = finalize(prose)
        journal.complete_stage(stage_ing)
        result.update({"verdict": "pass", "ingest": ing})
    elif tri["verdict"] == "blocking":
        # 2 轮回炉仍 blocking:needs_human 标记后停——正文不落库不 ingest(防污染本体),
        # 稿全在版本库,人来裁决(蓝图 v2:标记后绕行,不阻塞后续任务)。
        journal.start_stage(f"ch{chapter}_needs_human")
        journal.complete_stage(f"ch{chapter}_needs_human")
        result.update({"verdict": "needs_human",
                       "note": f"{max_rounds} 轮回炉仍 blocking,待人裁决;正文未落库未 ingest,各轮稿在版本库"})
    else:
        # advisory:绝不自动重写(宪法);清单待批,人批后走既有 save-chapter→/ingest 链路。
        result.update({"verdict": "advisory",
                       "note": "advisory 不自动重写:草稿已留版本,建议清单待作者裁决;正文未自动落库"})
    return result
