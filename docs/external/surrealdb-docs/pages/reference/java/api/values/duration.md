---
title: "https://surrealdb.com/docs/reference/java/api/values/duration"
url: "https://surrealdb.com/docs/reference/java/api/values/duration"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/values/duration

Source: https://surrealdb.com/docs/reference/java/api/values/duration

SurrealDB [`duration`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) values map to Java's `java.time.Duration`. The SDK handles conversion automatically when deserializing query results into [`Value`](https://surrealdb.com/docs/reference/java/api/values/value) objects or POJOs.
* * *
##  Value methods[](https://surrealdb.com/docs/reference/java/api/values/duration#value-methods)
###  `.isDuration()`[](https://surrealdb.com/docs/reference/java/api/values/duration#is-duration)
Checks if the value is a duration.
Method Syntax

```java
value.isDuration()
```

**Returns:** `boolean`
###  `.getDuration()`[](https://surrealdb.com/docs/reference/java/api/values/duration#get-duration)
Returns the duration as a `java.time.Duration`.
Method Syntax

```java
value.getDuration()
```

**Returns:** `java.time.Duration`
* * *
##  POJO mapping[](https://surrealdb.com/docs/reference/java/api/values/duration#pojo-mapping)
When using typed methods, duration fields in your POJO should be declared as `Duration`.

```java
import java.time.Duration;

public class Task {
    public RecordId id;
    public String name;
    public Duration timeout;

    public Task() {}
}

Optional<Task> task = db.select(Task.class, new RecordId("task", "build"));
Duration timeout = task.get().timeout;
```

* * *
##  Example[](https://surrealdb.com/docs/reference/java/api/values/duration#example)
Working with duration values

```java
import com.surrealdb.Surreal;
import com.surrealdb.Response;
import com.surrealdb.Value;
import com.surrealdb.signin.RootCredential;
import java.time.Duration;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    Response response = db.query("RETURN 1h30m");
    Value result = response.take(0);

    if (result.isDuration()) {
        Duration d = result.getDuration();
    }
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/values/duration#see-also)
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) — Type mapping overview
  * •
[Value](https://surrealdb.com/docs/reference/java/api/values/value) — The Value class reference
  * •
[SurrealQL durations](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes#durations-and-datetimes) — Duration types in SurrealDB
