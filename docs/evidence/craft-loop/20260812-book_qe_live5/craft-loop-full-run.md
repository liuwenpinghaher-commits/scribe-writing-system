# craft-loop-full-run · chronological

work=book_qe_live5 demo=https://tonglu.qing.blue

- `2026-08-12T10:48:30.308317+00:00` **SESSION_START** — `{"work": "book_qe_live5", "demo": "https://tonglu.qing.blue"}`
- `2026-08-12T10:48:30.854036+00:00` **HTTP GET /api/health -> 200** — `{"note": "env health", "http_id": "http-001"}`
- `2026-08-12T10:48:30.854137+00:00` **BLOCK_START** — `{"block": "CL-B0"}`
- `2026-08-12T10:48:31.877370+00:00` **HTTP PUT /api/intent-goals?work=book_qe_live5 -> 200** — `{"note": "CL-B0 legal: engineering quota total_word_goal", "http_id": "http-002"}`
- `2026-08-12T10:48:32.118811+00:00` **HTTP GET /api/intent?work=book_qe_live5 -> 200** — `{"note": "CL-B0 read intent after goals", "http_id": "http-003"}`
- `2026-08-12T10:48:32.120686+00:00` **BLOCK_END** — `{"block": "CL-B0", "verdict": "green"}`
- `2026-08-12T10:48:33.620796+00:00` **BLOCK_START** — `{"block": "CL-B1", "prerequisite": "CL-B0 green"}`
- `2026-08-12T10:48:34.105869+00:00` **HTTP GET /api/entities?work=book_qe_live5 -> 200** — `{"note": "CL-B1 settings_min source entities", "http_id": "http-004"}`
- `2026-08-12T10:48:34.909543+00:00` **HTTP GET /api/character-relations?work=book_qe_live5 -> 200** — `{"note": "CL-B1 settings_min source relations", "http_id": "http-005"}`
- `2026-08-12T10:48:35.538663+00:00` **HTTP GET /api/world-rules?work=book_qe_live5 -> 200** — `{"note": "CL-B1 settings_min source world-rules", "http_id": "http-006"}`
- `2026-08-12T10:48:36.475625+00:00` **HTTP GET /api/motifs?work=book_qe_live5 -> 200** — `{"note": "CL-B1 settings_min source motifs", "http_id": "http-007"}`
- `2026-08-12T10:48:37.179600+00:00` **HTTP GET /api/promises?work=book_qe_live5 -> 200** — `{"note": "CL-B1 settings_min source promises", "http_id": "http-008"}`
- `2026-08-12T10:48:37.919123+00:00` **HTTP GET /api/craft-gates?work=book_qe_live5 -> 200** — `{"note": "CL-B1 settings_min source craft-gates-A", "http_id": "http-009"}`
- `2026-08-12T10:48:38.321575+00:00` **BLOCK_END** — `{"block": "CL-B1", "verdict": "green", "unlock_CL_B2": true}`
- `2026-08-12T10:48:39.821685+00:00` **BLOCK_START** — `{"block": "CL-B2", "prerequisite": "CL-B1 green", "phase": "red_demo"}`
- `2026-08-12T10:48:40.163385+00:00` **HTTP POST /api/orchestration/proposal/apply?work=book_qe_live5 -> 200** — `{"note": "CL-B2 legal world_write+approve: SHORT synopsis for red state", "http_id": "http-010"}`
- `2026-08-12T10:48:41.218567+00:00` **HTTP GET /api/chapter?seq=2&work=book_qe_live5 -> 200** — `{"note": "CL-B2 read chapter AFTER short synopsis", "http_id": "http-011"}`
- `2026-08-12T10:48:41.589764+00:00` **HTTP GET /api/craft-gates?work=book_qe_live5&seq=2 -> 200** — `{"note": "CL-B2 craft-gates at RED (gate_b may still pass)", "http_id": "http-012"}`
- `2026-08-12T10:48:41.590731+00:00` **BLOCK_RED** — `{"block": "CL-B2", "synopsis_cn_len": 21, "gate_b_ok": true}`
- `2026-08-12T10:48:43.428571+00:00` **HTTP POST /api/orchestration/proposal/apply?work=book_qe_live5 -> 200** — `{"note": "CL-B2 legal world_write+approve: LONG synopsis reverify green", "http_id": "http-013"}`
- `2026-08-12T10:48:44.479314+00:00` **HTTP GET /api/chapter?seq=2&work=book_qe_live5 -> 200** — `{"note": "CL-B2 read chapter AFTER long synopsis", "http_id": "http-014"}`
- `2026-08-12T10:48:44.767779+00:00` **HTTP GET /api/craft-gates?work=book_qe_live5&seq=2 -> 200** — `{"note": "CL-B2 craft-gates at GREEN", "http_id": "http-015"}`
- `2026-08-12T10:48:44.770140+00:00` **BLOCK_END** — `{"block": "CL-B2", "verdict": "green", "red_syn": 21, "green_syn": 99}`
- `2026-08-12T10:48:46.270276+00:00` **BLOCK_START** — `{"block": "CL-B3", "prerequisite": "CL-B2 green"}`
- `2026-08-12T10:48:46.498221+00:00` **HTTP GET /api/chapter?seq=2&work=book_qe_live5 -> 200** — `{"note": "CL-B3 beats source", "http_id": "http-016"}`
- `2026-08-12T10:48:46.500696+00:00` **BLOCK_END** — `{"block": "CL-B3", "verdict": "green"}`
- `2026-08-12T10:48:48.000811+00:00` **BLOCK_START** — `{"block": "CL-B4", "prerequisite": "CL-B3 green"}`
- `2026-08-12T10:48:48.332218+00:00` **HTTP GET /api/chapter?seq=2&work=book_qe_live5 -> 200** — `{"note": "CL-B4 truth/deductions", "http_id": "http-017"}`
- `2026-08-12T10:48:48.880243+00:00` **HTTP GET /api/craft-gates?work=book_qe_live5&seq=2 -> 200** — `{"note": "CL-B4 gates B3-B6 fields", "http_id": "http-018"}`
- `2026-08-12T10:48:48.882003+00:00` **BLOCK_END** — `{"block": "CL-B4", "verdict": "green", "scene_truth_cn_len": 150}`
- `2026-08-12T10:48:50.382118+00:00` **BLOCK_START** — `{"block": "CL-B5", "prerequisite": "CL-B4 green"}`
- `2026-08-12T10:48:52.693625+00:00` **HTTP GET /api/chapter?seq=2&work=book_qe_live5 -> 200** — `{"note": "CL-B5 pre-check prose length", "http_id": "http-019"}`
- `2026-08-12T10:48:53.036648+00:00` **HTTP POST /api/save-chapter?work=book_qe_live5 -> 200** — `{"note": "CL-B5 legal prose path: POST /save-chapter (not emergency world REST)", "http_id": "http-020"}`
- `2026-08-12T10:48:54.426695+00:00` **HTTP GET /api/chapter?seq=2&work=book_qe_live5 -> 200** — `{"note": "CL-B5 verify prose after save", "http_id": "http-021"}`
- `2026-08-12T10:48:54.683328+00:00` **HTTP GET /api/craft-gates?work=book_qe_live5&seq=2 -> 200** — `{"note": "CL-B5 gate_c after prose", "http_id": "http-022"}`
- `2026-08-12T10:48:54.686565+00:00` **BLOCK_END** — `{"block": "CL-B5", "verdict": "green", "prose_cn_len": 1823}`
- `2026-08-12T10:48:56.186687+00:00` **BLOCK_START** — `{"block": "CL-B6", "prerequisite": "CL-B5 green"}`
- `2026-08-12T10:48:56.487336+00:00` **HTTP GET /api/promises?work=book_qe_live5 -> 200** — `{"note": "CL-B6 open promises", "http_id": "http-023"}`
- `2026-08-12T10:48:57.069967+00:00` **HTTP GET /api/chapter?seq=2&work=book_qe_live5 -> 200** — `{"note": "CL-B6 prose touch keywords", "http_id": "http-024"}`
- `2026-08-12T10:48:57.071520+00:00` **BLOCK_END** — `{"block": "CL-B6", "verdict": "green"}`
- `2026-08-12T10:48:57.071546+00:00` **REGRESSION_START**
- `2026-08-12T10:48:57.402626+00:00` **HTTP POST /api/storyline/inject-preview?work=book_qe_live5 -> 200** — `{"note": "regression storyline omit", "http_id": "http-025"}`
- `2026-08-12T10:48:57.403374+00:00` **REGRESSION_END** — `{"promise_mode": "omit", "has_开放伏笔": false, "layer": "supplemental", "has_open_promise_body": false}`

