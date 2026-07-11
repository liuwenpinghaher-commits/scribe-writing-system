---
title: "https://surrealdb.com/docs/reference/query-language/scripting/arguments"
url: "https://surrealdb.com/docs/reference/query-language/scripting/arguments"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/scripting/arguments

Source: https://surrealdb.com/docs/reference/query-language/scripting/arguments

Additional arguments can be passed in to the function from SurrealDB. These are accessible as an array using the `arguments` object within the JavaScript function.

```surql
-- Create a new parameter
LET $val = "SurrealDB";
-- Create a new parameter
LET $words = ["awesome", "advanced", "cool"];
-- Pass the parameter values into the function
CREATE article SET summary = function($val, $words) {
	const [val, words] = arguments;
	return `${val} is ${words.join(', ')}`;
};
```

Output

```surql
[
	{
		id: article:k59tbq3ivsdaf9nzryf5,
		summary: 'SurrealDB is awesome, advanced, cool'
	}
]
```
