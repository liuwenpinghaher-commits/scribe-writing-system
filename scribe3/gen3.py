"""驱动「对话驱动写作」流真机连写 10 章(乱世铜炉),验证全闭环 + 跨章防复读根因修复。

每章:取前文已用措辞(避免清单) → 提思路+avoid → /chat/write(主编自调 s3_ 工具取限知帧/伏笔)
→ /save-chapter(软校验返回 QC,含跨章复读)→ 下章帧已更新。

根因修复(本驱动验证):单遍长程生成的"复读病"——模型跨章逐字复用自己偏爱的措辞/意象,
逐章 QC 查不到。这里在【生成前】把前文独特短语作为 avoid 清单注入 prompt,从源头预防,
并在生成后用 find_cross_chapter_repetitions 跨章度量,对照基线证明下降。

跑:scribe3/.venv/bin/python -u -m scribe3.gen3
"""
import json
import urllib.parse
import urllib.request

from scribe3.critique import distinctive_phrases, find_cross_chapter_repetitions

BASE = "http://127.0.0.1:3321"
WORK = "main"
FOC_DAN = "role:单嫣"
FOC_HU = "role:胡不为"

# 10 章思路(贴乱世铜炉既有设定/伏笔:单嫣/胡不为/十二镇煞钉/寒妇封印/奈何谷;
# 一场一 POV,因果回收,情感弧推进。主编会自调 s3_project_frame/s3_list_promises 兜底限知)。
PREMISES = [
    (FOC_DAN, "第1章(约1500字),单嫣限知视角:老槐树下,单嫣见胡不为举镇煞钉,钉身嗡鸣似要认主。"
     "她认出这是四百年前清潭派云阳真人熔的十二镇煞钉之一,当年正是她引胡不为去梧桐村盗的这枚。"
     "钉认主之日,便是寒妇封印将松之时。冷峻克制,留白,埋下'她为何要引他盗钉'的悬念。"),
    (FOC_HU, "第2章(约1500字),胡不为限知视角:镇煞钉在掌心越鸣越烈,贪念又起想私吞。"
     "下林村神兽夜里异动示警;胡梦见长发覆面的女人立在床前(寒妇之兆,他不知)。"
     "他只当盗钉心虚。契诃夫之枪的不祥感,严格限知——寒妇真相绝不写进他视角。"),
    (FOC_DAN, "第3章(约1500字),单嫣限知视角:封印松动,第一缕煞气渗出,寒妇将出。"
     "单嫣赶去阻止,却见胡不为已被钉中青光缚住、动弹不得。抉择:救胡还是先封煞。"
     "情感弧:由旁观到不得不出手。回收前两章'她引他盗钉'的因果。"),
    (FOC_DAN, "第4章(约1500字),单嫣限知视角:她解开胡身上的青光,代价是泄了自己一缕清潭派真气,"
     "暴露了她'非寻常村妇'的底。胡惊疑她的来历;单嫣含糊带过,只说钉不能留在他身上。"
     "二人就钉的去向起第一次正面冲突。埋'她真气从何而来'的新悬念。"),
    (FOC_HU, "第5章(约1500字),胡不为限知视角:他不肯交钉,趁夜独自带钉逃往奈何谷想另寻买家。"
     "途中遇乌家祭祖的队伍,撞见七年前那桩旧案的当事人。限知:他不知单嫣早料到他会逃。"
     "悬念:乌家与镇煞钉的牵连初现。"),
    (FOC_DAN, "第6章(约1500字),单嫣限知视角:她不追,反去见清潭派旧识,揭开她当年为何叛出师门、"
     "又为何要让镇煞钉认主——她在赌一个'以煞制煞'的局。情感弧:愧疚与决绝交织。"
     "回收第4章'她真气从何而来';埋更大的局。"),
    (FOC_HU, "第7章(约1500字),胡不为限知视角:奈何谷中钉彻底认主,他第一次能驱使钉力,得意忘形,"
     "却也第一次听见寒妇的低语(他以为是自己心声)。他用钉力伤了乌家追兵,尝到力量也尝到代价。"
     "限知:寒妇借钉渗入他心智,他浑然不觉。"),
    (FOC_DAN, "第8章(约1500字),单嫣限知视角:她察觉钉已认主、寒妇渗入胡身,局势失控超出预料。"
     "她赶往奈何谷,沿途布下清潭派封煞旧阵。情感弧:从'用胡'到'悔'到'要救他这个人'的转折。"),
    (FOC_DAN, "第9章(约1500字),单嫣限知视角:谷中相遇,胡已半被寒妇夺舍,人钉难分。"
     "单嫣以真气强行唤他神智,二人第一次摊牌:她坦白当年引他盗钉的全部因果。"
     "高潮前夜:胡在'吞钉之力'与'信单嫣'之间挣扎。"),
    (FOC_DAN, "第10章(约1500字),单嫣限知视角:封煞阵成,寒妇将出未出之际,胡自断与钉的认主之契,"
     "代价惨烈。单嫣以一缕清潭真气助他斩契,寒妇暂封,钉归死寂。"
     "情感弧收束:由'局'到'人'。回收全部前文因果,留'寒妇只是暂封'的余韵。"),
]


