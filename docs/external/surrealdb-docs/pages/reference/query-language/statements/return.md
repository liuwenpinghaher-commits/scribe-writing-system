---
title: "https://surrealdb.com/docs/reference/query-language/statements/return"
url: "https://surrealdb.com/docs/reference/query-language/statements/return"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/return

Source: https://surrealdb.com/docs/reference/query-language/statements/return

The `RETURN` statement can be used to return an implicit value or the result of a query, and to set the return value for a transaction, block, or function.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/return#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
RETURN @value
```

RETURN@value
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/return#example-usage)
###  Basic usage[](https://surrealdb.com/docs/reference/query-language/statements/return#basic-usage)
`RETURN` is always followed by a value. As every data type in SurrealDB is a type of [value](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values), the `RETURN` statement can return anything from simple values to the result of queries.

```surql
-- Return a simple value
RETURN 123;
RETURN "I am a string!";
RETURN {
	prop: "value"
};

-- Return the result of a query
RETURN SELECT * FROM person;
RETURN (CREATE person).id;
```

Values on their own are treated as if they have an implicit `RETURN` in front. As such, the following queries return the same output as in the previous example.

```surql
123;
"I am a string!";
{
	prop: "value"
};
SELECT * FROM person;
(CREATE person).id;
```

##  Transaction return value[](https://surrealdb.com/docs/reference/query-language/statements/return#transaction-return-value)
`RETURN` statements can set the result of any transaction. This includes transactions, blocks and functions.
Transaction return value

```surql
BEGIN TRANSACTION;

-- We are executing quite a few queries here
LET $firstname = "John";
LET $lastname = "Doe";

LET $person = CREATE ONLY person CONTENT {
	firstname: $firstname,
	lastname: $lastname,
};

-- But because we end with a RETURN query, only the person's ID will be returned
-- The results of the other queries will be omitted.
RETURN $person.id;

-- One issue with this approach is that query errors are generic.
-- To get around that, use a block, which is executed as a transaction by itself.

COMMIT TRANSACTION;
```

##  Return breaks execution[](https://surrealdb.com/docs/reference/query-language/statements/return#return-breaks-execution)
`RETURN` breaks execution of statements, functions and transactions.
Function return value

```surql
DEFINE FUNCTION fn::person::create($firstname: string, $lastname: string) {
	LET $person = CREATE person CONTENT {
		firstname: $firstname,
		lastname: $lastname,
	};

	-- The RETURN statement will set the return value of the custom function, and further queries will not be executed.
	RETURN $person.id;

    -- This query will never be executed
    CREATE person SET firstname = "Stephen", lastname = "Strange";
};

fn::person::create("Thanos", "Johnson");
SELECT * FROM person;
```

Functions

```surql
DEFINE FUNCTION fn::round::up($num: number) {
    IF $num % 2 == 0 {
        RETURN $num; -- Breaks execution for the function
    };

    -- This is only executed if the RETURN inside the IF statement did not break execution
    RETURN $num + 1;
};
```

Transactions

```surql
BEGIN;
RETURN 1; -- Is executed
CREATE a; -- Is not executed
RETURN 2; -- Is not executed
COMMIT;
```

Lastly, if not executed inside a transaction or function, `RETURN` will break execution until the most top-level statement it is executed in. RETURN will **not** prevent top level statements from being executed, nor will it adjust their output.
Statements

```surql
LET $id = 123;
LET $id = {
    IF $id {
        RETURN type::record('table', $id);
    };

    RETURN table:rand();
};

-- This still executes. The `RETURN` statement only broke until the block in the variable assignment.
$id;
```
