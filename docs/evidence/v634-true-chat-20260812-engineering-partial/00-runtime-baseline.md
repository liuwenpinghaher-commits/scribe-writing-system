# runtime baseline · v6.3.4 engineering window

- entry (protocol): https://tonglu.qing.blue
- entry (working from executor host): https://qing.blue
- captured_at_utc: 2026-08-11T16:51:07Z
- evidence window: 2026-08-12T00:00:00Z → 2026-08-11T16:51:07Z

## GET https://qing.blue/api/health
```json
{
  "ok": true,
  "ns": "scribe3",
  "db": "ok",
  "changefeed": {
    "enabled": true,
    "alive": true,
    "started_at": 1786466995.6652515,
    "last_ok_at": null,
    "last_error": null,
    "poll_count": 7,
    "invalidate_count": 0,
    "cursors": {
      "cache_watch": 117077665283309568
    },
    "work": "main"
  },
  "locks": {
    "distributed": true,
    "db_inflight": true
  },
  "surreal_flags": {
    "hybrid_search_native": true,
    "changefeed_cache": true,
    "db_inflight_lock": true,
    "db_knowledge_frame": true,
    "stats_view": true,
    "live_granular": true,
    "distributed_lock": true
  }
}
```

## GET https://qing.blue/api/ready
```json
{}
```

## GET /capabilities (demo backend session; flags)
```json
{
  "snapshot_v1": true,
  "editorial_thread_v1": true,
  "memory_fabric_v1": true,
  "context_inspector_v1": true,
  "assembler_v1": true,
  "emergency_rest_write": false,
  "ingest_lease": true,
  "ingest_policy": true,
  "mcp_craft_gate": true
}
```

## Asserts
- memory_fabric_v1 == true → **True**
- emergency_rest_write == false → **False**
- ingest_lease → True
- context_inspector_v1 → True

## Hermes
- docker bridge 172.18.0.1:8646/8645 → **200 ok**
- host 127.0.0.1:8645/8646 → not published
- H* **not SKIP** (gateway available); unexercised parallel → FAIL

## deploy
- stack: prod-backend-1 / prod-surreal-1 on 82.157.130.140
- no second Surreal / no Grok-local Surreal for acceptance
