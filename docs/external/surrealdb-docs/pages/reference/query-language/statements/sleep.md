---
title: "https://surrealdb.com/docs/reference/query-language/statements/sleep"
url: "https://surrealdb.com/docs/reference/query-language/statements/sleep"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/sleep

Source: https://surrealdb.com/docs/reference/query-language/statements/sleep

The `SLEEP` statement is used to introduce a delay or pause in the execution of a query or a batch of queries for a specific amount of time.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/sleep#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
SLEEP @duration;
```

SLEEP@duration;
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/sleep#example-usage)
The following query shows example usage of this statement.

```surql
-- Sleep one second
SLEEP 1s;
-- Sleep 100 milliseconds
SLEEP 100ms;
```

For more dynamic usage of sleep, see SurrealDB's [sleep](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep) function.
##  SLEEP during parallel operations[](https://surrealdb.com/docs/reference/query-language/statements/sleep#sleep-during-parallel-operations)
A `SLEEP` statement does not interfere with operations that are underway in the background, such as a [`DEFINE INDEX`](https://surrealdb.com/docs/reference/query-language/statements/define/indexes) statement using the `CONCURRENTLY` clause.

```surql
CREATE |user:50000| SET name = id.id() RETURN NONE;
DEFINE INDEX unique_name ON TABLE user FIELDS name UNIQUE CONCURRENTLY;
INFO FOR INDEX unique_name ON TABLE user;
SLEEP 50ms;
INFO FOR INDEX unique_name ON TABLE user;
SLEEP 50ms;
INFO FOR INDEX unique_name ON TABLE user;
SLEEP 50ms;
INFO FOR INDEX unique_name ON TABLE user;
```

Possible output

```surql
-------- Query 1 --------
{
	building: {
		count: 0,
		status: 'initial'
	}
}

-------- Query 2 --------
{
	building: {
		count: 17250,
		status: 'initial'
	}
}

-------- Query 3 --------
{
	building: {
		count: 33542,
		status: 'initial'
	}
}

-------- Query 4 --------
{
	building: {
		status: 'built'
	}
}
```

##  Use cases[](https://surrealdb.com/docs/reference/query-language/statements/sleep#use-cases)
`SLEEP` can be useful in a small number of situations, such as:
  * •
Testing and debugging: can be used to understand how concurrent transactions interact, test how systems handle timeouts and delays, simulate behaviour in more distant regions with longer latency
  * •
Throttling: can be used to throttle the execution of operations to prevent the database from being overwhelmed by too many requests at once
  * •
Security measures: can be used to slow down the response rate of login attempts to mitigate the risk of brute force attacks
