---
title: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml"
url: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml

Source: https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml

> !NOTE: Before you begin  
>  Make sure you’ve [installed SurrealDB](https://surrealdb.com/docs/running/installation) — it should only take a second!
#  ML command[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#ml-command)
##  ML Command help[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#ml-command-help)
To see the help information and usage instructions, in a terminal run the `surreal ml --help` command without any further arguments. This command gives general information on the arguments, inputs, and additional options for the `ml` command.

```bash
surreal ml --help
```

The output of the above command :

```
Manage SurrealML models within an existing database

Usage: surreal ml [OPTIONS] <COMMAND>

Commands:
  import  Import a SurrealML model into an existing database
  export  Export a SurrealML model from an existing database
  help    Print this message or the help of the given subcommand(s)

Options:
  -h, --help  Print help

Logging:
  -l, --log <LOG>                              The logging level for the command-line tool [env: SURREAL_LOG=] [default: info] [possible values: none, full, error, warn, info, debug, trace]
      --log-format <LOG_FORMAT>                The format for terminal log output [env: SURREAL_LOG_FORMAT=] [default: text] [possible values: text, json]
      --log-socket <LOG_SOCKET>                Send logs to the specified host:port [env: SURREAL_LOG_SOCKET=]
      --log-file-level <LOG_FILE_LEVEL>        Override the logging level for file output [env: SURREAL_LOG_FILE_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-otel-level <LOG_OTEL_LEVEL>        Override the logging level for OpenTelemetry output [env: SURREAL_LOG_OTEL_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-socket-level <LOG_SOCKET_LEVEL>    Override the logging level for unix socket output [env: SURREAL_LOG_SOCKET_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-socket-format <LOG_SOCKET_FORMAT>  The format for socket output [env: SURREAL_LOG_SOCKET_FORMAT=] [default: text] [possible values: text, json]
      --log-file-enabled                       Whether to enable log file output [env: SURREAL_LOG_FILE_ENABLED=]
      --log-file-path <LOG_FILE_PATH>          The directory where log files will be stored [env: SURREAL_LOG_FILE_PATH=] [default: logs]
      --log-file-name <LOG_FILE_NAME>          The name of the log file [env: SURREAL_LOG_FILE_NAME=] [default: surrealdb.log]
      --log-file-format <LOG_FILE_FORMAT>      The format for log file output [env: SURREAL_LOG_FILE_FORMAT=] [default: text] [possible values: text, json]
      --log-file-rotation <LOG_FILE_ROTATION>  The log file rotation interval [env: SURREAL_LOG_FILE_ROTATION=] [default: daily] [possible values: daily, hourly, never]
```

  

##  Export command[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#export-command)
The ML export command is used to export an existing machine learning model from SurrealDB.
###  Command arguments[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#command-arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `-e,--endpoint/--conn`  | Sets the url of the database server to connect to  |  
| `-u / --user`  | Sets master username for the database  |  
| `-p / --pass`  | Sets master password for the database  |  
| `-t` / `--token`  | Sets the authentication token to use when connecting to the server. Connect to SurrealDB using a JWT instead of user credentials  |  
| `--ns`  | Sets the desired namespace in which to import data  |  
| `--db`  | Sets the desired database into which to import data  |  
| `--name`  | Represents the name of the model that you want to export  |  
| `--version`  | Represents the version of the model that you want to export  |  
###  Positional argument[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#positional-argument)  
| Arguments  | Description  |  
| --- | --- |  
| `file`  | Sets the path to the file which should be exported  |  
###  Example usage[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#example-usage)
To perform a SurrealQL database import from a local file, in a terminal run the `surreal import` command with the required arguments.

```bash
surreal ml export --conn http://localhost:8000 --user root --pass secret --ns main --db main --name my-surrealml-model --version 1.0.0 my-surrealml-model.surml
```

Using token-based authentication:

```bash
surreal ml export --conn http://localhost:8000 --token <token> --ns main --db main --name my-surrealml-model --version 1.0.0 my-surrealml-model.surml
```

###  Command help[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#command-help)
To see the help information and usage instructions, in a terminal run the `surreal ml export --help` command without any further arguments. This command gives general information on the arguments, inputs, and additional options for the `ml export` command.

```bash
surreal ml export --help
```

The output of the above command :

```
Export a SurrealML model from an existing database

Usage: surreal ml export [OPTIONS] --name <NAME> --version <VERSION> --namespace <NAMESPACE> --database <DATABASE> [FILE]

Arguments:
  [FILE]  Path to the SurrealML file to export. Use dash - to write into stdout. [default: -]

Options:
      --name <NAME>              The name of the model [env: SURREAL_NAME=]
      --version <VERSION>        The version of the model [env: SURREAL_VERSION=]
  -e, --endpoint <ENDPOINT>      Remote database server url to connect to [default: ws://localhost:8000] [aliases: --conn]
  -u, --username <USERNAME>      Database authentication username to use when connecting [env: SURREAL_USER=] [aliases: --user]
  -p, --password <PASSWORD>      Database authentication password to use when connecting [env: SURREAL_PASS=] [aliases: --pass]
  -t, --token <TOKEN>            Authentication token in JWT format to use when connecting [env: SURREAL_TOKEN=]
      --auth-level <AUTH_LEVEL>  Level on which the authenticating user is defined [env: SURREAL_AUTH_LEVEL=] [default: root] [possible values: root, namespace, ns, database, db]
      --namespace <NAMESPACE>    The namespace selected for the operation [env: SURREAL_NAMESPACE=] [aliases: --ns]
      --database <DATABASE>      The database selected for the operation [env: SURREAL_DATABASE=] [aliases: --db]
  -h, --help                     Print help

Logging:
  -l, --log <LOG>                              The logging level for the command-line tool [env: SURREAL_LOG=] [default: info] [possible values: none, full, error, warn, info, debug, trace]
      --log-format <LOG_FORMAT>                The format for terminal log output [env: SURREAL_LOG_FORMAT=] [default: text] [possible values: text, json]
      --log-socket <LOG_SOCKET>                Send logs to the specified host:port [env: SURREAL_LOG_SOCKET=]
      --log-file-level <LOG_FILE_LEVEL>        Override the logging level for file output [env: SURREAL_LOG_FILE_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-otel-level <LOG_OTEL_LEVEL>        Override the logging level for OpenTelemetry output [env: SURREAL_LOG_OTEL_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-socket-level <LOG_SOCKET_LEVEL>    Override the logging level for unix socket output [env: SURREAL_LOG_SOCKET_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-socket-format <LOG_SOCKET_FORMAT>  The format for socket output [env: SURREAL_LOG_SOCKET_FORMAT=] [default: text] [possible values: text, json]
      --log-file-enabled                       Whether to enable log file output [env: SURREAL_LOG_FILE_ENABLED=]
      --log-file-path <LOG_FILE_PATH>          The directory where log files will be stored [env: SURREAL_LOG_FILE_PATH=] [default: logs]
      --log-file-name <LOG_FILE_NAME>          The name of the log file [env: SURREAL_LOG_FILE_NAME=] [default: surrealdb.log]
      --log-file-format <LOG_FILE_FORMAT>      The format for log file output [env: SURREAL_LOG_FILE_FORMAT=] [default: text] [possible values: text, json]
      --log-file-rotation <LOG_FILE_ROTATION>  The log file rotation interval [env: SURREAL_LOG_FILE_ROTATION=] [default: daily] [possible values: daily, hourly, never]
```

  

##  Import command[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#import-command)
The ML import command is used to import a new machine learning model into SurrealDB.
###  Command arguments[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#command-arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `-e, --endpoint / --conn`  | Sets the url of the database server to connect to  |  
| `-u / --user`  | Sets master username for the database  |  
| `-p / --pass`  | Sets master password for the database  |  
| `--ns`  | Sets the desired namespace in which to import data  |  
| `-t` / `--token`  | Sets the authentication token to use when connecting to the server. Connect to SurrealDB using a JWT instead of user credentials  |  
| `--db`  | Sets the desired database into which to import data  |  
###  Positional argument[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#positional-argument-1)  
| Arguments  | Description  |  
| --- | --- |  
| `file`  | Sets the path to the file which should be imported  |  
###  Example usage[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#example-usage-1)
To perform a SurrealQL database import from a local file, in a terminal run the `surreal import` command with the required arguments.

```bash
surreal ml import --conn http://localhost:8000 --user root --pass secret \
  --ns main --db main my-surrealml-model.surml
```

Using token-based authentication:

```bash
surreal import --conn http://localhost:8000 --token <token> --ns main --db main my-surrealml-model.surml
```

###  Command help[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/ml#command-help-1)
To see the help information and usage instructions, in a terminal run the `surreal ml import --help` command without any further arguments. This command gives general information on the arguments, inputs, and additional options for the `ml import` command.

```bash
surreal ml import --help
```

The output of the above command :

```
Import a SurrealML model into an existing database

Usage: surreal ml import [OPTIONS] --namespace <NAMESPACE> --database <DATABASE> <FILE>

Arguments:
  <FILE>  Path to the SurrealML file to import

Options:
  -e, --endpoint <ENDPOINT>      Remote database server url to connect to [default: ws://localhost:8000] [aliases: --conn]
  -u, --username <USERNAME>      Database authentication username to use when connecting [env: SURREAL_USER=] [aliases: --user]
  -p, --password <PASSWORD>      Database authentication password to use when connecting [env: SURREAL_PASS=] [aliases: --pass]
  -t, --token <TOKEN>            Authentication token in JWT format to use when connecting [env: SURREAL_TOKEN=]
      --auth-level <AUTH_LEVEL>  Level on which the authenticating user is defined [env: SURREAL_AUTH_LEVEL=] [default: root] [possible values: root, namespace, ns, database, db]
      --namespace <NAMESPACE>    The namespace selected for the operation [env: SURREAL_NAMESPACE=] [aliases: --ns]
      --database <DATABASE>      The database selected for the operation [env: SURREAL_DATABASE=] [aliases: --db]
  -h, --help                     Print help

Logging:
  -l, --log <LOG>                              The logging level for the command-line tool [env: SURREAL_LOG=] [default: info] [possible values: none, full, error, warn, info, debug, trace]
      --log-format <LOG_FORMAT>                The format for terminal log output [env: SURREAL_LOG_FORMAT=] [default: text] [possible values: text, json]
      --log-socket <LOG_SOCKET>                Send logs to the specified host:port [env: SURREAL_LOG_SOCKET=]
      --log-file-level <LOG_FILE_LEVEL>        Override the logging level for file output [env: SURREAL_LOG_FILE_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-otel-level <LOG_OTEL_LEVEL>        Override the logging level for OpenTelemetry output [env: SURREAL_LOG_OTEL_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-socket-level <LOG_SOCKET_LEVEL>    Override the logging level for unix socket output [env: SURREAL_LOG_SOCKET_LEVEL=] [possible values: none, full, error, warn, info, debug, trace]
      --log-socket-format <LOG_SOCKET_FORMAT>  The format for socket output [env: SURREAL_LOG_SOCKET_FORMAT=] [default: text] [possible values: text, json]
      --log-file-enabled                       Whether to enable log file output [env: SURREAL_LOG_FILE_ENABLED=]
      --log-file-path <LOG_FILE_PATH>          The directory where log files will be stored [env: SURREAL_LOG_FILE_PATH=] [default: logs]
      --log-file-name <LOG_FILE_NAME>          The name of the log file [env: SURREAL_LOG_FILE_NAME=] [default: surrealdb.log]
      --log-file-format <LOG_FILE_FORMAT>      The format for log file output [env: SURREAL_LOG_FILE_FORMAT=] [default: text] [possible values: text, json]
      --log-file-rotation <LOG_FILE_ROTATION>  The log file rotation interval [env: SURREAL_LOG_FILE_ROTATION=] [default: daily] [possible values: daily, hourly, never]
```
