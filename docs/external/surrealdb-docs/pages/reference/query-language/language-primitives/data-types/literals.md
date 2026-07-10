---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals

A literal is a value that may have multiple representations or formats, similar to an enum or a union type. A literal can be composed of strings, numbers, objects, arrays, or durations.
##  Examples[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals#examples)
A literal can be as simple as a declaration that a parameter must be a certain value.

```surql
LET $nine: 9 = 9;
LET $nine: 9 = 10;
```

Response

```surql
-------- Query --------

NONE

-------- Query --------

"Tried to set `$nine`, but couldn't coerce value: Expected `9` but found `10`"
```

Using `|` allows a literal to be a number of possible options.

```surql
LET $nine: 9 | "9" | "nine" = "Nein";
```

Response

```surql
"Tried to set `$nine`, but couldn't coerce value: Expected `9 | '9' | 'nine'` but found `'Nein'`"
```

A literal can contain possible types in addition to possible values.

```surql
LET $flexible_param: datetime | uuid | "N/A" = "N/A";
LET $flexible_param: datetime | uuid | "N/A" = <datetime>"2024-09-01";
```

Literals that include the option to be an array or an object can contain rich data.

```surql
LET $status: "Ok" | { err: string } = { err: "Forgot to plug it in" };
```

##  Literals in database schema[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals#literals-in-database-schema)
Literals can be defined inside a database schema by using a [DEFINE FIELD](https://surrealdb.com/docs/reference/query-language/statements/define/field) statement.

```surql
DEFINE FIELD error_info ON TABLE information TYPE
      { error: "Continue" }
    | { error: "RetryWithId", id: string }
    | { error: "Deprecated", message: string };

CREATE information SET
	error_info = { error: "Deprecated", message: "You shouldn't use this anymore" };
-- Doesn't conform to definition, will not work
CREATE information SET
	error_info = "You shouldn't use this anymore";
```

Response

```surql
-------- Query --------

[
	{
		error_info: {
			error: 'Deprecated',
			message: "You shouldn't use this anymore"
		},
		id: info:pkckjrri8q1pg12unyuo
	}
]

-------- Query --------

"Couldn't coerce value for field `error_info` of `information:qbohn4wu4l2t81wj2fb3`: Expected `{ error: 'Continue' } | { error: 'RetryWithId', id: string } | { error: 'Deprecated', message: string }` but found `\"You shouldn't use this anymore\"`"
```

##  Matching on literals[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals#matching-on-literals)
While SurrealQL does not have a `match` or `switch` operator, `IF ELSE` statements can be used to match on a literal, particularly if each possible type is an object. The following shows a similar example to the above except that each object begins with a field containing the name of the type of error.

```surql
DEFINE FIELD error_info ON TABLE information TYPE
	{ Continue:    { message: "" }} |
	{ Retry: { error: "Retrying", after: duration }} |
	{ Deprecated:  { message: string }};
```

Next, we will [define a function](https://surrealdb.com/docs/reference/query-language/statements/define/function) to handle this field and return a certain type of message depending on the error. Note the following:
  * •
The `LET` statement in the first line is simply to shorten the path to the information contained inside `error_info`
  * •
`IF ELSE` statement works here because [IF](https://surrealdb.com/docs/reference/query-language/statements/throw) involves a check for [truthiness](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness), returning `true` as long as it finds a value that is not none, empty, or zero.

```surql
DEFINE FUNCTION fn::handle_error($data: record<information>) -> string {
	LET $err = $data.error_info;
	RETURN IF $err.Continue {
		"Continue"
	}
	ELSE IF $err.Retry {
		sleep($err.Retry.after);
		"Now retrying again"
	}
	ELSE IF $err.Deprecated {
		$err.Deprecated.message
	}
};
```

With the function set up, the `info` records can be inserted and run one at a time through the function.

```surql
LET $info = INSERT INTO information [
	{ error_info: { Continue: { message: "" } }},
	{ error_info: { Retry: { error: "Retrying", after: 1s } }},
	{ error_info: { Deprecated: { message: "Thought I said you shouldn't use this anymore" } }}
];

fn::handle_error($info[0].id);
fn::handle_error($info[1].id);
fn::handle_error($info[2].id);
```

Output

```surql
-------- Query --------

'Continue'

-------- Query --------

-- After waiting 1 second
'Now retrying again'

-------- Query --------

"Thought I said you shouldn't use this anymore"
```
