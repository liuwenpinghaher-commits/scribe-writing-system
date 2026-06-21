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
secs = []
prev = ""
for i in range(3):
    instr = INSTR0 if i == 0 else CONT
    r = cli.post(f"/works/{WID}/chapters/{SEQ}/actions/continue",
                 json={"instruction": instr, "target_chars": 1150, "prev": prev})
    if r.status_code >= 300:
        print("✗ gen", i, r.status_code, r.text[:200]); sys.exit(1)
    sec = r.json()["content"].strip()
    secs.append(sec)
    prev = ("\n".join(secs))[-1800:]
    print(f"  节{i+1}: +{len(sec)}字  累计{sum(len(s) for s in secs)}")

full = "\n\n".join(secs)
r = cli.post(f"/works/{WID}/chapters/{SEQ}/prose", json={"content": full, "lock": False})
print("存稿", r.status_code)

# 生成后去重通道(跨段复读 prompt 治不了,确定性扫描+定向改写)
rd = cli.post(f"/works/{WID}/chapters/{SEQ}/dedup", json={})
if rd.status_code < 300:
    j = rd.json()
    print(f"去重: changed={j['changed']} 复读{len(j['reps'])}处 → {j.get('saved_len')}字")
    if j["changed"]:
        full = j.get("text") or full   # 端点回传去重后正文
else:
    print("去重端点", rd.status_code, rd.text[:120])

path = f"/tmp/newbook_ch{SEQ}.txt"
open(path, "w").write(full)
print(f"=== 第{SEQ}章 {len(full)}字 → {path} ===")
print(full[:300])
