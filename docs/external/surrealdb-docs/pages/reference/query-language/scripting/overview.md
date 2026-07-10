---
title: "https://surrealdb.com/docs/reference/query-language/scripting/overview"
url: "https://surrealdb.com/docs/reference/query-language/scripting/overview"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/scripting/overview

Source: https://surrealdb.com/docs/reference/query-language/scripting/overview

SurrealDB allows for advanced functions with complicated logic, by allowing embedded functions to be written in JavaScript. These functions support the ES2020 JavaScript specification.
##  Setup[](https://surrealdb.com/docs/reference/query-language/scripting/overview#setup)
To allow scripting functions to be used, the `--allow-scripting` flag must be passed in when using the `surreal start` command to start the database.
##  Simple function[](https://surrealdb.com/docs/reference/query-language/scripting/overview#simple-function)
Embedded JavaScript functions within SurrealDB support all functionality in the ES2020 specification including async / await functions, and generator functions. Any value from SurrealDB is converted into a JavaScript type automatically, and the return value from the JavaScript function is converted to a SurrealDB value.

```surql
CREATE person SET scores = function() {
	return [1,2,3].map(v => v * 10);
};
```

Output

```surql
[
	{
		id: person:zju99ptfepm87ylqf2h2,
		scores: [
			10,
			20,
			30
		]
	}
]
```
