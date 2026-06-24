"""驱动新「对话驱动写作」流真机连写 3 章(乱世铜炉),验证全闭环 + 质量。

每章:提思路 → /chat/write(主编自调 s3_ 工具取限知帧/伏笔,出 ⟦PROPOSAL⟧ 草稿)
→ /save-chapter(软校验返回 QC/泄露)→ /ingest(知识回写)→ 下章帧已更新。

跑:scribe3/.venv/bin/python -m scribe3.gen3
"""
import json
import sys
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:3321"
WORK = "main"
FOC = "role:单嫣"

# 3 章思路(贴乱世铜炉既有设定/伏笔;主编会自己 s3_list_promises/s3_project_frame 兜底)
PREMISES = [
    "写第1章完整本章(约1500字),单嫣限知视角:老槐树下,单嫣见胡不为举镇煞钉,钉身嗡鸣似要认主。"
    "她认出这是四百年前清潭派云阳真人熔的十二镇煞钉之一,当年正是她引胡不为去梧桐村盗的这枚。"
    "她心知:钉认主之日,便是寒妇封印将松之时。冷峻克制,留白,埋下'她为何要引他盗钉'的悬念。",
    "写第2章完整本章(约1500字),胡不为限知视角:镇煞钉在他掌心越鸣越烈,贪念又起想私吞。"
    "下林村神兽夜里异动示警;胡梦见一个长发覆面的女鬼立在床前(寒妇之兆,但他不知)。"
    "他只当是盗钉心虚。要有契诃夫之枪的不祥感,但严格限知——胡不知道的私密(寒妇真相)绝不写进他视角。",
    "写第3章完整本章(约1500字),单嫣限知视角:封印松动,第一缕煞气渗出,寒妇将出。"
    "单嫣赶去阻止,却见胡不为已被钉中青光缚住、动弹不得。她面临抉择:救胡还是先封煞。"
    "情感弧推进:由旁观到不得不出手。回收前两章埋的'她引他盗钉'的因果。",
]


def chat_write(msg, chapter):
    q = urllib.parse.urlencode({"work": WORK, "chapter": chapter, "focalizer": FOC, "msg": msg})
    req = urllib.request.Request(f"{BASE}/chat/write?{q}")
    delta, prose, tools = [], [], []
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw in r:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            try:
                d = json.loads(line[5:].strip())
            except Exception:
                continue
            if d.get("delta"):
                delta.append(d["delta"])
            elif d.get("tool"):
                tools.append(d["tool"])
            elif d.get("proposal"):
                prose.append(d["proposal"]["prose"])
            elif d.get("error"):
                print("  ERR", d["error"])
    return "".join(prose) or "".join(delta), tools


def post(path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(f"{BASE}{path}", data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def main():
    results = []
    for i, premise in enumerate(PREMISES, 1):
        print(f"\n{'='*60}\n第 {i} 章 · 主编书写中(真 Hermes,自调工具)…", flush=True)
        prose, tools = chat_write(premise, i)
        if not prose.strip():
            print(f"  ✗ 第{i}章无产出,跳过"); continue
        sc = post("/save-chapter", {"seq": i, "prose": prose, "title": f"第{i}章", "focalizer": FOC})
        ingested = "✓"  # /save-chapter 已后台触发 ingest;P07 去双触发
        qc = sc.get("qc", {})
        wc = len("".join(prose.split()))
        print(f"  字数 {wc} | 工具 {len(tools)} | QC 复读{qc.get('repetition',0)}/排比{qc.get('structural',0)}/升华{qc.get('purple',0)}"
              f" | 限知泄露 {sc.get('leaks',0)} | 回写 {ingested}", flush=True)
        print(f"  开头:{prose[:120].strip()}…", flush=True)
        results.append({"ch": i, "wc": wc, "qc": qc, "leaks": sc.get("leaks", 0), "prose": prose})

    print(f"\n{'='*60}\n汇总:写出 {len(results)} 章 · 共 {sum(r['wc'] for r in results)} 字"
          f" · 总泄露 {sum(r['leaks'] for r in results)}", flush=True)
    json.dump(results, open("/tmp/gen3_result.json", "w"), ensure_ascii=False)
    return results


if __name__ == "__main__":
    main()
