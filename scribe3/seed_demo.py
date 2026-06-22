"""一次性 demo 种子:把焦三/老道泄露场景填进 NS=scribe3,供写作台 v2 实操演示。

跑:scribe3/.venv/bin/python -m scribe3.seed_demo
(additive CREATE;重复跑会因 id 已存在报错——这是一次性 demo 种子。清库见 README。)
"""
from scribe3.scenario import luanshi_leak_world
from scribe3.store import SurrealStore


def main() -> None:
    store = SurrealStore(ns="scribe3", db="main")
    try:
        store.apply_schema()
        luanshi_leak_world(store)
        # 给读者帧加一条:读者已知"老道是流云观追索者",焦三视角不知 → 反讽点
        from scribe3.ontology import Fact, KnowledgeEdge
        store.add_fact(Fact("fact:追索", "role:老道", "身份", "流云观追索者", valid_from=1, secret=True))
        store.add_knowledge(KnowledgeEdge("reader", "fact:追索", since_chapter=1))
        print("✓ NS=scribe3 已填 demo:焦三/老道乱岗对峙 + 反讽点。开 API+前端即可看。")
    finally:
        store.close()


if __name__ == "__main__":
    main()
