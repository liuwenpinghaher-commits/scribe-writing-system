---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/scope"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/scope"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/scope

Source: https://surrealdb.com/docs/reference/query-language/statements/define/scope

Warning
This statement was deprecated in favour of `DEFINE ACCESS ... TYPE RECORD` in SurrealDB versions 2.x, and has been removed as of SurrealDB 3.0. Learn more in the [DEFINE ACCESS](https://surrealdb.com/docs/reference/query-language/statements/define/access).
#  `DEFINE SCOPE` statement[](https://surrealdb.com/docs/reference/query-language/statements/define/scope#define-scope-statement)
Setting scope access allows SurrealDB to operate as a web database. With scopes you can set authentication and access rules which enable fine-grained access to tables and fields.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/define/scope#requirements)
  * •
You must be authenticated as a root or namespace user before you can use the `DEFINE SCOPE` statement.
  * •
[You must select your namespace and database](https://surrealdb.com/docs/reference/query-language/statements/use) before you can use the `DEFINE SCOPE` statement.

##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/scope#statement-syntax)
SurrealQL Syntax

```syntax
DEFINE SCOPE [ OVERWRITE | IF NOT EXISTS ] @name SESSION @duration SIGNUP @expression SIGNIN @expression [ COMMENT @string ]
```

##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/define/scope#example-usage)
Below shows how you can create a scope using the `DEFINE SCOPE` statement.

```surql
-- Enable scope authentication directly in SurrealDB
DEFINE SCOPE account SESSION 24h
	SIGNUP ( CREATE user SET email = $email,
	  pass = crypto::argon2::generate($pass) )
	SIGNIN ( SELECT * FROM user WHERE email = $email
	  AND crypto::argon2::compare(pass, $pass) )
;
```

##  Using `IF NOT EXISTS` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/scope#using-if-not-exists-clause)
The `IF NOT EXISTS` clause can be used to define a scope only if it does not already exist. If the scope already exists, the `DEFINE SCOPE` statement will return an error.

```surql
-- Create a SCOPE if it does not already exist
DEFINE SCOPE IF NOT EXISTS example;
```
