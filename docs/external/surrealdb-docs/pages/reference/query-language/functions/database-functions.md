---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions

Database functions are SurrealQL's built-in, namespaced helpers (`string::split()`, `math::mean()`, `time::now()`, and so on). They run inside the database engine and are the usual choice for everyday querying and data shaping.
SurrealQL also supports other kinds of callable logic:
  * •
[JavaScript functions](https://surrealdb.com/docs/reference/query-language/scripting/overview) — embedded scripts when the JavaScript runtime is enabled; see the scripting docs for definitions, context, and limits.
  * •
[SurrealML functions](https://surrealdb.com/docs/explore/ml-models) — helpers used with SurrealML.

Several function families transform values across representation boundaries (JSON, CBOR, tokens, runtime query strings). See [Representations and codecs](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs) for when to use each.
The table below lists all of SurrealDB's function modules, grouped by purpose and data type, with short examples and links to detailed documentation.  
| Function  | Description and Example  |  
| --- | --- |  
| [`API`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/api)  |  These functions can be used to add middleware to a defined API endpoint. Example: `api::timeout(1s)`  |  
| [`Array`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array)  |  These functions can be used when working with, and  
manipulating arrays of data. Example: `array::len([1,2,3])`  |  
| [`Bytes`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/bytes)  |  These functions can be used when working with bytes in  
SurrealQL. Example: `bytes::len("SurrealDB".to_bytes());`  |  
| [`Count`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/count)  |  This function can be used when counting field values and  
expressions. Example: `count([1,2,3])`  |  
| [`Crypto`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto)  |  These functions can be used when hashing data, encrypting  
data, and for securely authenticating users into the  
database. Example: `crypto::argon2::generate("MyPaSSw0RD")`  |  
| [`Duration`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration)  |  Funcions and constants for converting between numeric values  
and duration data. Example: `duration::days(90h30m)`  |  
| [`Encoding`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding)  |  Encode and decode values as JSON, CBOR, or Base64.  
Example: `encoding::cbor::encode({'foo': 'bar'})`  |  
| [`Eval`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval)  |  Evaluate a SurrealQL or ISO GQL query string at runtime inside the  
caller's transaction.  
Example: `eval::surql("RETURN 1 + 1")`  |  
| [`Files`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/file)  |  These functions can be used to work with files.  
Example: `f"my_bucket:/my_book.txt".get()`  |  
| [`Geo`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/geo)  |  These functions can be used when working with and analysing  
geospatial data. Example:{' '} `geo::distance((-0.04, 51.55), (30.46, -17.86))`  |  
| [`HTTP`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/http)  |  These functions can be used when opening and submitting  
remote web requests, and webhooks. Example: `http::get('https://surrealdb.com')`  |  
| [`Math`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math)  |  Functions and constants for  
analysing numeric data and numeric collections. Example:{' '} ` 					math::max([ 26.164, 13.746189, 23, 16.4, 41.42 ]) 				`  |  
| [`Not`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/not)  |  This function reverses the truthiness of a value. Example: `not(true)`  |  
| [`Object`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/object)  |  These functions can be used when working with, and  
manipulating data objects. Example:{' '} ` 					object::from_entries([[ "a", 1 ],[ "b", true ]]) 				`  |  
| [`Parse`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse)  |  These functions can be used when parsing email addresses and  
URL web addresses. Example:{' '} ` 					parse::url::domain("http://127.0.0.1/index.html") 				`  |  
| [`Rand`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/rand)  |  These functions can be used when generating random data  
values. Example:{' '} ` 					rand::enum('one', 'two', 3, 4.15385, 'five', true) 				`  |  
| [`Record`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record)  |  These functions can be used to retrieve specific metadata  
from a SurrealDB Record ID. Example: `record::id(person:tobie)`  |  
| [`Search`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/search)  |  These functions are used in conjunction with the{' '} `@@`operator (the 'matches' operator) to either  
collect the relevance score or highlight the searched  
keywords within the content. Example:{' '} ` 					SELECT search::score(1) AS score FROM book WHERE title 					@1@ 'rust web' 				`  |  
| [`Sequence`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sequence)  |  These functions can be used to work with a defined sequence. Example: `sequence::nextval('mySeq2')`  |  
| [`Session`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/session)  |  These functions return information about the current  
SurrealDB session. Example: `session::db()`  |  
| [`Set`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set)  |  These functions can be used when working with, and  
manipulating sets of data. Example: ``set::len({1,2,3})``  |  
| [`Sleep`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sleep)  |  This function can be used to introduce a delay or pause in  
the execution of a query or a batch of queries for a  
specific amount of time. Example: `sleep(900ms)`  |  
| [`String`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string)  |  These functions can be used when working with and  
manipulating text and string values. Example:{' '} `string::reverse('emosewa si 0.2 BDlaerruS')`  |  
| [`Time`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time)  |  Functions and constants for  
working with and manipulating datetime values. Example: `time::timezone()`  |  
| [`Type`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/type)  |  These functions can be used for generating and coercing data  
to specific data types. Example: `type::is_number(500)`  |  
| [`Value`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value)  |  This module contains several miscellaneous functions that  
can be used with values of any type. Example:{' '} `value::diff([true, false], [true, true])`  |  
| [`Vector`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/vector)  |  A collection of essential vector operations that provide  
foundational functionality for numerical computation,  
machine learning, and data analysis. Example: `vector::add([1, 2, 3], [1, 2, 3])`  |  
##  How to use database functions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions#how-to-use-database-functions)
###  Classic syntax[](https://surrealdb.com/docs/reference/query-language/functions/database-functions#classic-syntax)
Functions in SurrealDB can always be called using their full path names beginning with the package names indicated above, followed by the function arguments.

```surql
string::split("SurrealDB 3.0 is now here!", " ");
array::len([1,2,3]);
type::is_number(10);
type::record("cat", "mr_meow");
```

Response

```surql
-------- Query --------

[
	'SurrealDB',
	'3.0',
	'is',
	'now',
	'here!'
]

-------- Query --------

3

-------- Query --------

true

-------- Query --------

cat:mr_meow
```

###  Method syntax[](https://surrealdb.com/docs/reference/query-language/functions/database-functions#method-syntax)
Functions that are called on an existing value can be called using method syntax, using the `.` (dot) operator.
The following functions will produce the same output as the classic syntax above. `type::record()` cannot be called with method syntax because it is used to outright create a record ID from nothing, rather than being called on an existing value.

```surql
"SurrealDB 3.1 is now here!".split(" ");
[1,2,3].len();
10.is_number();
```

The method syntax is particularly useful when calling a number of functions inside a single query.

```surql
array::len(array::windows(array::distinct(array::flatten([[1,2,3],[1,4,6],[4,2,4]])), 2));
```

Without method chaining, a query of this type is often written across multiple nested lines:

```surql
array::len(
    array::clump(
        array::distinct(
            array::flatten([[1,2,3],[1,4,6],[4,2,4]])
        )
    , 2)
);
```

However, method chaining syntax allows queries of this type to be read from left to right in a functional manner. This is known as method chaining. As each of the methods below except the last return an array, further array methods can thus be called by using the `.` operator. The final method then returns an integer.

```surql
[[1,2,3],[1,4,6],[4,2,4],2].flatten().distinct().windows(2).len();
```

This can be made even more readable by splitting over multiple lines.

```surql
[[1,2,3],[1,4,6],[4,2,4]]
    .flatten()
    .distinct()
    .windows(2)
    .len();
```

###  Conversion from `::` (double colon) to `_` (underscore) syntax[](https://surrealdb.com/docs/reference/query-language/functions/database-functions#conversion-from--double-colon-to-_-underscore-syntax)
Available since: v3.0.0
Full function paths in SurrealDB were converted to match the method syntax detailed above.

```surql
-- Old syntax
type::is::record(person:one);
-- Method syntax
person:one.is_record();
-- New syntax now matches method syntax
type::is_record(person:one);
```

###  Built-in constants[](https://surrealdb.com/docs/reference/query-language/functions/database-functions#built-in-constants)
Some modules expose constants (fixed values) as well as functions. Consts use the same `module::name` path syntax as for functions, but omit parentheses because they access direct values instead of a function to be called.
  * •
**[Math](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#math-constants)** — numeric constants (π, e, τ, infinities, and related values).
  * •
**[Time](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#time-constants)** — `time::epoch`, `time::minimum`, and `time::maximum`.
  * •
**[Duration](https://surrealdb.com/docs/reference/query-language/functions/database-functions/duration#duration-constants)** — `duration::max`.

```surql
RETURN [math::pi, math::tau, math::e];
```

Response

```surql
[
	3.141592653589793f,
	6.283185307179586f,
	2.718281828459045f
]
```

##  Aggregate functions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions#aggregate-functions)
A few functions can be used not just on their own but with a [`GROUP BY`](https://surrealdb.com/docs/reference/query-language/clauses/group-by) clause including as part of a [pre-computed table view](https://surrealdb.com/docs/reference/query-language/statements/define/table#pre-computed-table-views).
These functions are:
  * •
[`count()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/count)
  * •
[`math::max()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmax)
  * •
[`math::min()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmin)
  * •
[`math::sum()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathsum)
  * •
[`math::mean()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmean)
  * •
[`math::stddev()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathstddev)
  * •
[`math::variance()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathvariance)
  * •
[`time::max()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemax)
  * •
[`time::min()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemin)

##  Anonymous functions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions#anonymous-functions)
SurrealDB also allows for the creation of anonymous functions (also known as closures) that do not need to be defined on the database. See [the page on closures](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) for more details.
##  Extensions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions#extensions)
You can also write your own functions in Rust that can be compiled to WASM modules, linked to, and called from the database. For more on how extensions are built and run, see [Extensions](https://surrealdb.com/docs/learn/extensions).
