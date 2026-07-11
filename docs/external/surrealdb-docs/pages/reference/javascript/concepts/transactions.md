---
title: "https://surrealdb.com/docs/reference/javascript/concepts/transactions"
url: "https://surrealdb.com/docs/reference/javascript/concepts/transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/concepts/transactions

Source: https://surrealdb.com/docs/reference/javascript/concepts/transactions

Transactions allow you to execute a group of queries atomically, meaning either all changes are applied or none are. This is essential for maintaining data consistency when performing related operations that must not be partially applied.
##  API references[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#api-references)  
| Method  | Description  |  
| --- | --- |  
| [` db.beginTransaction() `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#begintransaction)  | Starts a new transaction  |  
| [` txn.commit() `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#commit)  | Commits the transaction, applying all changes  |  
| [` txn.cancel() `](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#cancel)  | Cancels the transaction, discarding all changes  |  
##  Starting a transaction[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#starting-a-transaction)
Call `.beginTransaction()` on any [`Surreal`](https://surrealdb.com/docs/reference/javascript/api/core/surreal) or [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) instance to start a new transaction. The returned [`SurrealTransaction`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction) object provides all the same [query methods](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries) as a regular session, but every operation is executed within the transaction scope.

```ts
const txn = await db.beginTransaction();
```

##  Executing queries within a transaction[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#executing-queries-within-a-transaction)
Use the transaction object to execute queries just as you would on the `Surreal` instance. All operations are held in a pending state until you commit or cancel.

```ts
const txn = await db.beginTransaction();

await txn.create(new RecordId('users', 'alice'))
    .content({ name: 'Alice', email: 'alice@example.com' });

await txn.create(new RecordId('users', 'bob'))
    .content({ name: 'Bob', email: 'bob@example.com' });
```

##  Committing changes[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#committing-changes)
Call `.commit()` to apply all pending changes to the database. After committing, the transaction cannot be used again.

```ts
await txn.commit();
```

##  Cancelling and rolling back[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#cancelling-and-rolling-back)
Call `.cancel()` to discard all pending changes. This is typically done when an error occurs during the transaction. After cancelling, the transaction cannot be used again.

```ts
await txn.cancel();
```

##  Retrying on write conflict[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#retrying-on-write-conflict)
Queries executed within a transaction can fail with a write conflict under concurrent load, just like queries outside a transaction. Since `SurrealTransaction` exposes the same query methods as a regular session, you can chain [`.retry()`](https://surrealdb.com/docs/reference/javascript/api/queries/query#retry) onto any statement inside the transaction to replay it with exponential backoff.

```ts
const txn = await db.beginTransaction();

await txn.update(new RecordId('accounts', 'alice'))
    .merge({ balance: from.balance - 100 })
    .retry({ attempts: 3 });

await txn.commit();
```

See [Retrying on write conflict](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#retrying-on-write-conflict) for how to configure a connection-wide default.
##  Handling errors in transactions[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#handling-errors-in-transactions)
Always wrap transaction logic in a try-catch block to ensure the transaction is cancelled if any operation fails. This prevents partial changes from being committed.

```ts
const txn = await db.beginTransaction();

try {
    const from = await txn.select(new RecordId('accounts', 'alice'));
    const to = await txn.select(new RecordId('accounts', 'bob'));

    if (from.balance < 100) {
        throw new Error('Insufficient funds');
    }

    await txn.update(new RecordId('accounts', 'alice'))
        .merge({ balance: from.balance - 100 });

    await txn.update(new RecordId('accounts', 'bob'))
        .merge({ balance: to.balance + 100 });

    await txn.commit();
} catch (error) {
    await txn.cancel();
    throw error;
}
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#best-practices)
###  Keep transactions short[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#keep-transactions-short)
Execute transactions quickly to avoid holding resources longer than necessary. Perform any validation or external API calls before starting the transaction.

```ts
if (!isValidEmail(email)) {
    throw new Error('Invalid email');
}

const txn = await db.beginTransaction();
await txn.create(new RecordId('users', id)).content({ email });
await txn.commit();
```

###  Do not reuse transactions[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#do-not-reuse-transactions)
Once a transaction is committed or cancelled, create a new one for subsequent operations.

```ts
const txn1 = await db.beginTransaction();
await txn1.create(record1).content(data1);
await txn1.commit();

const txn2 = await db.beginTransaction();
await txn2.create(record2).content(data2);
await txn2.commit();
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/concepts/transactions#learn-more)
  * •
[SurrealTransaction API reference](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction) for the complete transaction interface
  * •
[Executing queries](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries) for the query methods available on transactions
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/javascript/concepts/multiple-sessions) for running transactions on isolated sessions
