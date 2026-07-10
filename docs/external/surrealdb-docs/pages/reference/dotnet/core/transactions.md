---
title: "https://surrealdb.com/docs/reference/dotnet/core/transactions"
url: "https://surrealdb.com/docs/reference/dotnet/core/transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/transactions

Source: https://surrealdb.com/docs/reference/dotnet/core/transactions

Transactions allow you to execute a group of queries atomically, meaning either all changes are applied or none are. This is essential for maintaining data consistency when performing related operations that must not be partially applied.  
| Method  | Description  |  
| --- | --- |  
| [` session.BeginTransaction() `](https://surrealdb.com/docs/reference/dotnet/core/transactions#begintransaction)  | Create a new transaction scoped to the current session.  |  
| [` txn.Commit() `](https://surrealdb.com/docs/reference/dotnet/core/transactions#commit)  | Commit the transaction to the database, applying all changes made within  
the transaction scope.  |  
| [` txn.Cancel() `](https://surrealdb.com/docs/reference/dotnet/core/transactions#cancel)  | Cancel and discard all changes made in the transaction.  |  
##  `.BeginTransaction()`[](https://surrealdb.com/docs/reference/dotnet/core/transactions#begintransaction)
Creates a new transaction scoped to the current session. Transactions allow you to execute multiple queries atomically.
Method Syntax

```csharp
await session.BeginTransaction(cancellationToken)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/transactions#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous  
operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/transactions#example-usage)

```csharp
// Begin a new transaction on the current session
await using var txn = await db.BeginTransaction();

// Execute queries within the transaction
await txn.Create("person", new { Name = "John" });
await txn.Create("person", new { Name = "Jane" });

// Commit all changes atomically
await txn.Commit();
```

  

##  `.Commit()`[](https://surrealdb.com/docs/reference/dotnet/core/transactions#commit)
Commits the transaction to the database, applying all changes made within the transaction scope.
Note
After committing, the transaction cannot be used again.
Method Syntax

```csharp
await txn.Commit(cancellationToken)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/transactions#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous  
operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/transactions#example-usage-1)

```csharp
await using var txn = await db.BeginTransaction();

await txn.Create("order", new { Total = 99.99 });
await txn.Create("invoice", new { OrderId = "order:1" });

// Commit all changes — either both succeed or neither does
await txn.Commit();
```

  

##  `.Cancel()`[](https://surrealdb.com/docs/reference/dotnet/core/transactions#cancel)
Cancels and discards all changes made in the transaction.
Note
After canceling, the transaction cannot be used again.
Method Syntax

```csharp
await txn.Cancel(cancellationToken)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/transactions#arguments-2)  
| Arguments  | Description  |  
| --- | --- |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous  
operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/transactions#example-usage-2)

```csharp
await using var txn = await db.BeginTransaction();

try
{
    await txn.Create("order", new { Total = 99.99 });

    // ... more operations

    await txn.Commit();
}
catch
{
    // Discard all changes on error
    await txn.Cancel();
}
```
