# runtime baseline · v6.3.4 engineering window

- entry (protocol): https://tonglu.example.com
- entry (working from executor host): https://example.com
- captured_at_utc: 2026-08-11T17:06:21Z
- evidence window: 2026-08-11T16:00:00Z → 2026-08-11T17:06:21Z (start ≤ end)

## GET https://example.com/api/health
- HTTP 200
- body.ok: **True**
```json
{
  "ok": true,
  "ns": "scribe3",
  "db": "ok"
}
```
Full: `13-capability-audit/health.json`

## GET /ready (prod-backend-1 → 127.0.0.1:3321/ready)
- HTTP 200
- body.ready: **True**
```json
{
  "ready": true
}
```
Full: `13-capability-audit/ready.json`

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

## Asserts (boolean checks, not raw flag values)
| check | required | observed |
|-------|----------|----------|
| health_ok | true | **True** |
| ready_ok (body.ready===true) | true | **True** |
| memory_fabric_v1 is true | true | **True** (flag=True) |
| emergency_rest_write is false | true | **True** (flag=False) |

## Hermes
- docker bridge 172.18.0.1:8646/8645 → 200 ok
- host 127.0.0.1:8645/8646 → not published
- H* not SKIP (gateway available); unexercised parallel → FAIL

## deploy
- stack: prod-backend-1 / prod-surreal-1 on 203.0.113.10
- no second Surreal / no Grok-local Surreal for acceptance
