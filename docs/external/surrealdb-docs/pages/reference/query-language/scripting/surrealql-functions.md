---
title: "https://surrealdb.com/docs/reference/query-language/scripting/surrealql-functions"
url: "https://surrealdb.com/docs/reference/query-language/scripting/surrealql-functions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/scripting/surrealql-functions

Source: https://surrealdb.com/docs/reference/query-language/scripting/surrealql-functions

## 
#  SurrealQL functions[](https://surrealdb.com/docs/reference/query-language/scripting/surrealql-functions#surrealql-functions)
Embedded scripting functions have access to native SurrealQL functions, allowing for complex and performant operations otherwise not possible. SurrealQL functions are published under the `surrealdb.functions` variable. Custom functions are not available within the embedded JavaScript function at the moment.

```surql
RETURN function() {
	// Using the rand::uuid::v4() function
	const uuid = surrealdb.functions.rand.uuid.v4();
};
```
