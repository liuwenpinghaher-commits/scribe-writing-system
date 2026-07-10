---
title: "https://surrealdb.com/docs/reference/query-language/scripting/type-conversion"
url: "https://surrealdb.com/docs/reference/query-language/scripting/type-conversion"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/scripting/type-conversion

Source: https://surrealdb.com/docs/reference/query-language/scripting/type-conversion

Any value from SurrealDB is converted into a JavaScript type automatically, and the return value from the JavaScript function is converted to a SurrealQL value. Boolean values, Integers, Floats, Strings, Arrays, Objects, and Date objects are all converted automatically to and from SurrealQL values.

```surql
CREATE user:test SET created_at = function() {
	return new Date();
};
```

Output

```surql
[
	{
		created_at: d'2026-04-02T01:13:18.408Z',
		id: user:test
	}
]
```

In addition, a number of special classes are included within the JavaScript functions for the additional types which are not built into JavaScript. These enable the creation of [`duration`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) values, [`record`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) ids, and [`UUID`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/strings#uuid) values from within JavaScript.
Any values of these types passed into embedded scripting functions are also represented with these special classes.

```surql
CREATE user:test SET
	session_timeout = function() {
		return new Duration('1w');
	},
	best_friend = function() {
		return new Record('user', 'joanna');
	},
	identifier = function() {
		return new Uuid('03412258-988f-47cd-82db-549902cdaffe');
	}
;
```

Output

```surql
[
	{
		best_friend: user:joanna,
		id: user:test1,
		identifier: u'03412258-988f-47cd-82db-549902cdaffe',
		session_timeout: 1w
	}
]
```
