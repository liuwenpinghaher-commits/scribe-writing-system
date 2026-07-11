---
title: "https://surrealdb.com/docs/reference/java/api/values/file-ref"
url: "https://surrealdb.com/docs/reference/java/api/values/file-ref"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/values/file-ref

Source: https://surrealdb.com/docs/reference/java/api/values/file-ref

The `FileRef` class represents a reference to a [file stored in SurrealDB](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files). A file reference consists of a storage bucket name and a unique file key within that bucket.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Methods[](https://surrealdb.com/docs/reference/java/api/values/file-ref#methods)
###  `.getBucket()`[](https://surrealdb.com/docs/reference/java/api/values/file-ref#get-bucket)
Returns the name of the storage bucket containing the file.
Method Syntax

```java
fileRef.getBucket()
```

**Returns:** `String`
###  `.getKey()`[](https://surrealdb.com/docs/reference/java/api/values/file-ref#get-key)
Returns the unique key identifying the file within its bucket.
Method Syntax

```java
fileRef.getKey()
```

**Returns:** `String`
* * *
##  Example[](https://surrealdb.com/docs/reference/java/api/values/file-ref#example)
Working with file references

```java
import com.surrealdb.Surreal;
import com.surrealdb.Response;
import com.surrealdb.Value;
import com.surrealdb.FileRef;
import com.surrealdb.signin.RootCredential;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    Response response = db.query("SELECT avatar FROM user:tobie");
    Value result = response.take(0);

    if (result.isFile()) {
        FileRef file = result.getFile();
        String bucket = file.getBucket();
        String key = file.getKey();
    }
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/values/file-ref#see-also)
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) — Type mapping overview
  * •
[Value](https://surrealdb.com/docs/reference/java/api/values/value) — The Value class reference
  * •
[SurrealQL files](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files) — File storage in SurrealDB
