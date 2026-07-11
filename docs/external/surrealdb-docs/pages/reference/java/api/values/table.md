---
title: "https://surrealdb.com/docs/reference/java/api/values/table"
url: "https://surrealdb.com/docs/reference/java/api/values/table"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/values/table

Source: https://surrealdb.com/docs/reference/java/api/values/table

SurrealDB table values represent table names and are returned as `String` values in the Java SDK. The [`Value`](https://surrealdb.com/docs/reference/java/api/values/value) class provides methods to check for and extract table values.
* * *
##  Value methods[](https://surrealdb.com/docs/reference/java/api/values/table#value-methods)
###  `.isTable()`[](https://surrealdb.com/docs/reference/java/api/values/table#is-table)
Checks if the value is a table name.
Method Syntax

```java
value.isTable()
```

**Returns:** `boolean`
###  `.getTable()`[](https://surrealdb.com/docs/reference/java/api/values/table#get-table)
Returns the table name as a `String`.
Method Syntax

```java
value.getTable()
```

**Returns:** `String`
* * *
##  Example[](https://surrealdb.com/docs/reference/java/api/values/table#example)
Working with table values

```java
import com.surrealdb.Surreal;
import com.surrealdb.Response;
import com.surrealdb.Value;
import com.surrealdb.signin.RootCredential;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    Response response = db.query("RETURN <table> 'person'");
    Value result = response.take(0);

    if (result.isTable()) {
        String tableName = result.getTable();
    }
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/values/table#see-also)
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) — Type mapping overview
  * •
[Value](https://surrealdb.com/docs/reference/java/api/values/value) — The Value class reference
  * •
[SurrealQL tables](https://surrealdb.com/docs/reference/query-language/statements/define/table) — Table definitions in SurrealDB
