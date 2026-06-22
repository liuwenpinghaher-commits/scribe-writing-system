"""scribe3 体检 cron 入口:连 NS=scribe3 → health_report → markdown([SILENT] 若干净)。

作为 Hermes cron 的前置 script(stdout 注入 agent prompt):agent 据此判断,只在异常时通知。
纯机械检查(连贯性)不需 LLM;干净即 [SILENT]。
"""
from scribe3.health import health_report, render_markdown
from scribe3.store import SurrealStore


def main() -> None:
    store = SurrealStore(ns="scribe3", db="main")
    try:
        store.apply_schema()
        rep = health_report(store, up_to=store.max_chapter())
        if not rep.clean:                    # --no-agent watchdog:干净=空 stdout=静默
            print(render_markdown(rep))
    finally:
        store.close()


if __name__ == "__main__":
    main()
