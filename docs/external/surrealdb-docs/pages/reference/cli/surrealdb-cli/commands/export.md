---
title: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export"
url: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export

Source: https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export

> !NOTE: BEFORE YOU START  
>  Make sure you’ve [installed SurrealDB](https://surrealdb.com/docs/running/installation) — it should only take a second!
##  Syntax [](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export#syntax)
Export a database as a SurrealQL script

```bash
surreal export [OPTIONS] --namespace <NAMESPACE> --database <DATABASE> [FILE]
```

##  Command options [](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export#command-options)  
| Arguments  | Description  |  
| --- | --- |  
| `-e` / `--endpoint` / `--conn`  | Sets the url of the database server to connect to. Defaults to <http://127.0.0.1>:8000 if not specified  |  
| `-u` / `--user`  | Sets master username for the database  |  
| `-p` / `--pass`  | Sets master password for the database  |  
| `-t` / `--token`  | Sets the authentication token to use when connecting to the server. Connect to SurrealDB using a JWT instead of user credentials  |  
| `--ns`  | Sets the desired namespace in which to export data  |  
| `--db`  | Sets the desired database into which to export data  |  
##  Export options [](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export#export-options)  
| Arguments  | Description  |  
| --- | --- |  
| `--only`  | Whether only specific resources should be exported. When provided, only the resources specified will be exported.  |  
| `--users`  | Whether system users should be exported possible values: true, false.  |  
| `--accesses`  | Whether access methods (Record or JWT) should be exported possible values: true, false  |  
| `--params`  | Whether databases parameters should be exported possible values: true, false  |  
| `--functions`  | Whether functions should be exported possible values: true, false  |  
| `--analyzers`  | Whether analyzers should be exported possible values: true, false  |  
| `--tables [tables]`  | Whether tables should be exported, optionally providing a list of tables  |  
| `--versions`  | Whether SurrealKV versioned records should be exported possible values: true, false  |  
| `--records`  | Whether records should be exported possible values: true, false  |  
| `-l` / `--log`  | The logging level for the command-line tool default: info possible values: none, full, error, warn, info, debug, trace  |  
##  Positional argument[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export#positional-argument)  
| Arguments  | Description  |  
| --- | --- |  
| `file`  | Sets the path to the file which should be exported. If not provided, export data will be printed to stdout (and can thus be redirected using `>`).  |  
##  Example usage[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export#example-usage)
To perform a SurrealQL database export into a local file, in a terminal run the `surreal export` command with the required arguments.

```bash
surreal export --conn http://localhost:8000 --user root --pass secret --ns main --db main export.surql
```

Using token-based authentication:

```bash
surreal export --conn http://localhost:8000 --token <token> --ns main --db main export.surql
```

##  Using environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export#using-environment-variables)
Important
Most of the flags mentioned in the command output above also mention a corresponding [environment variables](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#command-environment-variables). 
For example, the `--username` flag can be configured with the `SURREAL_USER` environment variable instead. 
When using the `surreal export` command, you can also use environment variables to set the values for the command-line flags. 
For more on the environment variables available for CLI commands or SurrealDB instances in general, see the [environment variables](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#command-environment-variables) page.
##  OPTION IMPORT keyword[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export#option-import-keyword)
The output of a database export includes a line that contains the keywords `OPTION IMPORT`. This command is used internally to ensure that side effects do not run when the data is imported, such as [events](https://surrealdb.com/docs/reference/query-language/statements/define/event) and [table views](https://surrealdb.com/docs/reference/query-language/statements/define/table#pre-computed-table-views).
As of SurrealDB 3.0.4, imports via the [`surreal import`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import) and [`/import`](https://surrealdb.com/docs/reference/rest-api/http-protocol#import) HTTP endpoint require the automatically generated `OPTION IMPORT` line to be present in order to disable events, live queries, field processing, and result output for optimal import performance. If side effects are desired when importing data, remove the line and use the [`/sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#sql) endpoint instead.
##  Command help[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/export#command-help)
To see the help information and usage instructions, in a terminal run the `surreal export --help` command without any further arguments. This command gives general information on the arguments, inputs, and additional options for the export command.

```bash
surreal export --help
```

The output of the above command :

```
Export an existing database as a SurrealQL script

Usage: surreal export [OPTIONS] --namespace <NAMESPACE> --database <DATABASE> [FILE]

Arguments:
  [FILE]  Path to the SurrealQL file to export. Use dash - to write into stdout. [default: -]

Options:
  -e, --endpoint <ENDPOINT>      Database endpoint to export from [default: http://localhost:8000]
  -u, --username <USERNAME>      Database authentication username to use when connecting [env: SURREAL_USER=] [aliases: --user]
  -p, --password <PASSWORD>      Database authentication password to use when connecting [env: SURREAL_PASS=] [aliases: --pass]
  -t, --token <TOKEN>            Authentication token in JWT format to use when connecting [env: SURREAL_TOKEN=]
      --auth-level <AUTH_LEVEL>  Level on which the authenticating user is defined [env: SURREAL_AUTH_LEVEL=] [default: root] [possible
                                 values: root, namespace, ns, database, db]
      --namespace <NAMESPACE>    The namespace selected for the operation [env: SURREAL_NAMESPACE=] [aliases: --ns]
      --database <DATABASE>      The database selected for the operation [env: SURREAL_DATABASE=] [aliases: --db]
      --only                     Whether only specific resources should be exported
      --users [<USERS>]          Whether users should be exported [possible values: true, false]
      --accesses [<ACCESSES>]    Whether access methods should be exported [possible values: true, false]
      --params [<PARAMS>]        Whether params should be exported [possible values: true, false]
      --functions [<FUNCTIONS>]  Whether functions should be exported [possible values: true, false]
      --analyzers [<ANALYZERS>]  Whether analyzers should be exported [possible values: true, false]
      --tables [<TABLES>]        Whether tables should be exported, optionally providing a list of tables
      --versions [<VERSIONS>]    Whether versions should be exported [possible values: true, false]
      --records [<RECORDS>]      Whether records should be exported [possible values: true, false]
  -h, --help                     Print help

Logging:
  -l, --log <LOG>                              The logging level for the command-line tool [env: SURREAL_LOG=] [default: info] [possible
                                               values: none, full, error, warn, info, debug, trace]
      --log-format <LOG_FORMAT>                The format for terminal log output [env: SURREAL_LOG_FORMAT=] [default: text] [possible
                                               values: text, json]
      --log-socket <LOG_SOCKET>                Send logs to the specified host:port [env: SURREAL_LOG_SOCKET=]
      --log-file-level <LOG_FILE_LEVEL>        Override the logging level for file output [env: SURREAL_LOG_FILE_LEVEL=] [possible values:
                                               none, full, error, warn, info, debug, trace]
      --log-otel-level <LOG_OTEL_LEVEL>        Override the logging level for OpenTelemetry output [env: SURREAL_LOG_OTEL_LEVEL=] [possible
                                               values: none, full, error, warn, info, debug, trace]
      --log-socket-level <LOG_SOCKET_LEVEL>    Override the logging level for unix socket output [env: SURREAL_LOG_SOCKET_LEVEL=] [possible
                                               values: none, full, error, warn, info, debug, trace]
      --log-socket-format <LOG_SOCKET_FORMAT>  The format for socket output [env: SURREAL_LOG_SOCKET_FORMAT=] [default: text] [possible
                                               values: text, json]
      --log-file-enabled                       Whether to enable log file output [env: SURREAL_LOG_FILE_ENABLED=]
      --log-file-path <LOG_FILE_PATH>          The directory where log files will be stored [env: SURREAL_LOG_FILE_PATH=] [default: logs]
      --log-file-name <LOG_FILE_NAME>          The name of the log file [env: SURREAL_LOG_FILE_NAME=] [default: surrealdb.log]
      --log-file-format <LOG_FILE_FORMAT>      The format for log file output [env: SURREAL_LOG_FILE_FORMAT=] [default: text] [possible
                                               values: text, json]
      --log-file-rotation <LOG_FILE_ROTATION>  The log file rotation interval [env: SURREAL_LOG_FILE_ROTATION=] [default: daily] [possible
                                               values: daily, hourly, never]
```
