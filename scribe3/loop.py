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
# leaks 有独立 leaks_degraded 旗;degeneration/ai_grade 走 degraded_stages。
_PASS_CRITICAL_STAGES = ("aggregate_ai_grade",)


def triage(post: dict) -> dict:
    """把 /post-check 响应按 severity 三分流。返回
    {"verdict": "blocking"|"advisory"|"pass", "blocking": [...], "advisory_count": int,
     "degraded_stages": [...], "leaks": [...]}。

    blocking 判据(蓝图 §3-① 四项):
      ① find_leaks 非空(限知泄露,本体公证处判定)
      ② issues 里 type=="degeneration" 且 meta.severity=="blocking"(模型退化指纹)
      ③ ai_grade.grade=="heavy"(整章 AI 味定档,确定性文本统计聚合)
      ④ issues 里 meta.severity=="S1"(FindingsSchema 阻断档,悲观合流产物)
    pass 门(假绿防护):leaks_degraded 或关键检测 stage 降级 → 最高只能 advisory,
    绝不把"没查到"当"没病"。
    """
    blocking: list[dict] = []
    leaks = post.get("leaks") or []
    for lk in leaks:
        blocking.append({"detector": "find_leaks", "kind": "leak",
                         "quote": str((lk or {}).get("marker") or lk)[:60],
                         "note": f"帧外私密破绽词(fact={((lk or {}).get('fact_id') or '?')})"})
    for iss in post.get("issues") or []:
        meta = iss.get("meta") or {}
        sev = str(meta.get("severity") or "")
        if iss.get("type") == "degeneration" and sev == "blocking":
            blocking.append({"detector": "find_degeneration", "kind": meta.get("kind") or "degeneration",
                             "quote": str(iss.get("text") or "")[:60],
                             "note": str(iss.get("message") or "")})
        elif sev.upper() == "S1":
            blocking.append({"detector": "findings_schema", "kind": iss.get("type") or "S1",
                             "quote": str(iss.get("text") or "")[:60],
                             "note": str(iss.get("message") or "")})
    grade = (post.get("ai_grade") or {}).get("grade")
    if grade == "heavy":
        gates = (post.get("ai_grade") or {}).get("gates_hit") or []
        blocking.append({"detector": "aggregate_ai_grade", "kind": "ai_grade_heavy",
                         "quote": "", "note": f"整章 AI 味定档 heavy(命中 Gate {'/'.join(gates)})"})

    degraded_stages = list(post.get("degraded_stages") or [])
    leaks_degraded = bool(post.get("leaks_degraded"))
    # advisory 清单本体(蓝图 §3-①:"rewrite 建议清单呈给作者",不能只给数量)——
    # 复用 issues/punct_suggestions 的 range 数据,人批时可定位原文。
    # 注:type=="leak" 的 issue 是顶层 leaks 的同事另一投影(post-check F-05 兼容层),
    # 已作 blocking 承载,不再进待批清单——防同一处泄密双重计数(P0 门真机发现)。
    advisory_items = ([{"type": i.get("type"), "message": i.get("message"),
                        "text": (str(i.get("text") or ""))[:60], "range": i.get("range")}
                       for i in (post.get("issues") or [])
                       if not _is_blocking_issue(i) and i.get("type") != "leak"]
                      + [{"type": "punct", "message": str(s.get("message") or "标点建议"),
                          "text": (str(s.get("text") or ""))[:60], "range": s.get("range")}
                         for s in (post.get("punct_suggestions") or [])])

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
        # setting(实体登记提醒)不拦截 pass(D-013,P0 门真机发现):它指向"去登记
        # 实体"而非"改稿",且 pass 后的 ingest 本就做实体抽取入待批,拦截只会让
        # 几乎每章卡人;提示仍随 advisory_items 返回,不丢信息。
        gating = [i for i in advisory_items if i.get("type") != "setting"]
        verdict = "advisory" if gating else "pass"
    return {"verdict": verdict, "blocking": blocking,
            "advisory_count": len(advisory_items), "advisory_items": advisory_items,
            "degraded_stages": degraded_stages, "leaks": leaks}


def _is_blocking_issue(iss: dict) -> bool:
    meta = iss.get("meta") or {}
    sev = str(meta.get("severity") or "")
    return ((iss.get("type") == "degeneration" and sev == "blocking")
            or sev.upper() == "S1")


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
    lines = [f"## 上稿被确定性检测打回(即将进行第 {next_attempt} 轮重写)",
             "以下硬伤必须全部消除;未列出的部分保持原有叙事意图与质感,不要整体翻新:"]
    for b in blocking[:12]:   # 量控:防超长 findings 稀释组装链其余强制项
        q = f"「{b['quote']}」" if b.get("quote") else ""
        lines.append(f"- [{b.get('detector')}] {b.get('note') or b.get('kind')}{q}"
                     f"——{imper.get(b.get('detector'), '消除该硬伤')}。")
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

        stage_chk = f"ch{chapter}_a{attempt}_post_check"
        journal.start_stage(stage_chk)
        post = post_check(prose)
        journal.complete_stage(stage_chk)

        tri = triage(post)
        vid = None
        try:
            vid = persist_version(prose, attempt, tri["verdict"])
        except Exception as e:   # 留版失败不阻断编排(与 save-chapter 端点先例同)
            _log.warning("loop ch%s attempt%s 留版失败(继续): %s", chapter, attempt, e)
        rounds.append({"attempt": attempt, "verdict": tri["verdict"],
                       "version_id": vid,
                       "blocking_summary": _round_summary(tri["blocking"]),
                       "blocking": tri["blocking"],
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
