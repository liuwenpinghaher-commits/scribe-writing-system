---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids

UUIDs represent UUID v4 and v7 values. They can be obtained via either the:
  * •
[`rand::uuid::*` functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand#randuuidv4)
  * •
[casted from strings](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/casting#uuid)
  * •
or via [string prefixes](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/strings#uuid)

Note
SurrealDB does not eagerly convert a string into a UUID. An implicit `u` prefix or cast using `<uuid>` is required instead.

```surql
rand::uuid::v4();
rand::uuid::v7();
<uuid> "a8f30d8b-db67-47ec-8b38-ef703e05ad1b";
u"a8f30d8b-db67-47ec-8b38-ef703e05ad1b";
```
