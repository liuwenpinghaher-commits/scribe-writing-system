#!/usr/bin/env python3
"""重新渲染第1章并用优化后的prompt评测质量。"""
import requests, json, time, re, os, sys
from collections import Counter

BASE = 'http://127.0.0.1:3321'

print('=== 重新渲染第1章(优化后prompt v2) ===', flush=True)
t0 = time.time()
r = requests.post(f'{BASE}/render?work=main', json={
    'focalizer': 'role:时闻盂', 'chapter': 1, 'target_words': 6000, 'max_tokens': 4096
}, timeout=600)
t1 = time.time()
prose = r.json().get('prose', '')
wc = len(''.join(prose.split()))
print(f'渲染完成: {wc}字, 耗时{int(t1-t0)}秒', flush=True)

# 存稿
save_r = requests.post(f'{BASE}/save-chapter?work=main', json={
    'seq': 1, 'prose': prose, 'title': '引子·贺客', 'focalizer': 'role:时闻盂'
})
sj = save_r.json()
print(f'存稿: {sj.get("status")}, QC: rep={sj["qc"]["repetition"]} struct={sj["qc"]["structural"]} purple={sj["qc"]["purple"]} leaks={sj["leaks"]}', flush=True)

# 质量分析
ai = re.findall(r'嘴角勾起|眼底闪过|命运的齿轮|心中一紧|不由得|不禁|仿佛|似乎|宛如|犹如', prose)
ngrams = Counter(prose[i:i+8] for i in range(len(prose)-8))
repeats = [(g, c) for g, c in ngrams.most_common(20) if c >= 3 and not re.match(r'^[\s\u3000\uff0c\u3002\uff01\uff1f\uff1b\uff1a\u3001\n]+$', g)]
sents = [s.strip() for s in re.split(r'[。！？\n]', prose) if len(s.strip()) > 0]
avg_len = sum(len(s) for s in sents) // max(1, len(sents))

# 对话检测
quotes = len(re.findall(r'[""\u201c\u201d].{2,}', prose))
verbs = len(re.findall(r'说道|问道|答道|喊道|叫道|道:', prose))
dialog = quotes + verbs

# 五维度
env = len(re.findall(r'夜幕|月色|风声|雾气|烛光|月光|炊烟|翠竹|潭水|峡谷|树林|岩壁|古榕|桃李|唢呐|红布|蜘蛛|田泥|草屑|酒气', prose))
body = len(re.findall(r'颤着手|膝一软|翻倒|踉跄|瘫坐|跪在|冲到|俯身|搀抱|策马|牵驴|蹲|吐|抹|刮|撑|攥|捏|推|拽', prose))
psy = len(re.findall(r'心中|暗想|暗呼|心下|心知|心底|只觉|觉得|想道|暗道|料想|心脏|猛地', prose))
sens = len(re.findall(r'听见|看到|闻到|感觉|觉得|触到|听来|闻到了|看见了|摸了摸|辣|温热|凉|腥|涩', prose))

print(f'\n=== 质量分析 ===', flush=True)
print(f'字数: {wc} | 句长: {avg_len}字/句 | 段落: {len([p for p in prose.split(chr(10)+chr(10)) if p.strip()])}', flush=True)
print(f'环境: {env} ({env/max(1,wc)*1000:.1f}千分号) | 身体: {body} ({body/max(1,wc)*1000:.1f}千分号) | 心理: {psy} ({psy/max(1,wc)*1000:.1f}千分号) | 感官: {sens} ({sens/max(1,wc)*1000:.1f}千分号)', flush=True)
print(f'对话: {dialog}次 ({dialog/max(1,wc)*1000:.1f}千分号) | AI腔: {len(ai)}处 | 跨段复读: {len(repeats)}处', flush=True)
if repeats:
    for g, c in repeats[:5]:
        print(f'  "{g}" x{c}', flush=True)
if ai:
    print(f'  AI腔: {ai}', flush=True)

print(f'\n开头(前200字):\n{prose[:200]}', flush=True)
print(f'\n结尾(后200字):\n{prose[-200:]}', flush=True)

# 对比原文
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '乱世铜炉.md'), encoding='utf-8') as f:
    orig = f.read(20000)
orig_wc = len(''.join(orig.split()))
orig_sents = [s.strip() for s in re.split(r'[。！？\n]', orig) if len(s.strip()) > 0]
orig_avg = sum(len(s) for s in orig_sents) // max(1, len(orig_sents))
orig_env = len(re.findall(r'夜幕|月色|风声|雾气|烛光|月光|炊烟|翠竹|潭水|峡谷|树林|岩壁|古榕|桃李|唢呐|红布|蜘蛛|田泥|草屑|酒气', orig))
orig_body = len(re.findall(r'颤着手|膝一软|翻倒|踉跄|瘫坐|跪在|冲到|俯身|搀抱|策马|牵驴|蹲|吐|抹|刮|撑|攥|捏|推|拽', orig))
orig_psy = len(re.findall(r'心中|暗想|暗呼|心下|心知|心底|只觉|觉得|想道|暗道|料想|心脏|猛地', orig))
orig_sens = len(re.findall(r'听见|看到|闻到|感觉|觉得|触到|听来|闻到了|看见了|摸了摸|辣|温热|凉|腥|涩', orig))
orig_ai = re.findall(r'嘴角勾起|眼底闪过|命运的齿轮|心中一紧|不由得|不禁|仿佛|似乎|宛如|犹如', orig)

print(f'\n=== 原文对比 ===', flush=True)
print(f'原文: {orig_wc}字 | 句长: {orig_avg}字/句', flush=True)
print(f'环境: {orig_env} ({orig_env/max(1,orig_wc)*1000:.1f}千分号) | 身体: {orig_body} ({orig_body/max(1,orig_wc)*1000:.1f}千分号) | 心理: {orig_psy} ({orig_psy/max(1,orig_wc)*1000:.1f}千分号) | 感官: {orig_sens} ({orig_sens/max(1,orig_wc)*1000:.1f}千分号)', flush=True)
print(f'AI腔: {len(orig_ai)}处', flush=True)

print(f'\n=== 改进对比 ===', flush=True)
print(f'AI腔: 3处(v1) → 1处(v2) → {len(ai)}处(v3)', flush=True)
print(f'句长: 20字(v1) → 20字(v2) → {avg_len}字(v3) vs 原文{orig_avg}字', flush=True)
print(f'限知泄露: 0(v1) → 0(v2) → {sj["leaks"]}(v3)', flush=True)
