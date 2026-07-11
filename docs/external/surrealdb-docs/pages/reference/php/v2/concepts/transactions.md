---
title: "https://surrealdb.com/docs/reference/php/v2/concepts/transactions"
url: "https://surrealdb.com/docs/reference/php/v2/concepts/transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v2/concepts/transactions

Source: https://surrealdb.com/docs/reference/php/v2/concepts/transactions

A transaction groups statements so they either all succeed or all fail. This keeps related changes consistent, for example when transferring a value between two records.
##  Transaction blocks[](https://surrealdb.com/docs/reference/php/v2/concepts/transactions#transaction-blocks)
The simplest approach wraps statements in [`BEGIN TRANSACTION`](https://surrealdb.com/docs/reference/query-language/statements/begin) and [`COMMIT TRANSACTION`](https://surrealdb.com/docs/reference/query-language/statements/commit) and runs them as a single query with `run()`. SurrealDB rolls back the whole block if any statement fails. This works over both WebSocket and HTTP.

```php
$db->run('
    BEGIN TRANSACTION;
    UPDATE account:one SET balance -= 100;
    UPDATE account:two SET balance += 100;
    COMMIT TRANSACTION;
');
```

Use [`CANCEL TRANSACTION`](https://surrealdb.com/docs/reference/query-language/statements/cancel) inside the block, or a [`THROW`](https://surrealdb.com/docs/reference/query-language/statements/throw) expression, to abort and roll back from within SurrealQL.
##  Explicit transaction handles[](https://surrealdb.com/docs/reference/php/v2/concepts/transactions#explicit-transaction-handles)
For finer control over a WebSocket connection, the [`ConnectionController`](https://surrealdb.com/docs/reference/php/v2/api/core#connectioncontroller) exposes explicit transaction handles through `connection()`. Call `begin()` to start one, then `commit()` or `cancel()` with the returned handle.

```php
$txn = $db->connection()->begin();

try {
    // ... run statements bound to $txn ...
    $db->connection()->commit($txn);
} catch (\Throwable $error) {
    $db->connection()->cancel($txn);
    throw $error;
}
```

Note
Explicit handles require the transactions feature, which depends on the WebSocket engine and a compatible server version. For most applications, a transaction block run with `run()` is simpler and works everywhere.
##  Learn more[](https://surrealdb.com/docs/reference/php/v2/concepts/transactions#learn-more)
  * •
[Surreal API reference](https://surrealdb.com/docs/reference/php/v2/api/core#connectioncontroller) for the transaction methods
  * •
[Executing queries](https://surrealdb.com/docs/reference/php/v2/concepts/executing-queries) for running statements
  * •
[BEGIN](https://surrealdb.com/docs/reference/query-language/statements/begin) and [COMMIT](https://surrealdb.com/docs/reference/query-language/statements/commit) for the SurrealQL statements
