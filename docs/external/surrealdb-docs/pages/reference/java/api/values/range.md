---
title: "https://surrealdb.com/docs/reference/java/api/values/range"
url: "https://surrealdb.com/docs/reference/java/api/values/range"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/values/range

Source: https://surrealdb.com/docs/reference/java/api/values/range

SurrealDB range values represent a bounded interval. In the Java SDK, ranges are accessed through [`Value`](https://surrealdb.com/docs/reference/java/api/values/value) methods that return the start and end bounds.
Note
For record ID ranges used in CRUD operations (select, update, delete), see [`RecordIdRange`](https://surrealdb.com/docs/reference/java/api/values/record-id#record-id-range).
* * *
##  Value methods[](https://surrealdb.com/docs/reference/java/api/values/range#value-methods)
###  `.isRange()`[](https://surrealdb.com/docs/reference/java/api/values/range#is-range)
Checks if the value is a range.
Method Syntax

```java
value.isRange()
```

**Returns:** `boolean`
###  `.getRangeStart()`[](https://surrealdb.com/docs/reference/java/api/values/range#get-range-start)
Returns the start bound of the range, if present.
Method Syntax

```java
value.getRangeStart()
```

**Returns:** `Optional`
###  `.getRangeEnd()`[](https://surrealdb.com/docs/reference/java/api/values/range#get-range-end)
Returns the end bound of the range, if present.
Method Syntax

```java
value.getRangeEnd()
```

**Returns:** `Optional`
* * *
##  Example[](https://surrealdb.com/docs/reference/java/api/values/range#example)
Working with range values

```java
import com.surrealdb.Surreal;
import com.surrealdb.Response;
import com.surrealdb.Value;
import com.surrealdb.signin.RootCredential;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    Response response = db.query("RETURN 1..10");
    Value result = response.take(0);

    if (result.isRange()) {
        Optional<Value> start = result.getRangeStart();
        Optional<Value> end = result.getRangeEnd();
    }
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/values/range#see-also)
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) — Type mapping overview
  * •
[Value](https://surrealdb.com/docs/reference/java/api/values/value) — The Value class reference
  * •
[RecordIdRange](https://surrealdb.com/docs/reference/java/api/values/record-id#record-id-range) — Range-based CRUD operations
