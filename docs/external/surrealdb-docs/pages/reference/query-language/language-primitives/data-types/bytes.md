---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/bytes"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/bytes"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/bytes

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/bytes

Bytes represent raw binary data. While most data in SurrealDB is stored as strings or structured values, bytes are useful when working with encoded data such as hashes, binary identifiers, or compact representations.
##  Casting from strings[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/bytes#casting-from-strings)
Bytes can be created by casting from a string, and are displayed using hexidecimal encoding.

```surql
<bytes>"I am some bytes";
```

Output

```surql
b"4920616D20736F6D65206279746573"
```

##  Conversion from other types[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/bytes#conversion-from-other-types)
Available since: v2.3.0
Conversions can be performed between bytes, strings, and arrays.

```surql
-- array<int> to bytes to string
<string><bytes>[99, 101, 108, 108, 97, 114, 32, 100, 111, 111, 114];
-- string to bytes to array<int>
<array><bytes>"Hobbits";
```

Output

```surql
-------- Query --------

'cellar door'

-------- Query --------

[72, 111, 98, 98, 105, 116, 115]
```

##  Byte strings[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/bytes#byte-strings)
Available since: v3.0.0
A string preceded by a `b` prefix can be turned into bytes as long as the string represents a hexidecimal value.

```surql
b"486F6262697473";

<string>b"486F6262697473";

<string>b"This won't work though";
```

Output

```surql
-------- Query --------

b"486F6262697473";

-------- Query --------

'Hobbits'

-------- Query --------

"There was a problem with the database: Parse error: Unexpected
  character `T` expected hexidecimal digit
 --> [1:11]
  |
1 | <string>b\"This won't work though\";
  |           ^ 
"
```
