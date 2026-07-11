---
title: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables"
url: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables

Source: https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables

Environment variables can be used to tailor the behaviour of a running SurrealDB instance.
Environment variables are divided into four types: 
  * •
**SurrealDB environment variables** : environment variables that pertain to the overall running of a SurrealDB server. Example: `SURREAL_DEFAULT_DATABASE`. Includes an [operator and internal config](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#operator-and-internal-config) subsection for advanced settings.
  * •
**Command environment variables** : environment variables that can be used in lieu of a command flag. Example: `SURREAL_CAPS_ALLOW_ALL=true surreal start`, equivalent to `surreal start --allow-all`.
  * •
**Storage backend environment variables** : environment variables that pertain to a certain storage backend. Example: `SURREAL_SURREALKV_MAX_SEGMENT_SIZE`.
  * •
**SurrealDB Cloud environment variables** : environment variables that are set via the [Configure instance](https://surrealdb.com/docs/build/deployment/surrealdb-cloud/getting-started/create-an-instance#configure-an-instance) sidebar for a SurrealDB Cloud instance.

Many environment variables have a maximum value equivalent to the greatest possible `usize`, which is an unsigned integer with a number of bytes depending on the target that the database runs on. For most systems this will be 64 bits, leading to a maximum size of 18_446_744_073_709_551_615 (264), while for 32 bits the maximum will be 4_294_967_296 (232).
##  SurrealDB environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#surrealdb-environment-variables)
These environment variables can be used to configure a SurrealDB server to configure areas such as the HTTP server and client, limits, telemetry, and so on.
###  Batch config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#batch-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_NORMAL_FETCH_SIZE`  | 500  | A usize  | The maximum number of keys that should be scanned at once in general queries.  |  
| `SURREAL_EXPORT_BATCH_SIZE`  | 1000  | A usize  | The maximum number of keys that should be scanned at once for export queries.  |  
| `SURREAL_COUNT_BATCH_SIZE`  | 10,000  | A usize  | The maximum number of keys that should be scanned at once for count queries.  |  
| `SURREAL_INDEXING_BATCH_SIZE`  | 250  | A usize  | The maximum number of keys to scan at once per concurrent indexing batch.  |  
###  Cache config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#cache-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_TRANSACTION_CACHE_SIZE`  | 10,000  | A usize  | Specifies the number of items which can be cached within a single transaction.  |  
| `SURREAL_DATASTORE_CACHE_SIZE`  | 1,000  | A usize  | The number of definitions which can be cached across transactions.  |  
| `SURREAL_HNSW_CACHE_SIZE`  | 268,435,456 (256 MiB)  | A usize  | The maximum size of the HNSW vector cache.  |  
| `SURREAL_DISKANN_CACHE_SIZE`  | 268,435,456 (256 MiB)  | A usize  |  The maximum total size, in bytes, of the DISKANN index cache, shared across all DISKANN indexes in the process. DISKANN graph data lives in the key-value store and is paged through this bounded cache. The DISKANN counterpart of `SURREAL_HNSW_CACHE_SIZE`.  |  
###  File config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#file-config)
Server-side filesystem access for features that read paths from disk (notably the `mapper()` filter on [`DEFINE ANALYZER`](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer)). This is separate from `SURREAL_BUCKET_FOLDER_ALLOWLIST` (below), which gates the experimental [files](https://surrealdb.com/docs/learn/schema-management/files/buckets) feature.  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_FILE_ALLOWLIST`  | none (deny all)  | Colon-separated paths on Unix; semicolon-separated on Windows  |  Directories the server may read when an analyzer uses `mapper('<path>')`. An empty or unset value denies every path. Each dictionary file must resolve under one of the listed directories. See [DEFINE ANALYZER — mapper](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer#mapperpath).  |  
| `SURREAL_BUCKET_FOLDER_ALLOWLIST`  | none  | Comma-separated paths  | Specifies a list of paths in which files can be accessed.  |  
| `SURREAL_GLOBAL_BUCKET`  | none  | A string  | Specifies the name of a global bucket for file data.  |  
| `SURREAL_GLOBAL_BUCKET_ENFORCED`  | false  | true, false  | Whether to enforce a global bucket for file data.  |  
###  HTTP client config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#http-client-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_MAX_HTTP_REDIRECTS`  | 10  | A usize  | The maximum number of HTTP redirects allowed within http functions.  |  
| `SURREAL_MAX_HTTP_IDLE_CONNECTIONS_PER_HOST`  | 128  | A usize  | The maximum number of idle HTTP connections to maintain per host.  |  
| `SURREAL_MAX_HTTP_IDLE_CONNECTIONS`  | 1000  | A usize  | The maximum number of idle HTTP connections to maintain.  |  
| `SURREAL_HTTP_IDLE_TIMEOUT_SECS`  | 90  | A usize  | The timeout for idle HTTP connections before closing.  |  
| `SURREAL_HTTP_CONNECT_TIMEOUT_SECS`  | 30  | A usize  | The timeout for connecting to HTTP endpoints.  |  
| `SURREAL_USER_AGENT`  | SurrealDB  | A string  | The USER-AGENT string used by HTTP requests.  |  
###  HTTP server config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#http-server-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_NET_MAX_CONCURRENT_REQUESTS`  | 1,048,576  | A usize  | How many concurrent network requests can be handled at once  |  
| `SURREAL_HTTP_MAX_ML_BODY_SIZE`  | 4,398,046,511,104 (4 GiB)  | A usize  | Maximum HTTP body size of the HTTP /ml endpoints  |  
| `SURREAL_HTTP_MAX_MCP_BODY_SIZE`  | 4,194,304 (4 MiB)  | A usize  |  Maximum HTTP body size of the HTTP `/mcp`endpoint. See [MCP](https://surrealdb.com/docs/build/ai-agents/mcp).  |  
| `SURREAL_HTTP_MAX_SQL_BODY_SIZE`  | 1,048,576 (1 MiB)  | A usize  | Maximum HTTP body size of the HTTP /sql endpoint  |  
| `SURREAL_HTTP_MAX_GQL_BODY_SIZE`  | 1,048,576 (1 MiB)  | A usize  |  Maximum HTTP body size of the HTTP `/gql`endpoint. See [GQL via HTTP](https://surrealdb.com/docs/learn/querying/gql/via-http).  |  
| `SURREAL_HTTP_MAX_API_BODY_SIZE`  | 4,194,304 (4 MiB)  | A usize  | The maximum HTTP body size of the HTTP /api endpoint.  |  
| `SURREAL_HTTP_MAX_RPC_BODY_SIZE`  | 4,194,304 (4 MiB)  | A usize  | Maximum HTTP body size of the HTTP /rpc endpoint.  |  
| `SURREAL_HTTP_MAX_KEY_BODY_SIZE`  | 16,384 (16 KiB)  | A usize  | Maximum HTTP body size of the HTTP /key endpoints  |  
| `SURREAL_HTTP_MAX_SIGNUP_BODY_SIZE`  | 1024 (1 KiB)  | A usize  | Maximum HTTP body size of the HTTP /signup endpoint.  |  
| `SURREAL_HTTP_MAX_IMPORT_BODY_SIZE`  | 4,398,046,511,104 (4 GiB)  | A usize  | Maximum HTTP body size of the HTTP /import endpoints  |  
| `SURREAL_HTTP_MAX_SIGNIN_BODY_SIZE`  | 1024 (1 KiB)  | A usize  | The maximum HTTP body size of the HTTP /signin endpoints  |  
###  MCP config 
Available since: v3.1.0
[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#mcp-config-since-vv310-)
Used by the built-in [Model Context Protocol](https://surrealdb.com/docs/build/ai-agents/mcp) server (`/mcp` on `surreal start`, `surreal mcp` on stdio). Stdio namespace/database selection uses `SURREAL_MCP_NS` and `SURREAL_MCP_DB` on the [`mcp`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/mcp) subcommand.  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_MCP_QUERY_TIMEOUT_SECS`  | 60  |  Seconds (integer); `0`disables  | Outer timeout on each MCP tool execution.  |  
| `SURREAL_MCP_MAX_RESULT_BYTES`  | 262,144 (256 KiB)  |  Bytes (integer); `0`disables  | Maximum serialised tool / resource response size; larger results are truncated with a marker.  |  
| `SURREAL_MCP_RUN_MAX_ARGS`  | 64  | A positive integer  |  Maximum arguments for a single `run`tool call.  |  
| `SURREAL_MCP_PARAMS_MAX_KEYS`  | 256  | A positive integer  | Maximum top-level keys in MCP parameter / data objects.  |  
###  GQL config 
Available since: v3.2.0
[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#gql-config-since-vv320-)
Resource limits for experimental [ISO GQL](https://surrealdb.com/docs/learn/querying/gql/overview) `MATCH` execution. Errors name the limit when it is exceeded. The language can be enabled by passing in the [`--allow-experimental gql`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start#experimental-capabilities) flag when starting the database.  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_GQL_MAX_PATH_ROWS`  | 1,000,000  | A usize  |  Per source row, bounds live and emitted rows during variable-length path expansion in a GQL `MATCH`.  |  
| `SURREAL_GQL_MAX_JOIN_BUILD_ROWS`  | 1,000,000  | A usize  | Bounds the in-memory build side of hash joins between GQL match patterns (and distinct-operator working sets).  |  
| `SURREAL_GQL_MAX_OUTPUT_ROWS`  | 1,000,000  | A usize  | Bounds cumulative rows emitted by GQL hash-join operators (including cross joins).  |  
###  Limits config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#limits-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_EXTERNAL_SORTING_BUFFER_LIMIT`  | 50000  | A usize  | The number of result records which will trigger on-disk sorting.  |  
| `SURREAL_STRING_SIMILARITY_LIMIT`  | 16384  | A usize  | The maximum input string length for similarity/distance functions  |  
| `SURREAL_GENERATION_ALLOCATION_LIMIT`  | 1,048,576  | A usize  |  Limits memory allocation for certain built-in functions (e.g., string::replace) to avoid uncontrolled memory usage. Default is 1,048,576 bytes (computed as 2 20).  |  
| `SURREAL_IDIOM_RECURSION_LIMIT`  | 256  | A usize  | The maximum recursive idiom path depth allowed.  |  
| `SURREAL_MAX_COMPUTATION_DEPTH`  | 120  | A usize  | Specifies how deep recursive computation will go before erroring.  |  
| `SURREAL_MAX_CONCURRENT_TASKS`  | 64  | A usize  | Specifies how many concurrent jobs can be buffered in the worker channel.  |  
| `SURREAL_MAX_OBJECT_PARSING_DEPTH`  | 100  | A usize  | Specifies how deep the parser will parse nested objects and arrays in a query.  |  
| `SURREAL_MAX_ORDER_LIMIT_PRIORITY_QUEUE_SIZE`  | 1000  | A usize  | The maximum size of the priority queue triggering usage of the priority queue for the result collector.  |  
| `SURREAL_MAX_QUERY_PARSING_DEPTH`  | 20  | A usize  | Specifies how deep the parser will parse recursive queries (queries within queries).  |  
| `SURREAL_OPERATOR_BUFFER_SIZE`  | 2  | A usize  | The number of batches each operator buffers ahead of downstream demand. Set to 0 to disable operator-level pipeline buffering.  |  
| `SURREAL_REGEX_SIZE_LIMIT`  | 10,485,760 (10 MiB)  | A usize  | Limits the maximum allowed size (in bytes) for regular expressions. This prevents excessive memory consumption when building complex or very large regex patterns.  |  
###  Runtime config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#runtime-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_RUNTIME_MAX_BLOCKING_THREADS`  | 512  | A usize  | Number of threads which can be started for blocking operations.  |  
| `SURREAL_RUNTIME_STACK_SIZE`  | 10,485,760 (10 MiB)  | A usize  | Runtime thread memory stack size. Default stack size is doubled if compiled from source in Debug mode.  |  
| `SURREAL_RUNTIME_WORKER_THREADS`  | Number of CPU cores (minimum 4)  | A usize  | Number of runtime worker threads used to start.  |  
###  Scripting config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#scripting-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_SCRIPTING_MAX_STACK_SIZE`  | 262_144 (256 KiB)  | A usize  | Maximum stack size of the JavaScript function runtime.  |  
| `SURREAL_SCRIPTING_MAX_MEMORY_LIMIT`  | 2,097,152 (2 MiB)  | A usize  | Maximum memory limit of the JavaScript function runtime.  |  
| `SURREAL_SCRIPTING_MAX_TIME_LIMIT`  | 5000 (5000 milliseconds or 5 seconds)  | A usize  | Maximum allowed time in milliseconds that a JavaScript function is allowed to run for.  |  
###  Security config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#security-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_INSECURE_FORWARD_ACCESS_ERRORS`  | false  | true, false  | Forward all signup/signin/authenticate query errors to a client performing authentication. Do not use in production.  |  
###  Surrealism config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#surrealism-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_LAZY_SURREALISM`  | false  | true, false  | Whether to lazy-load Surrealism modules instead of eagerly compiling them at server startup.  |  
| `SURREAL_SURREALISM_CACHE_SIZE`  | 100  | A usize  | The number of surrealism modules which can be cached across transactions.  |  
| `SURREAL_SURREALISM_MAX_POOL_SIZE`  | 8  | A usize  | Per-module controller pool size ceiling for Surrealism WASM modules.  |  
| `SURREAL_SURREALISM_MAX_MEMORY`  | None (unlimited)  | A usize  | Per-module WASM linear memory ceiling in bytes.  |  
| `SURREAL_SURREALISM_MAX_EXECUTION_TIME`  | None (unlimited)  | A u64 (milliseconds)  | Per-invocation execution time ceiling for Surrealism WASM modules.  |  
| `SURREAL_SURREALISM_MAX_KV_ENTRIES`  | None (unlimited)  | A usize  | Per-module KV store entry count ceiling.  |  
| `SURREAL_SURREALISM_MAX_KV_VALUE_BYTES`  | None (unlimited)  | A usize  | Per-module KV store maximum value size in bytes.  |  
| `SURREAL_SURREALISM_LOG_LEVEL`  | debug  | none, full, error, warn, info, debug, trace  | Controls the tracing level at which Surrealism module stdout is emitted.  |  
###  Telemetry config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#telemetry-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_TELEMETRY_DISABLE_METRICS`  | false  | true, false  | Whether to disable sending metrics to the GRPC OTEL collector.  |  
| `SURREAL_TELEMETRY_DISABLE_TRACING`  | false  | true, false  | Whether to disable sending traces to the GRPC OTEL collector.  |  
| `SURREAL_TELEMETRY_NAMESPACE`  | none  | A string  | If set then use this as value for the namespace label when sending telemetry  |  
| `SURREAL_TELEMETRY_PROVIDER`  | none  | otlp  | If set to "otlp" then telemetry is sent to the GRPC OTEL collector.  |  
| `SURREAL_TOKIO_CONSOLE_ENABLED`  | false  | true, false  | Whether to enable [tokio console](https://github.com/tokio-rs/console).  |  
| `SURREAL_TOKIO_CONSOLE_RETENTION`  | 60  | A usize  | How long, in seconds, to retain data for completed events.  |  
| `SURREAL_TOKIO_CONSOLE_SOCKET_ADDR`  | none  | String to a socket address  | The socket address that Tokio Console will bind to.  |  
###  WebSocket config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#websocket-config)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_WEBSOCKET_MAX_MESSAGE_SIZE`  | 134,217,728 (128 MiB)  | A usize  | The maximum WebSocket message size.  |  
| `SURREAL_WEBSOCKET_MAX_WRITE_BUFFER_SIZE`  | Greatest possible usize value  | A usize  | The maximum write buffer size before backpressure is applied.  |  
| `SURREAL_WEBSOCKET_READ_BUFFER_SIZE`  | 131,072 (128 KiB)  | A usize  | The size of the read buffer for WebSocket connections. This controls how much data can be buffered when reading from WebSocket connections. Larger values can improve performance for high-throughput connections but consume more memory per connection.  |  
| `SURREAL_WEBSOCKET_WRITE_BUFFER_SIZE`  | 131,072 (128 KiB)  | A usize  | The size of the write buffer for WebSocket connections. This controls how much data can be buffered when writing to WebSocket connections. Larger values can improve performance for high-throughput connections but consume more memory per connection.  |  
| `SURREAL_WEBSOCKET_RESPONSE_BUFFER_SIZE`  | 0  | A usize  | How many responses can be buffered when delivering to the client.  |  
| `SURREAL_WEBSOCKET_RESPONSE_CHANNEL_SIZE`  | 100  | A usize  | Number of messages that can be queued for sending via WebSocket.  |  
| `SURREAL_WEBSOCKET_RESPONSE_FLUSH_PERIOD`  | 3  | A usize  | How often (in milliseconds) any buffered responses are flushed to the WebSocket client.  |  
###  Operator and internal config[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#operator-and-internal-config)
Available since: v3.2.0
These settings are for operators, benchmarks, and advanced debugging — not typical application configuration. They are documented so core contributors and self-hosted deployments can find configuration options that already exist in the engine. Changing them can affect performance, reproducibility, or live-query behaviour; leave defaults in place unless you have a specific reason to tune them.  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_RAND_SEED`  | none (non-deterministic)  |  A `u64`  | Seeds the engine-wide RNG for reproducible runs in benchmarks and tests. Do not use in production.  |  
| `SURREAL_LIVE_QUERY_ENGINE`  | `inline`  |  `inline`, `router`  |  Selects the live-query execution engine. `inline`is the historical behaviour; `router`decouples write cost from subscriber count (experimental rollout).  |  
| `SURREAL_LIVE_QUERY_RETENTION`  | 1h  | A duration  |  How long the router engine retains live-query event history for subscriber resume. Only applies when `SURREAL_LIVE_QUERY_ENGINE=router`.  |  
| `SURREAL_HNSW_BUILD_SEED`  | none  |  A `u64`  | Seeds HNSW index construction for reproducible graph layouts in benchmarks. Do not use in production.  |  
###  Other environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#other-environment-variables)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_BUILD_METADATA`  | Automatically populated  | A string  | The version identifier of this build. Defaults to the CARGO_PKG_VERSION environment variable if not specified.  |  
| `SURREAL_DATASTORE_AOL`  | never  | never|sync|async  | Append-only log mode. Only used by the memory engine.  |  
| `SURREAL_DATASTORE_PERSIST`  | none  | String to a file path  | Filesystem path for persistence. Only used by the memory engine.  |  
| `SURREAL_DATASTORE_RETENTION`  | 0 (unlimited)  | A duration  | Version retention period as a duration string. Used by memory and surrealkv engines.  |  
| `SURREAL_DATASTORE_SNAPSHOT`  | never  | never|duration  | Snapshot interval. Only used by the memory engine.  |  
| `SURREAL_DATASTORE_SYNC_DATA`  | every  | never|every|duration  | The sync mode for the database. Used by memory, rocksdb, and surrealkv engines.  |  
| `SURREAL_DATASTORE_VERSIONED`  | false  | true|false|0|1  | Whether MVCC versioning is enabled. Used by memory and surrealkv engines.  |  
| `SURREAL_MEMORY_THRESHOLD`  | 0  | A usize or suffixed integer  | Configuring the memory threshold which can be used across the programme to check if the amount of memory available to the programme is lower than required. The value can be specified as bytes (b, or without any suffix), kibibytes (k, kb, or kib), mebibytes (m, mb, or mib), or gibibytes (g, gb, or gib). If the environment variable is not specified, then the threshold is not used, and no memory limit is enabled.  |  
| `SURREAL_REGEX_CACHE_SIZE`  | 1000  | A usize  | The number of computed regexes which can be cached in the engine.  |  
##  Command environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#command-environment-variables)
Many of the arguments passed into [the CLI](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) can be set using the above environment variables instead.
As each of these environment variables correspond to a flag or a required argument passed into a command, it is good practice to put together a command that matches the environment variables you wish to set. Once the database server conforms to your expected behaviour, you can then pull out the values passed into each flag for your environment variables.
For example, take the following command to start the database.

```bash
surreal start --user root --pass secret --allow-net --deny-funcs "crypto::md5, http::post, http::delete"
```

If we now wanted to use environment variables instead of the `--allow-net` and `--deny-funcs` flags, we would use the `SURREAL_CAPS_ALLOW_NET` and `SURREAL_CAPS_DENY_FUNC` environment variables.
As the `--allow-net` flag was passed in without a following value, the same will be the case with the `SURREAL_CAPS_ALLOW_NET` environment variable, becoming `SURREAL_CAPS_ALLOW_NET=`. The `--deny-funcs` flag can also be used on its own to deny execution of all functions, but in this case is followed by a string to indicate which exact functions are not allowed to be executed. As such, the `SURREAL_CAPS_DENY_FUNC` environment variable must also be followed by a string, becoming `SURREAL_CAPS_DENY_FUNC="crypto::md5, http::post, http::delete"`.
The command would then look like the following:
BashPowerShell

```bash
SURREAL_CAPS_ALLOW_NET
SURREAL_CAPS_DENY_FUNC="crypto::md5, http::post, http::delete"
surreal start --user root --pass secret
```

```powershell
$env:SURREAL_CAPS_ALLOW_NET
$env:SURREAL_CAPS_DENY_FUNC="crypto::md5, http::post, http::delete"
surreal start --user root --pass secret
```

A command environment variable that takes a boolean will be set to true if the flag is present, and following it with `true` will cause an error.
For example, the `SURREAL_CAPS_ALLOW_ALL` environment variable is used to set whether to allow all capabilities such as scripting and allowing network access. The flag `--allow-all` is all that is needed to set to `true`. But as an environment variable, the value `true` must be included to override its default `false` value.
SURREAL_CAPS_ALLOW_ALL example

```bash
# set to default false
surreal start

# Same, but implicitly shown
SURREAL_CAPS_ALLOW_ALL=false surreal start

# Set to true
SURREAL_CAPS_ALLOW_ALL=true surreal start

# Set to true
surreal start --allow-all

# Error: only --allow-all needed to set to true
surreal start --allow-all true
```
  
| Environment variable  | Command arg  | For command(s)  | Default  | Allowed values  | Details  |  
| --- | --- | --- | --- | --- | --- |  
| `SURREAL_ASYNC_EVENT_PROCESSING_INTERVAL`  | `async-event-processing-interval`  | `start`  | 5s  | A duration  | The interval at which to process async events.  |  
| `SURREAL_AUTH_LEVEL`  | `auth-level`  | `export`, `import`, `sql`  | root  | root, namespace, ns, database, db  | Authentication level to use when connecting.  |  
| `SURREAL_BIND`  | `bind`  | `start`  | 127.0.0.1:8000  | String to an address  | The hostname or IP address(es) to listen for connections on.  |  
| `SURREAL_CAPS_ALLOW_ALL`  | `allow-all`  | `start`  | false  | true, false  | Allow all capabilities.  |  
| `SURREAL_CAPS_ALLOW_ARBITRARY_QUERY`  | `allow-arbitrary-query`  | `start`  | none  | guest, record, system (comma-separated)  | Allows arbitrary queries to be used by user groups except when specifically denied. Alternatively, you can provide a comma-separated list of user groups to allow specifically denied user groups to prevail over any other allowed user group.  |  
| `SURREAL_CAPS_ALLOW_EVAL_QUERY`  | `allow-eval-query`  | `start`, `sql`  | none (denied for all subjects)  | guest, record, system (comma-separated)  |  Allow `eval::surql`and `eval::gql`for listed subject groups. Not enabled by `--allow-all`. Still subject to [arbitrary-query](https://surrealdb.com/docs/learn/security/authorization/capabilities#arbitrary-queries)restrictions — `--deny-arbitrary-query`blocks `eval`for that subject even when eval is allowed here. For remote clients, set on the `start`process only. See [Capabilities and remote connections](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/sql#capabilities-and-remote-connections).  |  
| `SURREAL_CAPS_ALLOW_EXPERIMENTAL`  | `allow-experimental`  | `start`, `sql`  | none  | files, surrealism, gql (comma-separated)  |  Allow execution of experimental features. For remote clients, set on the `start`process. On `surreal sql`, affects embedded engines and REPL parse validation only. See [experimental capabilities](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start#experimental-capabilities).  |  
| `SURREAL_CAPS_ALLOW_FUNC`  | `allow-funcs`  | `start`  | all functions allowed  |  Empty, `*`, or comma-separated function paths  |  Allow execution of all functions except for functions that are specifically denied. Set to an empty value or `*`to allow all functions. Use a comma-separated list (for example, `array,string::len,http::get`) to allow specific function families or names. Values such as `true`are not valid. The environment variable name is singular ( `FUNC`), matching the `--allow-funcs`flag.  |  
| `SURREAL_CAPS_ALLOW_GUESTS`  | `allow-guests`  | `start`  | true  | true, false  | Allow guest users to execute queries.  |  
| `SURREAL_CAPS_ALLOW_NET`  | `allow-net`  | `start`  | none  | Comma-separated list of paths  | Allow all or certain outbound network access.  |  
| `SURREAL_CAPS_ALLOW_SCRIPT`  | `allow-scripting`  | `start`  | true  | true, false  | Allow execution of embedded scripting functions.  |  
| `SURREAL_CAPS_ALLOW_INSECURE_STORABLE_CLOSURES`  | `allow-insecure-storable-closures`  | `start`  | false  | true, false  | Takes a boolean. Prevents closures from being stored, which eliminates a potential attack surface. For version 2.5.0, this can still be allowed by using this capability.  |  
| `SURREAL_CAPS_DENY_ALL`  | `deny-all`  | `start`  | false  | true, false  | Deny all capabilities.  |  
| `SURREAL_CAPS_DENY_EVAL_QUERY`  | `deny-eval-query`  | `start`, `sql`  | none  | guest, record, system (comma-separated)  |  Deny `eval::surql`and `eval::gql`for listed subject groups. Deny prevails over allow at the same specificity. For remote clients, set on the `start`process.  |  
| `SURREAL_CAPS_DENY_FUNC`  | `deny-funcs`  | `start`  | false  | true, false, comma-separated list  | Deny execution of all or certain functions.  |  
| `SURREAL_CAPS_DENY_GUESTS`  | `deny-guests`  | `start`  | true  | true, false  | Deny guest users from executing queries.  |  
| `SURREAL_CAPS_DENY_NET`  | `deny-net`  | `start`  | true  | true, false, comma-separated list  | Deny all or certain outbound access paths.  |  
| `SURREAL_CAPS_DENY_SCRIPT`  | `deny-scripting`  | `start`  | true  | true, false  | Deny execution of embedded scripting functions.  |  
| `SURREAL_CHANGEFEED_GC_INTERVAL`  | `changefeed-gc-interval`  | `start`  | 30s  | A duration  | The interval at which to perform changefeed garbage collection.  |  
| `SURREAL_CLIENT_IP`  | `client-ip`  | `start`  | none  | none, socket, CF-Connecting-IP, Fly-Client-IP, True-Client-IP, X-Real-IP, X-Forwarded-For, Forwarded  |  The method of detecting the client's IP address. `Forwarded`parses the RFC 7239 `Forwarded`header ( `for=`parameter).  |  
| `SURREAL_DATABASE`  | `database`  | `sql`  | main  | A string  | The database selected when starting the REPL.  |  
| `SURREAL_DATABASE`  | `database`  | `export`, `import`  | none  | A string  | The database selected for the import or export.  |  
| `SURREAL_DEFAULT_DATABASE`  | `default-database`  | `start`  | main  | A string  | The default database to use when starting a SurrealDB instance.  |  
| `SURREAL_DEFAULT_NAMESPACE`  | `default-namespace`  | `start`  | main  | A string  | The default namespace to use when starting a SurrealDB instance.  |  
| `SURREAL_HIDE_WELCOME`  | `hide-welcome`  | `sql`  | false  | true, false  | Whether to show the welcome message when starting the REPL.  |  
| `SURREAL_IMPORT_FILE`  | `import-file`  | `start`  | none  | A file path  | Path to a SurrealQL file that will be imported when starting the server.  |  
| `SURREAL_INDEX_COMPACTION_INTERVAL`  | `index-compaction-interval`  | `start`  | 5s  | A duration  | The interval at which to perform changefeed garbage collection.  |  
| `SURREAL_KEY`  | `key`  | `start`  | none  | A string 16, 24, or 32 bytes long  | Encryption key to use for on-disk encryption. Not currently in use.  |  
| `SURREAL_KVS_CA`  | `kvs-ca`  | `start`  | none  | String to a path  | Path to the CA file used when connecting to the remote KV store.  |  
| `SURREAL_KVS_CRT`  | `kvs-crt`  | `start`  | none  | String to a path  | Path to the certificate file used when connecting to the remote KV store.  |  
| `SURREAL_KVS_KEY`  | `kvs-key`  | `start`  | none  | String to a path  | Path to the private key file used when connecting to the remote KV store.  |  
| `SURREAL_LAZY_SURREALISM`  | `lazy-surrealism`  | `start`  | false  | true, false  | Whether to lazy-load Surrealism modules instead of eagerly compiling them at server startup.  |  
| `SURREAL_LOG`  | `log`  | `start`, `fix`  | info  | none, full, error, warn, info, debug, trace  | The logging level for the database server.  |  
| `SURREAL_LOG_FILE_ENABLED`  | `log-file-enabled`  | `start`  | false  | true, false  | Toggles file output.  |  
| `SURREAL_LOG_FILE_FORMAT`  | `log-file-format`  | `start`  | none  | text, json  | The format for log file output.  |  
| `SURREAL_LOG_FILE_LEVEL`  | `log-file-level`  | `start`  | none  | none, full, error, warn, info, debug, trace  | Override the logging level for file output  |  
| `SURREAL_LOG_FILE_NAME`  | `log-file-name`  | `start`  | surrealdb.log  | String to a file  | Filename for logs (default: `surrealdb.log`)  |  
| `SURREAL_LOG_FILE_PATH`  | `log-file-path`  | `start`  | logs  | String to a path  | Sets the directory for logs  |  
| `SURREAL_LOG_FILE_ROTATION`  | `log-file-rotation`  | `start`  | daily  | daily, hourly, never  | Sets the rotation duration for logs.  |  
| `SURREAL_LOG_FORMAT`  | `log-format`  | `start`  | text  | text, json  | Sets the format for logs.  |  
| `SURREAL_LOG_OTEL_LEVEL`  | `log-otel-level`  | `start`  | SURREAL_LOG logging level  | none, full, error, warn, info, debug, trace  | Override the logging level for OpenTelemetry  |  
| `SURREAL_LOG_SOCKET`  | `log-socket`  | `start`  | none  | String to a host:port  | Send logs to the specified host:port  |  
| `SURREAL_LOG_SOCKET_FORMAT`  | `log-socket-format`  | `start`  | text  | text, json  | Set the format of the logs to the socket.  |  
| `SURREAL_LOG_SOCKET_LEVEL`  | `log-socket-level`  | `start`  | SURREAL_LOG logging level  | none, full, error, warn, info, debug, trace  | Override the logging level for socket logs. Possible values: none, full, error, warn, info, debug, trace  |  
| `SURREAL_NAME`  | `name`  | `ml export`  | none  | A string  | The name of the model.  |  
| `SURREAL_NAMESPACE`  | `namespace`  | `sql`  | main  | A string  | The namespace to connect to via the REPL.  |  
| `SURREAL_NAMESPACE`  | `namespace`  | `export`, `import`  | none  | A string  | The namespace selected for the import/export operation.  |  
| `SURREAL_NO_BANNER`  | `no-banner`  | `start`  | false  | true, false  | Whether to hide the startup banner.  |  
| `SURREAL_NO_DEFAULTS`  | `no-defaults`  | ``start``  | false  | true, false  | Whether to disable default namespace and database creation. Conflicts with SURREAL_DEFAULT_DATABASE and SURREAL_DEFAULT_NAMESPACE, which set a default value for namespace and database for a new instance.  |  
| `SURREAL_NO_IDENTIFICATION_HEADERS`  | `no-identification-headers`  | `start`  | false  | true, false  | Whether to suppress the server name and version headers.  |  
| `SURREAL_NODE_MEMBERSHIP_CHECK_INTERVAL`  | `node-membership-check-interval`  | `start`  | 15s  | A duration  | The interval at which to process and archive inactive nodes.  |  
| `SURREAL_NODE_MEMBERSHIP_CLEANUP_INTERVAL`  | `node-membership-cleanup-interval`  | `start`  | 300s  | A duration  | The interval at which to process and cleanup archived nodes.  |  
| `SURREAL_NODE_MEMBERSHIP_REFRESH_INTERVAL`  | `node-membership-refresh-interval`  | `start`  | 3s  | A duration  | The interval at which to refresh node registration information.  |  
| `SURREAL_PASS`  | `pass`  | `export`, `import`, `sql`, `start`  | none  | A string  | Database authentication password to use when connecting.  |  
| SURREAL_PATH  | `path`  | `fix`, `start`  | memory  | A string  | Database path used for storing data. As a required argument (albeit with a default), it is not passed in via `--path`.  |  
| `SURREAL_PLANNER_STRATEGY`  | `planner-strategy`  | `start`  | best-effort  | best-effort|compute-only|all-read-only  | Which strategy to use with the new query planner introduced in SurrealDB 3.0. The default setting uses the new planner for read-only statements, falling back to the previous compute planner on unimplemented paths. The new planner can be skipped entirely by using compute-only.  |  
| `SURREAL_QUERY_TIMEOUT`  | `query-timeout`  | `start`  | none  | A duration  | The maximum duration that a set of statements can run for.  |  
| `SURREAL_RECLAIM_INTERVAL`  | `reclaim-interval`  | `start`  | 60s  | A duration  |  How often the background reaper scans for tombstoned namespace, database, and index data to physically delete after a `REMOVE`statement.  |  
| `SURREAL_RECLAIM_GRACE`  | `reclaim-grace`  | `start`  | 10m  | A duration  |  Minimum age a removed namespace, database, or index must reach before its data is reclaimed. The effective grace is the maximum of this value and `--tikv-gc-lifetime`on TiKV backends.  |  
| `SURREAL_SLOW_QUERY_LOG_THRESHOLD`  | `slow-log-threshold`  | `start`  | none  | A duration  | A duration specifying the minimum execution time after which a log is made to indicate a slow query  |  
|  `SURREAL_SLOW_QUERY_LOG_PARAM_ALLOW``slow-log-param-allow`  | `slow-log-param-allow`  | `start`  | none  | Comma-separated strings  | A comma-separated list of parameter names to include in slow query logs.  |  
| `SURREAL_SLOW_QUERY_LOG_PARAM_DENY`  | `slow-log-param-deny`  | `start`  | none  | Comma-separated strings  | A comma-separated list of parameter names to omit from slow query logs.  |  
| `SURREAL_STRICT`  | `strict`  | `start`  | false  | true, false  | Whether strict mode is enabled on this database instance. Ignored since SurrealDB 3.0 after which strictness is defined [per database](https://surrealdb.com/docs/reference/query-language/statements/define/database#defining-a-strict-database) instead of instance.  |  
| `SURREAL_TEMPORARY_DIRECTORY`  | `temporary-directory`  | `start`  | none  | String to a directory  | Sets the directory for storing temporary database files  |  
| `SURREAL_TOKEN`  | `token`  | `export`, `import`, `sql`  | none  | A string  | Authentication token in JWT format to use when connecting.  |  
| `SURREAL_TRANSACTION_TIMEOUT`  | `transaction-timeout`  | `start`  | none  | A duration  | The maximum duration that any single transaction can run for.  |  
| `SURREAL_UNAUTHENTICATED`  | `unauthenticated`  | `start`  | false  | true, false  | Whether to allow unauthenticated access.  |  
| `SURREAL_USER`  | `user`  | `export`, `import`, `sql`, start  | none  | A string  | Database authentication username to use when connecting.  |  
| `SURREAL_VERSION`  | `version`  | `ml export`  | none  | A string  | The version of the ML model.  |  
| `SURREAL_WEB_CRT`  | `web-crt`  | `start`  | none  | String to a path  | Path to the certificate file for encrypted client connections.  |  
| `SURREAL_WEB_KEY`  | `web-key`  | `start`  | none  | String to a path  | Path to the private key file for encrypted client connections.  |  
##  Storage backend environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#storage-backend-environment-variables)
These environment variables are used to configure the storage backend for SurrealDB.
###  RocksDB environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#rocksdb-environment-variables)
Many RocksDB environment variables pertain to memory use. The default configuration results in the following rough estimates of RocksDB memory use on different instances:  
| Instance memory size  | Estimate  |  
| --- | --- |  
| 512 MiB  | ~ 80MiB  |  
| 1 GiB  | ~ 80MiB  |  
| 2 GiB  | ~ 640MiB  |  
| 4 GiB  | ~ 1.25GiB  |  
| 8 GiB  | ~ 3.25GiB  |  
| 24 GiB  | ~ 12GiB  |  
| 128 GiB  | ~ 67GiB  |  
The available environment variables for configuring a RocksDB instance are:  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_ROCKSDB_BACKGROUND_FLUSH`  | true  | false, true  | Whether to enable background WAL file flushing.  |  
| `SURREAL_ROCKSDB_BACKGROUND_FLUSH_INTERVAL`  | 200 (milliseconds)  | A usize  | The interval in milliseconds between background flushes.  |  
| `SURREAL_ROCKSDB_BLOB_COMPRESSION_TYPE`  | snappy  | none, snappy, lz4, zstd  | Compression type used for blob files.  |  
| `SURREAL_ROCKSDB_BLOB_FILE_SIZE`  | 268,435,456 (256 MiB)  | A usize  | The target blob file size for RocksDB.  |  
| `SURREAL_ROCKSDB_ENABLE_BLOB_GC`  | true  | true, false  | Whether to enable blob garbage collection for RocksDB.  |  
| `SURREAL_ROCKSDB_BLOB_GC_AGE_CUTOFF`  | 0.5  | Float between 0 and 1  | Fractional age cutoff for blob GC.  |  
| `SURREAL_ROCKSDB_BLOB_GC_FORCE_THRESHOLD`  | 0.5  | Float between 0 and 1  | Discardable ratio threshold to force GC.  |  
| `SURREAL_ROCKSDB_BLOB_COMPACTION_READAHEAD_SIZE`  | 0  | A usize  | Readahead size for blob compaction/GC.  |  
| `SURREAL_ROCKSDB_BLOCK_CACHE_SIZE`  | Dynamically calculated via greater of ((system memory / 2) - 1 GiB) and 16MiB  | A usize  |  RocksDB [block cache size](https://github.com/facebook/rocksdb/wiki/memory-usage-in-rocksdb)in bytes  |  
| `SURREAL_ROCKSDB_BLOCK_SIZE`  | 65,536 (64 KiB)  | A usize  | The size of each uncompressed data block in bytes.  |  
| `SURREAL_ROCKSDB_COMPACTION_READAHEAD_SIZE`  | 4 MiB (systems under 4 GiB), 8 MiB (up to 16 GiB), 16 MiB (others)  | A usize  | The readahead buffer size used during compaction.  |  
| `SURREAL_ROCKSDB_COMPACTION_STYLE`  | level  | level, universal  | Use to specify the database compaction style.  |  
| `SURREAL_ROCKSDB_DELETION_FACTORY_DELETE_COUNT`  | 50  | A usize  | The number of deletions to track in the window.  |  
| `SURREAL_ROCKSDB_DELETION_FACTORY_RATIO`  | 0.5  | A float  | The ratio of deletions to track in the window.  |  
| `SURREAL_ROCKSDB_DELETION_FACTORY_WINDOW_SIZE`  | 1000  | A usize  | The size of the window used to track deletions.  |  
| `SURREAL_ROCKSDB_ENABLE_BLOB_FILES`  | true  | true, false  | Whether to enable separate key and value file storage.  |  
| `SURREAL_ROCKSDB_ENABLE_PIPELINED_WRITES`  | true  | true, false  | Whether to use separate queues for WAL writes and memtable writes.  |  
| `SURREAL_ROCKSDB_GROUPED_COMMIT`  | true  | true, false  | Whether to enable grouped commit when sync is enabled. When enabled, multiple transaction commits are batched together and flushed to disk with a single fsync operation, improving throughput. When disabled, each transaction is committed and synced individually, which may provide lower latency for single transactions at the cost of reduced throughput under high load. Only used when SURREAL_SYNC_DATA is enabled and SURREAL_ROCKSDB_BACKGROUND_FLUSH is disabled.  |  
| `SURREAL_ROCKSDB_GROUPED_COMMIT_MAX_BATCH_SIZE`  | 4096  | A usize  | The maximum number of transactions in a single grouped commit batch. Used to prevent unbounded memory growth while still allowing large batches for efficiency. Larger batches improve throughput but increase memory usage and commit latency.  |  
| `SURREAL_ROCKSDB_GROUPED_COMMIT_TIMEOUT`  | 5ms  | A duration  | The maximum wait time in nanosecond before forcing a grouped commit. Used to ensure that transactions do not wait indefinitely when concurrency is low, and to balance between transaction latency and write throughput.  |  
| `SURREAL_ROCKSDB_GROUPED_COMMIT_WAIT_THRESHOLD`  | 12  | A usize  | Threshold for deciding whether to wait for more transactions. If the current batch size is greater or equal to this threshold (and below ROCKSDB_GROUPED_COMMIT_MAX_BATCH_SIZE), then the coordinator will wait up to ROCKSDB_GROUPED_COMMIT_TIMEOUT to collect more transactions. Smaller batches are flushed immediately to preserve low latency.  |  
| `SURREAL_ROCKSDB_FILE_COMPACTION_TRIGGER`  | 4  | A usize  | The number of files needed to trigger level 0 compaction.  |  
| `SURREAL_ROCKSDB_JOBS_COUNT`  | Number of CPUs * 2  | A usize  | The maximum number of threads to use for flushing and compaction.  |  
| `SURREAL_ROCKSDB_KEEP_LOG_FILE_NUM`  | 10  | A usize  | The maximum number of information log files to keep.  |  
| `SURREAL_ROCKSDB_MAX_CONCURRENT_SUBCOMPACTIONS`  | 4  | A usize  | The maximum number threads which will perform compactions.  |  
| `SURREAL_ROCKSDB_MAX_OPEN_FILES`  | 1024  | A usize  | The maximum number of open files which can be opened by RocksDB.  |  
| `SURREAL_ROCKSDB_MAX_WRITE_BUFFER_NUMBER`  | 2 (systems under 4 GiB), 4 (up to 16 GiB), 8 (up to 64 GiB), 32 (others)  | A usize  | The maximum number of write buffers which can be used.  |  
| `SURREAL_ROCKSDB_MIN_BLOB_SIZE`  | 4096  | A usize  | The minimum size in bytes of a value for it to be stored in blob files.  |  
| `SURREAL_ROCKSDB_MIN_WRITE_BUFFER_NUMBER_TO_MERGE`  | 2  | A usize  | The minimum number of write buffers to merge before writing to disk.  |  
| `SURREAL_ROCKSDB_SST_MAX_ALLOWED_SPACE_USAGE`  | 0  | A usize  | The maximum allowed space usage for SST files in bytes. The default of 0 means unlimited and disables space monitoring. When this limit is reached, the datastore enters read-and-deletion-only mode, where only read and delete operations are allowed. This allows gradual space recovery through data deletion.  |  
| `SURREAL_ROCKSDB_STORAGE_LOG_LEVEL`  | warn  | none, full, error, warn, info, debug, trace  | The information log level of the RocksDB library.  |  
| `SURREAL_ROCKSDB_TARGET_FILE_SIZE_BASE`  | 67,108,864 (64 MiB)  | —  | The target file size for compaction in bytes.  |  
| `SURREAL_ROCKSDB_TARGET_FILE_SIZE_MULTIPLIER`  | 2  | A usize  | The target file size multiplier for each compaction level.  |  
| `SURREAL_ROCKSDB_THREAD_COUNT`  | Number of CPUs on machine  | A usize  | The number of threads to start for flushing and compaction.  |  
| `SURREAL_ROCKSDB_WAL_SIZE_LIMIT`  | 0  | A usize  | The write-ahead-log size limit in MiB.  |  
| `SURREAL_ROCKSDB_WRITE_BUFFER_SIZE`  | 32 MiB (systems under 1 GiB), 64 MiB (up to 16 GiB), 128 MiB (others)  | A usize  | The amount of data each write buffer can build up in memory.  |  
| `SURREAL_SYNC_DATA`  | true  | true, false  | Whether to sync writes to disk before acknowledgement.  |  
###  SurrealKV environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#surrealkv-environment-variables)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_SURREALKV_ENABLE_VLOG`  | true  | true, false  | Whether to enable value log separation.  |  
| `SURREAL_SURREALKV_VERSIONED_INDEX`  | false  | true, false  | Whether to enable versioned index. Only applies when versioning is enabled.  |  
| `SURREAL_SURREALKV_BLOCK_SIZE`  | 65_536 (64 KiB)  | A usize  | The block size in bytes.  |  
| `SURREAL_SURREALKV_VLOG_MAX_FILE_SIZE`  | 64 MiB (systems under 4 GiB), 128 MiB (up to 16 GiB), 256 MiB (up to 64 GiB), 512 MiB (others)  | A usize  | The readahead buffer size used during compaction.  |  
| `SURREAL_SURREALKV_VLOG_THRESHOLD`  | 4096 (4 KiB)  | A usize  | The value log threshold in bytes. Values larger than this are stored in the value log.  |  
| `SURREAL_SURREALKV_BLOCK_CACHE_CAPACITY`  | Dynamically calculated via greater of ((system memory / 2) - 1 GiB) and 16MiB  | A usize  | The maximum log file size in bytes.  |  
| `SURREAL_SURREALKV_GROUPED_COMMIT_TIMEOUT`  | 5ms  | A duration in nanoseconds  | The maximum wait time in nanoseconds before forcing a grouped commit. Ensures that transactions do not wait indefinitely under low concurrency and balances commit latency against write throughput.  |  
| `SURREAL_SURREALKV_GROUPED_COMMIT_WAIT_THRESHOLD`  | 12  | A usize  | Threshold for deciding whether to wait for more transactions. If the current batch size is greater or equal to this threshold (and below SURREAL_SURREALKV_GROUPED_COMMIT_MAX_BATCH_SIZE), then the coordinator will wait up to SURREAL_SURREALKV_GROUPED_COMMIT_TIMEOUT to collect more transactions. Smaller batches are flushed immediately to preserve low latency.  |  
| `SURREAL_SURREALKV_GROUPED_COMMIT_MAX_BATCH_SIZE`  | 4096  | A usize  | The maximum number of transactions in a single grouped commit batch. This prevents unbounded memory growth while still allowing large batches for efficiency. Larger batches improve throughput but increase memory usage and commit latency.  |  
###  TiKV environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#tikv-environment-variables)  
| Environment variable  | Default  | Allowed values  | Notes  |  
| --- | --- | --- | --- |  
| `SURREAL_TIKV_API_VERSION`  | 1  | A u8  | Which TiKV cluster API version to use.  |  
| `SURREAL_TIKV_ASYNC_COMMIT`  | true  | true, false  | Whether to use asynchronous transactions.  |  
| `SURREAL_TIKV_KEYSPACE`  | none  | A string  | A string specifying the keyspace identifier for data isolation.  |  
| `SURREAL_TIKV_GRPC_MAX_DECODING_MESSAGE_SIZE`  | 4,194,304 (4 MiB)  | A usize  | Sets the maximum decoding size of a gRPC message.  |  
| `SURREAL_TIKV_ONE_PHASE_COMMIT`  | true  | true, false  | Whether to use one-phase transaction commit.  |  
| `SURREAL_TIKV_REQUEST_TIMEOUT`  | 10  | A usize  | The duration in seconds for requests before they time out.  |  
###  FoundationDB environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#foundationdb-environment-variables)
Warning
FoundationDB support is deprecated in SurrealDB `3.0`. Please plan to migrate to a supported storage backend.  
| Environment variable  | Default value  | Notes  |  
| --- | --- | --- |  
| `SURREAL_FOUNDATIONDB_TRANSACTION_MAX_RETRY_DELAY`  | 500  | The maximum delay between transaction retries in milliseconds.  |  
| `SURREAL_FOUNDATIONDB_TRANSACTION_RETRY_LIMIT`  | 5  | The maximum number of times a transaction can be retried.  |  
| `SURREAL_FOUNDATIONDB_TRANSACTION_TIMEOUT`  | 5000  | The maximum transaction timeout in milliseconds.  |  
##  SurrealDB Cloud environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#surrealdb-cloud-environment-variables)
Instances on SurrealDB Cloud are not started with a CLI command or environment variables. Instead, they can be set on the [Configure Instance](https://surrealdb.com/docs/build/deployment/surrealdb-cloud/getting-started/create-an-instance#configure-an-instance) panel.
