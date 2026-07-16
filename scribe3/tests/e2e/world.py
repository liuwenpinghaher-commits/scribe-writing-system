"""乱世铜炉设定数据——两档 e2e 共用。真调档经前端/MCP 写,确定性档直接填 store。

只提炼六类 e2e 测试所需的自洽子集(非复刻 tools/e2e_test.py 的全量质量分析数据):
角色/世界规则/势力各若干 + 一条【焦点角色不知情】的秘密事实(供限知泄露测试③)。
"""
from scribe3.ontology import Entity, Fact


def populate(st):
    """把一套自洽的限知设定写进 store(角色/规则/势力/秘密事实)。"""
    # 角色
    st.add_entity(Entity("role:胡不为", "character", "胡不为",
                         traits={"backstory": "风水师/江湖骗子,贪财怕死有底线。",
                                 "personality_tags": ["贪财", "怕死", "机敏", "有底线"]}))
    st.add_entity(Entity("role:老乌头", "character", "老乌头",
                         traits={"backstory": "乌家第32代守墓人。",
                                 "personality_tags": ["坚守", "孤独", "忠义"]}))
    # 世界规则
    st.add_world_rule("灵龙镇煞钉", "magic", source="阳铜黑狗血七七四十九天炼成",
                      limitations=["造法费心费力"], scope="global", established_chapter=1)
    # 势力
    st.add_faction("青叶门", ideology="夺妖兽还丹", status="active",
                   public_face="仙子门派", private_operation="掠夺妖兽内丹", first_mention_chapter=2)
    # 秘密事实(限知泄露测试③要用:focalizer 胡不为【不知情】的秘密)。
    # leak_markers 是系统为限知泄露设计的"破绽词":出现在非持有者视角散文里=穿帮
    # (find_leaks 用 leak_markers or [value] 逐个 re 匹配,故 marker 必须是 prose 里的精确子串)。
    st.add_fact(Fact("fact:secret1", "role:老乌头", "隐情",
                     "老乌头是乌家末代守墓人,四百年封印将破", valid_from=1, secret=True,
                     leak_markers=["末代守墓人"]))
    st.semantic_index("fact:secret1", "老乌头是乌家末代守墓人,四百年封印将破")


# 限知泄露测试用:一段"焦点角色不该知道的秘密泄进正文"的稿子
LEAK_PROSE = "胡不为一眼就看穿,老乌头竟是乌家末代守墓人,那封印四百年将破。"
LEAK_FOCALIZER = "role:胡不为"      # 胡不为视角,不该知道老乌头的隐情
LEAK_SECRET_MARKER = "末代守墓人"
