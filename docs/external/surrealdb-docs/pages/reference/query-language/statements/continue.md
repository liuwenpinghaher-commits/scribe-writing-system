---
title: "https://surrealdb.com/docs/reference/query-language/statements/continue"
url: "https://surrealdb.com/docs/reference/query-language/statements/continue"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/continue

Source: https://surrealdb.com/docs/reference/query-language/statements/continue

The CONTINUE statement can be used to skip an iteration of a loop, like within the [FOR statement](https://surrealdb.com/docs/reference/query-language/statements/for).
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/continue#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
CONTINUE
```

CONTINUE
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/continue#example-usage)
The following queries shows example usage of this statement.
Skipping an iteration of a loop unless a certain condition is met:

```surql
-- Set can_vote to true for every person over 18 years old.
FOR $person IN (SELECT id, age FROM person) {
	IF ($person.age < 18) {
		CONTINUE;
	};

	UPDATE $person.id SET can_vote = true;
};
```

Skipping an iteration of a loop when bad data is encountered:

```surql
-- Data retrieved from somewhere which contains many NONE values
LET $weather = [
	{
		city: 'London',
		temperature: 22.2,
		timestamp: 1722565566389
	},
	NONE,
	{
		city: 'London',
		temperature: 20.1,
		timestamp: 1722652002699
	},
    {
        city: 'Phoenix',
        temperature: 45.1,
        timestamp: 1722565642160
    },
    NONE,
    NONE,
    {
        city: 'Phoenix',
        temperature: 45.1,
        timestamp: 1722652070372
    },
];

FOR $data IN $weather {
    IF $data IS NONE {
        CONTINUE;
    };

	CREATE weather CONTENT $data;
};
```
