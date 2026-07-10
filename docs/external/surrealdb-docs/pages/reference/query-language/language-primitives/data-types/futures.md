---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures

Note
The `future` type is only available up to SurrealDB 2.x. Since version 3.0.0, it has been replaced by [defined fields using the `COMPUTED` clause](https://surrealdb.com/docs/reference/query-language/statements/define/field#computed-fields). Most examples in this page include an equivalent `COMPUTED` clause to aid in migrating to the new implementation.
Futures are values which are only computed when the data is selected and returned to the client. Futures can be stored inside records, to enable dynamic values which are always calculated when queried.
##  Simple futures[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures#simple-futures)
Any value or expression can be used inside a future. This value will be dynamically computed on every access to the record.
Legacy future typeWith COMPUTED clause

```surql
CREATE person SET accessed_date = <future> { time::now() };
```

```surql
-- Only used inside a DEFINE FIELD statement
DEFINE FIELD accessed_date ON person COMPUTED time::now();
```

##  Futures inside schema definitions[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures#futures-inside-schema-definitions)
A future can be added to a schema definition as well.
Legacy future typeWith COMPUTED clause

```surql
DEFINE FIELD accessed_at ON TABLE user VALUE <future> { time::now() };

CREATE user:one;
SELECT * FROM ONLY user:one;
-- Sleep for one second
SLEEP 1s;
-- `accessed_at` is a different value now
SELECT * FROM ONLY user:one;
```

```surql
DEFINE FIELD accessed_at ON TABLE user COMPUTED time::now();

CREATE user:one;
SELECT * FROM ONLY user:one;
-- Sleep for one second
SLEEP 1s;
-- `accessed_at` is a different value now
SELECT * FROM ONLY user:one;
```

This differs from a `VALUE` clause which is only calculated when it is modified (created or updated), but is not recalculated during a `SELECT` query which does not modify a record.

```surql
DEFINE FIELD updated ON TABLE user VALUE time::now();

CREATE user:one;
SELECT * FROM ONLY user:one;
-- Sleep for one second
SLEEP 1s;
-- `updated` is still the same
SELECT * FROM ONLY user:one;
```

##  Futures depending on statements[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures#futures-depending-on-statements)
If the value of a future is the result of a statement, it must be wrapped in parentheses.
Legacy future typeWith COMPUTED clause

```surql
DEFINE FIELD random_movie
    ON app_screen
    VALUE <future> { 
        (SELECT * FROM ONLY movie ORDER BY RAND() LIMIT 1) 
    };
```

```surql
-- No need for parentheses
DEFINE FIELD random_movie
    ON app_screen
    COMPUTED SELECT * FROM ONLY movie ORDER BY RAND() LIMIT 1;
```

If your statement is wrapped in parentheses, you need to access the fields using the $parent variable.

```surql
DEFINE FIELD OVERWRITE followers
    ON user
    VALUE <future> { 
        (SELECT VALUE count FROM ONLY follower_count 
            WHERE user = $parent.id LIMIT 1) ?? 0
        };
```

##  Avoiding infinite recursion[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures#avoiding-infinite-recursion)
When defining a future on a field, be sure to avoid any statements that would cause infinite recursion. In the following example, the `random_friend` field is defined by a statement that uses a `SELECT` statement on all the fields of the same `person` table, one of which will also use the same `future` to compute its value.

```surql
CREATE |person:10| SET name = "Person " + <string>id.id() RETURN NONE;

DEFINE FIELD random_friend
    ON person
    VALUE <future> { 
        (SELECT * FROM ONLY person ORDER BY RAND() LIMIT 1) 
    };

CREATE person;
```

Output

```surql
'Reached excessive computation depth due to functions, subqueries, or futures'
```

A `SELECT` query that does not access the field defined by a future will avoid the infinite recursion.

```surql
CREATE |person:10| SET name = "Person " + <string>id.id() RETURN NONE;

DEFINE FIELD random_friend
    ON person
    VALUE <future> { 
        (SELECT VALUE name FROM ONLY person ORDER BY RAND() LIMIT 1) 
    };

CREATE person;
```

Output

```surql
[
	{
		id: person:4o973bouhd6xrj8l2x69,
		random_friend: 'Person imoy71qbhnsgjtczybiq'
	}
]
```
