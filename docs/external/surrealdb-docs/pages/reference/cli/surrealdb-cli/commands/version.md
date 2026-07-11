---
title: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/version"
url: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/version"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/version

Source: https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/version

> !NOTE: BEFORE YOU START  
>  Make sure you’ve [installed SurrealDB](https://surrealdb.com/docs/running/installation) — it should only take a second!
##  Command options[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/version#command-options)  
| Arguments  | Description  |  
| --- | --- |  
| `-e` / `--endpoint`  | Remote database server url to connect to aliases: conn  |  
##  Example usage[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/version#example-usage)
To display the current command-line tool version, along with the platform and architecture, in a terminal run the `surreal version` command without any further arguments.

```bash
surreal version
```

Sample output:

```
2.2.1 for macos on aarch64
```

If an endpoint is specified, only the version number will be displayed.

```bash
surreal version --endpoint http://localhost:8000
```

Output:

```
2.2.1
```

###  Check version with CLI flags[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/version#check-version-with-cli-flags)

```bash
surreal -V
```

```bash
surreal --version
```

Sample output:

```
SurrealDB command-line interface and server 2.2.1 for macos on aarch64
```

##  Command help[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/version#command-help)
To see the help information and usage instructions, in a terminal run the `surreal version --help` command without any further arguments. This command gives general information on the arguments, inputs, and additional options for the `version` command.

```bash
surreal version --help
```

The output of the above command:

```
Output the command-line tool and remote server version information

Usage: surreal version [OPTIONS]

Options:
  -e, --endpoint <ENDPOINT>  Remote database server url to connect to
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
