login 200
health 200 True
post_check 200 ok_for_claim False phase red
claim meta 409 {"detail": {"code": "reader_claim", "message": "正文未过可读机判（含验收腔或场面未覆盖）", "blocking": ["anti_meta.M2", "anti_meta.M6", "anti_meta.M2", "anti_meta.M3", "anti_meta.M1", "anti_meta.M1", "anti_meta.M1", "anti_meta.M1", "anti_me
claim code reader_claim
save 200 saved
omit omit 开放伏笔 False
ack 200 {'ok': True, 'work': 'book_qe_live5', 'seq': 2, 'ack': {'id': {'table_name': 'chapter_reader_ack', 'id': 'book_qe_live5_2'}, 'note': 'smoke', 'prose_fp': '8afa1
ALL_DEMO_SMOKE_OK
