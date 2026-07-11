---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep

This function can be used to introduce a delay or pause in the execution of a query or a batch of queries for a specific amount of time.  
| Function  | Description  |  
| --- | --- |  
| [`sleep()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep#sleep)  | Delays or pauses in the execution of a query or a batch of queries.  |  
##  `sleep`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep#sleep)
The `sleep` function delays or pauses the execution of a query or a set of statements.
API DEFINITION

```surql
sleep(duration) -> none
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN sleep(1s);
RETURN sleep(500ms);
```

SurrealDB also has a [SLEEP statement](https://surrealdb.com/docs/reference/query-language/statements/sleep) statement that accepts a datetime; however, the `sleep` function can be used in more dynamic ways such as the following example that simulates a 100ms delay between each record in a query.

```surql
-- Create 3 `person` records
CREATE |person:3|;

LET $now = time::now();

SELECT *, 
  sleep(100ms) AS _, 
  time::now() - $now AS elapsed
FROM person;
```

Response

```surql
[
	{
		_: NONE,
		elapsed: 101ms457µs,
		id: person:fkgvriz1kl2tcgv6yqfq
	},
	{
		_: NONE,
		elapsed: 203ms599µs,
		id: person:lgibwdgtvx4v8ck60guk
	},
	{
		_: NONE,
		elapsed: 305ms728µs,
		id: person:pr0uby896y1az2p44wtw
	}
]
```

##  SLEEP during parallel operations[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep#sleep-during-parallel-operations)
The `sleep()` function does not interfere with operations that are underway in the background, such as a [`DEFINE INDEX`](https://surrealdb.com/docs/reference/query-language/statements/define/indexes) statement using the `CONCURRENTLY` clause.

```surql
CREATE |user:50000| SET name = id.id() RETURN NONE;
DEFINE INDEX unique_name ON TABLE user FIELDS name UNIQUE CONCURRENTLY;
INFO FOR INDEX unique_name ON TABLE user;√
RETURN sleep(50ms);
INFO FOR INDEX unique_name ON TABLE user;
RETURN sleep(50ms);
INFO FOR INDEX unique_name ON TABLE user;
RETURN sleep(50ms);
INFO FOR INDEX unique_name ON TABLE user;
```

Possible output

```surql
-------- Query 1 --------
{ 
    building: {
        initial: 0,
        pending: 0,
        status: 'indexing', 
        updated: 0
    }
}

-------- Query 2 --------
{ 
    building: {
        initial: 100,
        pending: 20,
        status: 'indexing', 
        updated: 0
    }
}

-------- Query 3 --------
{ 
    building: {
        initial: 100,
        pending: 4,
        status: 'indexing', 
        updated: 16
    }
}

-------- Query 4 --------
{
    building: {
        status: 'ready'
    }
}
```

##  Use cases[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep#use-cases)
Putting a database to sleep can be useful in a small number of situations, such as:
  * •
Testing and debugging: can be used to understand how concurrent transactions interact, test how systems handle timeouts and delays, simulate behaviour in more distant regions with longer latency
  * •
Throttling: can be used to throttle the execution of operations to prevent the database from being overwhelmed by too many requests at once
  * •
Security measures: can be used to slow down the response rate of login attempts to mitigate the risk of brute force attacks
