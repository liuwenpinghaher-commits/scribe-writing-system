---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/user"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/user"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/user

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/user

Available since: v3.0.5
The `ALTER USER` statement can be used to modify an existing defined database [user](https://surrealdb.com/docs/reference/query-language/statements/define/user).
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/user#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER USER [ IF EXISTS ] @name
  ON [ ROOT | NAMESPACE | DATABASE ]
  [ PASSWORD @pass | PASSHASH @hash ]
  [ ROLES @role, ... ]
  [ DURATION FOR TOKEN [ @duration | NONE ] ]
  [ DURATION FOR SESSION [ @duration | NONE ] ]
  [ COMMENT @string | DROP COMMENT ]
```

ALTER USERIFEXISTS@nameONROOTNAMESPACEDATABASEPASSWORD@passPASSHASH@hashROLES@role,@roleDURATIONFORTOKEN@durationNONEDURATIONFORSESSION@durationNONECOMMENT@stringDROPCOMMENT
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/alter/user#example-usage)

```surql
-- Define a user with viewer role
DEFINE USER billy ON DATABASE PASSWORD "example" ROLES VIEWER;

-- Congrats on your promotion billy,
-- be sure to use this power for good
ALTER USER billy ON DATABASE ROLES EDITOR;
```
