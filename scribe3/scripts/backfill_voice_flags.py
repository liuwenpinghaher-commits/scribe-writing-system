#!/usr/bin/env python
"""R2-11(彻查 C-2):voice_evolution_flag 存量烂账诊断 + 修复脚本。

背景
----
- **ingest_seq=NONE 孤儿**:068 前 ingest 产的 flag 无 ingest_seq(NONE),被
  「NONE=手动种」的 purge 保护语义误伤成永久孤儿(实测 main 1052/1068 条全 open、
  纸命 216 条同病)。GET /voice-flags 返回全书 open,fold 会把几百条历史噪声折进
  演化 prompt。
- **裸名双轨**:P1-11 前 ingest 的 voice_shift 路径写裸名(如 `胡不为`),而
  fold_voice_flags/add_char_state 一律用 `role:` 前缀匹配 → 裸名 flag 永不被 fold
  (前端 fold 空操作)。P1-11 已在写入层(add_voice_flag)补前缀,但存量裸名仍在。

安全
----
默认 **DRY-RUN**(只诊断不写)。写操作必须显式 `--yes`:
- `--fix-bare-names`:裸名补 `role:` 前缀。**安全**——裸名 flag 本就 fold 不到,补前缀
  只会让它恢复可 fold,不改变任何语义。
- `--archive-stale-none`:把 ingest_seq IS NONE 的 open flag 归 status=done。**有风险**
  ——无法从数据区分「068 前 ingest 产」与「真手动种」的 flag,归档会误伤后者。仅在确认
  某 work 没有手动 voice flag(纯 ingest 驱动)时使用。

生产红线:本脚本会写库,**先对 DB 做 surreal export 备份**再加 `--yes` 跑。

用法
----
  python scribe3/scripts/backfill_voice_flags.py                    # 全 work dry-run 诊断
  python scribe3/scripts/backfill_voice_flags.py --work main        # 单 work 诊断
  python scribe3/scripts/backfill_voice_flags.py --fix-bare-names --yes
  python scribe3/scripts/backfill_voice_flags.py --work loop-qa --archive-stale-none --yes
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scribe3.store import SurrealStore, list_works   # noqa: E402


def diagnose(st: SurrealStore) -> dict:
    rows = st._query(
        "SELECT meta::id(id) AS id, character, trigger_chapter, ingest_seq, status "
        "FROM voice_evolution_flag")
    none_seq = [r for r in rows if r.get("ingest_seq") is None and r.get("status") == "open"]
    bare = [r for r in rows if r.get("character") and ":" not in str(r["character"])]
    prefixed_names = {str(r["character"]).split(":")[-1] for r in rows
                      if r.get("character") and ":" in str(r["character"])}
    bare_dup = [r for r in bare if str(r["character"]) in prefixed_names]
    return {"total": len(rows), "open": sum(1 for r in rows if r.get("status") == "open"),
            "none_open": none_seq, "bare": bare, "bare_dup": len(bare_dup)}


def fix_bare_names(st: SurrealStore, bare_rows: list) -> int:
    n = 0
    for r in bare_rows:
        try:
            st._execute_write(
                "UPDATE type::thing('voice_evolution_flag',$id) SET character=$c",
                {"id": r["id"], "c": f"role:{r['character']}"})
            n += 1
        except Exception as e:   # noqa: BLE001
            print(f"    ! 修裸名失败 {r.get('id')}: {e}")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="voice_evolution_flag 存量诊断/修复(R2-11)")
    ap.add_argument("--work", help="只处理某 work(默认全部注册书)")
    ap.add_argument("--fix-bare-names", action="store_true", help="裸名补 role: 前缀(安全)")
    ap.add_argument("--archive-stale-none", action="store_true",
                    help="归档 ingest_seq=NONE 的 open flag(有风险:可能误伤手动种)")
    ap.add_argument("--yes", action="store_true", help="确认执行写操作(否则 dry-run)")
    args = ap.parse_args()

    works = [args.work] if args.work else [w["slug"] for w in list_works()]
    for work in works:
        st = SurrealStore(ns="scribe3", db=work)
        try:
            d = diagnose(st)
            print(f"[{work}] 共 {d['total']}(open {d['open']}) | "
                  f"ingest_seq=NONE&open {len(d['none_open'])} | 裸名 {len(d['bare'])}"
                  f"(与前缀名并存 {d['bare_dup']})")
            if args.fix_bare_names and d["bare"]:
                if args.yes:
                    print(f"  → 已补前缀 {fix_bare_names(st, d['bare'])} 条裸名 flag")
                else:
                    print(f"  → [DRY-RUN] 将补前缀 {len(d['bare'])} 条裸名(加 --yes 执行)")
            if args.archive_stale_none and d["none_open"]:
                if args.yes:
                    st._execute_write(
                        "UPDATE voice_evolution_flag SET status='done' "
                        "WHERE ingest_seq IS NONE AND status='open'")
                    print(f"  → 已归档 {len(d['none_open'])} 条 NONE open flag(status=done)")
                else:
                    print(f"  → [DRY-RUN] 将归档 {len(d['none_open'])} 条 NONE open flag"
                          f"(加 --yes;⚠ 可能误伤手动种 flag)")
        finally:
            st.close()


if __name__ == "__main__":
    main()
