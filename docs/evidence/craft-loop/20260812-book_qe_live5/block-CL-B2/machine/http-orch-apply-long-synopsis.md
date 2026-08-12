### http-013 · 2026-08-12T10:48:43.091078+00:00
**POST** `/api/orchestration/proposal/apply?work=book_qe_live5`  
note: CL-B2 legal world_write+approve: LONG synopsis reverify green

```json
REQUEST
{
  "proposal": {
    "id": "prop_craftloop_b2_green_fix",
    "ops": [
      {
        "tool": "s3_patch_chapter_plan",
        "args": {
          "seq": 2,
          "synopsis": "灰狸逼近铜匙秘密，覃灰七以假铜片挡过索要；冷锅婆干哑嗓音点破炉灰未冷，压力骤升。起因是灰狸伸手索物，转折是冷锅婆点破与假物挡过，结果是齿边缺口露一线而信息差仍在。章末钩子：炉子仍温着，匙齿疼进皮肉。"
        },
        "label": "CL-B2 green fix long synopsis",
        "status": "pending"
      }
    ],
    "summary": "craft-loop sequential: fix synopsis>=80"
  },
  "decision": "approve",
  "execute": true
}
```

status: **200**

```
RESPONSE
{"work":"book_qe_live5","proposal":{"id":"prop_craftloop_b2_green_fix","ops":[{"tool":"s3_patch_chapter_plan","args":{"seq":2,"synopsis":"灰狸逼近铜匙秘密，覃灰七以假铜片挡过索要；冷锅婆干哑嗓音点破炉灰未冷，压力骤升。起因是灰狸伸手索物，转折是冷锅婆点破与假物挡过，结果是齿边缺口露一线而信息差仍在。章末钩子：炉子仍温着，匙齿疼进皮肉。"},"label":"CL-B2 green fix long synopsis","status":"written","result":{"status":"written","seq":2,"fields":["synopsis"]}}],"summary":"craft-loop sequential: fix synopsis>=80","applied":[{"tool":"s3_patch_chapter_plan","result":{"status":"written","seq":2,"fields":["synopsis"]}}],"errors":[],"status":"applied"},"ui_events":[],"ui_target":null,"focus_policy":"soft"}
```

