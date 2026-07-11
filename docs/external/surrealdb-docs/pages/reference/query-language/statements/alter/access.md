---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/access"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/access"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/access

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/access

Available since: v3.0.5
The `ALTER ACCESS` statement can be used to modify an existing defined [access](https://surrealdb.com/docs/reference/query-language/statements/define/access).
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/access#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER ACCESS [ IF EXISTS ] @name
  ON [ ROOT | NAMESPACE | DATABASE ]
  [ AUTHENTICATE @expression | DROP AUTHENTICATE ]
  [ DURATION
    [ FOR GRANT [ @duration | NONE ] ]
    [ FOR TOKEN [ @duration | NONE ] ]
    [ FOR SESSION [ @duration | NONE ] ]
  ]
  [ COMMENT @string | DROP COMMENT ]
```

ALTER ACCESSIFEXISTS@nameONROOTNAMESPACEDATABASEAUTHENTICATE@expressionDROPAUTHENTICATEDURATIONFORGRANT@durationNONEFORTOKEN@durationNONEFORSESSION@durationNONECOMMENT@stringDROPCOMMENT
Note that this statement does not allow modification of the access type itself (`RECORD` / `JWT` / `BEARER`), only its duration, the `AUTHENTICATE` clause, and a `COMMENT`.
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/alter/access#example-usage)

```surql
-- Define an access
DEFINE ACCESS account ON DATABASE TYPE RECORD
	SIGNUP ( CREATE user SET email = $email,
	  pass = crypto::argon2::generate($pass) )
	SIGNIN ( SELECT * FROM user WHERE email = $email
	  AND crypto::argon2::compare(pass, $pass) )
	DURATION FOR TOKEN 15m, FOR SESSION 12h;

-- Shorten the token duration
ALTER ACCESS account ON DATABASE DURATION FOR TOKEN 1m;
```
