---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/session"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/session"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/session

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/session

These functions return information about the current SurrealDB session.  
| Function  | Description  |  
| --- | --- |  
| [`session::ac()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionac)  | Returns the current user's access method  |  
| [`session::db()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessiondb)  | Returns the currently selected database  |  
| [`session::id()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionid)  | Returns the current user's session ID  |  
| [`session::ip()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionip)  | Returns the current user's session IP address  |  
| [`session::ns()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionns)  | Returns the currently selected namespace  |  
| [`session::origin()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionorigin)  | Returns the current user's HTTP origin  |  
| [`session::rd()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionrd)  | Returns the current user's record authentication data  |  
| [`session::token()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessiontoken)  | Returns the current user's authentication token  |  
##  `session::ac`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionac)
Note
This function was known as `session::sc` in versions of SurrealDB before 2.0. The behaviour has not changed.
The `session::ac` function returns the current user's access method.
API DEFINITION

```surql
session::ac() -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN session::ac();

"user"
```

  
  

##  `session::db`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessiondb)
The `session::db` function returns the currently selected database.
API DEFINITION

```surql
session::db() -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN session::db();

"my_db"
```

  

##  `session::id`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionid)
The `session::id` function returns the current user's session ID.
API DEFINITION

```surql
session::id() -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN session::id();

"I895rKuixHwCNIduyBIYH2M0Pga7oUmWnng5exEE4a7EB942GVElGrnRhE5scF5d"
```

  

##  `session::ip`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionip)
The `session::ip` function returns the current user's session IP address.
API DEFINITION

```surql
session::ip() -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN session::ip();

"2001:db8:3333:4444:CCCC:DDDD:EEEE:FFFF"
```

  

##  `session::ns`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionns)
The `session::ns` function returns the currently selected namespace.
API DEFINITION

```surql
session::ns() -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN session::ns();

"my_ns"
```

  

##  `session::origin`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionorigin)
The `session::origin` function returns the current user's HTTP origin.
API DEFINITION

```surql
session::origin() -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN session::origin();

"http://localhost:3000"
```

  

##  `session::rd`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessionrd)
The `session::rd` function returns the current user's record authentication.
API DEFINITION

```surql
session::rd() -> string
```

##  `session::token`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session#sessiontoken)
The `session::token` function returns the current authentication token.
API DEFINITION

```surql
session::token() -> string
```
