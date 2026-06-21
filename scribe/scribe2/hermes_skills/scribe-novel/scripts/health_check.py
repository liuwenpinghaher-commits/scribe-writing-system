#!/usr/bin/env python3
"""scribe 体检脚本(Hermes cron 的 script-injection 用)。
确定性算承诺线健康(超期/红鲱鱼未澄清/回收缺铺垫/承诺密度过高),stdout 成为 agent 上下文;
无问题输出 [SILENT](cron 不推送)。一致性(力量代价等需 LLM)交给加载了 scribe-novel skill 的 agent。

**开关 = Hermes cron 任务;开发期不创建 cron,本脚本仅供手动跑/接线后用。**
用法:WORK_ID=<hex> python3 health_check.py   或   python3 health_check.py <work_id>
"""
import os
import sys


def _setup_path():
    here = os.path.dirname(os.path.abspath(__file__))
    scribe_root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))  # …/scribe
    if scribe_root not in sys.path:
        sys.path.insert(0, scribe_root)


def review(work_id: str) -> list[str]:
    from scribe2.conn import connect, domain_from
    d = domain_from(connect())
    rows = d.list_foreshadows_status(work_id)
    issues: list[str] = []
    maxc = max((c.get("seq") or 0 for c in d.list_chapters(work_id)), default=0)
    open_cnt = [0] * (maxc + 2)
    for f in rows:
        name = f.get("summary") or f.get("promise") or "(未命名)"
        beats = f.get("beats") or []
        if f.get("overdue"):
            issues.append(f"超期未回收:「{name}」埋第{f.get('chapter')}章,已开太久")
        if f.get("ftype") == "红鲱鱼" and not any(b.get("kind") in ("twist", "misdirect") for b in beats):
            issues.append(f"红鲱鱼没澄清/转折:「{name}」别让假线索烂尾")
        if f.get("state") == "paid":
            setups = len([b for b in beats if b.get("kind") in ("plant", "reinforce")]) or (len(f.get("echoes") or []) + 1)
            if setups < 2:
                issues.append(f"回收缺铺垫:「{name}」只有{setups}处铺垫(建议≥2,三次法则更佳)")
        # 承诺密度
        c0 = f.get("chapter") or 1
        end = (f.get("payoff_chapter") or maxc) if f.get("state") != "abandoned" else c0 - 1
        for ch in range(c0, min(end, maxc) + 1):
            open_cnt[ch] += 1
    for ch in range(1, maxc + 1):
        if open_cnt[ch] > 6:
            issues.append(f"承诺密度过高:第{ch}章同时开着{open_cnt[ch]}条承诺,读者易超载")
    return issues


def main() -> int:
    _setup_path()
    work_id = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WORK_ID", "")).strip()
    if not work_id:
        print("[SILENT]")  # 没指定书,静默
        return 0
    try:
        issues = review(work_id)
    except Exception as e:  # 体检失败也别刷屏,留痕给 agent
        print(f"体检脚本出错:{e}")
        return 0
    if not issues:
        print("[SILENT]")
        return 0
    print("【承诺线体检·发现以下问题,请核对并给修订建议】")
    for i in issues:
        print("· " + i)
    print("\n(一致性/力量代价请用 scribe2 工具 check_chapter 逐章核;以上为确定性预筛)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
