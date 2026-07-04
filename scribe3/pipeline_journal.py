"""crash-safe 分阶段流水线 journal + resume 协议(方案B任务23)。

背景(对标 oh-story short-analyze/output-contract.md:73-88 的分阶段输出契约):
长流程(批量 ingest/analyze/import)一旦中途崩溃(进程被杀/断电/异常退出),不能靠
"猜哪里断了"来续跑——必须有一份显式记录:Stage 开始时立刻置
`in_progress=<stage_name>` 并落盘,Stage 完全跑通后才把它移入
`stages_completed[]` 并清空 `in_progress`,再落盘。resume 时:
  - `in_progress` 非空 → 说明上次崩在这个 Stage 中途,该 Stage **没有"部分完成"
    这个状态**,只能整体从头重跑(幂等是调用方 Stage 实现自己的责任,journal 只
    负责告诉调用方"从这里重来");
  - `in_progress` 为空 → 上次是干净收尾的,`stages_completed` 里的直接跳过即可。

## 为什么选 JSON 文件而不是 DB 表(取舍记录)

journal 存在的意义就是在"数据库不可用/事务失败/进程被杀"时依然能告诉下一次运行
"上次崩在哪"——如果把它存进 DB 表,DB 事务本身失败或连接不上时,journal 会跟着
一起丢失或读不到,恰好在最需要它的时刻失灵。文件系统的写入路径更短、失败模式更
简单,且不依赖任何外部服务就能读写,所以 journal 单独落地为一个与调用方约定路径
的 JSON 文件(建议放在该次批量任务的 work 目录下,与该任务生命周期绑定)。

## 落盘原子性

每次 `start_stage`/`complete_stage` 都是"写临时文件 + `os.replace`"两步:先把完整
JSON 写进同目录下的临时文件并 flush+fsync,再用 `os.replace` 原子换名。`os.replace`
在 POSIX 上保证要么看到旧文件要么看到新文件,不会看到半截内容,所以哪怕进程在写
的瞬间被杀,journal 文件本身也始终是一份合法 JSON,不会因为"journal 自己写坏了"
而让 resume 逻辑连当前状态都读不出来。

## 接线指引(留给后续任务)

批量 ingest 循环用法:
    j = PipelineJournal(work_dir / "journal.json")
    for seq, chapter in enumerate(chapters):
        stage = f"ingest_ch{seq}"
        if j.should_skip(stage):
            continue
        j.start_stage(stage)
        ingest_chapter(chapter)      # 中途崩溃 → in_progress 停在这里,下次重跑整章
        j.complete_stage(stage)

与已有 `_pending_ingest` 去重机制是互补关系而非冲突:journal 管的是"阶段级"续跑
(从哪个 Stage 重新开始),`_pending_ingest` 管的是"单条记录级"幂等(同一章重复
ingest 不会重复写入)。两者可以叠加使用——journal 决定"从第几章重跑",
`_pending_ingest` 保证"哪怕这一章被重跑多次,落库结果也不重复"。
本任务(B23)只交付独立模块,接线到具体批量流程(story-import 等)留给任务 B24。
"""
from __future__ import annotations

import json
import os
from pathlib import Path


class PipelineJournal:
    """单个文件持久化的分阶段流水线进度记录。

    磁盘格式::

        {"in_progress": str | None, "stages_completed": [str, ...]}

    文件不存在时视为全新 journal(in_progress=None, stages_completed=[])。
    """

    def __init__(self, path: str | Path):
        self._path = Path(path)
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._in_progress: str | None = data.get("in_progress")
            self._stages_completed: list[str] = list(data.get("stages_completed", []))
        else:
            self._in_progress = None
            self._stages_completed = []
            self._flush()

    def start_stage(self, name: str) -> None:
        """标记某 Stage 开始执行,立即落盘。崩在该 Stage 中途时,resume_point() 会指回这里。"""
        self._in_progress = name
        self._flush()

    def complete_stage(self, name: str) -> None:
        """标记某 Stage 完全跑通:计入 stages_completed,清空 in_progress,立即落盘。"""
        if name not in self._stages_completed:
            self._stages_completed.append(name)
        if self._in_progress == name:
            self._in_progress = None
        self._flush()

    def in_progress(self) -> str | None:
        """当前(或上次崩溃时)正在进行、尚未 complete 的 Stage 名;干净状态下为 None。"""
        return self._in_progress

    def stages_completed(self) -> list[str]:
        """已完整跑通的 Stage 名列表(顺序为完成顺序)。"""
        return list(self._stages_completed)

    def resume_point(self) -> str | None:
        """崩溃恢复点:等价于 in_progress()。非空即该 Stage 需要从头整体重跑。"""
        return self._in_progress

    def should_skip(self, name: str) -> bool:
        """该 Stage 是否已经完整完成过,调用方可据此在续跑循环里直接跳过。"""
        return name in self._stages_completed

    def _flush(self) -> None:
        """原子落盘:写临时文件 + fsync + os.replace,任何时刻磁盘上都是合法 JSON。"""
        payload = {
            "in_progress": self._in_progress,
            "stages_completed": self._stages_completed,
        }
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self._path)
