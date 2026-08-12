### http-025 · 2026-08-12T10:48:57.071614+00:00
**POST** `/api/storyline/inject-preview?work=book_qe_live5`  
note: regression storyline omit

```json
REQUEST
{
  "seq": 2
}
```

status: **200**

```
RESPONSE
{"name":"storyline_polish","layer":"supplemental","text":"\n\n【故事线提示｜借鉴勿当设定点名】\n- 近程阶段：#1:outline, #2:outline\n","raw":"#1:outline, #2:outline","enabled":true,"promise_mode":"omit","audit":{"line_count":1,"not_a_kpi":"tokens_saved","redline_safe":true,"source":"storyline_inject_polish.v1","promise_mode":"omit","notes_in_prompt":false,"craft_only_injected_ids":[],"craft_only_skipped":[],"has_open_promise_body":false},"control":{"uses_tokens_saved":false},"feed":{"window_seqs":[],"promise_mode":"omit","fed":true,"notes_in_prompt":false,"craft_only_injected_ids":[],"craft_only_skipped":[],"use_store":true}}
```

