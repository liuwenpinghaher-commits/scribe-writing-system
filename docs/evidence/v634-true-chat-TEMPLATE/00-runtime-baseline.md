# runtime baseline
- entry: https://tonglu.example.com
- GET https://tonglu.example.com/api/health →
- GET https://tonglu.example.com/api/ready →
- GET https://tonglu.example.com/api/capabilities → flags.memory_fabric_v1,
  flags.emergency_rest_write, flags.ingest_lease, flags.context_inspector_v1, ...
- Hermes deduce preview/full 可达性：ok / degraded / unavailable（影响 H* SKIP）
- 证据窗起止 UTC：
- deploy 备注（hot 时间可选）：
