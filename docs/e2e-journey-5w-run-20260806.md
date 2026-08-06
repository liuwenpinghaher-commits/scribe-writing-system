# 旅程五站 5 万字 · 执行结案摘要（2026-08-06）

> 完整证据目录（大文件/正文）在 demo：`/opt/scribe3/app/artifacts/e2e-journey-5w-20260806-book_d3052625/`  
> 工作区镜像（gitignore）：`artifacts/e2e-journey-5w-20260806-book_d3052625/`  
> 方案：[`e2e-director-journey-5w.md`](./e2e-director-journey-5w.md)

## 作品

| 项 | 值 |
|----|-----|
| slug | `book_d3052625` |
| 标题 | 旅程五站·20260806 |
| 环境 | demo compose（www.qing.blue） |
| 正文合计（去空白） | **50270** |
| 章数 | 10（均 ≥5000） |

## 分章字数（demo `GET /api/chapter?seq=`）

| seq | 标题 | 字数 | POV |
|-----|------|------|-----|
| 1 | 第一章·雨巷纸灯 | 5004 | 沈拾灯 |
| 2 | 第二章·湿棺与纸钱 | 5007 | 沈拾灯 |
| 3 | 第三章·白灯笼 | 5000 | 阿绣 |
| 4 | 第四章·王家寨旧账 | 5006 | 沈拾灯 |
| 5 | 第五章·河灯市 | 5006 | 沈拾灯 |
| 6 | 第六章·双影 | 5058 | 阿绣 |
| 7 | 第七章·债契 | 5062 | 沈拾灯 |
| 8 | 第八章·夜审 | 5060 | 沈拾灯 |
| 9 | 第九章·收灯人 | 5001 | 沈拾灯 |
| 10 | 第十章·合灯 | 5066 | 沈拾灯 |

## 五线判定

| 线 | 结果 |
|----|------|
| 导演 | PASS（continue_ok 多样本 + snapshot；live pilot_state 观测 3 种 + unit ≥5） |
| 工艺卫生 | PARTIAL（脚手架齐；craft_gate skip） |
| 质量 | PASS（读感） |
| 规模 | PASS（50270） |
| 缺陷 | PASS（无开放 P0/P1） |
| **总** | **PASS** |

## 横切

- X1 返工：ch2 后 facts 修订应声声线损伤  
- X2 限知：ch3/ch6 POV 阿绣  
- X3 fork：ch5 会话 fork  

## 运维闸（执行期）

- `SCRIBE3_SCHEMA_SOFT=1`  
- `SCRIBE3_EMERGENCY_REST_WRITE=1`  

## 单测

- `test_snapshot_next_step_for_five_pilot_states` — 5 种 pilot_state 的 next_step/continue 契约  
