### http-020 · 2026-08-12T10:48:52.694039+00:00
**POST** `/api/save-chapter?work=book_qe_live5`  
note: CL-B5 legal prose path: POST /save-chapter (not emergency world REST)

```json
REQUEST
{
  "seq": 2,
  "prose": "<omitted cn_len=1823 chars_stored=1848>",
  "title": "第二章 · 齿边",
  "focalizer": "role:qin_huiqi",
  "_prose_cn_len": 1823
}
```

status: **200**

```
RESPONSE
{"status":"saved","seq":2,"qc":{"repetition":0,"structural":2,"purple":0,"cross_repetition":6,"duplicate_lines":0,"emotion_telling":0},"cross_repetition_phrases":["从怀里渗出来，像一截没烧","味从怀里渗出来，像一截没","怀里渗出来，像一截没烧完","渗出来，像一截没烧完的香","腥味从怀里渗出来，像一截","里渗出来，像一截没烧完的"],"leaks":0,"leak_error":null,"qc_errors":null,"ingesting":false,"ingest_enqueued":false,"craft_compliance":{"ok":true,"gate":"C","detail":"C-Det pass","root_causes":[],"fails":[]},"final_stamp":{"stamped":false,"allowed":true,"code":"unchanged","craft":{"allowed":true,"code":"ok","detail":"craft finalize gates pass","blocking":[],"gate_a":{"gate":"A","work":"book_qe_live5","seq":null,"ok":true,"pass":true,"checks":[{"id":"A1","ok":true,"verdict":"pass","detail":"intent 三字段非空","evidence":{"intent_keys":["reader_feeling","emotional_arc","red_lines","total_word_goal"]},"root_cause_hint":null,"hard":true},{"id":"A2","ok":true,"verdict":"pass","detail":"2 名档案齐全角色","evidence":{"ids":["role:hui_li","role:qin_huiqi"]},"root_cause_hint":null,"hard":true},{"id":"A-ARC","ok":false,"verdict":"warn","detail":"主角色缺 Lie 锚 2 人: 灰狸, 覃灰七","evidence":{"names":["灰狸","覃灰七"]},"root_cause_hint":"RC-EMPTY-AUX","hard":false},{"id":"A3","ok":true,"verdict":"pass","detail":"facts=1 rules=1","evidence":{"facts":1,"rules":1},"root_cause_hint":null,"hard":true},{"id":"A4","ok":true,"verdict":"pass","detail":"关系 1 条","evidence":{"count":1},"root_cause_hint":null,"hard":true},{"id":"A5","ok":true,"verdict":"pass","detail":"母题 1","evidence":{"names":["余烬"]},"root_cause_hint":null,"hard":true},{"id":"A6","ok":true,"verdict":"pass","detail":"open 伏笔 1","evidence":{"sample":["铜匙齿边缺口要回收"]},"root_cause_hint":null,"hard":true},{"id":"A7","ok":true,"verdict":"pass","detail":"brief.promises=dict","evidence":{},"root_cause_hint":null,"hard":true}],"blocking":[],"rc_hints":[],"degraded":[]},"gate_b":{"gate":"B","work":"book_qe_live5","seq":2,"ok":true,"pass":true,"checks":[{"id":"B1","ok":true,"verdict":"pass","detail":"大纲 99 字","evidence":{"len":99},"root_cause_hint":null,"hard":true},{"id":"B2","ok":true,"verdict":"pass","detail":"节拍 3","evidence":{"count":3},"root_cause_hint":null,"hard":true},{"id":"B3","ok":true,"verdict":"pass","detail":"scene_truth 150 字","evidence":{"len":150},"root_cause_hint":null,"hard":true},{"id":"B4","ok":true,"verdict":"pass","detail":"涉及 2 角色","evidence":{"ids":["role:qin_huiqi","role:hui_li"]},"root_cause_hint":null,"hard":true},{"id":"B5","ok":true,"verdict":"pass","detail":"2 条限知投影","evidence":{"ids":["role:qin_huiqi","role:hui_li"]},"root_cause_hint":null,"hard":true},{"id":"B6","ok":true,"verdict":"pass","detail":"投影 verbatim 可对齐真相","evidence":{},"root_cause_hint":null,"hard":true},{"id":"B6s","ok":true,"verdict":"pass","detail":"投影未过期 (rev=1)","evidence":{"truth_revision":1},"root_cause_hint":null,"hard":true},{"id":"B8","ok":false,"verdict":"warn","detail":"投影缺五层标题: ['role:qin_huiqi', 'role:hui_li']","evidence":{"ids":["role:qin_huiqi","role:hui_li"]},"root_cause_hint":"RC-SCHEMA-WEAK","hard":false},{
```

