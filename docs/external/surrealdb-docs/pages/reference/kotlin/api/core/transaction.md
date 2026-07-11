---
title: "https://surrealdb.com/docs/reference/kotlin/api/core/transaction"
url: "https://surrealdb.com/docs/reference/kotlin/api/core/transaction"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/api/core/transaction

Source: https://surrealdb.com/docs/reference/kotlin/api/core/transaction

`SurrealTransaction` represents an in-progress [transaction](https://surrealdb.com/docs/reference/kotlin/concepts/transactions). It is itself a queryable, so the [CRUD builders](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder) are available scoped to the transaction. Transactions are started with the extension functions on a [session](https://surrealdb.com/docs/reference/kotlin/api/core/session) and require the **WebSocket** transport.
**Source:** [surrealdb.kotlin](https://github.com/surrealdb/surrealdb.kotlin)
Import

```kotlin
import com.surrealdb.kotlin.beginTransaction
import com.surrealdb.kotlin.transaction
```

* * *
##  `session.transaction { }`[](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#transaction-block)
Runs the block against a new `SurrealTransaction`, committing it if the block returns normally and cancelling it if the block throws.
Method Syntax

```kotlin
session.transaction { /* ... */ }
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `block`  | `suspend SurrealTransaction.() -> Unit`  | The operations to run inside the transaction.  |  
**Returns:** `Unit`
Example

```kotlin
client.transaction {
    create(RecordId("person", "tx"))
        .content(buildJsonObject { put("name", "Tx") })
        .await()
}
```

##  `session.beginTransaction()`[](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#begin-transaction)
Begins a transaction explicitly and returns a `SurrealTransaction` for manual commit or cancel.
Method Syntax

```kotlin
session.beginTransaction()
```

**Returns:** `SurrealTransaction`
Example

```kotlin
val tx = client.beginTransaction()
try {
    tx.create(Table("person")).content(buildJsonObject { put("name", "Ada") }).await()
    tx.commit()
} catch (cause: Throwable) {
    tx.cancel()
    throw cause
}
```

* * *
##  Methods[](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#methods)
###  `.commit()`[](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#commit)
Commits the transaction, persisting all its operations.
Method Syntax

```kotlin
tx.commit()
```

**Returns:** `Unit`
###  `.cancel()`[](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#cancel)
Cancels the transaction, discarding all its operations.
Method Syntax

```kotlin
tx.cancel()
```

**Returns:** `Unit`
##  Properties[](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#properties)  
| Property  | Type  | Description  |  
| --- | --- | --- |  
| `txnId`  | `String`  | The transaction's identifier.  |  
##  Learn more[](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#learn-more)
  * •
[Transactions](https://surrealdb.com/docs/reference/kotlin/concepts/transactions)
  * •
[Session](https://surrealdb.com/docs/reference/kotlin/api/core/session)
  * •
[Query builders](https://surrealdb.com/docs/reference/kotlin/api/core/query-builder)
