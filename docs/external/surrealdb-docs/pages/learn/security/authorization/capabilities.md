---
title: "https://surrealdb.com/docs/learn/security/authorization/capabilities"
url: "https://surrealdb.com/docs/learn/security/authorization/capabilities"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/security/authorization/capabilities

Source: https://surrealdb.com/docs/learn/security/authorization/capabilities

Most powerful features — scripting, functions, network access — are disabled by default and must be explicitly enabled by an administrator per use case.
Important
Capabilities can be enabled and configured in SurrealDB Cloud. This is done by clicking on the "Configure instance" button in the SurrealDB Cloud dashboard. Learn more about capabilities in SurrealDB Cloud [in the Cloud documentation](https://surrealdb.com/docs/build/deployment/surrealdb-cloud/getting-started/create-an-instance#configure-an-instance).
When a query wants to use a capability that is not allowed, SurrealDB will reject it.
Rejected Query

```surql
http::get("https://www.surrealdb.com");

["Access to network target 'www.surrealdb.com:443' is not allowed"]
```

This rejection will also be logged in the SurrealDB server.
Rejected Query Logging

```bash
WARN surrealdb_core::ctx::context: Capabilities denied outgoing network connection attempt, target: 'www.surrealdb.com:443'
```

In production deployments, we recommend denying all capabilities by default and specifically allowing only those required.

```bash
surreal start --deny-all --allow-funcs "array, string, crypto::argon2, http::get" --allow-net api.example.com:443
```

You can learn more about best practices when using capabilities in our [Security Best Practices](https://surrealdb.com/docs/learn/security/best-practices/security-best-practices#capabilities) guide.
##  Priority[](https://surrealdb.com/docs/learn/security/authorization/capabilities#priority)
By default, all capabilities are denied unless allowed. Some few capabilities (e.g. functions) are allowed by default.
Capabilities can be configured globally (e.g. `--allow-all`, `--deny-all`), generally (e.g. `--allow-net`, `--deny-funcs`) or specifically (e.g. `--deny-net 192.168.1.1`, `--allow-funcs string::len`).  
When capabilities are configured, the more specific capabilities prevail over the less specific. At the same level of specificity, denies always prevail over allows.
###  Examples[](https://surrealdb.com/docs/learn/security/authorization/capabilities#examples)
Capabilities configured generally prevail over those defined globally:
  * •
Running with `--deny-all --allow-scripting` will deny all capabilities except for scripting.
  * •
Running with `--allow-all --deny-net` will allow all capabilities except for network.

Capabilities configured specifically prevail over those defined globally or generally:
  * •
Running with `--deny-all --allow-net example.com` will deny all capabilities except network connections to `example.com`.
  * •
Running with `--allow-all --deny-funcs http` will allow all capabilities except for calling functions of the `http` family.
  * •
Running with `--deny-funcs --allow-funcs string::len` will deny all functions except for `string::len`.
  * •
Running with `--allow-net --deny-net 10.0.0.0/8` will allow all network connections except to the `10.0.0.0/8` block.

Capabilities denied specifically prevail over those allowed specifically:
  * •
Running with `--deny-funcs crypto --allow-funcs md5` will deny all functions of the `crypto` including `crypto::md5`.
  * •
Running with `--allow-funcs crypto --deny-funcs md5` will allow all functions of the `crypto` family except for `crypto::md5`.

##  Server versus client configuration[](https://surrealdb.com/docs/learn/security/authorization/capabilities#server-versus-client-configuration)
Capability flags on [`surreal start`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) configure the **running database instance**. That is what enforces permissions when clients connect over HTTP, WebSocket, RPC, or [`surreal sql`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/sql) to a remote endpoint.
[`surreal sql`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/sql) accepts the same flags, but they apply differently:  
| How you connect  | Configure capabilities on  |  
| --- | --- |  
| Remote server (`ws://`, `http://`, …)  |  **`surreal start`**(or server env vars)  |  
| Embedded storage (`memory`, `rocksdb://…`, …)  | **`surreal sql`** |  
When using a remote server, flags on `surreal sql` do **not** enable or disable execution-time checks such as [`eval::*`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval), arbitrary-query gates, or experimental features. They can still affect **REPL line parsing** before a query is sent.
See [Capabilities and remote connections](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/sql#capabilities-and-remote-connections) for detail.
##  List[](https://surrealdb.com/docs/learn/security/authorization/capabilities#list)
List of options for allowing capabilities:  
| Option  | Description  | Default  |  
| --- | --- | --- |  
| -A, --allow-all  | Allow all capabilities except for those more specifically denied like experimental features  | False  |  
| -A, --allow-arbitrary-query  | Denies arbitrary queries to be used by user groups. Possible user groups are: 'guest', 'record', and 'system'.  | False  |  
| --allow-experimental  |  Allow the usage of one or more experimental features. Possible values are `files`, `surrealism`, and `gql`, separated by a comma. See [experimental capabilities](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start#experimental-capabilities)for which tag enables each feature.  | None  |  
| --allow-eval-query target,...  |  Allow the `eval::surql`and `eval::gql`functions for certain user groups ( `guest`, `record`, `system`). Denied for everyone by default, even under `--allow-all`. Cannot bypass `--deny-arbitrary-query`for the same subject. See [eval queries](https://surrealdb.com/docs/learn/security/authorization/capabilities#eval-queries).  | None  |  
| --allow-funcs target,...  | Allow execution of all functions except for functions that are specifically denied. Alternatively, you can provide a comma-separated list of function names to allow  | None  |  
| --allow-guests  | Allow non-authenticated users to execute queries when authentication is enabled  | False  |  
| --allow-net target,...  | Allow all outbound network access except for network targets that are specifically denied. Alternatively, you can provide a comma-separated list of network targets to allow  | None  |  
| --allow-scripting  | Allow execution of embedded scripting functions  | False  |  
List of options for denying capabilities:  
| Option  | Description  | Default  |  
| --- | --- | --- |  
| -D, --deny-all  | Deny all capabilities except for those more specifically allowed  | False  |  
| -D, --deny-arbitrary-query  | Denies arbitrary queries from being used by user groups. Possible user groups are: 'guest', 'record', and 'system'  | False  |  
| --deny-eval-query target,...  |  Deny the `eval::surql`and `eval::gql`functions for certain user groups ( `guest`, `record`, `system`). Specifically denied groups prevail over allowed groups. See [eval queries](https://surrealdb.com/docs/learn/security/authorization/capabilities#eval-queries).  | None  |  
| --deny-funcs target,...  | Deny execution of all functions except for functions that are specifically allowed. Alternatively, you can provide a comma-separated list of function names to deny  | None  |  
| --deny-guests  | Deny non-authenticated users to execute queries when authentication is enabled  | False  |  
| --deny-net target,...  | Deny all outbound network access except for network targets that are specifically allowed. Alternatively, you can provide a comma-separated list of network targets to deny  | None  |  
| --deny-scripting  | Deny execution of embedded scripting functions  | False  |  
##  Guest access[](https://surrealdb.com/docs/learn/security/authorization/capabilities#guest-access)
Guest access is used when you want to expose certain parts of a database to non-authenticated users. It's useful when you want to serve datasets publicly and still require authentication for the rest of the system.
Even when this capability is allowed, a guest user can only execute functions or data operations like SELECT, CREATE, etc, and only if the `PERMISSIONS` clause for the resource being used in the query allows it.

```surql
// Prepare tables with custom PERMISSIONS
test/test> DEFINE TABLE protected PERMISSIONS NONE;
test/test> DEFINE TABLE public PERMISSIONS FULL;

// When guest access is allowed
$ surreal start --allow-guests

test/test> CREATE public;
[{ id: public:uy0qzy31v4xox8vivrd4 }]

test/test> SELECT * FROM public;
[{ id: public:uy0qzy31v4xox8vivrd4 }]

test/test> CREATE protected;
[]

test/test> SELECT * FROM protected;
[]

// When guest access is denied
$ surreal start --deny-guests

test/test> CREATE public;
There was a problem with the database: There was a problem with the database: IAM error: Not enough permissions to perform this action

test/test> SELECT * FROM public;
There was a problem with the database: There was a problem with the database: IAM error: Not enough permissions to perform this action

test/test> CREATE protected;
There was a problem with the database: There was a problem with the database: IAM error: Not enough permissions to perform this action

test/test> SELECT * FROM protected;
There was a problem with the database: There was a problem with the database: IAM error: Not enough permissions to perform this action
```

##  Functions[](https://surrealdb.com/docs/learn/security/authorization/capabilities#functions)
SurrealDB offers [built-in functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array) to perform common operations like string manipulation, math, etc. Users can also define [their own functions](https://surrealdb.com/docs/reference/query-language/statements/define/function) with custom logic.
In certain environments, you may not want users to use specific functions (i.e. `http::*`) or execute any custom function at all. You can use the allow/deny lists to configure what functions are allowed and what functions are denied.

```bash
// Allow all functions except the http family and crypto::md5()
surreal start --allow-funcs --deny-funcs "http","crypto::md5"

// Allow certain custom functions only (all custom functions start with "fn::")
surreal start --allow-funcs "fn::shared_fn"
```

##  Network[](https://surrealdb.com/docs/learn/security/authorization/capabilities#network)
SurrealDB offers http functions that can access external network endpoints.
If you want to allow or deny access to certain network target, you can configure the network options accordingly. Here are some examples:

```surql
// Deny network access to localhost and private IPv4 ranges
$ surreal start --allow-net --deny-net "127.0.0.1","localhost","10.0.0.0/8","192.168.0.0/16","172.16.0.0/12"

// Allow access to an internal system but only to port 443
$ surreal start --allow-net internal.example.com:433

// Allow access to some private networks but not to others
$ surreal start --allow-net 10.0.0.0/16 --deny-net 10.10.0.0/24
```

SurrealDB will perform DNS lookups and prevent network access to a hostname that resolves to an IP network target defined within `--deny-net`. 
Warning
SurrealDB currently does not perform reverse DNS lookups to prevent http functions directly accessing an IP address, even when the hostname that resolves to that IP address is listed within `--deny-net`. This is an issue when SurrealDB is configured with allow network access by default e.g `--allow-net --deny-net www.google.com` or when the IP is in the allowlist, but the hostname that resolves to that IP is in the denylist e.g `--allow-net 172.217.169.14 --deny-net www.google.com`
It is **strongly recommended** that you deny by default by defining specific `--allow-net` targets and using additional layers of network security within your infrastructure.
##  Arbitrary queries[](https://surrealdb.com/docs/learn/security/authorization/capabilities#arbitrary-queries)
Available since: v2.2.0
The `--allow-arbitrary-query` and `--deny-arbitrary-query` allows database administrators to allow or deny arbitrary quering by either guest, record or system users, or a combination of those. This capability settings affects the following: [/sql endpoint](https://surrealdb.com/docs/reference/rest-api/http#sql), [/key endpoints](https://surrealdb.com/docs/reference/rest-api/http#get-table), [/graphql endpoint](https://surrealdb.com/docs/reference/rest-api/http#graphql), [/gql endpoint](https://surrealdb.com/docs/reference/rest-api/http-protocol#gql), [RPC methods](https://surrealdb.com/docs/reference/rest-api/rpc) `use`, `select`, `create`, `update`, `merge`, `patch`, `delete`, `relate`, `insert`, `insert_relation`, `query`, `gql`, and `graphql`, and the [`eval::*`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval) functions.
Endpoints that do not accept arbitrary queries such as [`/version`](https://surrealdb.com/docs/reference/rest-api/http#version) and [authentication endpoints](https://surrealdb.com/docs/reference/rest-api/http#signin) are not affected.
The `--deny-arbitrary-query` flag is often preceded with a [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api) statement to set up certain endpoints that users can use to access database resources in place of arbitrary queries.
##  Eval queries[](https://surrealdb.com/docs/learn/security/authorization/capabilities#eval-queries)
Available since: v3.2.0
The [`eval::surql`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval) and [`eval::gql`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval) functions evaluate query strings at runtime. They are controlled by **`--allow-eval-query`**and**`--deny-eval-query`**, with subject groups`guest` , `record`, and `system`.
Unlike most capabilities, **eval is denied for every subject by default** , including when you pass `--allow-all`. You must opt in explicitly:

```bash
surreal start --allow-eval-query
```

Arbitrary queries are **allowed by default** on the server, so you do not need `--allow-arbitrary-query` for eval unless you have restricted arbitrary queries (for example with `--deny-arbitrary-query` or `--deny-all`). If a subject is denied arbitrary queries — a common pattern alongside [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api) — **`eval`is denied for that subject too** , even when `--allow-eval-query` includes them. `eval` cannot bypass arbitrary-query lockdown.
Deny rules at the same specificity prevail over allow rules. A record user calling an owner-defined function that invokes `eval` is still checked as `record` — auth limiting never escalates the subject.
Configure `--allow-eval-query` on **`surreal start`**when clients connect to a remote instance. It is not required on`surreal sql` for remote connections — only for [embedded REPL sessions](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/sql#capabilities-and-remote-connections).
`eval::gql` additionally requires the **`gql`experimental capability**. See [Eval functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval) and [Representations and codecs](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs).
