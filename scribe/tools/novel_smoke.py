"""生成管线真实冒烟测试:REST 驱动 doubao 写一章,观察真实输出。
跑:cd scribe && .venv/bin/python tools/novel_smoke.py
"""
import time
import httpx

BASE = "http://127.0.0.1:3320"
OWNER = "novelist-smoke"
H = {"X-Owner-Id": OWNER, "Content-Type": "application/json"}


def main():
    c = httpx.Client(base_url=BASE, headers=H, timeout=300)

    # 1. 建作品
    wid = c.post("/works", json={
        "title": "冒烟·生成测试", "premise": "乱世之中一座会吞噬人命的古铜炉", "genre": "古典志怪武侠",
    }).json()["work_id"]
    print("work_id:", wid)

    # 2. 北极星(真实跑 intent 功能)
    r = c.put(f"/works/{wid}/author-intent", json={
        "reader_feeling": "苍凉、克制、宿命般的悲悯,读罢久久不能言语",
        "core_emotional_arc": "懵懂少年目睹乱世人命如草芥,由麻木到痛,再到以一身担一炉之业",
        "why_write": "写乱世里小人物的尊严",
        "central_promise": "铜炉吞命,而人心可逆天命",
        "do_not_betray": ["不用现代词汇与网络腔", "不直白说教", "悲剧不廉价、不煽情"],
    })
    print("intent:", r.status_code)

    # 3. 建第 1 章(真实跑 chapter 功能)
    r = c.put(f"/works/{wid}/chapters", json={
        "seq": 1, "title": "引子·铜炉夜啼",
        "outline": {"beats": ["村中喜宴夜,醉汉横尸于铜炉旁", "炉中似有低啼", "少年撞见,命运由此改写"]},
    })
    cid = r.json()["chapter_id"]
    print("chapter_id:", cid)

    # 4. 真实调 continue 生成(验证转向修复:吃 instruction + 长度可控)
    t0 = time.time()
    r = c.post(f"/works/{wid}/chapters/1/actions/continue", json={
        "instruction": "写一个守炉老人,名叫『聋伯』,深夜独自往那尊古铜炉里添炭;他听不见声响,却觉出炉壁发烫、炉中似有人语。要出现『聋伯』『添炭』『铜炉』。",
        "target_chars": 700,
    })
    dt = time.time() - t0
    if r.status_code != 200:
        print("生成失败", r.status_code, r.text[:300])
        return
    content = r.json()["content"]
    print(f"\n=== 生成耗时 {dt:.1f}s,字数 {len(content)} ===\n")
    print(content)

    # 5. 成本账本(真实跑 cost 功能)
    print("\n=== 成本 ===", c.get(f"/works/{wid}/cost").json())


if __name__ == "__main__":
    main()
