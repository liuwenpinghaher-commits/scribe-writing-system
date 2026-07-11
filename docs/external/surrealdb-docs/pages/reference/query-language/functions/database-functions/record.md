---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/record"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/record"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/record

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/record

These functions can be used to retrieve specific metadata from a SurrealDB Record ID.  
| Function  | Description  |  
| --- | --- |  
| [`record::exists()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordexists)  | Checks to see if a SurrealDB Record ID exists  |  
| [`record::id()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordid)  | Extracts and returns the identifier from a SurrealDB Record ID  |  
| [`record::tb()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordtb)  | Extracts and returns the table name from a SurrealDB Record ID  |  
| [`record::refs()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordrefs)  | Extracts and returns the record IDs of any records that have a record link along with a `REFERENCES` clause  |  
| [`record::is_edge()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordis_edge)  | Identifies whether the value passed in is a graph edge  |  
##  `record::exists`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordexists)
The `record::exists` function checks to see if a given record exists.
API DEFINITION

```surql
record::exists(record) -> bool
```

A simple example showing the output of this function when a record does not exist and when it does:

```surql
RETURN record::exists(r"person:tobie");
-- false

CREATE person:tobie;
RETURN record::exists(r"person:tobie");
-- true
```

A longer example of `record::exists` using method syntax:

```surql
FOR $person IN ["Haakon_VII", "Ferdinand_I", "Manuel_II", "Wilhelm_II", "George_I", "Albert_I", "Alfonso_XIII", "George_V", "Frederick_VIII"] {
    LET $record_name = type::record("person", $person.lowercase());
    IF !$record_name.exists() {
        CREATE $record_name;
    }
}
```

##  `record::id`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordid)
The `record::id` function extracts and returns the identifier from a SurrealDB Record ID.
API DEFINITION

```surql
record::id(record) -> value
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN record::id(person:tobie);

'tobie'
```

##  `record::tb`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordtb)
The `record::tb` function extracts and returns the table name from a SurrealDB Record ID.
API DEFINITION

```surql
record::tb(record) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN record::tb(person:tobie);

-- 'person'
```

  
  

##  `record::is_edge`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#recordis_edge)
Available since: v3.0.0
The `record::is_edge` function checks to see if the value passed in is a graph edge.
API DEFINITION

```surql
record::is_edge(record | string) -> bool
```

```surql
RELATE person:one->likes:first_like->person:two;

-- Both return true
record::is_edge(likes:first_like);
record::is_edge("likes:first_like");
```

##  Method chaining[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/record#method-chaining)
Method chaining allows functions to be called using the `.` dot operator on a value of a certain type instead of the full path of the function followed by the value.

```surql
-- Traditional syntax
record::id(r"person:aeon");

-- Method chaining syntax
r"person:aeon".id();
```

Response

```surql
'aeon'
```

This is particularly useful for readability when a function is called multiple times.

```surql
-- Traditional syntax
record::table(array::max([r"person:aeon", r"person:landevin"]));

-- Method chaining syntax
[r"person:aeon", r"person:landevin"].max().table();
```

Response

```surql
'person'
```
