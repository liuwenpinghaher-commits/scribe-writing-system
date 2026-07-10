---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files

Available since: v3.0.0
Files are accessed by a path, which is prefixed with an `f` to differentiate it from a regular string.
Some examples of file pointers:

```surql
f"bucket:/some/key/to/a/file.txt";
f"bucket:/some/key/with\ escaped";
```

To work with the files that can be accessed through these pointers, use the following:
  * •
A [`DEFINE BUCKET`](https://surrealdb.com/docs/reference/query-language/statements/define/bucket) statement to set up the bucket to hold the files
  * •
[Files functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file) such as `file::put()` and `file::get()`

```surql
DEFINE BUCKET my_bucket BACKEND "memory";
f"my_bucket:/some_file.txt".put("Some text inside");
f"my_bucket:/some_file.txt".get();
<string>f"my_bucket:/some_file.txt".get();
```

Output

```surql
-------- Query --------

b"536F6D65207465787420696E73696465"

-------- Query --------

'Some text inside'
```

```

```
