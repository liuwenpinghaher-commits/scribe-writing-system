---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/access"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/access"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/access

Source: https://surrealdb.com/docs/reference/query-language/statements/define/access

Defining an access method allows SurrealDB to grant access to resources using different kinds of credentials.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/define/access#requirements)
  * •
You must be authenticated as a [system user](https://surrealdb.com/docs/learn/security/authentication/authentication#system-users) at the same level or higher than the level on which access is defined.

##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/access#statement-syntax)
SurrealQL Syntax

```syntax
DEFINE ACCESS [ OVERWRITE | IF NOT EXISTS ] @name
  ON [ ROOT | NAMESPACE | DATABASE ]
  TYPE [
    JWT [ ALGORITHM @algorithm KEY @key | URL @url ]
    | RECORD
      [ SIGNUP @expression ]
      [ SIGNIN @expression ]
      [ WITH JWT
        [ ALGORITHM @algorithm KEY @key | URL @url ]
        [ WITH ISSUER KEY @key ]
      ]
      [ WITH REFRESH ]
    | BEARER FOR [ USER | RECORD ]
  [ AUTHENTICATE @expression ]
  [ DURATION
    [ FOR GRANT @duration ]
    [ FOR TOKEN @duration ]
    [ FOR SESSION @duration ]
  ]
  [ COMMENT @string ]
```

##  JSON Web Token (JWT) access[](https://surrealdb.com/docs/reference/query-language/statements/define/access#json-web-token-jwt-access)
A JWT access method allows accessing SurrealDB with a token signed by a trusted issuer. The contents of the token will be trusted by SurrealDB as long as it has been signed with a trusted credential.
Learn more about [JWT access method in the documentation](https://surrealdb.com/docs/reference/query-language/statements/define/access/jwt).
##  Record access[](https://surrealdb.com/docs/reference/query-language/statements/define/access#record-access)
A record access method allows accessing SurrealDB as a [record user](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users). Record users allow SurrealDB to operate as a web database by offering mechanisms to define custom signin and signup logic as well as custom table and field permissions.
Learn more about [record access method in the documentation](https://surrealdb.com/docs/reference/query-language/statements/define/access/record).
##  Bearer access[](https://surrealdb.com/docs/reference/query-language/statements/define/access#bearer-access)
A bearer access method allows generating bearer grants with an associated key that can be used to access SurrealDB as a specific [system user](https://surrealdb.com/docs/learn/security/authentication/authentication#system-users) or [record user](https://surrealdb.com/docs/learn/security/authentication/authentication#record-users). Bearer grants allow other systems and software to authenticate with SurrealDB using a secure and unique credential that can be audited and revoked at any time.
Learn more about [bearer access method in the documentation](https://surrealdb.com/docs/reference/query-language/statements/define/access/bearer).
##  Duration[](https://surrealdb.com/docs/reference/query-language/statements/define/access#duration)
The duration clause specifies the duration of the token returned after successful authentication with the access method as well as the duration of the session established both using the access method and the aforementioned token. The difference between these concepts is explained in the [expiration documentation](https://surrealdb.com/docs/learn/security/authentication/authentication#expiration).

```surql
-- Create a RECORD access method for accounts
-- On successful authentication, a token expiring after 15 minutes will be returned
-- This token can be used to establish a session that will expire after 6 hours
-- The token will be automatically used to authenticate the session
DEFINE ACCESS account ON DATABASE TYPE RECORD
	SIGNUP ( CREATE user SET email = $email, pass = crypto::argon2::generate($pass) )
	SIGNIN ( SELECT * FROM user WHERE email = $email
	  AND crypto::argon2::compare(pass, $pass) )
	DURATION FOR TOKEN 15m, FOR SESSION 12h
;
```

##  With `AUTHENTICATE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/access#with-authenticate-clause)
The authenticate clause can be used to change the record identifier returned by the `SIGNIN` and `SIGNUP` clauses or replace the identifier provided in the token when authenticating `WITH JWT`, In the context of [`DEFINE ACCESS ... TYPE RECORD`](https://surrealdb.com/docs/reference/query-language/statements/define/access/record), the `AUTHENTICATE` clause is always executed across signin, signup and token authentication.
When used in a [`DEFINE ACCESS ... TYPE JWT`](https://surrealdb.com/docs/reference/query-language/statements/define/access/jwt), the `AUTHENTICATE` clause is used to validate the token claims and can be used to log or stop authentication attempts.
In both cases, the clause expects nothing to be returned and will otherwise fail with a generic error. The `THROW` statement can be called to return a custom error to the end user.
##  Using `IF NOT EXISTS` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/access#using-if-not-exists-clause)
The `IF NOT EXISTS` clause can be used to define an access method only if it does not already exist. If the access method already exists, the `DEFINE ACCESS` statement will return an error.

```surql
-- Create an ACCESS if it does not already exist
DEFINE ACCESS IF NOT EXISTS example ON NAMESPACE ...;
```

##  Using `OVERWRITE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/access#using-overwrite-clause)
The `OVERWRITE` clause can be used to define an access method and overwrite an existing one if it already exists. You should use the `OVERWRITE` clause when you want to modify an existing access method definition. If the access method already exists, the `DEFINE ACCESS` statement will overwrite the existing access method definition with the new one.

```surql
-- Create an ACCESS and overwrite if it already exists
DEFINE ACCESS OVERWRITE example ON NAMESPACE ...;
```
