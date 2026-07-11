---
title: "https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist"
url: "https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist

Source: https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist

The [Surrealist](https://app.surrealdb.com/query) query editor provides syntax highlighting, query validation, and real-time execution. Query results are displayed in a tabular format, making it easy to analyse and visualise data.
##  Getting started[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist#getting-started)
To get started with SurrealQL in Surrealist, go to the [Surrealist Query Editor](https://app.surrealdb.com/query) and start writing your SurrealQL queries. You can use the query editor to write queries, execute them, and view the results in real-time.
###  Setting up a connection[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist#setting-up-a-connection)
Within the connection list you will find a special connection called Sandbox, which is always available and allows you to test and experiment without storing data persistently. The Sandbox is useful for learning SurrealQL, testing queries, and more. This connection is designed for simple testing and not for evaluating performance, as it is limited to a single thread within the browser's WebAssembly engine. To persist your data while still experimenting, click on **Deploy to Cloud** in Surrealist to create a free SurrealDB Cloud instance.
In order to interact with a SurrealDB database by any other means you must first create a connection. Connections store the details required to connect to a database, such as the endpoint, namespace, database, and authentication details. When you select an active connection in Surrealist, you will connect to the database and be able to interact with it using the available interface views.
After opening a connection, you can switch to another connection at any time by pressing the connection name in the top left of the interface. This will open the connection list allowing you to switch to another connection, or create a new one.
You can also create a new custom connection which will allow you to connect to a remote or local SurrealDB instance.
###  Setting a namespace and database for connections.[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist#setting-a-namespace-and-database-for-connections)
If you are using a connection (local or remote), you need to set the [namespace and database](https://surrealdb.com/docs/concepts#namespaces-and-databases) for the connection before you can start writing queries.
For example, you can set both the namespace to `main` and the database to `main`. This will set the namespace and database for the current connection.
###  Writing a query[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist#writing-a-query)
Once you have a connection open, you can use the SurrealQL query editor to create some data. For example, you can create a new record in the person table.

```surql
CREATE person SET name = "John", age = 30;
```

In the query editor, you can use syntax highlighting, code completion, and validation to help you write your queries more efficiently. To execute a query, press the run query button at the bottom of the query editor.
##  Learn more[](https://surrealdb.com/docs/learn/querying/surrealql/executing-queries/via-surrealist#learn-more)
To learn more about SurrealQL and how to write queries using Surrealist, check out the [Surrealist documentation](https://surrealdb.com/docs/explore/surrealist).
