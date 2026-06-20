from scribe2.conn import domain_from
def test_domain_from_conn(db):
    d = domain_from(db); d.s.init_schema()
    w = d.create_work("接线书")
    assert d.get_work(w)["title"] == "接线书"
