---
title: "https://surrealdb.com/docs/manage/self-hosted/monitoring-and-observability"
url: "https://surrealdb.com/docs/manage/self-hosted/monitoring-and-observability"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/manage/self-hosted/monitoring-and-observability

Source: https://surrealdb.com/docs/manage/self-hosted/monitoring-and-observability

SurrealDB exposes a built-in **`/health`**HTTP endpoint suitable for load balancer and orchestrator probes. A successful response indicates the process is accepting requests. Combine`/health` with deeper checks so you detect partial failures — slow queries, disk pressure, replication lag — before probes alone would fire.
For everything beyond a liveness probe, the [Observability](https://surrealdb.com/docs/manage/observability) section is the canonical reference and operator guide. The pages there cover metrics, telemetry access, audit logs and slow-query logs for both Community and Enterprise editions.
[Observability overview Edition matrix (Community vs Enterprise), Prometheus and OTLP quickstart, what's new in 3.1, Tokio console, structured logging.](https://surrealdb.com/docs/manage/observability)[Metrics reference Access paths, label catalogue, ~60 metrics grouped by signal family, the public allowlist, and the 3.0 → 3.1 migration table.](https://surrealdb.com/docs/manage/observability/metrics)[Configuration reference Every telemetry, audit-log and slow-query environment variable, plus recommended configurations for local, production and multi-tenant deployments.](https://surrealdb.com/docs/manage/observability/configuration)[Audit logging (Enterprise) Events captured, record shape, rotation, hash chaining, redaction and pipeline self-metrics.](https://surrealdb.com/docs/manage/observability/audit-logging)[Slow-query logging (Enterprise) Threshold-based capture of long-running queries with the same file-sink, hash-chain and redaction options as the audit pipeline.](https://surrealdb.com/docs/manage/observability/slow-query-logging)
##  Integrating with common observability stacks[](https://surrealdb.com/docs/manage/self-hosted/monitoring-and-observability#integrating-with-common-observability-stacks)
The OpenTelemetry exporter speaks OTLP gRPC, so anything that ingests OTLP works. Two common patterns:
  * •
**Prometheus pull.** Scrape the built-in `/metrics` endpoint. Anonymous scrapers see only the [public allowlist](https://surrealdb.com/docs/manage/observability/metrics#public-metrics-allowlist); pass root credentials to unlock the full surface. Build Grafana dashboards on the resulting time series and pair with Alertmanager for the [alert hints](https://surrealdb.com/docs/manage/observability/metrics#alert-hints) recommended for production.
  * •
**OTLP push.** Point SurrealDB at an OpenTelemetry collector and route from there into Prometheus remote-write, Tempo / Jaeger for traces, and Loki or a SIEM for logs (including audit and slow-query records when their OTel export is opted in). Label streams by environment (`production`, `staging`, `dev`) at the collector so dashboards do not mix traffic accidentally.

Either path uses the same `surrealdb.*` instrument namespace and the same `service.edition` resource attribute, so dashboards travel cleanly across deployments.
##  Key signals to watch[](https://surrealdb.com/docs/manage/self-hosted/monitoring-and-observability#key-signals-to-watch)
The full alert-hints starter set lives on the [metrics page](https://surrealdb.com/docs/manage/observability/metrics#alert-hints), but the must-watch signals for any production deployment are:
  * •
**Error rate** — `rate(surrealdb_statement_total{outcome="error"}[5m])` rising sharply against baseline.
  * •
**Transaction conflicts** — `rate(surrealdb_transaction_conflicts_total[5m])`, which doubles as the retry-pressure signal.
  * •
**Latency tails** — histogram percentiles on `surrealdb_statement_duration_seconds`, `surrealdb_query_duration_seconds`, `surrealdb_http_request_duration_seconds`.
  * •
**Active sessions and live queries** — `surrealdb_session_active`, `surrealdb_live_query_active` for capacity planning.
  * •
**Audit pipeline health (Enterprise)** — `surrealdb_audit_dropped`, `surrealdb_audit_append_errors`, `surrealdb_audit_queue_depth` to catch lost or delayed audit records.

Define SLOs where appropriate — latency and availability targets — and use burn-rate alerts on the resulting error budgets rather than relying on one-off thresholds alone.
