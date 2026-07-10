---
title: "https://surrealdb.com/docs/running/multi-node"
url: "https://surrealdb.com/docs/running/multi-node"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/running/multi-node

Source: https://surrealdb.com/docs/running/multi-node

Multi-node SurrealDB requires **shared distributed storage** — a backend that every query node can reach with transactional consistency. A single RocksDB file on one server (or one Kubernetes pod) is **not** a multi-node cluster; it is the [single-node, on-disk](https://surrealdb.com/docs/running/file-backed) model.
For managed production clusters, see the [Scale](https://surrealdb.com/pricing/scale) plan on [SurrealDB Cloud](https://surrealdb.com/docs/build/deployment/surrealdb-cloud/what-is-surrealdb-cloud), which runs on **SurrealDS**. For self-hosted highly available setups on Kubernetes, see [Amazon EKS](https://surrealdb.com/docs/build/deployment/self-hosted/amazon-eks), [Google GKE](https://surrealdb.com/docs/build/deployment/self-hosted/google-gke), and [Azure AKS](https://surrealdb.com/docs/build/deployment/self-hosted/azure-aks).
The section below uses **TiKV** as a local open-source playground for experimenting with multi-node connectivity. It is not the storage engine behind Cloud Scale or Enterprise SurrealDS deployments.
##  Local development[](https://surrealdb.com/docs/running/multi-node#local-development)
The following starts a local distributed-storage playground for development, then connects SurrealDB to it.

```bash
curl -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
tiup playground --tag surrealdb --mode tikv-slim --pd 1 --kv 1
```

Start SurrealDB against the playground endpoint:

```bash
surreal start tikv://127.0.0.1:2379
```

The default logging level for the database server is `info`. To control the logging verbosity, specify the `--log` argument. The following command starts the database with `debug` level logging, resulting in more logs being output to the terminal. If extra verbosity is not needed, specify a lower level or simply remove the flag, which will default to the `info` level.

```bash
surreal start --log debug tikv://127.0.0.1:2379
```

Configure your initial root-level user with `--user` and `--pass`. The root user is persisted in storage, so you do not need those flags on subsequent starts.

```bash
surreal start --user root --pass secret tikv://127.0.0.1:2379
```

Change the listen port with `--bind`:

```bash
surreal start --user root --pass secret --bind 0.0.0.0:8080 tikv://127.0.0.1:2379
```

After running the above command, you should see the SurrealDB server start up successfully.

```text
surreal start --user root --pass secret --bind 0.0.0.0:8080 tikv://127.0.0.1:2379
```

Output

```text
2025-02-14T12:16:28.660617Z  INFO surreal::env: Running 2.2.0 for macos on aarch64
2025-02-14T12:16:28.660678Z  INFO surrealdb::core::kvs::ds: Connecting to kvs store at tikv://127.0.0.1:2379
...
2025-02-14T12:16:28.680066Z  INFO surrealdb::net: Started web server on 0.0.0.0:8080
```

For details on the different commands available, visit the [CLI tool documentation](https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview).
##  Environment variables[](https://surrealdb.com/docs/running/multi-node#environment-variables)
Environment variables such as `SURREAL_TIKV_REQUEST_TIMEOUT` can be set to modify distributed-storage client behaviour. See [distributed storage environment variables](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#tikv-environment-variables).
