---
title: "https://surrealdb.com/docs/reference/query-language/statements/throw"
url: "https://surrealdb.com/docs/reference/query-language/statements/throw"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/throw

Source: https://surrealdb.com/docs/reference/query-language/statements/throw

The `THROW` statement can be used to throw an error in a place where something unexpected is happening. Execution of the query will be aborted and the error will be returned to the client. While a string is most commonly seen after a `THROW` statement, any [value](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values) at all can be used as error output.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/throw#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
THROW @error
```

THROW@error
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/throw#example-usage)
The following query shows example usage of this statement.

```surql
-- Throw an error
THROW "some error message";
```

The following query shows the `THROW` statement being used to send back a custom error to the client.

```surql
-- In this example, we throw a custom error when a user provides invalid signin details
DEFINE ACCESS user ON DATABASE TYPE RECORD
	SIGNIN {
		LET $user = (SELECT * FROM user WHERE username = $username
		  AND crypto::argon2::compare(password, $password));
		IF !$user {
			THROW "You either provided invalid credentials, or a user with the username " + <string> $username + " might not exist.";
		};

		RETURN $user;
	}
	DURATION FOR SESSION 1w
;
```

`THROW` can contain any value: arrays, objects, and so on. It can even take the value of a separate `SELECT` statement:

```surql
CREATE event:one SET time = d'2025-10-08T07:15:04.994633Z';
CREATE event:two SET time = d'2025-10-08T07:15:04.996995Z';
THROW SELECT * FROM event;
```

Response

```surql
"An error occurred: [{ id: event:one, time: d'2025-10-08T07:15:04.994633Z' }, { id: event:two, time: d'2025-10-08T07:15:04.996995Z' }]"
```

`THROW` can also be used to cancel a transaction, usually inside an `IF` statement checking a condition.

```surql
BEGIN TRANSACTION;
LET $transfer_amount = 150;
CREATE account:one SET dollars =  100;
CREATE account:two SET dollars =  100;
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
