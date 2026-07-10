---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/regex"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/regex"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/regex

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/regex

Available since: v3.0.0
A `regex` can be created by casting from a string.
The following examples all return `true`.

```surql
-- Either 'a' or 'b'
<regex> "a|b" = "a";

-- Either color or colour
<regex> "col(o|ou)r" = "colour";

-- Case-insensitive match on English color, colour, or French couleur
<regex> "((?i)col(o|ou)r|couleur)" = "COULEUR";
```

While `regex` was added as a standalone type in version 2.3.0, regex matching has always been available via the [`string::matches()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringmatches) function.

```surql
string::matches("a", "a|b");
string::matches("colour", "col(o|ou)r");
string::matches("COULEUR", "((?i)col(o|ou)r|couleur)");
```
