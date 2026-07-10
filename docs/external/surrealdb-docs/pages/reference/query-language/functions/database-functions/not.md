---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/not"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/not"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/not

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/not

This function can be used to reverse the truthiness of a value.  
| Function  | Description  |  
| --- | --- |  
| [`not()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/not#not)  | Reverses the truthiness of a value.  |  
##  `not`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/not#not)
The `not` function reverses the truthiness of a value. It is functionally identical to `!`, the [NOT](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#not) operator.
API DEFINITION

```surql
not(any) -> bool
```

```surql
RETURN not("I speak the truth");
-- false
```

A value is not [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness) if it is NONE, NULL, false, empty, or has a value of 0. As such, all the following return `true`.

```surql
RETURN [
    not(""),
    not(false),
    not([]),
    not({}),
    not(0)
];
```

Similarly, the function can be used twice to determine whether a value is truthy or not. As each item in the example below is truthy, calling `not()` twice will return the value `true` for each.

```surql
RETURN [
    not(not("I have value")),
    not(not(true)),
    not(not(["value!"])),
    not(not({i_have: "value"})),
    not(not(100))
];
```

Doubling the `!` operator is functionally identical to the above and is a more commonly seen pattern.

```surql
RETURN [
    !!"I have value",
    !!true,
    !!["value!"],
    !!{i_have: "value"},
    !!100
];
```
