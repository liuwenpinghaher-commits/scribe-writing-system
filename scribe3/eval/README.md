# craft-eval 尺子数据

本目录是 [`docs/plans/2026-08-26-craft-ruler-loop.md`](../../docs/plans/2026-08-26-craft-ruler-loop.md) 的评测真源。

- `holdout.json`：**冻结**。种子 `20260826`，43 章留出。禁止改章号。每轮开工校验 `holdout.sha256`。
- `chapters.json`：214 节在现存母本上的行界。`r1_skip_reason` 非空的节不进 R1。
- `citation_spotcheck.json`：20 条拆文书证能否在母本搜到（行号已整体偏移，只认句子）。
- `extract_card.py`：给一节原文出 21 段卡。禁止读留出章 gold。few-shot 只从 dev 抽。
- `score_r1.py`：五硬字段机械分。评分器可读留出 gold。
- `run_r1.py`：对留出可评章拆卡并打分。均分在 `r1_before.json`。
- `negatives.py`：三类机械负样本（削 / 灌 / 说明书）。禁止手挑、禁止用模型改写。
- `score_r2.py`：gold 为翻了的章：原文应判翻，三类负样本应判没翻。
- `run_r2.py`：`python -m scribe3.eval.run_r2 --label before`。clean 复用 `preds/r1_before/`。`--jobs` 并行，resume 默认开。
- `pool.py`：有序线程池。`jobs=1` 与串行等价。
- `stop.json`：**冻结**。R1 stop=0.70，R2 stop=0.775。冻结 ≠ 过线。tag `craft-eval-ruler-v1`。
- `blind_r1.py`：对已有系统卡做第三方盲评，对照机械 R1，不重拆。
- `human_spotcheck.json`：人抽查 10% 清单（seed=20260826）。不空等作者。
- `card_schema.py`：21 个段题。读取侧 `canonical_heading` 把诡秘的「章」映成铜炉的「节」。评分键仍是「节」，不许改。
- `lotm.py` / `chapters_lotm.json`：诡秘 1394 章界（1-based，来自 `00-index.md`）。
- `probe_lotm.json`：**冻结**。种子 `20260826`，20 章跨书探针。不进 few-shot。校验 `probe_lotm.sha256`。
- `citation_spotcheck_lotm.json`：20 条诡秘书证能否在全文搜到。
- `quick.json`：**冻结**。铜炉留出可评 8 + 诡秘探针 4。迭代只跑这个。校验 `quick.sha256`。
- `provider.py`：`--provider` 默认 `coding`（必须注入 complete_fn）；`hermes` 要显式点名。
- `sample_scene.py`：评测侧样章。不调 playbook。产物在 `docs/craft-samples/`，不作闸的证据。
- `r1_lotm_probe_gold.json`：诡秘探针金卡对金卡（证明评分器能读），不是模型 R1。

现行执行顺序：[`docs/plans/2026-08-26-craft-two-books.md`](../../docs/plans/2026-08-26-craft-two-books.md)。

母本因版权不入库（见根 `.gitignore`）。本机没有全文时，先把 txt 拷到该路径再跑脚本。
