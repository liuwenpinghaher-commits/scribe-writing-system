---
title: "https://surrealdb.com/docs/reference/query-language/statements/break"
url: "https://surrealdb.com/docs/reference/query-language/statements/break"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/break

Source: https://surrealdb.com/docs/reference/query-language/statements/break

The BREAK statement can be used to break out of a loop, such as inside one created by the [FOR statement](https://surrealdb.com/docs/reference/query-language/statements/for).
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/break#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
BREAK
```

BREAK
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/break#example-usage)
The following queries shows example usage of this statement.
Creating a person for everyone in the array where the number is less than or equal to 5:

```surql
LET $numbers = [1,2,3,4,5,6,7,8,9];

FOR $num IN $numbers {
    IF $num > 5 {
        BREAK;

    } ELSE IF $num < 5 {
        CREATE type::record(
            'person', $num
        ) CONTENT {
            name: "Person number " + <string>$num
        };
    };
};
```

Breaking out of a loop once unwanted data is encountered:

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

-- Sort the data to move the NONE values to the end
-- and break once the first NONE is reached
FOR $data IN array::sort::desc($weather) {
    IF $data IS NONE {
        BREAK;
    } ELSE {
        CREATE weather CONTENT $data;
    };
};
```
