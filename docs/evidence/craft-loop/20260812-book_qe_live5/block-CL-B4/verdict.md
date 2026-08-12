# CL-B4 · verdict

**verdict: green**

| Hard ID | pass | 备注 |
|---------|------|------|
| CL-B4-H1 | PASS | 150 |
| CL-B4-H2 | PASS | ["role:qin_huiqi", "role:hui_li"] |
| CL-B4-H3 | PASS | {"inv": ["role:qin_huiqi", "role:hui_li"], "ded_ids": ["role:qin_huiqi", "role:h |
| CL-B4-H4a | PASS | PASS 演绎含【感知】等块与 scene_truth 同源；server gate_b B6 pass；人接受 soft 风险 |
| CL-B4-H4b | PASS | grounding_llm_skipped if endpoint unused |
| CL-B4-H5 | PASS | PASS 读者知铜匙=钥匙；灰狸不知 |
| CL-B4-H6 | PASS | prose present; server save leaks=0 |

## 人主裁行

- **CL-B4-H4a**: PASS 演绎含【感知】等块与 scene_truth 同源；server gate_b B6 pass；人接受 soft 风险
- **CL-B4-H5**: PASS 读者知铜匙=钥匙；灰狸不知

## 机算锚点

```json
{
  "CL-B4-H1": {
    "pass": true,
    "value": 150
  },
  "CL-B4-H2": {
    "pass": true,
    "value": [
      "role:qin_huiqi",
      "role:hui_li"
    ]
  },
  "CL-B4-H3": {
    "pass": true,
    "value": {
      "inv": [
        "role:qin_huiqi",
        "role:hui_li"
      ],
      "ded_ids": [
        "role:qin_huiqi",
        "role:hui_li"
      ]
    }
  },
  "CL-B4-H4a": {
    "pass": true,
    "value": {
      "verbatim_hits": 2
    },
    "human": "PASS 演绎含【感知】等块与 scene_truth 同源；server gate_b B6 pass；人接受 soft 风险"
  },
  "CL-B4-H4b": {
    "pass": true,
    "note": "grounding_llm_skipped if endpoint unused",
    "status": "skip"
  },
  "CL-B4-H5": {
    "pass": true,
    "human": "PASS 读者知铜匙=钥匙；灰狸不知"
  },
  "CL-B4-H6": {
    "pass": true,
    "value": "role:qin_huiqi",
    "note": "prose present; server save leaks=0"
  }
}
```
