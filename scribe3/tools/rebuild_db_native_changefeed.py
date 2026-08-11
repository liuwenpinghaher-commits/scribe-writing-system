"""Demo/可丢数据：按库重建并 apply_schema，使关键表自带 CHANGEFEED。

在「全新 DB」上 Surreal 3.2 对 SCHEMAFULL + CHANGEFEED 的 SHOW CHANGES 可用；
对**已损坏 feed 的旧库**，DEFINE OVERWRITE 往往无法恢复，需 REMOVE DATABASE。

用法（backend 容器内 / 已配 SURREAL 环境）::

  python -m scribe3.tools.rebuild_db_native_changefeed --db main --yes
  python -m scribe3.tools.rebuild_db_native_changefeed --all --yes

危险：销毁该 DB 全部数据。默认 dry-run。
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def _list_databases(st) -> list[str]:
    info = st._query("INFO FOR NS;")
    d = info if isinstance(info, dict) else (info[0] if isinstance(info, list) and info else {})
    dbs = d.get("databases") or {}
    # values like DEFINE DATABASE x
    names = []
    for k, v in dbs.items():
        names.append(str(k))
    return sorted(names)


def _verify_feed(st, table: str = "proposition") -> bool:
    try:
        # 写一条探针再 SHOW
        st._execute_write(
            f"CREATE {table} SET entity_id=$e, attribute=$a, value=$v, valid_from=1;"
            if table == "proposition"
            else f"CREATE {table} SET _probe=$p;",
            {"e": "role:cf_probe", "a": "_cf", "v": "rebuild_ok", "p": True}
            if table == "proposition"
            else {"p": True},
        )
    except Exception:
        # chapter 等表字段不同，只依赖 SHOW define 事件
        pass
    try:
        rows = st._query(f"SHOW CHANGES FOR TABLE {table} SINCE 0 LIMIT 20;") or []
        return bool(rows)
    except Exception:
        return False


def rebuild_one(db: str, *, ns: str = "scribe3", dry_run: bool = True) -> dict:
    from scribe3.store import SurrealStore

    out = {"db": db, "dry_run": dry_run, "ok": False}
    if dry_run:
        out["ok"] = True
        out["note"] = "dry-run: would REMOVE DATABASE + DEFINE + apply_schema"
        return out

    # 用任意连接进 NS
    hub = SurrealStore(ns=ns, db=db)
    try:
        # REMOVE 可能断开当前 DB
        try:
            hub._execute_write(f"REMOVE DATABASE `{db}`;", {})
        except Exception:
            try:
                hub._execute_write(f"REMOVE DATABASE {db};", {})
            except Exception as e:
                out["error"] = f"remove: {e}"
                return out
        try:
            hub._execute_write(f"DEFINE DATABASE `{db}`;", {})
        except Exception:
            hub._execute_write(f"DEFINE DATABASE {db};", {})
    finally:
        try:
            hub.close()
        except Exception:
            pass

    st = SurrealStore(ns=ns, db=db)
    try:
        st.apply_schema()
        ok_prop = _verify_feed(st, "proposition")
        # cache_watch 仍应存在
        try:
            st._execute_write(
                "CREATE cache_watch SET table_name=$t, work=$w;",
                {"t": "rebuild_probe", "w": db},
            )
            cw = st._query("SHOW CHANGES FOR TABLE cache_watch SINCE 0 LIMIT 10;") or []
            ok_cw = bool(cw)
        except Exception:
            ok_cw = False
        out["proposition_feed"] = ok_prop
        out["cache_watch_feed"] = ok_cw
        out["ok"] = bool(ok_prop or ok_cw)
        return out
    except Exception as e:
        out["error"] = str(e)[:300]
        return out
    finally:
        try:
            st.close()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", action="append", dest="dbs", help="可重复；或 --all")
    p.add_argument("--all", action="store_true", help="NS 下全部 DB（跳过 _reg）")
    p.add_argument("--ns", default="scribe3")
    p.add_argument("--yes", action="store_true", help="确认销毁数据")
    p.add_argument("--commit", action="store_true", help="真执行（默认 dry-run）")
    args = p.parse_args(argv)

    dry = not args.commit
    if args.commit and not args.yes:
        print("拒绝：真执行须同时 --commit --yes", file=sys.stderr)
        return 2

    from scribe3.store import SurrealStore

    probe = SurrealStore(ns=args.ns, db="main")
    try:
        all_dbs = _list_databases(probe)
    finally:
        try:
            probe.close()
        except Exception:
            pass

    skip = {"_reg"}
    if args.all:
        targets = [d for d in all_dbs if d not in skip]
    else:
        targets = list(args.dbs or ["main"])

    print(json.dumps({"ns": args.ns, "targets": targets, "dry_run": dry}, ensure_ascii=False))
    results = []
    for db in targets:
        r = rebuild_one(db, ns=args.ns, dry_run=dry)
        results.append(r)
        print(json.dumps(r, ensure_ascii=False))
    ok = all(x.get("ok") for x in results)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
