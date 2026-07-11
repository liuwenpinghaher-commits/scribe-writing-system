---
title: "https://surrealdb.com/docs/reference/kotlin/concepts/transactions"
url: "https://surrealdb.com/docs/reference/kotlin/concepts/transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/kotlin/concepts/transactions

Source: https://surrealdb.com/docs/reference/kotlin/concepts/transactions

[Transactions](https://surrealdb.com/docs/reference/query-language/language-primitives/transactions) group multiple operations so they either all succeed or all fail together. The Kotlin SDK exposes transactions as extension functions on a [session](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions): a block form that commits or cancels automatically, and an explicit form for manual control.
Note
Transactions require a stateful connection and are only available over the **WebSocket** transport. Check support with [`client.supports(SurrealFeature.Transactions)`](https://surrealdb.com/docs/reference/kotlin/api/core/surreal-client#supports).
##  API references[](https://surrealdb.com/docs/reference/kotlin/concepts/transactions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [`session.transaction { }`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#transaction-block)  | Runs a block, committing or cancelling automatically  |  
| [`session.beginTransaction()`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#begin-transaction)  | Begins a transaction explicitly  |  
| [`tx.commit()`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#commit)  | Commits the transaction  |  
| [`tx.cancel()`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#cancel)  | Cancels the transaction  |  
##  Block form[](https://surrealdb.com/docs/reference/kotlin/concepts/transactions#block-form)
The [`transaction { }`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#transaction-block) builder runs your block against a [`SurrealTransaction`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction), commits it if the block returns normally, and cancels it if the block throws. The transaction is itself a queryable, so all the [CRUD builders](https://surrealdb.com/docs/reference/kotlin/concepts/data-manipulation) are available scoped to it.

```kotlin
import com.surrealdb.kotlin.query.RecordId
import com.surrealdb.kotlin.transaction
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

client.transaction {
    create(RecordId("person", "tx"))
        .content(buildJsonObject { put("name", "Tx") })
        .await()

    update(RecordId("counter", "1"))
        .content(buildJsonObject { put("hits", 2) })
        .await()
}
```

##  Explicit form[](https://surrealdb.com/docs/reference/kotlin/concepts/transactions#explicit-form)
For finer control, begin a transaction with [`.beginTransaction()`](https://surrealdb.com/docs/reference/kotlin/api/core/transaction#begin-transaction) and commit or cancel it yourself.

```kotlin
import com.surrealdb.kotlin.query.Table
import com.surrealdb.kotlin.beginTransaction
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

val tx = client.beginTransaction()
try {
    tx.create(Table("person"))
        .content(buildJsonObject { put("name", "Ada") })
        .await()
    tx.commit()
} catch (cause: Throwable) {
    tx.cancel()
    throw cause
}
```

##  Learn more[](https://surrealdb.com/docs/reference/kotlin/concepts/transactions#learn-more)
  * •
[Transaction reference](https://surrealdb.com/docs/reference/kotlin/api/core/transaction) for the full API
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/kotlin/concepts/multiple-sessions) — transactions run within a session
  * •
[SurrealQL transactions](https://surrealdb.com/docs/reference/query-language/language-primitives/transactions) for transaction semantics
