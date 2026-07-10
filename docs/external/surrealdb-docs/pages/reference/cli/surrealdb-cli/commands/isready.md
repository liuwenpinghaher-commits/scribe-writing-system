---
title: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/isready"
url: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/isready"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/isready

Source: https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/isready

> !NOTE: BEFORE YOU START  
>  Make sure you’ve [installed SurrealDB](https://surrealdb.com/docs/running/installation) — it should only take a second!
##  Command options[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/isready#command-options)  
| Arguments  | Description  |  
| --- | --- |  
| `-e` / `--endpoint` / `--conn `  | Sets the url of the database server to connect to  |  
##  Example usage[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/isready#example-usage)
To display the current command-line tool version, along with the platform and architecture, in a terminal run the surreal version command without any further arguments.

```bash
surreal isready --conn http://localhost:8000
```

The output of the command will either be a simple `OK` if ready, or some sort of error depending on the situation.

```bash
# Server is running and ready
OK

# Output if server not started yet
2026-02-10T04:12:10.274572Z ERROR surrealdb_server::cli: There was an error processing a WebSocket request: IO error: Connection refused (os error 61)
```

##  Command help[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/isready#command-help)
To see the help information and usage instructions, in a terminal run the `surreal isready --help` command without any further arguments. This command gives general information on the arguments, inputs, and additional options for the export command.

```bash
surreal isready --help
```

The output of the above command:

```
Check if the SurrealDB server is ready to accept connections

Usage: surreal is-ready [OPTIONS]

Options:
  -e, --endpoint <ENDPOINT>  Remote database server url to connect to [default: ws://localhost:8000]
  -h, --help                 Print help

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
