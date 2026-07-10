---
title: "https://surrealdb.com/docs/reference/java/api/core/transaction"
url: "https://surrealdb.com/docs/reference/java/api/core/transaction"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/core/transaction

Source: https://surrealdb.com/docs/reference/java/api/core/transaction

The `Transaction` class wraps a set of operations into an atomic unit. Changes made within a transaction are only applied when committed, and can be rolled back by cancelling. Transactions are created by calling [`.beginTransaction()`](https://surrealdb.com/docs/reference/java/api/core/surreal#begin-transaction) on a `Surreal` instance.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Methods[](https://surrealdb.com/docs/reference/java/api/core/transaction#methods)
Note
The `Transaction` class only supports `.query()` with raw SurrealQL strings. Parameterised queries via `.queryBind()` are not available inside transactions. To pass dynamic values, interpolate them directly in the SurrealQL string or use SurrealQL parameters defined earlier in the transaction.
###  `.query(sql)`[](https://surrealdb.com/docs/reference/java/api/core/transaction#query)
Executes a SurrealQL query within the transaction. The query results are not visible outside the transaction until it is committed.
Method Syntax

```java
tx.query(sql)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `sql`  | `String`  | The SurrealQL query string to execute within the transaction.  |  
**Returns:** [`Response`](https://surrealdb.com/docs/reference/java/api/core/response)
Example

```java
Transaction tx = db.beginTransaction();
Response response = tx.query("CREATE person SET name = 'Alice'");
tx.commit();
```

###  `.commit()`[](https://surrealdb.com/docs/reference/java/api/core/transaction#commit)
Commits the transaction, applying all changes made within it to the database. After committing, the transaction object should not be reused.
Method Syntax

```java
tx.commit()
```

**Returns:** `void`
Example

```java
Transaction tx = db.beginTransaction();
tx.query("CREATE person SET name = 'Alice'");
tx.query("CREATE person SET name = 'Bob'");
tx.commit();
```

###  `.cancel()`[](https://surrealdb.com/docs/reference/java/api/core/transaction#cancel)
Cancels the transaction, discarding all changes made within it. No data is written to the database. After cancelling, the transaction object should not be reused.
Method Syntax

```java
tx.cancel()
```

**Returns:** `void`
Example

```java
Transaction tx = db.beginTransaction();
tx.query("DELETE person");
tx.cancel();
```

* * *
##  Complete example[](https://surrealdb.com/docs/reference/java/api/core/transaction#complete-example)
Atomic transfer

```java
import com.surrealdb.Surreal;
import com.surrealdb.Transaction;
import com.surrealdb.signin.RootCredential;

try (Surreal db = new Surreal()) {
    db.connect("ws://localhost:8000");
    db.useNs("bank").useDb("ledger");
    db.signin(new RootCredential("root", "root"));

    Transaction tx = db.beginTransaction();
    try {
        tx.query("UPDATE accounts:alice SET balance = balance - 200");
        tx.query("UPDATE accounts:bob SET balance = balance + 200");
        tx.commit();
    } catch (Exception e) {
        tx.cancel();
        throw e;
    }
}
```

* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/core/transaction#see-also)
  * •
[Surreal](https://surrealdb.com/docs/reference/java/api/core/surreal) — Connection and method reference
  * •
[Response](https://surrealdb.com/docs/reference/java/api/core/response) — Query response reference
  * •
[Transactions](https://surrealdb.com/docs/reference/java/concepts/transactions) — Transaction concepts and patterns
  * •
[SurrealQL BEGIN](https://surrealdb.com/docs/reference/query-language/statements/begin) — Server-side transaction syntax
