#!/usr/bin/env python3
"""灌入角色深描数据到运行DB"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scribe3.store import SurrealStore

st = SurrealStore(url='ws://127.0.0.1:8001/rpc', ns='scribe3', db='main')

profiles = {
    '胡不为': dict(
        appearance='约三十一二年纪,甚是瘦弱,着一袭半旧的黄布直裰,唇上留了两条细细的髭胡。',
        personality_detail='贪财怕死,心思活络,嘴上天花乱坠实则胆子极小。但关键时刻良心未泯,能做出正确的选择。',
        abilities='[{"name":"风水堪舆","level":"忽悠级"},{"name":"灵龙镇煞钉","level":"持有(不懂用法)"}]',
        weaknesses=['贪财','怕死','爱吹牛','对妖怪毫无抵抗之力'],
        surface_goal='挣钱糊口,安全回家', deep_need='活下去,不做亏心事', internal_conflict='贪财vs良心', fear='妖怪、厉鬼、黑暗中独自一人',
        first_appearance=2),
    '老乌头': dict(
        appearance='半边脸上扭曲突结,连到额头上方,毛发尽无,疤痕板结光润。左手齐肘断掉,只余一副空荡荡的袖子。',
        personality_detail='沉默寡言,一生坚守家族使命。孤独而执着,明知力不从心仍不放弃。',
        abilities='[{"name":"镇守术(残缺)","level":"仅余巡查"}]',
        weaknesses=['残废','孤独','无道术传承'],
        surface_goal='守住奈何谷封印', deep_need='完成家族四百年使命', internal_conflict='力不从心vs不能放弃', fear='厉鬼脱困涂炭生灵',
        first_appearance=1),
    '蔺得岷': dict(
        appearance='面如重枣的长须老者,剑眉朗目,颇有威严。',
        personality_detail='正统名门大师兄,爱面子,但遇事能拿主意。对门派声誉看得极重。',
        abilities='[{"name":"捉妖术","level":"中等"},{"name":"天周盘","level":"熟练"}]',
        weaknesses=['好面子','实力一般','对青叶门心怀忌惮'],
        surface_goal='捉拿犯查兽', deep_need='维护严台山声誉', internal_conflict='实力vs面子', fear='在师弟面前丢脸',
        first_appearance=3),
    '赵姑娘': dict(
        appearance='年轻女子,白衣,裙幅低垂,长袖翩翩,由风而动。仙姿妙态,直如凌波神女。',
        personality_detail='说话稚嫩温柔如黄莺,但暗藏锋芒。好整以暇,不急不躁。背景深不可测。',
        abilities='[{"name":"竹笛术","level":"不明(极高)"}]',
        weaknesses=['自负'],
        surface_goal='夺取犯查还丹', deep_need='完成门主任务', internal_conflict='玩闹vs认真', fear='无',
        first_appearance=3),
    '时闻盂': dict(
        appearance='体格瘦小的青年,一双黝黑的细爪子如抖筛子般。',
        personality_detail='村中普通青年,好面子能喝酒。机缘巧合下开了阴阳眼,从此人生改变。',
        abilities='[{"name":"阴阳眼","level":"天生(不可逆)"}]',
        weaknesses=['胆小','好面子'],
        surface_goal='适应阴阳眼', deep_need='找到人生方向', internal_conflict='普通人vs通灵者', fear='看到不该看的东西',
        first_appearance=1),
}

for name, p in profiles.items():
    sql = "UPDATE type::thing('character', $n) SET appearance=$ap, personality_detail=$pd, abilities=$ab, weaknesses=$wk, surface_goal=$sg, deep_need=$dn, internal_conflict=$ic, fear=$fr, first_appearance=$fa"
    st._db.query(sql, {'n': name, 'ap': p['appearance'], 'pd': p['personality_detail'],
                       'ab': p.get('abilities'), 'wk': p.get('weaknesses', []),
                       'sg': p['surface_goal'], 'dn': p['deep_need'],
                       'ic': p['internal_conflict'], 'fr': p['fear'],
                       'fa': p.get('first_appearance')})
    print(f"  {name}: profile set", flush=True)

# 验证
for c in st.characters():
    sg = (c.traits or {}).get('surface_goal', '')
    if sg:
        print(f"  {c.name}: goal={sg[:30]}", flush=True)
st.close()
print("\nDone.", flush=True)
