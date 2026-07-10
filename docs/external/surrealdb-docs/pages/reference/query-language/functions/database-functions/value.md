---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/value"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/value"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/value

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/value

This module contains several miscellaneous functions that can be used with values of any type.  
| Function  | Description  |  
| --- | --- |  
| [`.chain()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#chain)  | Allows an anonymous function to be called on a value  |  
| [`value::diff()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valuediff)  | Returns the operation required for one value to equal another  |  
| [`value::expect()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valueexpect)  | Returns the current value if the closure that captures it returns a value of `true`  |  
| [`value::patch()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valuepatch)  | Applies JSON Patch operations to a value  |  
##  `.chain()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#chain)
The `.chain()` method passes a value into a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) through which an operation can be performed to return any value.
API DEFINITION

```surql
value.chain(closure) -> value;
```

The output of this function is usually based on the value passed into the closure, but can be something else entirely.

```surql
'SurrealDB'.chain(|$n| $n + ' 3.0');
-- 'SurrealDB 3.0'

'SurrealDB'.chain(|$n| "Something else");
```

The function is only called using the `.` operator (method syntax) and, as the name implies, works well within a chain of methods.

```surql
{ company: 'SurrealDB', latest_version: '3.1' }
    .chain(|$name| <string>$name)
    .replace('SurrealDB', 'SURREALDB!!!!!');
```

Response

```surql
"{ company: 'SURREALDB!!!!!', latest_version: '3.1' }"
```

For a similar function that allows using a closure on each item in an array instead of a value as a whole, see [array::map](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymap).
##  `value::diff`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valuediff)
The `value::diff` function returns an object that shows the [JSON Patch](https://jsonpatch.com/) operation(s) required for the first value to equal the second one.
API DEFINITION

```surql
value::diff(value, $other: value) -> array<object>
```

The following is an example of the `value::diff` function used to display the changes required to change one string into another. Note that the JSON Patch spec requires an array of objects, and thus an array will be returned even if only one patch is needed between two values.

```surql
RETURN 'tobie'.diff('tobias');
```

Output

```surql
[
	{
		op: 'change',
		path: '/',
		value: '@@ -1,5 +1,6 @@
 tobi
-e
+as
'
	}
]
```

An example of the output when the diff output includes more than one operation:

```surql
{ company: 'SurrealDB' }.diff({ company: 'SurrealDB!!',
  latest_version: '3.1',
  location: city:london });
```

Response

```surql
[
	{
		op: 'change',
		path: '/company',
		value: '@@ -2,8 +2,10 @@
 urrealDB
+!!
'
	},
	{
		op: 'add',
		path: '/latest_version',
		value: '2.0'
	},
	{
		op: 'add',
		path: '/location',
		value: city:london
	}
]
```

##  `value::expect`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valueexpect)
Available since: v3.1.0
The `value::expect` function returns the original value if the closure it is passed into matches a certain condition, and an error otherwise.
API DEFINITION

```surql
value.expect(closure) -> value;
value.expect(closure, $message: string) -> value;
```

This function uses the original value as the first argument. If the original closure returns `true`, the original value is returned.

```surql
{ name: "Loki" }.expect(|$obj| $obj.name = "Loki");
-- [{ name: 'Loki' }]

{ name: "Loki" }.expect(|$obj| $obj.name = "Baldr");
-- 'An error occurred: value::expect assertion failed'
```

A user-defined error string can added after the closure if more context is desired.

```surql
{ name: "Loki" }
	.expect(
		|$obj| $obj.name = "Baldr", 
		"Norse god's name should be Loki"
	);

-- "An error occurred: value::expect assertion failed with message: 'Norse god's name should be Loki'"
```

This method is most conveniently used when chaining methods to make assertions about the data before it reaches the end of the chain.

```surql
"My name is Billy1980"
    .lowercase()
    .split(' ')
    .expect(
        |$words| $words.all(|$word| $word.len() <= 8),
        "Found content greater than 8 characters")
    .join('');

-- "An error occurred: value::expect assertion failed with message: 'Found content greater than 8 characters'"
```

As closures in SurrealDB take ownership of the values of their arguments, this function clones the original value in order to return it. It is thus only recommended to use when debugging or when the assertion is a simple one.
##  `value::patch`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valuepatch)
The `value::patch` function applies an array of [JSON Patch](https://jsonpatch.com/) operations to a value. Patches produced by [`value::diff()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valuediff) round-trip correctly, including when the value is a top-level scalar (the empty path `""` refers to the root value per RFC 6901).
For `copy` and `move` operations, the `from` pointer must be a **non-empty** JSON Pointer; an empty `from` is rejected at parse time.
API DEFINITION

```surql
value::patch(value, $patch: array<object>) -> value
```

```surql
LET $company = {
    company: 'SurrealDB',
    latest_version: '1.5.4'
};

$company.patch([{
		'op': 'replace',
		'path': 'latest_version',
		'value': '3.0'
}]);
```

Response

```surql
{
	company: 'SurrealDB',
	version: '3.0'
}
```
