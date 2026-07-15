"""U-005 一次性回填:把 Hermes state.db 里丢失的主编对话补回 scribe3 的 chat_message。

背景:chat_stream/chat_agentic_stream 长期不留痕(已修),导致《印迹》那场"贴世界观全案
→ 主编逐批录入 15 世界规则 + 6 势力"的整场对话在 scribe3 侧凭空消失(库里只有成果,
没有对话)。但 Hermes 网关的 state.db 完整留着这场 session。此脚本把它抽出来、过滤掉
工具噪声、按原始时间戳补回对应书的主编线程,作者在主编面板即可回看。

安全:
- 只读 Hermes state.db(sqlite),绝不改它;
- 写生产 SurrealDB 前【必须】已备份(surreal_backup.sh);
- 幂等:同一 (thread, source, session_id) 的既有回填行先删后插,重复跑不产生重复;
- 保留原始时间戳(不能用 add_chat_message——它硬编码 ts=time::now() 会把时序打乱);
- 只回填 role∈{user,assistant} 且 content 非空的行,工具/审批帧一律丢弃;
- --dry-run 只打印不落库(默认)。--commit 才真写。

用法:
  scribe3/.venv/bin/python -m scribe3.tools.backfill_editorial_chat \
    --work book_2acba371 --profile scribe3_write \
    --session run_73ccf5486cd245c0a96fc19cc7c3bc1f            # dry-run
  ...  --commit                                               # 真写
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import datetime, timezone

from scribe3.store import SurrealStore

SOURCE_TAG = "backfill_hermes_state"


def _read_session(state_db: str, session_id: str) -> list[dict]:
    """从 Hermes state.db 读一场 session 的纯对话(user/assistant 非空),按时序。"""
    con = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT role, content, timestamp FROM messages "
            "WHERE session_id = ? AND role IN ('user','assistant') "
            "AND TRIM(COALESCE(content,'')) != '' "
            "ORDER BY timestamp, id",
            (session_id,)).fetchall()
    finally:
        con.close()
    out = []
    for role, content, ts in rows:
        out.append({"role": role, "text": content,
                    "iso": datetime.fromtimestamp(float(ts), tz=timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%SZ")})
    return out


def _existing_backfill_count(st: SurrealStore, thread_id: str, session_id: str) -> int:
    rows = st._query(
        "SELECT count() AS n FROM chat_message "
        "WHERE thread_id=$tid AND trace.source=$src AND trace.session_id=$sid GROUP ALL",
        {"tid": thread_id, "src": SOURCE_TAG, "sid": session_id})
    return (rows[0]["n"] if rows else 0)


def backfill(work: str, profile: str, session_id: str, *, commit: bool) -> dict:
    state_db = os.path.expanduser(f"~/.hermes/profiles/{profile}/state.db")
    if not os.path.exists(state_db):
        raise SystemExit(f"state.db 不存在: {state_db}")

    msgs = _read_session(state_db, session_id)
    if not msgs:
        raise SystemExit(f"session {session_id} 没有可回填的对话行(user/assistant 非空)")

    st = SurrealStore(url="ws://127.0.0.1:8001/rpc", ns="scribe3", db=work)
    st.apply_schema()
    thread = st.get_or_create_editorial_thread(work, "author")
    thread_id = thread["thread_id"]
    turn_id = f"backfill:{session_id[:16]}"   # 整场 = 一个连续 turn(一次贴稿→主编逐批回复)

    already = _existing_backfill_count(st, thread_id, session_id)

    print(f"  书: {work}   线程: {thread_id}")
    print(f"  来源: {profile}/state.db  session: {session_id}")
    print(f"  可回填对话行: {len(msgs)}(user {sum(m['role']=='user' for m in msgs)} / "
          f"assistant {sum(m['role']=='assistant' for m in msgs)})")
    print(f"  时间范围: {msgs[0]['iso']} → {msgs[-1]['iso']}")
    print(f"  该 session 既有回填行: {already}(将先删后插,保证幂等)")
    print("  ---")
    for i, m in enumerate(msgs, 1):
        print(f"  {i:2d} [{m['role']:9}] {m['text'].replace(chr(10), ' ')[:64]}")

    if not commit:
        print("\n  [dry-run] 未写库。加 --commit 才真正回填。")
        return {"dry_run": True, "rows": len(msgs)}

    # 幂等:先删同 (thread, source, session) 的既有回填行
    st._execute_write(
        "DELETE chat_message WHERE thread_id=$tid AND trace.source=$src AND trace.session_id=$sid",
        {"tid": thread_id, "src": SOURCE_TAG, "sid": session_id})

    # 逐条 CREATE,保留原始时间戳(不能用 add_chat_message——它 ts=time::now())
    for m in msgs:
        st._execute_write(
            "CREATE chat_message SET work=$w, chapter=0, stage='discuss', role=$r, "
            "text=$t, turn=$turn, thread_id=$tid, "
            "trace={source:$src, session_id:$sid}, "
            "ts=type::datetime($iso) RETURN NONE",
            {"w": work, "r": m["role"], "t": m["text"], "turn": turn_id,
             "tid": thread_id, "src": SOURCE_TAG, "sid": session_id, "iso": m["iso"]})

    final = _existing_backfill_count(st, thread_id, session_id)
    print(f"\n  ✅ 回填完成:{final} 行已入《{work}》主编线程(源标记 trace.source={SOURCE_TAG})")
    return {"dry_run": False, "rows": final, "thread_id": thread_id}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--profile", default="scribe3_write")
    ap.add_argument("--session", required=True)
    ap.add_argument("--commit", action="store_true", help="真写库(默认 dry-run)")
    args = ap.parse_args()
    backfill(args.work, args.profile, args.session, commit=args.commit)


if __name__ == "__main__":
    main()
