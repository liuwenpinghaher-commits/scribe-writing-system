---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/field"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/field"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/field

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/field

The `ALTER FIELD` statement is used to change or entirely drop clauses of a defined field on a table.
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/field#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER FIELD [ IF EXISTS ] ON [ TABLE ] @table 
[ 
    DROP TYPE |
    DROP FLEXIBLE |
    DROP READONLY |
    DROP VALUE |
    DROP ASSERT |
    DROP DEFAULT |
    DROP COMMENT |
    DROP REFERENCE |
    FLEXIBLE |
    READONLY |
    REFERENCE |
    TYPE @type |
    VALUE @value |
    ASSERT @expression |
    DEFAULT [ ALWAYS ] @expression |
    [ PERMISSIONS [ NONE | FULL
		| FOR select @expression
		| FOR create @expression
		| FOR update @expression
		| FOR delete @expression
	] ]
    COMMENT @string |
]
```

ALTER FIELDIFEXISTSDROPTYPEFLEXIBLEREADONLYVALUEASSERTDEFAULTCOMMENTREFERENCEFLEXIBLEREADONLYREFERENCETYPE@typeVALUE@valueASSERT@expressionDEFAULTALWAYS@expressionPERMISSIONSNONEFULLWHERE@conditionCOMMENT@string
##  Examples[](https://surrealdb.com/docs/reference/query-language/statements/alter/field#examples)
As `ALTER FIELD` contains the same clauses available in a [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field) statement, be sure to see that page for more examples.
Here is one example in which the `name` field is defined for a record `user`:

```surql
DEFINE FIELD name ON user TYPE string;
```

Later on, a database-wide [parameter](https://surrealdb.com/docs/reference/query-language/statements/define/param) is defined to disallow certain user names. This can be followed up with an `ALTER FIELD` statement to add the `ASSERT` clause to it.

```surql
DEFINE PARAM $DISALLOWED_NAMES VALUE ["Lord British", "Lord Blackthorn"];
ALTER FIELD name ON user ASSERT $value NOT IN $DISALLOWED_NAMES;
CREATE user SET name = "Lord British";
```

Output

```surql
"Found 'Lord British' for field `name`, with record `user:yn4yttkg5w683q2937bq`, but field must conform to: $value NOTINSIDE $DISALLOWED_NAMES""
```

##  See also[](https://surrealdb.com/docs/reference/query-language/statements/alter/field#see-also)
  * •
[`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field)
