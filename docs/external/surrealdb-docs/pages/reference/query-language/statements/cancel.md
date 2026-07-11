---
title: "https://surrealdb.com/docs/reference/query-language/statements/cancel"
url: "https://surrealdb.com/docs/reference/query-language/statements/cancel"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/cancel

Source: https://surrealdb.com/docs/reference/query-language/statements/cancel

Each statement within SurrealDB is run within its own transaction. If a set of changes need to be made together, then groups of statements can be run together as a single transaction, either succeeding as a whole, or failing without leaving any residual data modifications. While a transaction will fail if any of its statements encounters an error, the `CANCEL` statement can also be used to cancel a transaction manually.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/cancel#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
CANCEL [ TRANSACTION ];
```

CANCELTRANSACTION;
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/cancel#example-usage)
The following query shows example usage of this statement.

```surql
BEGIN TRANSACTION;

-- Setup accounts
CREATE account:one SET balance = 135605.16;
CREATE account:two SET balance = 91031.31;

-- Move money
UPDATE account:one SET balance += 300.00;
UPDATE account:two SET balance -= 300.00;

-- Rollback all changes
CANCEL TRANSACTION;
```

`CANCEL` is not used to automatically cancel a transaction based on a condition such as inside an [IF..ELSE](https://surrealdb.com/docs/reference/query-language/statements/if-else) block. Instead, a [THROW](https://surrealdb.com/docs/reference/query-language/statements/throw) statement is used. THROW can be followed by any value, usually a string containing context behind the error.

```surql
BEGIN TRANSACTION;

-- Setup accounts
CREATE account:one SET balance = 135605.16;
CREATE account:two SET balance = 200.31;

-- Move money
UPDATE account:one SET balance += 300.00;
UPDATE account:two SET balance -= 300.00;

IF account:two.balance < 0 {
    THROW "Not enough funds";
};

COMMIT TRANSACTION;
```
