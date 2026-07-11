---
title: "https://surrealdb.com/docs/reference/java/api/values/geometry"
url: "https://surrealdb.com/docs/reference/java/api/values/geometry"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/values/geometry

Source: https://surrealdb.com/docs/reference/java/api/values/geometry

The `Geometry` class represents [SurrealDB geometric data types](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries). It currently supports point geometry, mapping to Java's `Point2D.Double` from `java.awt.geom`.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Methods[](https://surrealdb.com/docs/reference/java/api/values/geometry#methods)
###  `.isPoint()`[](https://surrealdb.com/docs/reference/java/api/values/geometry#is-point)
Checks if the geometry value is a point.
Method Syntax

```java
geometry.isPoint()
```

**Returns:** `boolean`
###  `.getPoint()`[](https://surrealdb.com/docs/reference/java/api/values/geometry#get-point)
Returns the point coordinates as a `Point2D.Double`. The `x` coordinate represents longitude and `y` represents latitude.
Method Syntax

```java
geometry.getPoint()
```

**Returns:** `Point2D.Double` (`java.awt.geom`)
* * *
##  Example[](https://surrealdb.com/docs/reference/java/api/values/geometry#example)
Working with geometry values

```java
import com.surrealdb.Surreal;
import com.surrealdb.Response;
import com.surrealdb.Value;
import com.surrealdb.Geometry;
import com.surrealdb.signin.RootCredential;
import java.awt.geom.Point2D;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    Response response = db.query(
        "RETURN <geometry> { type: 'Point', coordinates: [10.0, 20.0] }"
    );
    Value result = response.take(0);
    Geometry geo = result.getGeometry();

    if (geo.isPoint()) {
        Point2D.Double point = geo.getPoint();
    }
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/values/geometry#see-also)
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) — Type mapping overview
  * •
[Value](https://surrealdb.com/docs/reference/java/api/values/value) — The Value class reference
  * •
[SurrealQL geometries](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/geometries) — Geometry types in SurrealDB
