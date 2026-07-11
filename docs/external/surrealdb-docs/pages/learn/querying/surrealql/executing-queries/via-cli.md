---
title: "https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-cli"
url: "https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-cli"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-cli

Source: https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-cli

To get started, [install the SurrealDB CLI](https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview) on your local machine.
##  Getting started[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-cli#getting-started)
After installing the SurrealDB CLI, you can start writing SurrealQL queries by running the [`surreal start`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start) command in your terminal. You can also add the `--help` flag to view the available options and commands.
To start a SurrealDB server, run the surreal start command, using the options below. This example serves the database at the default location (http://localhost:8000), with a username and password.

```bash
surreal start --user root --pass secret
```

The server is actively running, and can be left alone until you want to stop hosting the SurrealDB server.
![Terminal start](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/~/assets/img/terminal-start.png)
##  Running queries[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-cli#running-queries)
To run a SurrealQL query, open up a new terminal window and run the [`surreal sql`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/sql) command. You will now be connected to the server and able to follow up with a query. For example, to run a simple `SELECT` query, you can run the following command:
Start a SurrealDB Shell with local endpoint

```bash
surreal sql --endpoint http://localhost:8000 --ns main --db main
```

Start a SurrealDB Shell with memory endpoint

```bash
## Run query in memory
surreal sql --endpoint memory --ns main --db main
```

![Terminal SQL](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/~/assets/img/terminal-sql.png)
##  Learn more[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-cli#learn-more)
Learn more about the available commands and options in the [SurrealDB CLI documentation](https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview).
