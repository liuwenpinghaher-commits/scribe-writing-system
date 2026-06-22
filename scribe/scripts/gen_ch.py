"""真机逐章生成:走 build_writing_context 注入 + Hermes。生成 N 节拼成整章→存稿→落文件。
用法:`.venv/bin/python scripts/gen_ch.py <WID> <SEQ> <第一节指令>`
"""
import sys, httpx

BASE = "http://127.0.0.1:3320"
H = {"X-Owner-Id": "u1"}
WID, SEQ = sys.argv[1], int(sys.argv[2])
INSTR0 = sys.argv[3] if len(sys.argv) > 3 else "开篇本章,古典志怪·乱世笔法,克制收尾。"
cli = httpx.Client(base_url=BASE, headers=H, timeout=1800)

CONT = "接上文自然续写,推进本章既定节奏(见上下文各线指令/伏笔节点);保持视角与声音一致,克制收尾、不点题升华。"
CAP = 4200   # 控总长~5800(节约2800字,累计≥4200即停→2节;cap在生成前检查会按整节溢出,故定低)
secs = []
prev = ""
i = 0
while sum(len(s) for s in secs) < CAP and i < 3:
    instr = INSTR0 if i == 0 else CONT
    r = cli.post(f"/works/{WID}/chapters/{SEQ}/actions/continue",
                 json={"instruction": instr, "target_chars": 1400, "prev": prev})
    if r.status_code >= 300:
        print("✗ gen", i, r.status_code, r.text[:200]); sys.exit(1)
    sec = r.json()["content"].strip()
    secs.append(sec)
    prev = ("\n".join(secs))[-1800:]
    i += 1
    print(f"  节{i}: +{len(sec)}字  累计{sum(len(s) for s in secs)}")

full = "\n\n".join(secs)
def _save(c):
    cli.post(f"/works/{WID}/chapters/{SEQ}/prose", json={"content": c, "lock": False})

def _dedup(c):  # 存稿后跑确定性去重(字面+结构+升华),回传去重后正文
    _save(c)
    rd = cli.post(f"/works/{WID}/chapters/{SEQ}/dedup", json={})
    return (rd.json().get("text") or c) if rd.status_code < 300 and rd.json().get("changed") else c

full = _dedup(full)
print(f"去重→{len(full)}字")

# 纪律门控:① 含 knowledge_leak → 外科式改那一句(不截断、保全章,craft 职业方法)
#           ② 剩结构性违规(双高潮等)→ 截到首个复发点+冷笔短收尾(续写整节必再复发)
BRIEF = INSTR0[:380]
dc = cli.post(f"/works/{WID}/chapters/{SEQ}/discipline-check", json={"brief": BRIEF})
v = dc.json() if dc.status_code < 300 else {"ok": True}
viols = list(v.get("violations") or [])
if "knowledge_leak" in viols:
    lf = cli.post(f"/works/{WID}/chapters/{SEQ}/leak-fix", json={})
    if lf.status_code < 300 and lf.json().get("changed"):
        full = lf.json().get("text") or full
        print(f"纪律:外科修泄露「{(lf.json().get('leaking') or '')[:24]}」→保全章")
    viols = [x for x in viols if x != "knowledge_leak"]
if viols and v.get("cut_after"):
    idx = full.find(v["cut_after"])
    if idx > 0:
        cut = full[:idx + len(v["cut_after"])]
        print(f"纪律✗ {viols} 复发@{idx}({idx*100//max(len(full),1)}%)→截断+冷收尾")
        rr = cli.post(f"/works/{WID}/chapters/{SEQ}/actions/continue",
                      json={"instruction": "用 2-4 句冷笔白描给这一章自然收束当前场景即可:绝不展开任何新情节/打斗/新角色/身世解说,只以一个不安的冷物象定格收尾。", "target_chars": 120, "prev": cut[-1000:]})
        ending = rr.json()["content"].strip() if rr.status_code < 300 else ""
        full = _dedup(cut + ("\n\n" + ending if ending else ""))
    else:
        print(f"纪律✗ {viols} 复发点未定位,保留原文")
elif not viols:
    print("纪律✓ 守纪")

_save(full)
path = f"/tmp/newbook_ch{SEQ}.txt"
open(path, "w").write(full)
print(f"=== 第{SEQ}章 {len(full)}字 → {path} ===")
print(full[:200])
