---
title: "https://surrealdb.com/docs/reference/java/api/values/datetime"
url: "https://surrealdb.com/docs/reference/java/api/values/datetime"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/values/datetime

Source: https://surrealdb.com/docs/reference/java/api/values/datetime

SurrealDB [`datetime`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) values map to Java's `java.time.ZonedDateTime`. The SDK handles conversion automatically when deserializing query results into [`Value`](https://surrealdb.com/docs/reference/java/api/values/value) objects or POJOs.
* * *
##  Value methods[](https://surrealdb.com/docs/reference/java/api/values/datetime#value-methods)
###  `.isDateTime()`[](https://surrealdb.com/docs/reference/java/api/values/datetime#is-datetime)
Checks if the value is a datetime.
Method Syntax

```java
value.isDateTime()
```

**Returns:** `boolean`
###  `.getDateTime()`[](https://surrealdb.com/docs/reference/java/api/values/datetime#get-datetime)
Returns the datetime as a `ZonedDateTime`.
Method Syntax

```java
value.getDateTime()
```

**Returns:** `java.time.ZonedDateTime`
* * *
##  POJO mapping[](https://surrealdb.com/docs/reference/java/api/values/datetime#pojo-mapping)
When using typed methods, datetime fields in your POJO should be declared as `ZonedDateTime` for reads unless you need a narrower type (`Instant`, `OffsetDateTime`, or `LocalDateTime`). When writing records, you can also use those types plus `java.util.Date` — see [Class converters](https://surrealdb.com/docs/reference/java/concepts/class-converters#temporal-types).

```java
import java.time.ZonedDateTime;

public class Event {
    public RecordId id;
    public String title;
    public ZonedDateTime createdAt;

    public Event() {}
}

Optional<Event> event = db.select(Event.class, new RecordId("event", "conf"));
ZonedDateTime when = event.get().createdAt;
```

* * *
##  Example[](https://surrealdb.com/docs/reference/java/api/values/datetime#example)
Working with datetime values

```java
import com.surrealdb.Surreal;
import com.surrealdb.Response;
import com.surrealdb.Value;
import com.surrealdb.signin.RootCredential;
import java.time.ZonedDateTime;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    Response response = db.query("RETURN time::now()");
    Value result = response.take(0);

    if (result.isDateTime()) {
        ZonedDateTime now = result.getDateTime();
    }
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/values/datetime#see-also)
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) — Type mapping overview
  * •
[Value](https://surrealdb.com/docs/reference/java/api/values/value) — The Value class reference
  * •
[SurrealQL datetimes](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/datetimes) — Datetime types in SurrealDB
