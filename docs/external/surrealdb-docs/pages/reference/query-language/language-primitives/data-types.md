---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types

SurrealQL allows you to describe data with specific data types. These data types are used to validate data and to generate the appropriate database schema.
##  Data types[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types#data-types)  
| Type  | Description  |  
| --- | --- |  
| `any`  | Use this when you explicitly don't want to specify the field's data type. The field will allow any data type supported by SurrealDB.  |  
| [`array`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/arrays)  | An array of items.  
The array type also allows you to define which types can be stored in the array and the required length.  |  
| [`bool`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/booleans)  | A value that can be either `true` or `false`.  |  
| [[`bytes`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/bytes)](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types#bytes)  | Stores a value in a byte array.  |  
| [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes)  | An [RFC 3339](https://datatracker.ietf.org/doc/html/rfc3339) compliant data type that stores a date with time and time zone.  |  
| [`decimal`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#decimal-numbers)  | Data type for storing [decimal floating point](https://en.wikipedia.org/wiki/Decimal128_floating-point_format) numbers.  |  
| [`duration`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/durations)  | Store a value representing a length of time. Can be added or subtracted from datetimes or other durations.  |  
| [`float`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#floating-point-numbers)  | Data type for storing [floating point](https://en.wikipedia.org/wiki/Double-precision_floating-point_format) numbers. Larger or extremely precise values should be stored as a decimal.  |  
| [`geometry`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types#geometry)  |  [RFC 7946](https://www.rfc-editor.org/rfc/rfc7946)compliant data type for storing geometry in the [GeoJson format](https://geojson.org/).  |  
| [`int`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#integer-numbers)  | Store a value in a 64 bit signed integer. Values can range between `-9223372036854775808` and `9223372036854775807` (inclusive). Larger values should be stored as a float or a decimal.  |  
| [`number`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers)  | Store numbers without specifying the type.  
SurrealDB will detect the type of number and store it using the minimal number of bytes.  |  
| [`object`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/object)  | Store formatted objects containing values of any supported type including nested objects or arrays.  |  
| [`range`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges)  | A range of possible values. Lower and upper bounds can be set, in the absence of which the range becomes open-ended. A range of integers can be used in a FOR loop.  |  
| [`regex`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/regex)  | A regular expression that can be used for matching strings.  |  
| [`record`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids)  | A record ID. Table names can be added inside angle brackets to restrict to certain table names.  |  
| [`set`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/sets)  | A set of items.  
The set type also allows you to define which types can be stored in the set and the required length.  
Items are automatically deduplicated and orderd.  |  
| [`string`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/strings)  | A value composed of text or text-like characters such as emojis.  |  
###  Examples[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types#examples)
Examples of the `geometry` type:

```surql
-- Define a field with a single type
DEFINE FIELD location ON TABLE restaurant TYPE geometry<point>;
-- Define a field with any geometric type
DEFINE FIELD area ON TABLE restaurant TYPE geometry<feature>;
-- Define a field with specific geometric types
DEFINE FIELD area ON TABLE restaurant
    TYPE geometry<polygon|multipolygon|collection>;
```

Examples of the `bytes` type:

```surql
-- Define a field with a single type
DEFINE FIELD image ON TABLE product TYPE bytes;

-- Create a record with a bytes field and set the value
CREATE foo SET value = <bytes>"bar";
```

##  Type expressions[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types#type-expressions)
Type expressions are not standalone types, but expressions to indicate which types are permitted.  
| Type  | Description  |  
| --- | --- |  
| [literal](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals)  | A value that may have multiple representations or formats, similar to an enum or a union type. Can be composed of strings, numbers, objects, arrays, or durations.  |  
| `option`  | Makes types optional and guarantees the field to be either empty (NONE) or some other type. Syntactic sugar for `type_name | NONE`.  |  
###  Examples[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types#examples-1)
Example of an `option` in a schema:

```surql
DEFINE FIELD friends ON TABLE person TYPE option<array<person>>;
```

Example of a literal type:

```surql
DEFINE FIELD error_msg ON TABLE log TYPE 
    { code: 200, message: string } | 
    { code: 404, message: string };
```

As an option is syntactic sugar for `type | NONE`, an option is also simply another type of literal. This field definition is identical to the `option` example above.

```surql
DEFINE FIELD friends ON TABLE person TYPE array<person> | NONE;
```
