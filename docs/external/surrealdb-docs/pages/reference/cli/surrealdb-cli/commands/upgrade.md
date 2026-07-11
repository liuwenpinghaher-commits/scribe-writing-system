---
title: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade"
url: "https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade

Source: https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade

> !NOTE: BEFORE YOU START  
>  Make sure you’ve [installed SurrealDB](https://surrealdb.com/docs/running/installation) — it should only take a second!
##  Command options[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade#command-options)  
| Arguments  | Description  |  
| --- | --- |  
| `--nightly`  | installs the latest nightly version of SurrealDB  |  
| `--alpha`  | installs the latest alpha version of SurrealDB  |  
| `--beta`  | installs the latest beta version of SurrealDB  |  
| `--version`  | installs a specific version of SurrealDB  |  
| `--dry-run`  | Does not actually replace the currently installed version of SurrealDB.  |  
##  Example usage[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade#example-usage)
This example shows how you can use the upgrade command to upgrade to the latest version of SurrealDB.

```bash
surreal upgrade
```

##  Global install[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade#global-install)
If SurrealDB is installed globally on your system, you might need to run the upgrade command with elevated permissions, such as `sudo` on Unix-based systems or with administrator privileges in Windows.

```bash
sudo surreal upgrade
```

##  Install a specific version[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade#install-a-specific-version)
Use the `--version` flag to upgrade to a specific version of SurrealDB.

```bash
surreal upgrade --version [VERSION]

-- example
surreal upgrade --version 2.6.0
```

For a list of available versions and their release notes, see the [releases](https://surrealdb.com/releases) page.
##  Install the alpha release[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade#install-the-alpha-release)
Use the `--alpha` flag to upgrade to the latest alpha version of SurrealDB.

```bash
surreal upgrade --alpha
```

##  Install the beta release[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade#install-the-beta-release)
Use the `--beta` flag to upgrade to the latest beta version of SurrealDB.

```bash
surreal upgrade --beta
```

##  Install the nightly release[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade#install-the-nightly-release)
Use the `--nightly` flag to upgrade to the latest nightly version of SurrealDB.

```bash
surreal upgrade --nightly
```

##  Command help[](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/upgrade#command-help)
To see the help information and usage instructions, in a terminal run the `surreal upgrade --help` command without any further arguments. This command gives general information on the arguments, inputs, and additional options for the `upgrade` command.

```bash
surreal upgrade --help
```

The output of the above command:

```
Upgrade to the latest stable version

Usage: surreal upgrade [OPTIONS]

Options:
      --nightly            Install the latest nightly version
      --alpha              Install the latest alpha version
      --beta               Install the latest beta version
      --version <VERSION>  Install a specific version
      --dry-run            Don't actually replace the executable
  -h, --help               Print help

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