def chat_write(msg, chapter, focalizer):
    q = urllib.parse.urlencode({"work": WORK, "chapter": chapter, "focalizer": focalizer, "msg": msg})
    req = urllib.request.Request(f"{BASE}/chat/write?{q}")
    delta, prose, tools = [], [], []
    with urllib.request.urlopen(req, timeout=420) as r:
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
    with urllib.request.urlopen(req, timeout=420) as r:
        return json.load(r)


def _motif_terms() -> set[str]:
    """从 /motifs 取刻意母题/专名白名单(与 store.motif_terms 同口径),度量时放行。"""
    terms: set[str] = set()
    try:
        with urllib.request.urlopen(f"{BASE}/motifs?work={WORK}", timeout=30) as r:
            for m in json.load(r):
                name = m.get("name") or ""
                for ch in "()（）":
                    name = name.replace(ch, "|")
                for part in name.split("|"):
                    p = part.strip()
                    if len(p) >= 2:
                        terms.add(p)
    except Exception:
        pass
    terms.update({"镇煞钉", "灵龙镇煞钉", "奈何谷", "大元炼真经",
                  "清潭派", "云阳真人", "三百六十", "老槐树"})
    return terms


def _avoid_block(prior_proses: list[str], allow: set[str]) -> str:
    """从前 8 章正文抽独特措辞(剔除母题),拼成'避免逐字复用'指令块(源头防跨章复读)。"""
    avoid: list[str] = []
    seen: set[str] = set()
    for p in prior_proses[-8:]:
        for ph in distinctive_phrases(p, n=8, top=40, allow=allow):
            if ph not in seen and not ph.startswith("##") and "第" not in ph[:3]:
                seen.add(ph)
                avoid.append(ph)
    if not avoid:
        return ""
    sample = "、".join(f"「{a}」" for a in avoid[:120])
    return ("\n\n【防跨章复读·硬约束】前文已用过下列措辞/意象,本章**严禁逐字复用**,"
            "同一个意思请换感官/换喻体/换节奏另写一遍(这是单遍长程生成最易犯的复读病):\n" + sample)


def main():
    results = []
    prior_proses: list[str] = []
    allow = _motif_terms()
    for i, (foc, premise) in enumerate(PREMISES, 1):
        print(f"\n{'='*60}\n第 {i} 章 · {foc} · 主编书写中(真 Hermes,自调工具)…", flush=True)
        msg = premise + _avoid_block(prior_proses, allow)
        prose, tools = chat_write(msg, i, foc)
        if not prose.strip():
            print(f"  ✗ 第{i}章无产出,跳过"); continue
        sc = post("/save-chapter", {"seq": i, "prose": prose, "title": f"第{i}章", "focalizer": foc})
        qc = sc.get("qc", {})
        xrep = find_cross_chapter_repetitions(prose, prior_proses, n=8, allow=allow)
        wc = len("".join(prose.split()))
        print(f"  字数 {wc} | 工具 {len(tools)} | 单章QC 复读{qc.get('repetition',0)}/排比{qc.get('structural',0)}/升华{qc.get('purple',0)}"
              f" | **跨章复读 {len(xrep)}** | 限知泄露 {sc.get('leaks',0)}", flush=True)
        if xrep:
            print("    跨章复读命中:", "; ".join(h['phrase'] for h in xrep[:6]), flush=True)
        print(f"  开头:{prose[:90].strip()}…", flush=True)
        results.append({"ch": i, "foc": foc, "wc": wc, "qc": qc,
                        "cross_rep": len(xrep), "cross_rep_phrases": [h["phrase"] for h in xrep],
                        "leaks": sc.get("leaks", 0), "prose": prose})
        prior_proses.append(prose)

    total_xrep = sum(r["cross_rep"] for r in results)
    print(f"\n{'='*60}\n汇总:写出 {len(results)} 章 · 共 {sum(r['wc'] for r in results)} 字"
          f" · **总跨章复读 {total_xrep}** · 总泄露 {sum(r['leaks'] for r in results)}", flush=True)
    json.dump(results, open("/tmp/gen10_result.json", "w"), ensure_ascii=False)
    return results


if __name__ == "__main__":
    main()
