"""scribe3 体检 cron 入口:遍历全部注册书 → health_report → markdown([SILENT] 若全净)。

作为 Hermes cron 的前置 script(stdout 注入 agent prompt):agent 据此判断,只在异常时通知。
纯机械检查(连贯性)不需 LLM;干净即 [SILENT]。
审计 P2-9:原单书硬编码 db="main" 对其余书失明——改遍历 list_works 注册表。
"""
from scribe3.health import health_report, render_markdown
from scribe3.store import SurrealStore, list_works


def build_reports(works: list[str] | None = None, url: str | None = None) -> dict:
    """逐书体检:{work: report}。works 不传则取注册表全量(cron 场景)。
    单书失败不拖垮其余书(记入该书条目,如实上报)。"""
    if works is None:
        works = [w.get("slug") or w.get("db") or str(w) for w in list_works(url)]
    out: dict = {}
    for w in works:
        store = SurrealStore(url=url, ns="scribe3", db=w) if url else \
            SurrealStore(ns="scribe3", db=w)
        try:
            store.apply_schema()
            out[w] = health_report(store, up_to=store.max_chapter())
        except Exception as e:
            out[w] = e
        finally:
            try:
                store.close()
            except Exception:
                pass
    return out


def main() -> None:
    reports = build_reports()
    lines: list[str] = []
    for w, rep in reports.items():
        if isinstance(rep, Exception):
            lines.append(f"## 书 {w}\n体检失败(如实上报):{rep}")
        elif not rep.clean:
            lines.append(f"## 书 {w}\n{render_markdown(rep)}")
    if lines:                            # --no-agent watchdog:全净=空 stdout=静默
        print("\n\n".join(lines))


if __name__ == "__main__":
    main()
