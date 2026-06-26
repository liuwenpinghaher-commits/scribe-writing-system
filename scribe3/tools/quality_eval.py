#!/usr/bin/env python3
"""质量评测:生成文本 vs 原文,逐维度对比分析根因。"""
import sys, os, re, json, requests
from collections import Counter

BASE = 'http://127.0.0.1:3321'

# 取已存的第1章
r = requests.get(f'{BASE}/chapter?seq=1&work=main')
prose = r.json().get('prose', '')
wc = len(''.join(prose.split()))
print(f'=== 生成第1章: {wc}字 ===')

# 取原文前20000字
with open(os.path.join(os.path.dirname(__file__), '..', '..', '乱世铜炉.md'), encoding='utf-8') as f:
    orig = f.read(20000)
orig_wc = len(''.join(orig.split()))
print(f'=== 原文前段: {orig_wc}字 ===\n')

def analyze(text, label):
    wc = len(''.join(text.split()))
    sents = [s.strip() for s in re.split(r'[。！？\n]', text) if len(s.strip()) > 0]
    avg_len = sum(len(s) for s in sents) // max(1, len(sents))

    dims = {
        '环境描写': r'夜幕|月色|风声|雾气|烛光|月光|炊烟|翠竹|潭水|峡谷|树林|岩壁|古榕|桃李|唢呐|红布|蜘蛛|田泥|草屑|酒气',
        '身体动作': r'颤着手|膝一软|翻倒|踉跄|瘫坐|跪在|冲到|俯身|搀抱|策马|牵驴|蹲|吐|抹|刮|撑|攥|捏|推|拽',
        '心理活动': r'心中|暗想|暗呼|心下|心知|心底|只觉|觉得|想道|暗道|料想|心脏|猛地',
        '感官描写': r'听见|看到|闻到|感觉|觉得|触到|听来|闻到了|看见了|摸了摸|辣|温热|凉|腥|涩',
        '对话标记': r'[「」""""].{2,}|说道|问道|答道|喊道|叫道',
    }
    print(f'--- {label} ({wc}字, {len(sents)}句, 均{avg_len}字/句) ---')
    for name, pat in dims.items():
        matches = len(re.findall(pat, text))
        per_k = matches / max(1, wc) * 1000
        print(f'  {name}: {matches}次 ({per_k:.1f}千分号)')

    # AI腔
    ai = re.findall(r'嘴角勾起|眼底闪过|命运的齿轮|心中一紧|不由得|不禁|仿佛|似乎|宛如|犹如', text)
    print(f'  AI腔套语: {len(ai)}处')

    # 跨段复读
    ngrams = Counter(text[i:i+8] for i in range(len(text)-8))
    repeats = [(g, c) for g, c in ngrams.most_common(20) if c >= 3 and not re.match(r'^[\s，。！？；：、]+$', g)]
    print(f'  跨段复读(8字>=3次): {len(repeats)}处')
    if repeats:
        for g, c in repeats[:3]:
            print(f'    "{g}" x{c}')

    # 段落长度分布
    paras = [p.strip() for p in text.split('\n') if p.strip()]
    if paras:
        para_lens = [len(p) for p in paras]
        print(f'  段落数: {len(paras)}, 均长: {sum(para_lens)//len(paras)}字, 最长: {max(para_lens)}字')

    return {'wc': wc, 'avg_sent': avg_len, 'repeats': len(repeats), 'ai': len(ai)}

gen_stats = analyze(prose, '生成')
print()
orig_stats = analyze(orig, '原文')

print('\n=== 根因分析 ===')
print(f'1. 句长: 生成{gen_stats["avg_sent"]}字 vs 原文{orig_stats["avg_sent"]}字')
print(f'2. 跨段复读: 生成{gen_stats["repeats"]}处 vs 原文{orig_stats["repeats"]}处')
print(f'3. AI腔: 生成{gen_stats["ai"]}处 vs 原文{orig_stats["ai"]}处')
print(f'4. 字数: 生成{gen_stats["wc"]}字 vs 原文{orig_stats["wc"]}字')

# 生成文本的续写拼接痕迹
print('\n=== 拼接痕迹检测 ===')
# 找段落边界处的断裂(上下文不连贯)
paras = [p.strip() for p in prose.split('\n\n') if p.strip()]
print(f'段落数(双换行分割): {len(paras)}')
if len(paras) > 3:
    for i in range(2, len(paras)-1, 2):
        prev_end = paras[i-1][-50:] if len(paras[i-1]) > 50 else paras[i-1]
        curr_start = paras[i][:50] if len(paras[i]) > 50 else paras[i]
        print(f'  段{i}: ...{prev_end}')
        print(f'       {curr_start}...')
