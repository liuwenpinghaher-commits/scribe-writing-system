#!/usr/bin/env python3
"""业务测试·第三轮:基于设定+推演,生成5章正文,每章≥5000字,限知双POV。
复用 app 的写作 prompt 装配(含第三轮修复的 _editor_write_system 限知屏蔽),
hermes 续写循环到目标字数;每章 find_leaks 零泄露验证 + 跨章复读度量 + 真 ingest 反哺。

跑: cd "<repo-root>" && scribe3/.venv/bin/python -u scribe3/tools/bt_render.py
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scribe3.store import SurrealStore
from scribe3.llm import hermes_complete
from scribe3.verify import find_leaks
from scribe3.ingest import ingest_chapter
from scribe3.critique import find_repetitions, find_cross_chapter_repetitions, distinctive_phrases
from scribe3.craft import build_craft_block
from scribe3 import app as A

WORK = "book_bfd18b78"
TARGET = 5200          # 每章目标字数(≥5000)
MAX_SEG = 6            # 单章最多续写段数

st = SurrealStore(ns="scribe3", db=WORK)

# 母题/专名白名单(跨章复读度量放行)
ALLOW = set()
for m in st.list_motifs() if hasattr(st, "list_motifs") else []:
    pass
ALLOW.update({"引魂铃", "回煞炉", "焚骨庵", "活炉", "清潭", "招魂幡", "叫魂郎",
              "柳三更", "白姑", "麻三娘", "焦判官", "聋祖", "阿枝", "回煞", "阳寿", "借寿"})


def wc(s):
    return len("".join(s.split()))


def build_instructions(focalizer, chapter):
    """完全复刻 app.chat_write 的 instructions 装配(验证第三轮修复后的限知 prompt)。"""
    instr = A._editor_write_system(st, focalizer=focalizer, chapter=chapter)
    instr += f"\n当前第 {chapter} 章。"
    if focalizer:
        instr += f"作者指定本章跟随焦点者 {focalizer} 的限知视角:贴该角色所知所感写,别写他不知道的私密。"
    instr += A._avoid_directive(st, chapter)
    instr += A._voice_anchor_block(st, focalizer)
    instr += A._arc_state_block(st, focalizer, chapter)
    instr += A._motif_block(st)
    instr += A._frame_block(st, focalizer, chapter)
    instr += A._revelation_discipline_block(focalizer)   # 机制M1:限知揭示纪律(配角不批发真相)
    instr += A._recap_block(st, chapter)
    craft = build_craft_block(st.list_craft_rules() or None)
    if craft:
        instr += "\n\n" + craft
    instr += A._final_reminder()
    return instr


def _strip_preamble(seg):
    """剥离模型偶尔产出的解说开场(如'好的,下面…')。"""
    seg = seg.strip()
    for mark in ["以下是", "好的", "下面我", "我来写", "（", "【思路", "本章"]:
        if seg[:6].startswith(mark):
            nl = seg.find("\n")
            if 0 < nl < 60:
                seg = seg[nl + 1:].strip()
                break
    return seg


def render_chapter(focalizer, chapter, title, syn, beats):
    instr = build_instructions(focalizer, chapter)
    beat_txt = "\n".join(f"  {i+1}. {b}" for i, b in enumerate(beats))
    open_msg = (
        f"写《{title}》。本章大纲:{syn}\n本章节拍(依次推进,每拍都要落到具体场景/动作/对话,忌概述):\n{beat_txt}\n\n"
        f"严格跟随 {focalizer} 的限知视角,志怪笔记体,冷峻克制有留白。"
        f"先写本章前两个节拍,约2000字。直接写正文,不要任何解说或标题。")
    prose = _strip_preamble(hermes_complete(open_msg, system=instr))
    seg = 1
    while wc(prose) < TARGET and seg < MAX_SEG:
        remain = TARGET - wc(prose)
        tail = prose[-700:]
        cont_msg = (
            f"本章已写到此处(节选末段,供你接续,切勿重写已有内容):\n…{tail}\n\n"
            f"紧接着往下写,推进到后续节拍(本章节拍:{syn})。约+{max(1500, remain)}字。"
            f"换感官/换喻体/换节奏,不得逐字复用前文措辞;保持 {focalizer} 限知视角与志怪笔记体。"
            f"直接写正文,不要解说。")
        nxt = _strip_preamble(hermes_complete(cont_msg, system=instr))
        if wc(nxt) < 50:
            break
        prose += "\n\n" + nxt
        seg += 1
    return prose


# ── 5章节拍(总纲→大纲→节拍:每章4-5拍具体场景)──
CHAPTERS = [
    ("role:柳三更", 1, "第一章·铃自鸣",
     "柳三更夜半为孙寡妇招魂,怀中半截引魂铃无端自鸣,引出白姑与阿枝。柳贪念与疑惧并起,白姑隐瞒。",
     ["乱葬岗夜景与柳三更招魂的行当细节(招魂幡、八字、三炷香),写他半真半骗的油滑与心虚",
      "招到一半,怀中半截引魂铃无舌自鸣,声细如游丝,亡魂似有所应,柳骇然",
      "青衣白姑携哑女阿枝自暗处现身,问铃的来历,话里藏话,处处不肯说透",
      "柳贪念又起(此铃或值钱),又疑又惧;白姑只冷冷留一句警告便去,阿枝回头看他一眼",
      "柳独留岗上,铃声未歇,夜风里像有人在喊他名字,他强自镇定收幡而归"]),
    ("role:柳三更", 2, "第二章·义庄骨",
     "柳三更求焦判官辨铃,义庄夜里见阿枝看寿灯,撞知二十年旧案的一角。麻三娘香堂的活炉踪迹初现。",
     ["柳带铃到城南义庄求老仵作焦判官辨认,义庄停尸与验骨的阴冷气氛",
      "焦判官验铃,神色微变,半吐半露提起二十年前一桩满门暴毙的旧案",
      "阿枝随白姑也在义庄,柳撞见阿枝盯着某具尸首头顶看'寿灯',童言无忌道破生死",
      "柳在义庄外听见香堂切口,瞥见一辆载着乌沉小炉的车('活炉'初现,他不知其真相)",
      "焦判官嘱柳莫沾这铃,柳口上应着,心里却盘算这铃能换几两银子"]),
    ("role:白姑", 3, "第三章·活炉影",
     "白姑限知视角:她追查活炉,揭活炉藏于临江戏班戏箱;同时察觉柳三更阳寿已被暗借。情感弧由'用柳'转向不忍。",
     ["白姑夜探临江戏班后台,戏箱、油彩、散场的冷清,她身手与心思都不似村妇",
      "她查出香堂的'活炉'就藏在戏班的戏箱里,随班游走城中收人阳寿",
      "阿枝悄悄告诉白姑:那个叫魂郎(柳)头顶的寿灯转暗了——他的阳寿正被活炉暗借",
      "白姑本只想借柳手中的半截铃成事,此刻心生不忍,回想当年自己引线之过",
      "她决意先护住柳,却仍不肯对他坦白真相,独自布下第一道清潭封煞的暗记"]),
    ("role:柳三更", 4, "第四章·焚骨庵",
     "柳三更被白姑半哄半逼同往焚骨庵,见聋祖与蒙尘本炉,铃在炉前剧鸣认主。柳惊知自己卷入大局,与白姑就毁炉起冲突。",
     ["白姑半哄半逼带柳上荒废的焚骨庵,山路、破庵、终年不熄的香火",
      "又聋又哑、半脸烧伤的守庵聋祖,沉默地守着一座丈许高、九窍刻古文的蒙尘铜炉(本炉)",
      "柳怀中半截引魂铃在本炉前骤然剧鸣、烫手,似要认主,他第一次驱使出一缕铃力",
      "柳惊知自己早已卷入一桩大局,又惧又怒,质问白姑到底要他做什么",
      "白姑只说这炉必须毁,柳本能地想逃、想保命,二人就毁炉与否正面冲突,不欢而散"]),
    ("role:白姑", 5, "第五章·借寿局",
     "白姑限知视角:麻三娘携活炉与香堂众围焚骨庵抢本炉,白姑布清潭旧阵护柳。她坦白当年引线之过,赌以铃制炉的局。高潮前夜,留余韵。",
     ["麻三娘率香堂众人连夜围上焚骨庵来抢本炉,火把、骨笛、被骨笛驱使的走尸,声势汹汹",
      "白姑布起清潭派的封煞旧阵护住柳与聋祖,真气外泄,暴露她清潭弃徒的底",
      "危急中白姑终于向柳坦白:二十年前正是她引线,才有这借寿的孽,她要赎",
      "她道出'以铃制炉'的赌局——半截铃认主之力或可反噬回煞炉,但要赌柳肯不肯",
      "高潮前夜:柳在保命逃走与信白姑留下之间挣扎,阵外骨笛声渐近,留一笔余韵收束"]),
]


def main():
    results = []
    prior = []
    t0 = time.time()
    for foc, seq, title, syn, beats in CHAPTERS:
        print(f"\n{'='*64}\n第{seq}章《{title}》· {foc} · 限知生成中…", flush=True)
        ts = time.time()
        prose = render_chapter(foc, seq, title, syn, beats)
        w = wc(prose)
        # 限知零泄露验证(第三轮 P0-1 核心)
        try:
            leaks = find_leaks(prose, st, foc, seq)
        except Exception as e:
            leaks = [{"err": str(e)[:80]}]
        # 复读度量
        rep = find_repetitions(prose)
        xrep = find_cross_chapter_repetitions(prose, prior, allow=ALLOW)
        # 落库 + 真 ingest 反哺(下一章帧据此更新)
        st.save_chapter(seq, prose, title=title, focalizer=foc)
        try:
            work = getattr(st, "db_name", None) or "main"
            ing = ingest_chapter(st, seq, hermes_complete, work=work)
        except Exception as e:
            ing = {"err": str(e)[:80]}
        dt = round(time.time() - ts)
        print(f"  字数 {w} | 限知泄露 {len(leaks)} | 单章复读 {len(rep)} | 跨章复读 {len(xrep)} "
              f"| ingest {ing.get('applied','?')} | 用时 {dt}s", flush=True)
        if leaks:
            print("   ⚠ 泄露:", json.dumps(leaks[:4], ensure_ascii=False)[:300], flush=True)
        if xrep:
            print("   跨章复读命中:", "; ".join(h["phrase"] for h in xrep[:5]), flush=True)
        print("   开头:", prose[:80].replace("\n", " "), flush=True)
        results.append({"seq": seq, "foc": foc, "title": title, "wc": w,
                        "leaks": len(leaks), "leak_detail": leaks[:6],
                        "rep": len(rep), "xrep": len(xrep),
                        "xrep_phrases": [h["phrase"] for h in xrep[:8]],
                        "prose": prose})
        prior.append(prose)

    total_w = sum(r["wc"] for r in results)
    total_leak = sum(r["leaks"] for r in results)
    total_xrep = sum(r["xrep"] for r in results)
    ge5000 = sum(1 for r in results if r["wc"] >= 5000)
    print(f"\n{'='*64}\n汇总:{len(results)}章 · 共{total_w}字 · 均{total_w//max(1,len(results))}字/章 "
          f"· ≥5000字 {ge5000}/{len(results)} · 总泄露 {total_leak} · 总跨章复读 {total_xrep} "
          f"· 全程 {round(time.time()-t0)}s", flush=True)
    json.dump(results, open("/tmp/bt_chapters.json", "w"), ensure_ascii=False, indent=1)
    print("已存 /tmp/bt_chapters.json", flush=True)
    st.close()


if __name__ == "__main__":
    main()
