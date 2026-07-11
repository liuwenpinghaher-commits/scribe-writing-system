---
title: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import"
url: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import

Source: https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import

> !NOTE: BEFORE YOU START  
>  Make sure you’ve [installed SurrealDB](https://surrealdb.com/docs/running/installation) — it should only take a second!
##  Command options [](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import#command-options)  
| Arguments  | Description  |  
| --- | --- |  
| `-e` / `--endpoint`  | Sets the url of the database server to connect to. Defaults to <http://127.0.0.1>:8000 if not specified  |  
| `-u` / `--user`  | Sets master username for the database  |  
| `-p` / `--pass`  | Sets master password for the database  |  
| `-t` / `--token`  | Sets the authentication token to use when connecting to the server. Connect to SurrealDB using a JWT instead of user credentials  |  
| `--ns`  | Sets the desired namespace in which to import data  |  
| `--db`  | Sets the desired database into which to import data  |  
##  Positional argument[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import#positional-argument)  
| Arguments  | Description  |  
| --- | --- |  
| `file`  | Sets the path to the file to import  |  
##  Example usage[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import#example-usage)
To perform a SurrealQL database import from a local file, in a terminal run the `surreal import` command with the required arguments.

```bash
surreal import --endpoint http://localhost:8000 --user root --pass secret \
  --ns main --db main downloads/surreal_deal_v1.surql
```

Using token-based authentication:

```bash
surreal import --endpoint http://localhost:8000 --token <token> --ns main \
  --db main downloads/surreal_deal_v1.surql
```

Note
If you are using Surrealist, you can import files into your database by using the `Import database` button in the Explorer view. See the [Surrealist documentation](https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records) for more information.
##  Validating files before import[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import#validating-files-before-import)
A good practice before importing for the first time is to use the [`surreal validate`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/validate) command to ensure that the statements therein are valid SurrealQL. This allows you to save time by failing quickly on the command line if there is invalid SurrealQL instead of starting a full database instance that will eventually fail in the middle of the import process.
##  Using environment variables[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import#using-environment-variables)
When using the `surreal import` command, you can also use environment variables to set the values for the command-line flags. 
Important
Most of the flags mentioned in the command output above also mention a corresponding [environment variables](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#command-environment-variables). 
For example, the `--username` flag can be configured with the `SURREAL_USER` environment variable instead. 
For more on the environment variables available for CLI commands or SurrealDB instances in general, see the [environment variables](https://surrealdb.com/docs/reference/cli/surrealdb-cli/environment-variables#command-environment-variables) page.
##  OPTION IMPORT[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import#option-import)
The output of a database export includes a line that contains the keywords `OPTION IMPORT`. This command is used internally to ensure that side effects do not run when the data is imported, such as [events](https://surrealdb.com/docs/reference/query-language/statements/define/event) and [table views](https://surrealdb.com/docs/reference/query-language/statements/define/table#pre-computed-table-views).
As of SurrealDB 3.0.4, this line must be present in order to use the `/import` endpoint. If side effects when importing a `.surql` file are desired, remove the `OPTION IMPORT` line and use the [`/sql`](https://surrealdb.com/docs/reference/rest-api/http-protocol#sql) endpoint instead.
##  Importing data from other databases and sources[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import#importing-data-from-other-databases-and-sources)
To import data from other sources besides `.surql` files (such as PostgreSQL, MongoDB, CSV data, Kafka, etc.), see the [migrations](https://surrealdb.com/docs/build/migrating) section of the documentation.
##  Command help[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import#command-help)
To see the help information and usage instructions, in a terminal run the `surreal import --help` command without any further arguments. This command gives general information on the arguments, inputs, and additional options for the `import` command.

```bash
surreal import --help
```

The output of the above command:

```
Import a SurrealQL script into an existing database

Usage: surreal import [OPTIONS] --namespace <NAMESPACE> --database <DATABASE> <FILE>

Arguments:
  <FILE>  Path to the SurrealQL file to import

Options:
  -e, --endpoint <ENDPOINT>      Database endpoint to import to [default: http://localhost:8000]
  -u, --username <USERNAME>      Database authentication username to use when connecting [env: SURREAL_USER=] [aliases: --user]
  -p, --password <PASSWORD>      Database authentication password to use when connecting [env: SURREAL_PASS=] [aliases: --pass]
  -t, --token <TOKEN>            Authentication token in JWT format to use when connecting [env: SURREAL_TOKEN=]
      --auth-level <AUTH_LEVEL>  Level on which the authenticating user is defined [env: SURREAL_AUTH_LEVEL=] [default: root] [possible
                                 values: root, namespace, ns, database, db]
      --namespace <NAMESPACE>    The namespace selected for the operation [env: SURREAL_NAMESPACE=] [aliases: --ns]
      --database <DATABASE>      The database selected for the operation [env: SURREAL_DATABASE=] [aliases: --db]
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
