---
title: "https://surrealdb.com/docs/reference/java/api/core/response"
url: "https://surrealdb.com/docs/reference/java/api/core/response"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/core/response

Source: https://surrealdb.com/docs/reference/java/api/core/response

The `Response` class wraps the results returned by a SurrealQL query execution. A single query string can contain multiple statements, and the `Response` holds the result of each statement indexed by its zero-based position.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Methods[](https://surrealdb.com/docs/reference/java/api/core/response#methods)
###  `.take(index)`[](https://surrealdb.com/docs/reference/java/api/core/response#take)
Extracts the result of a specific statement from the response by its zero-based index. The untyped variant returns a raw `Value`, while the typed variant deserializes the result into the specified Java class.
Method Syntax

```java
Value take(int num)
<T> List<T> take(Class<T> type, int num)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T>`  |  The class to deserialize the result into. Omit for an untyped `Value`return.  |  
| `num`  | `int`  | The zero-based index of the statement result to extract.  |  
**Returns:** `Value` (untyped) or `List` (typed)
Example

```java
Response response = db.query("SELECT * FROM users; SELECT * FROM posts;");

Value users = response.take(0);
List<Post> posts = response.take(Post.class, 1);
```

###  `.size()`[](https://surrealdb.com/docs/reference/java/api/core/response#size)
Returns the number of statement results contained in the response.
Method Syntax

```java
response.size()
```

**Returns:** `int`
Example

```java
Response response = db.query("SELECT * FROM users; SELECT * FROM posts;");
int count = response.size();
```

* * *
##  Complete example[](https://surrealdb.com/docs/reference/java/api/core/response#complete-example)
Working with multi-statement responses

```java
import com.surrealdb.Surreal;
import com.surrealdb.Response;
import com.surrealdb.signin.RootCredential;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("surrealdb").useDb("docs");
    db.signin(new RootCredential("root", "root"));

    Response response = db.query(
        "CREATE person SET name = 'Alice'; SELECT * FROM person;"
    );

    int statementCount = response.size();

    Value created = response.take(0);
    List<Person> people = response.take(Person.class, 1);
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/core/response#see-also)
  * •
[Surreal](https://surrealdb.com/docs/reference/java/api/core/surreal), Connection and method reference
  * •
[Executing queries](https://surrealdb.com/docs/reference/java/concepts/executing-queries), Query concepts and patterns
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types), Working with the Value class
  * •
[SurrealQL](https://surrealdb.com/docs/reference/query-language), Query language reference
