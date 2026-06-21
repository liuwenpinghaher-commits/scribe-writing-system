"""id 归一:domain 方法须同时接受裸 hex 与 'work:hex'。
根因:list_works/get_work 返回 'work:hex',但写引用方法做 f'work:{work}'。
主编 agentic 先 list_works(得 'work:hex')再 list_characters(那 id)会双前缀→空。
"""
from scribe2.conn import domain_from


def test_list_characters_accepts_prefixed_work_id(db):
    d = domain_from(db); d.s.init_schema()
    wid = d.create_work("书")            # 裸 hex(create_work 返回)
    d.add_character(wid, "沈舟", "查父亲沉船真相")
    wfull = d.list_works("u1")[0]["id"]  # 'work:hex'(list_works 返回)
    # 两种 id 格式都该查到角色
    assert len(d.list_characters(wid)) == 1
    assert len(d.list_characters(wfull)) == 1, "list_characters 须接受 'work:hex' 格式"


def test_settings_and_intent_accept_prefixed_work_id(db):
    d = domain_from(db); d.s.init_schema()
    wid = d.create_work("书")
    d.add_setting(wid, "古渡", "浊河北岸", "place")
    d.set_intent(wid, reader_feeling="苍凉")
    wfull = d.list_works("u1")[0]["id"]  # 'work:hex'
    assert len(d.list_settings(wfull)) == 1, "list_settings 须接受 'work:hex'"
    assert d.get_intent(wfull) and d.get_intent(wfull)["reader_feeling"] == "苍凉"
