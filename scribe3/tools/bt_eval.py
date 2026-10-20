#!/usr/bin/env python3
"""业务测试·第三轮:质量评估(vs 乱世铜炉风格维度)+ HTTP 读端点修复验证。
读 /tmp/bt_chapters.json,跑风格密度维度;并对 book_bfd18b78 验证第三轮读端点修复
(/post-check degraded、/project-tree 不泄密、/timeline 结构、/outline、/promises/ledger、/factions 屏蔽)。

跑: cd "<repo-root>" && scribe3/.venv/bin/python -u scribe3/tools/bt_eval.py
"""
import sys, os, json, re, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

BASE = "http://127.0.0.1:3321"
WORK = "book_bfd18b78"


def get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as r:
        return json.load(r)


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def wc(s):
    return len("".join(s.split()))


def style_dims(chapters):
    """乱世铜炉风格密度维度(对照 e2e_test 维度,密度=每千字次数)。"""
    text = "\n".join(c["prose"] for c in chapters)
    n = max(1, len(text))
    dims = {
        "环境氛围": r"夜|月|风|雾|烛|灯|雨|寒|烟|香火|岗|庵|河|炉火",
        "身体动作": r"颤|抖|攥|蹲|跪|扑|退|奔|缩|俯|掖|蜷|哆嗦|僵住|顿",
        "心理活动": r"心中|暗想|只觉|心知|心底|寻思|盘算|忖|暗道|患得患失|犹疑",
        "感官(视听嗅触)": r"听见|看见|闻到|觉出|触到|瞧见|嗅|耳里|眼角|指尖",
        "细节物象": r"铃|炉|幡|纸人|铜钱|骨|香|簪|寿灯|戏箱|八字|符",
        "对话标记": r"道[:：]|说[:：]|问[:：]|笑道|冷道|低声|喝道|「|」|“|”",
    }
    out = {}
    for name, pat in dims.items():
        cnt = len(re.findall(pat, text))
        out[name] = round(cnt / n * 1000, 1)
    # 句长
    sents = [s for s in re.split(r"[。！？\n]", text) if s.strip()]
    out["_句均长"] = round(sum(len(s) for s in sents) / max(1, len(sents)), 1)
    out["_总字"] = wc(text)
    return out


def main():
    chapters = json.load(open("/tmp/bt_chapters.json", encoding="utf-8"))
    print("=" * 64)
    print("质量评估 + 读端点修复验证")
    print("=" * 64)

    # ── 1. 硬指标 ──
    print("\n【1. 硬指标】")
    ge = [c for c in chapters if c["wc"] >= 5000]
    print(f"  章数 {len(chapters)} | ≥5000字 {len(ge)}/{len(chapters)} | "
          f"字数 {[c['wc'] for c in chapters]}")
    print(f"  限知泄露/章 {[c['leaks'] for c in chapters]} (目标全0) | "
          f"跨章复读/章 {[c['xrep'] for c in chapters]}")

    # ── 2. 风格密度 ──
    print("\n【2. 乱世铜炉风格密度(‰每千字)】")
    sd = style_dims(chapters)
    for k, v in sd.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}‰")
    print(f"  句均长: {sd['_句均长']}字  | 总字: {sd['_总字']}")

    # ── 3. HTTP 读端点修复验证(第三轮)──
    print("\n【3. 读端点修复验证(book_bfd18b78)】")
    checks = []

    # 3a. /post-check degraded 字段(P1-b)+ 限知泄露
    try:
        pc = post(f"/post-check?work={WORK}&seq=1",
                  {"prose": chapters[0]["prose"], "focalizer": chapters[0]["foc"]})
        has_deg = "degraded" in pc and "degraded_stages" in pc
        checks.append(("/post-check 含 degraded+degraded_stages(P1-b)", has_deg))
        checks.append((f"/post-check seq1 leaks={len(pc.get('leaks',[]))}", len(pc.get("leaks", [])) == 0))
    except Exception as e:
        checks.append((f"/post-check 调用: {str(e)[:60]}", False))

    # 3b. /project-tree 素材支不泄密(P0审计核心)
    try:
        tree = get(f"/project-tree?work={WORK}")
        blob = json.dumps(tree, ensure_ascii=False)
        SECRETS = ["另半截在白姑手中", "续来之魂渐成厉", "活炉游走城中收阳寿",
                   "满门借寿暴毙", "清潭门弃徒", "香堂以活炉游走城中收阳寿牟利"]
        leaked = [s for s in SECRETS if s in blob]
        checks.append(("/project-tree 素材支不含私密明文", not leaked))
        if leaked:
            print("   ⚠ project-tree 泄密:", leaked)
    except Exception as e:
        checks.append((f"/project-tree: {str(e)[:60]}", False))

    # 3c. /timeline 结构(P1-d N+1 重构后结构一致)
    try:
        tl = get(f"/timeline?work={WORK}")
        ok_tl = isinstance(tl, dict) or isinstance(tl, list)
        checks.append(("/timeline 返回正常(P1-d重构后)", bool(tl) and ok_tl))
    except Exception as e:
        checks.append((f"/timeline: {str(e)[:60]}", False))

    # 3d. /outline
    try:
        ol = get(f"/outline?work={WORK}")
        checks.append(("/outline 返回卷章结构", bool(ol)))
    except Exception as e:
        checks.append((f"/outline: {str(e)[:60]}", False))

    # 3e. /promises/ledger
    try:
        led = get(f"/promises/ledger?work={WORK}")
        checks.append(("/promises/ledger 返回伏笔台账", led is not None))
    except Exception as e:
        checks.append((f"/promises/ledger: {str(e)[:60]}", False))

    # 3f. /factions 私密屏蔽(REST,对照 s3_list_factions 修复)
    try:
        fac = get(f"/factions?work={WORK}")
        blob = json.dumps(fac, ensure_ascii=False)
        leaked_priv = "香堂以活炉游走城中收阳寿牟利" in blob or "续命牟利" in blob
        checks.append(("/factions private_operation 屏蔽", not leaked_priv))
    except Exception as e:
        checks.append((f"/factions: {str(e)[:60]}", False))

    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")

    # ── 汇总 ──
    passed = sum(1 for _, ok in checks if ok)
    all_ge5000 = len(ge) == len(chapters)
    all_no_leak = all(c["leaks"] == 0 for c in chapters)
    print("\n" + "=" * 64)
    print(f"硬指标: 5章≥5000字 {'✅' if all_ge5000 else '❌'} | 限知零泄露 {'✅' if all_no_leak else '❌'}")
    print(f"读端点验证: {passed}/{len(checks)} 通过")
    print("=" * 64)


if __name__ == "__main__":
    main()
