#!/usr/bin/env python3
"""初始化 _migration 表,登记已应用的迁移"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scribe3.store import SurrealStore

st = SurrealStore(url='ws://127.0.0.1:8001/rpc', ns='scribe3', db='main')
st._db.query("DEFINE TABLE IF NOT EXISTS _migration SCHEMALESS")
st._db.query("DEFINE FIELD IF NOT EXISTS applied_at ON _migration TYPE datetime")

existing = st._query("SELECT meta::id(id) AS id FROM _migration") or []
existing_ids = {r['id'] for r in existing if r and r.get('id')}
print(f"已登记: {len(existing_ids)} 个")

n = 0
for f in sorted(glob.glob('scribe3/migrations/*.surql')):
    name = os.path.basename(f).replace('.surql', '')
    key = f"_migration:{name}"
    if key not in existing_ids:
        sql = "CREATE type::thing('_migration', $name) SET applied_at = time::now()"
        st._db.query(sql, {"name": name})
        n += 1

print(f"新登记: {n} 个迁移")
st.close()