## HTTP calls (25)

- `2026-08-12T10:48:30.308670+00:00` `http-001` **GET** `/api/health` → 200 — env health
- `2026-08-12T10:48:31.654590+00:00` `http-002` **PUT** `/api/intent-goals?work=book_qe_live5` → 200 — CL-B0 legal: engineering quota total_word_goal
- `2026-08-12T10:48:31.878004+00:00` `http-003` **GET** `/api/intent?work=book_qe_live5` → 200 — CL-B0 read intent after goals
- `2026-08-12T10:48:33.621025+00:00` `http-004` **GET** `/api/entities?work=book_qe_live5` → 200 — CL-B1 settings_min source entities
- `2026-08-12T10:48:34.506841+00:00` `http-005` **GET** `/api/character-relations?work=book_qe_live5` → 200 — CL-B1 settings_min source relations
- `2026-08-12T10:48:35.310207+00:00` `http-006` **GET** `/api/world-rules?work=book_qe_live5` → 200 — CL-B1 settings_min source world-rules
- `2026-08-12T10:48:35.939377+00:00` `http-007` **GET** `/api/motifs?work=book_qe_live5` → 200 — CL-B1 settings_min source motifs
- `2026-08-12T10:48:36.876415+00:00` `http-008` **GET** `/api/promises?work=book_qe_live5` → 200 — CL-B1 settings_min source promises
- `2026-08-12T10:48:37.580369+00:00` `http-009` **GET** `/api/craft-gates?work=book_qe_live5` → 200 — CL-B1 settings_min source craft-gates-A
- `2026-08-12T10:48:39.821969+00:00` `http-010` **POST** `/api/orchestration/proposal/apply?work=book_qe_live5` → 200 — CL-B2 legal world_write+approve: SHORT synopsis for red state
- `2026-08-12T10:48:40.964227+00:00` `http-011` **GET** `/api/chapter?seq=2&work=book_qe_live5` → 200 — CL-B2 read chapter AFTER short synopsis
- `2026-08-12T10:48:41.219346+00:00` `http-012` **GET** `/api/craft-gates?work=book_qe_live5&seq=2` → 200 — CL-B2 craft-gates at RED (gate_b may still pass)
- `2026-08-12T10:48:43.091078+00:00` `http-013` **POST** `/api/orchestration/proposal/apply?work=book_qe_live5` → 200 — CL-B2 legal world_write+approve: LONG synopsis reverify green
- `2026-08-12T10:48:44.232505+00:00` `http-014` **GET** `/api/chapter?seq=2&work=book_qe_live5` → 200 — CL-B2 read chapter AFTER long synopsis
- `2026-08-12T10:48:44.480064+00:00` `http-015` **GET** `/api/craft-gates?work=book_qe_live5&seq=2` → 200 — CL-B2 craft-gates at GREEN
- `2026-08-12T10:48:46.270486+00:00` `http-016` **GET** `/api/chapter?seq=2&work=book_qe_live5` → 200 — CL-B3 beats source
- `2026-08-12T10:48:48.001022+00:00` `http-017` **GET** `/api/chapter?seq=2&work=book_qe_live5` → 200 — CL-B4 truth/deductions
- `2026-08-12T10:48:48.332872+00:00` `http-018` **GET** `/api/craft-gates?work=book_qe_live5&seq=2` → 200 — CL-B4 gates B3-B6 fields
- `2026-08-12T10:48:50.382349+00:00` `http-019` **GET** `/api/chapter?seq=2&work=book_qe_live5` → 200 — CL-B5 pre-check prose length
- `2026-08-12T10:48:52.694039+00:00` `http-020` **POST** `/api/save-chapter?work=book_qe_live5` → 200 — CL-B5 legal prose path: POST /save-chapter (not emergency world REST)
- `2026-08-12T10:48:53.838482+00:00` `http-021` **GET** `/api/chapter?seq=2&work=book_qe_live5` → 200 — CL-B5 verify prose after save
- `2026-08-12T10:48:54.427572+00:00` `http-022` **GET** `/api/craft-gates?work=book_qe_live5&seq=2` → 200 — CL-B5 gate_c after prose
- `2026-08-12T10:48:56.186895+00:00` `http-023` **GET** `/api/promises?work=book_qe_live5` → 200 — CL-B6 open promises
- `2026-08-12T10:48:56.487927+00:00` `http-024` **GET** `/api/chapter?seq=2&work=book_qe_live5` → 200 — CL-B6 prose touch keywords
- `2026-08-12T10:48:57.071614+00:00` `http-025` **POST** `/api/storyline/inject-preview?work=book_qe_live5` → 200 — regression storyline omit

## mvp_pass=True
