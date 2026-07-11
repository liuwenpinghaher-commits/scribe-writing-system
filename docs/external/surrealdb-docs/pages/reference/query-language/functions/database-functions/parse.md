---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse

These functions can be used when parsing email addresses and URL web addresses.  
| Function  | Description  |  
| --- | --- |  
| [`parse::email::host()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseemailhost)  | Parses and returns an email host from an email address  |  
| [`parse::email::user()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseemailuser)  | Parses and returns an email username from an email address  |  
| [`parse::url::domain()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurldomain)  | Parses and returns the domain from a URL  |  
| [`parse::url::fragment()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlfragment)  | Parses and returns the fragment from a URL  |  
| [`parse::url::host()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlhost)  | Parses and returns the hostname from a URL  |  
| [`parse::url::path()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlpath)  | Parses and returns the path from a URL  |  
| [`parse::url::port()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlport)  | Parses and returns the port number from a URL  |  
| [`parse::url::scheme()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlscheme)  | Parses and returns the scheme from a URL  |  
| [`parse::url::query()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlquery)  | Parses and returns the query string from a URL  |  
##  `parse::email::host`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseemailhost)
The `parse::email::host` function parses and returns an email host from a valid email address.
API DEFINITION

```surql
parse::email::host(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::email::host("info@surrealdb.com");

-- 'surrealdb.com'
```

  

##  `parse::email::user`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseemailuser)
The `parse::email::user` function parses and returns an email username from a valid email address.
API DEFINITION

```surql
parse::email::user(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::email::user("info@surrealdb.com");

-- "info"
```

  

##  `parse::url::domain`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurldomain)
The `parse::url::domain` function parses and returns domain from a valid URL.  
This function is similar to `parse::url::host` only that it will return `null` if the URL is an IP address.
API DEFINITION

```surql
parse::url::domain(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::url::domain("https://surrealdb.com:80/features?some=option#fragment");
RETURN parse::url::domain("http://127.0.0.1/index.html");
```

Response

```surql
"surrealdb.com"

NONE
```

  

##  `parse::url::fragment`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlfragment)
The `parse::url::fragment` function parses and returns the fragment from a valid URL.
API DEFINITION

```surql
parse::url::fragment(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::url::fragment("https://surrealdb.com:80/features?some=option#fragment");

-- 'fragment'
```

  

##  `parse::url::host`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlhost)
The `parse::url::host` function parses and returns the hostname from a valid URL.
API DEFINITION

```surql
parse::url::host(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::url::host("https://surrealdb.com:80/features?some=option#fragment");
RETURN parse::url::host("http://127.0.0.1/index.html");
```

Response

```surql
'surrealdb.com'

'127.0.0.1'
```

  

##  `parse::url::path`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlpath)
The `parse::url::path` function parses and returns the path from a valid URL.
API DEFINITION

```surql
parse::url::path(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::url::path("https://surrealdb.com:80/features?some=option#fragment");

-- '/features'
```

  

##  `parse::url::port`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlport)
The `parse::url::port` function parses and returns the port from a valid URL.
API DEFINITION

```surql
parse::url::port(string) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::url::port("https://surrealdb.com:80/features?some=option#fragment");

-- 80
```

  

##  `parse::url::scheme`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlscheme)
The `parse::url::scheme` function parses and returns the scheme from a valid URL, in lowercase, as an ASCII string without the ':' delimiter.
API DEFINITION

```surql
parse::url::scheme(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::url::scheme("https://surrealdb.com:80/features?some=option#fragment");

-- 'https'
```

  

##  `parse::url::query`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse#parseurlquery)
The `parse::url::query` function parses and returns the query from a valid URL.
API DEFINITION

```surql
parse::url::query(string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN parse::url::query("https://surrealdb.com:80/features?some=option#fragment");

-- 'some=option'
```
