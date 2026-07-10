---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/transactions"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/transactions

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/transactions

Each statement within SurrealDB is run within its own transaction by default. If a set of changes need to be made together, then groups of statements can be run together as a single transaction. If all of the statements within a transaction succeed, and the transaction is successful, then all of the data modifications made during the transaction are committed and become a permanent part of the database. If a transaction encounters errors and must be cancelled or rolled back, then any data modification made within the transaction is rolled back, and will not become a permanent part of the database.
##  Starting a transaction[](https://surrealdb.com/docs/reference/query-language/language-primitives/transactions#starting-a-transaction)
The `BEGIN` or `BEGIN TRANSACTION` statement starts a transaction in which multiple statements can be run together.
Starting a transaction

```surql
BEGIN [ TRANSACTION ];
```

The following query shows example usage of this statement.
Example usage of BEGIN TRANSACTION

```surql
-- Create a new account with the ID 'one' and set its initial balance to 135605.16
CREATE account:one SET balance = 135605.16;

-- Create another new account with the ID 'two' and set its initial balance to 91031.31
CREATE account:two SET balance = 91031.31;

-- Start a new database transaction. Transactions are a way to ensure multiple operations
-- either all succeed or all fail, maintaining data integrity.
BEGIN TRANSACTION;

-- Update the balance of account 'one' by adding 300.00 to the current balance.
-- This could represent a deposit or other form of credit on the balance property.
UPDATE account:one SET balance += 300.00;

-- Update the balance of account 'two' by subtracting 300.00 from the current balance.
-- This could represent a withdrawal or other form of debit on the balance property.
UPDATE account:two SET balance -= 300.00;

-- Finalise the transaction. This will apply the changes to the database. If there was an error
-- during any of the previous steps within the transaction, all changes would be rolled back and
-- the database would remain in its initial state.
COMMIT TRANSACTION;
```

##  Committing a transaction[](https://surrealdb.com/docs/reference/query-language/language-primitives/transactions#committing-a-transaction)
The [COMMIT](https://surrealdb.com/docs/reference/query-language/statements/commit) statement is used to commit a set of statements within a transaction, ensuring that all data modifications become a permanent part of the database.
Committing a transaction

```surql
COMMIT [ TRANSACTION ];
```

The following query shows example usage of this statement.
Example usage of COMMIT TRANSACTION

```surql
-- Setup accounts
CREATE account:one SET balance = 135605.16;
CREATE account:two SET balance = 91031.31;

BEGIN TRANSACTION;

-- Move money
UPDATE account:one SET balance += 300.00;
UPDATE account:two SET balance -= 300.00;

-- Finalise all changes
COMMIT TRANSACTION;
```

##  Cancelling a transaction[](https://surrealdb.com/docs/reference/query-language/language-primitives/transactions#cancelling-a-transaction)
The [CANCEL](https://surrealdb.com/docs/reference/query-language/statements/cancel) statement can be used to cancel a set of statements within a transaction, reverting or rolling back any data modification made within the transaction as a whole.
Cancelling a transaction

```surql
CANCEL [ TRANSACTION ];
```

The following query shows example usage of this statement.
Example usage of CANCEL TRANSACTION

```surql
-- Setup accounts
CREATE account:one SET balance = 135605.16;
CREATE account:two SET balance = 91031.31;

BEGIN TRANSACTION;

-- Move money
UPDATE account:one SET balance += 300.00;
UPDATE account:two SET balance -= 300.00;

-- Rollback all changes
CANCEL TRANSACTION;
```

##  THROW to conditionally cancel a transaction[](https://surrealdb.com/docs/reference/query-language/language-primitives/transactions#throw-to-conditionally-cancel-a-transaction)
While transactions are automatically rolled back if an error occurs in any of its statements, [THROW](https://surrealdb.com/docs/reference/query-language/statements/throw) can also be used to explicitly break out of a transaction at any point. `THROW` can be followed by any value which serves as the error message, usually a string.

```surql
CREATE account:one SET dollars =  100;
CREATE account:two SET dollars =  100;

LET $transfer_amount = 150;

BEGIN TRANSACTION;

UPDATE account:one SET dollars -= $transfer_amount;
UPDATE account:two SET dollars += $transfer_amount;
IF account:one.dollars < 0 {
    THROW "Insufficient funds, would have $" + <string>account:one.dollars + " after transfer"
};
COMMIT TRANSACTION;
SELECT * FROM account;
```

Output when $transfer_amount set to 150

```surql
'An error occurred: Insufficient funds, would have $-50 after transfer'
```

Output when $transfer_amount set to 50

```surql
[
	{
		dollars: 50,
		id: account:one
	},
	{
		dollars: 150,
		id: account:two
	}
]
```

##  See also[](https://surrealdb.com/docs/reference/query-language/language-primitives/transactions#see-also)
  * •
[Transactions and isolation](https://surrealdb.com/docs/transactions-and-isolation)
  * •
[Using transactions to test code for errors](https://surrealdb.com/docs/learn/querying/concepts-and-guides/testing#using-manual-transactions-for-testing)
