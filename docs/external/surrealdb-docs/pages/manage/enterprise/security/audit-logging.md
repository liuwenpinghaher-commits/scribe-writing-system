---
title: "https://surrealdb.com/docs/manage/enterprise/security/audit-logging"
url: "https://surrealdb.com/docs/manage/enterprise/security/audit-logging"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/manage/enterprise/security/audit-logging

Source: https://surrealdb.com/docs/manage/enterprise/security/audit-logging

The audit log pipeline in SurrealDB Enterprise emits an authoritative, identity-bound record for every authenticated action — statements, queries, transactions, RPC calls, sign-in attempts, sessions and HTTP requests. Records flow to a durable NDJSON file sink with optional tamper-evident SHA-256 hash chaining and a three-pass redactor for embedded PII.
The full pipeline reference — events captured, record shape, rotation and durability, hash chaining, redaction, overflow semantics, and pipeline self-metrics — lives under the Observability section:
  * •
**[Audit logging reference](https://surrealdb.com/docs/manage/observability/audit-logging)** — the canonical reference for the pipeline.
  * •
**[Configuration → Audit log knobs](https://surrealdb.com/docs/manage/observability/configuration#audit-log-knobs)** — every audit-log environment variable, including the [Compliance checklist](https://surrealdb.com/docs/manage/observability/configuration#compliance-checklist) for tamper-evident deployments.
  * •
**[Slow-query logging](https://surrealdb.com/docs/manage/observability/slow-query-logging)** — the sister pipeline that captures the long tail of slow queries for triage.
