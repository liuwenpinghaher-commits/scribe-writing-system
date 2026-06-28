#!/usr/bin/env python3
"""业务测试·第三轮 后处理:① 剥离 ⟦PROPOSAL⟧ 围栏 ② 跨章复读定向去重(系统自带 rewrite_cross_repetitions)
③ 重存库 ④ 重验限知泄露/跨章复读/字数。修复 bt_render 两个问题后重新验证。

跑: cd "/Users/miaoma/Downloads/写作 3.0" && scribe3/.venv/bin/python -u scribe3/tools/bt_post.py
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scribe3.store import SurrealStore
from scribe3.llm import hermes_complete
from scribe3.verify import find_leaks
from scribe3.critique import rewrite_cross_repetitions, find_cross_chapter_repetitions, find_repetitions

WORK = "book_bfd18b78"
ALLOW = {"引魂铃", "回煞炉", "焚骨庵", "活炉", "清潭", "招魂幡", "叫魂郎", "柳三更", "白姑",
         "麻三娘", "焦判官", "聋祖", "阿枝", "回煞", "阳寿", "借寿", "蜜枣糕", "招魂", "走尸"}

_FENCE = re.compile(r"⟦/?PROPOSAL[^⟧]*⟧")


def wc(s):
    return len("".join(s.split()))


def strip_fence(s):
    s = _FENCE.sub("", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def main():
    st = SurrealStore(ns="scribe3", db=WORK)
    chapters = json.load(open("/tmp/bt_chapters.json", encoding="utf-8"))
    chapters.sort(key=lambda c: c["seq"])
    print("=" * 64)
    print("后处理:剥围栏 + 跨章复读定向去重 + 重验")
    print("=" * 64)
    prior = []
    out = []
    for c in chapters:
        seq, foc, title = c["seq"], c["foc"], c["title"]
        prose = strip_fence(c["prose"])
        before_xrep = len(find_cross_chapter_repetitions(prose, prior, allow=ALLOW))
        # 跨章复读定向去重(系统自带,LLM逐句改写)
        res = rewrite_cross_repetitions(prose, prior, hermes_complete, allow=ALLOW)
        prose = res["prose"]
        after_xrep = res["after"]
        # 重验
        leaks = find_leaks(prose, st, foc, seq)
        rep = find_repetitions(prose)
        w = wc(prose)
        # 重存库(干净正文)
        st.save_chapter(seq, prose, title=title, focalizer=foc)
        print(f"第{seq}章《{title}》: {w}字 | 围栏已剥 | 跨章复读 {before_xrep}→{after_xrep}(改写{res['rewritten']}句) "
              f"| 单章复读 {len(rep)} | 限知泄露 {len(leaks)}", flush=True)
        out.append({"seq": seq, "foc": foc, "title": title, "wc": w,
                    "leaks": len(leaks), "leak_detail": leaks[:6],
                    "rep": len(rep), "xrep": after_xrep, "prose": prose})
        prior.append(prose)

    total_w = sum(o["wc"] for o in out)
    total_leak = sum(o["leaks"] for o in out)
    total_xrep = sum(o["xrep"] for o in out)
    ge = sum(1 for o in out if o["wc"] >= 5000)
    print(f"\n汇总:{len(out)}章 · {total_w}字 · 均{total_w//len(out)}字/章 · ≥5000字 {ge}/{len(out)} "
          f"· 总泄露 {total_leak} · 总跨章复读 {total_xrep}")
    json.dump(out, open("/tmp/bt_chapters.json", "w"), ensure_ascii=False, indent=1)
    print("已更新 /tmp/bt_chapters.json(干净正文)")
    st.close()


if __name__ == "__main__":
    main()
