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

# 纪律门控:LLM 判官检语义违规(双高潮/声音崩/解说倾泻)→截到复发点+续写,循环至守纪
BRIEF = INSTR0[:380]
for it in range(2):
    dc = cli.post(f"/works/{WID}/chapters/{SEQ}/discipline-check", json={"brief": BRIEF})
    if dc.status_code >= 300:
        print("纪律端点", dc.status_code); break
    v = dc.json()
    if v.get("ok") or not v.get("cut_after"):
        print("纪律✓ 守纪"); break
    idx = full.find(v["cut_after"])
    if idx < 0:
        print(f"纪律✗ {v.get('violations')} 但复发点未定位,跳过"); break
    cut = full[:idx + len(v["cut_after"])]
    print(f"纪律✗ {v.get('violations')} 复发@{idx}({idx*100//max(len(full),1)}%)→截断+续写")
    secs2, prev2 = [cut], cut[-1800:]
    while sum(len(s) for s in secs2) < CAP and len(secs2) < 3:
        rr = cli.post(f"/works/{WID}/chapters/{SEQ}/actions/continue",
                      json={"instruction": "严守本章命题、把这一章在既定克制范围内自然写完并冷笔收尾:绝不另起第二场打斗/高潮、绝不偷跑后续章剧情、绝不发明新登场角色;terse 角色(如阿萤)只零星碎语≤10字半截就断、不大段独白、不与主角同温。", "target_chars": 1300, "prev": prev2})
        if rr.status_code >= 300:
            break
        secs2.append(rr.json()["content"].strip())
        prev2 = ("\n".join(secs2))[-1800:]
    full = _dedup("\n\n".join(secs2))

_save(full)
path = f"/tmp/newbook_ch{SEQ}.txt"
open(path, "w").write(full)
print(f"=== 第{SEQ}章 {len(full)}字 → {path} ===")
print(full[:200])
