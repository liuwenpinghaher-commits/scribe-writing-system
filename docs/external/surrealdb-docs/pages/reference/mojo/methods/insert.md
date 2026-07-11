---
title: "https://surrealdb.com/docs/reference/mojo/methods/insert"
url: "https://surrealdb.com/docs/reference/mojo/methods/insert"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/methods/insert

Source: https://surrealdb.com/docs/reference/mojo/methods/insert

Inserts one or more records into a table. This is a convenience wrapper that runs `INSERT INTO   
;`.
Method Syntax

```python
client.insert(table, data_json, session, txn)
```

###  Arguments[](https://surrealdb.com/docs/reference/mojo/methods/insert#arguments)  
| Argument  | Description  |  
| --- | --- |  
| `table`  | The table to insert into.  |  
| `data_json`  | A single record or an array of records, as a JSON string.  |  
| `session`  | An optional session id.  |  
| `txn`  | An optional transaction id.  |  
###  Example usage[](https://surrealdb.com/docs/reference/mojo/methods/insert#example-usage)

```python
var resp = client.insert("person", '[{ "name": "Alice" }, { "name": "Bob" }]')
```

###  Translated query[](https://surrealdb.com/docs/reference/mojo/methods/insert#translated-query)

```surql
INSERT INTO $table $data_json;
```

###  See also[](https://surrealdb.com/docs/reference/mojo/methods/insert#see-also)
  * •
[`insert_relation()`](https://surrealdb.com/docs/reference/mojo/methods/insert-relation)
