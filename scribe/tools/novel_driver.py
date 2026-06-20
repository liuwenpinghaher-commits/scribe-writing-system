"""端到端小说驱动:用 scribe 真实 REST 系统写《九原渡》。

真实跑系统每个功能:北极星(intent)、设定(setting)、角色(character)、
伏笔(foreshadow)、卷(volume)、章(chapter)、生成(actions/continue)、
定稿(prose,触发后台章记忆/索引/一致性)、评改(critique)。

逐节拍生成:每个 beat 一次 continue(target_chars 控长 + 把本章前文塞进 instruction
保持连贯);_writing_context 自动注入跨章圣经/记忆。一章拼好后 save_prose 一次,
触发 ingest_chapter 建滚动摘要(供下一章 _writing_context)。

用法:
  cd scribe && .venv/bin/python tools/novel_driver.py --max-chapters 1     # 先写1章验证
  cd scribe && .venv/bin/python tools/novel_driver.py --max-chapters 10    # 写到第10章
  cd scribe && .venv/bin/python tools/novel_driver.py                      # 写完所有已设计章
可重复跑:已写的章自动跳过(state 文件记 done_seqs)。
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:3320"
OWNER = "jiuyuandu-author"

# 针对 critique 弱项(pace/coherence/surprise)的通用笔法提示,逐节附在 instruction 后
CRAFT_NOTE = (
    "【笔法】文白相间,古典白话;长短句交错,切忌每句都堆明喻(比喻精而不滥);"
    "有冲突/相遇处多用人物对话与动作推进剧情,让节奏有张有弛、有进展;"
    "每节至少一处意外或转折(期望反转/代价放大/信息不对称),不要平铺直叙、不要只写静态氛围;"
    "结尾让画面收束,不写顿悟升华句。"
)
HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / ".novel_state.json"
OUT_DIR = HERE.parent / "out" / "九原渡"


def _cjk_len(s: str) -> int:
    """中文字数:数汉字,不含标点空白。"""
    return len(re.findall(r"[一-鿿]", s or ""))


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def save_state(st: dict) -> None:
    STATE_PATH.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class Driver:
    def __init__(self, bible: dict, state: dict):
        self.bible = bible
        self.state = state
        self.c = httpx.Client(base_url=BASE, headers={"X-Owner-Id": OWNER},
                              timeout=600)

    # ---- 一次性建圣经(状态标记防重复 plant/volume)----
    def ensure_work(self):
        wid = self.state.get("work_id")
        if wid:
            r = self.c.get(f"/works/{wid}")
            if r.status_code == 200:
                return wid
        b = self.bible
        wid = self.c.post("/works", json={
            "title": b["title"], "premise": b["premise"], "genre": b["genre"],
        }).json()["work_id"]
        self.state["work_id"] = wid
        self.state["bible_built"] = False
        self.state["done_seqs"] = []
        save_state(self.state)
        log(f"建作品 {b['title']}: {wid}")
        return wid

    def build_bible(self, wid: str):
        if self.state.get("bible_built"):
            return
        b = self.bible
        # 北极星
        self.c.put(f"/works/{wid}/author-intent", json=b["intent"]).raise_for_status()
        log("北极星 已设")
        # 设定
        for s in b["settings"]:
            self.c.post(f"/works/{wid}/settings", json={
                "type_": s["type"], "name": s["name"], "description": s["description"],
            }).raise_for_status()
        log(f"设定 已写 {len(b['settings'])} 条")
        # 角色(含声音指纹 voice_profile.tone,供 _writing_context 注入)
        for ch in b["characters"]:
            self.c.post(f"/works/{wid}/characters", json={
                "name": ch["name"], "traits": ch.get("traits", {}),
                "motivation": ch.get("motivation", ""),
                "voice_profile": {"tone": ch.get("voice", "")},
            }).raise_for_status()
        log(f"角色 已建 {len(b['characters'])} 个")
        # 伏笔(REST plant 端点)
        self._plant_foreshadows(wid, b["foreshadows"])
        # 卷
        vol_map = {}
        for v in b["volumes"]:
            r = self.c.post(f"/works/{wid}/volumes", json={
                "seq": v["seq"], "title": v["title"], "arc_goal": v["arc_goal"]})
            r.raise_for_status()
            vol_map[str(v["seq"])] = r.json()["volume_id"]
        self.state["vol_map"] = vol_map
        log(f"卷 已建 {len(vol_map)} 卷")
        self.state["bible_built"] = True
        save_state(self.state)

    def _plant_foreshadows(self, wid: str, fores: list):
        planted = 0
        for f in fores:
            r = self.c.post(f"/works/{wid}/foreshadows", json={
                "summary": f["summary"], "foreshadow_chapter": f["chapter"],
                "importance": f.get("importance", "normal")})
            if r.status_code in (200, 201):
                planted += 1
            else:
                log(f"  伏笔 plant 失败 {r.status_code}: {f['summary'][:18]} -> {r.text[:80]}")
        log(f"伏笔 已埋 {planted}/{len(fores)} 条")

    # ---- 逐节拍写一章 ----
    def write_chapter(self, wid: str, ch: dict, target: int) -> dict:
        seq = ch["seq"]
        vol_id = self.state.get("vol_map", {}).get(str(ch.get("volume_seq", "")))
        self.c.put(f"/works/{wid}/chapters", json={
            "seq": seq, "title": ch["title"], "volume_id": vol_id,
            "outline": {"beats": ch["beats"]}}).raise_for_status()

        acc = ""
        for i, beat in enumerate(ch["beats"], 1):
            instr = ""
            if acc:
                instr += f"【本章前文(承接它继续,语气连贯,绝不重写或复述)】\n{acc[-1600:]}\n\n"
            instr += f"【本节要写(第{i}/{len(ch['beats'])}节,照此推进,不要另起炉灶)】\n{beat}"
            instr += "\n\n" + CRAFT_NOTE
            txt = self._gen_beat(wid, seq, instr, target)
            if not txt:
                log(f"  第{seq}章 第{i}节 生成空,重试一次")
                txt = self._gen_beat(wid, seq, instr, target)
            acc += ("\n\n" if acc else "") + txt.strip()
            log(f"  第{seq}章 第{i}/{len(ch['beats'])}节 +{_cjk_len(txt)}字 (累计{_cjk_len(acc)})")

        # 定稿(触发后台 ingest:章摘要/角色状态/关系/索引/一致性)
        self.c.post(f"/works/{wid}/chapters/{seq}/prose",
                    json={"content": acc, "lock": False}).raise_for_status()
        # 落地本地文件
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / f"第{seq:02d}章_{ch['title']}.md").write_text(
            f"# 第{seq}章 {ch['title']}\n\n{acc}\n", encoding="utf-8")
        # 等 ingest 把本章摘要建好(供下一章 _writing_context)
        self._wait_ingest(wid, seq)
        # 评分(真实跑 critique,仅评分不重写)
        score = self._critique_score(wid, seq)
        self.state.setdefault("done_seqs", []).append(seq)
        save_state(self.state)
        return {"seq": seq, "chars": _cjk_len(acc), "score": score}

    def _gen_beat(self, wid: str, seq: int, instruction: str, target: int) -> str:
        for attempt in range(3):
            try:
                r = self.c.post(f"/works/{wid}/chapters/{seq}/actions/continue",
                                json={"instruction": instruction, "target_chars": target})
                if r.status_code == 200:
                    return r.json().get("content", "")
                log(f"    gen {r.status_code}: {r.text[:120]}")
            except Exception as e:
                log(f"    gen 异常: {str(e)[:120]}")
            time.sleep(3 + attempt * 4)
        return ""

    def _wait_ingest(self, wid: str, seq: int, timeout: float = 180):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                mem = self.c.get(f"/works/{wid}/memory").json()
                if any(m.get("seq") == seq for m in mem.get("chapters", [])):
                    log(f"  第{seq}章 摘要已建 ({time.time()-t0:.0f}s)")
                    return
            except Exception:
                pass
            time.sleep(5)
        log(f"  第{seq}章 摘要等待超时,继续")

    def _critique_score(self, wid: str, seq: int) -> dict:
        try:
            r = self.c.post(f"/works/{wid}/chapters/{seq}/critique",
                            json={"content": "", "revise": False})
            if r.status_code == 200:
                crit = r.json().get("critique", {})
                log(f"  第{seq}章 评分 overall={crit.get('overall')} pass={crit.get('pass')} "
                    f"弱项={crit.get('worst_dims')}")
                return crit
        except Exception as e:
            log(f"  critique 异常: {str(e)[:100]}")
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bible", default=str(HERE / "bible_jiuyuandu.json"))
    ap.add_argument("--max-chapters", type=int, default=0, help="本次最多写几章(0=全部)")
    ap.add_argument("--target-chars", type=int, default=850, help="每节拍目标字数")
    args = ap.parse_args()

    bible = json.loads(Path(args.bible).read_text(encoding="utf-8"))
    state = load_state()
    d = Driver(bible, state)

    # 健康检查
    if d.c.get("/health").status_code != 200:
        log("后端 :3320 未就绪"); sys.exit(1)

    wid = d.ensure_work()
    d.build_bible(wid)

    done = set(d.state.get("done_seqs", []))
    todo = [ch for ch in bible["chapters"] if ch["seq"] not in done]
    if args.max_chapters > 0:
        todo = todo[:args.max_chapters]
    log(f"待写 {len(todo)} 章: {[c['seq'] for c in todo]}")

    total_chars = 0
    for ch in todo:
        t0 = time.time()
        res = d.write_chapter(wid, ch, args.target_chars)
        total_chars += res["chars"]
        log(f"✓ 第{res['seq']}章《{ch['title']}》完成 {res['chars']}字 "
            f"用时{time.time()-t0:.0f}s | 本次累计 {total_chars}字")

    # 全书累计字数
    try:
        summ = d.c.get("/works").json()
        wc = next((w.get("word_count") for w in summ if w.get("id") == wid), "?")
        log(f"全书累计字数(库): {wc}")
    except Exception:
        pass
    log("本次运行结束")


if __name__ == "__main__":
    main()
