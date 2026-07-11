---
title: "https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction"
url: "https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction

Source: https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction

The `SurrealTransaction` class provides transaction support for executing multiple queries atomically. When all desired queries have been executed, call [`commit()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#commit) to apply the changes to the database, or [`cancel()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#cancel) to discard them.
Transactions are created using the [`beginTransaction()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#begintransaction) method on a [`SurrealSession`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) instance.
**Extends:** [`SurrealQueryable`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable)
**Source:** [api/transaction.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/api/transaction.ts)
##  Overview[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#overview)
Transactions ensure that a group of operations are executed atomically - either all succeed or all fail. This is essential for maintaining data consistency when performing related operations.

```ts
const txn = await db.beginTransaction();

try {
    // All operations succeed or fail together
    await txn.create(recordId1).content(data1);
    await txn.create(recordId2).content(data2);
    await txn.commit(); // Apply all changes
} catch (error) {
    await txn.cancel(); // Discard all changes
}
```

##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#constructor)
The constructor is not called directly. Use [`SurrealSession.beginTransaction()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#begintransaction) to create transactions.
##  Transaction methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#transaction-methods)
###  `.commit()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#commit)
Commit the transaction to the database, applying all changes made within the transaction scope.
After committing, the transaction cannot be used again.
Method Syntax

```ts
txn.commit()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#returns)
`Promise` - Resolves when the transaction is committed
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#example)

```ts
const txn = await db.beginTransaction();

await txn.create(new RecordId('users', 'alice'))
    .content({ name: 'Alice', email: 'alice@example.com' });

await txn.create(new RecordId('users', 'bob'))
    .content({ name: 'Bob', email: 'bob@example.com' });

// Commit both creates atomically
await txn.commit();
console.log('Transaction committed successfully');
```

###  `.cancel()`[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#cancel)
Cancel and discard all changes made in the transaction.
After canceling, the transaction cannot be used again.
Method Syntax

```ts
txn.cancel()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#returns-1)
`Promise` - Resolves when the transaction is canceled
####  Example[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#example-1)

```ts
const txn = await db.beginTransaction();

try {
    await txn.create(new RecordId('users', 'alice'))
        .content({ name: 'Alice' });
    
    // Something goes wrong
    throw new Error('Validation failed');
} catch (error) {
    // Discard all changes
    await txn.cancel();
    console.log('Transaction cancelled:', error.message);
}
```

##  Inherited methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#inherited-methods)
As `SurrealTransaction` extends [`SurrealQueryable`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable), it inherits all query execution methods. All queries executed on a transaction instance are part of the transaction scope:
###  Query methods[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#query-methods)
  * •
[`query()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#query) - Execute raw SurrealQL
  * •
[`select()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#select) - Select records
  * •
[`create()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#create) - Create records
  * •
[`insert()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#insert) - Insert records
  * •
[`update()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#update) - Update records
  * •
[`upsert()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#upsert) - Upsert records
  * •
[`delete()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#delete) - Delete records
  * •
[`relate()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#relate) - Create graph relationships
  * •
[`live()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#live) - Subscribe to live queries
  * •
[`liveOf()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#liveof) - Subscribe to existing live queries
  * •
[`run()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#run) - Execute functions
  * •
[`auth()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#auth) - Get authenticated record user
  * •
[`api()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#api) - Access user-defined APIs

All of these operations are executed within the transaction context and will be committed or canceled together.
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#complete-examples)
###  Basic transaction[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#basic-transaction)

```ts
import { Surreal, RecordId } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');
await db.use({ namespace: 'main', database: 'main' });

// Start a transaction
const txn = await db.beginTransaction();

try {
    // Create a user
    const user = await txn.create(new RecordId('users', 'john'))
        .content({
            name: 'John Doe',
            email: 'john@example.com',
            balance: 1000
        });
    
    // Create a purchase
    const purchase = await txn.create(new RecordId('purchases', 'purchase1'))
        .content({
            user: new RecordId('users', 'john'),
            amount: 100,
            item: 'Widget'
        });
    
    // Update user balance
    await txn.update(new RecordId('users', 'john'))
        .merge({ balance: 900 });
    
    // Commit all changes atomically
    await txn.commit();
    console.log('Purchase completed successfully');
} catch (error) {
    // If anything fails, cancel the transaction
    await txn.cancel();
    console.error('Purchase failed:', error);
}
```

###  Money transfer transaction[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#money-transfer-transaction)

```ts
async function transferMoney(
    db: Surreal,
    fromUser: string,
    toUser: string,
    amount: number
) {
    const txn = await db.beginTransaction();
    
    try {
        // Get current balances
        const from = await txn.select(new RecordId('users', fromUser));
        const to = await txn.select(new RecordId('users', toUser));
        
        if (!from || !to) {
            throw new Error('User not found');
        }
        
        if (from.balance < amount) {
            throw new Error('Insufficient funds');
        }
        
        // Update both balances
        await txn.update(new RecordId('users', fromUser))
            .merge({ balance: from.balance - amount });
        
        await txn.update(new RecordId('users', toUser))
            .merge({ balance: to.balance + amount });
        
        // Create transaction record
        await txn.create(new RecordId('transactions', crypto.randomUUID()))
            .content({
                from: new RecordId('users', fromUser),
                to: new RecordId('users', toUser),
                amount,
                timestamp: new Date()
            });
        
        // Commit all changes
        await txn.commit();
        console.log(`Transferred ${amount} from ${fromUser} to ${toUser}`);
        return true;
    } catch (error) {
        await txn.cancel();
        console.error('Transfer failed:', error);
        return false;
    }
}

// Use the function
await transferMoney(db, 'alice', 'bob', 50);
```

###  Complex transaction with graph relationships[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#complex-transaction-with-graph-relationships)

```ts
async function createUserWithFollows(
    db: Surreal,
    userData: { name: string; email: string },
    followUserIds: string[]
) {
    const txn = await db.beginTransaction();
    
    try {
        // Create the user
        const userId = crypto.randomUUID();
        const user = await txn.create(new RecordId('users', userId))
            .content(userData);
        
        // Create follow relationships
        for (const followId of followUserIds) {
            await txn.relate(
                new RecordId('users', userId),
                new Table('follows'),
                new RecordId('users', followId),
                { followedAt: new Date() }
            );
        }
        
        // Create initial activity log
        await txn.create(new RecordId('activity', crypto.randomUUID()))
            .content({
                user: new RecordId('users', userId),
                action: 'user_created',
                timestamp: new Date()
            });
        
        // Commit everything
        await txn.commit();
        console.log('User and relationships created successfully');
        return user;
    } catch (error) {
        await txn.cancel();
        console.error('Failed to create user:', error);
        throw error;
    }
}
```

###  Transaction with error handling[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#transaction-with-error-handling)

```ts
async function atomicBulkOperation(db: Surreal, records: any[]) {
    const txn = await db.beginTransaction();
    const results: any[] = [];
    const errors: any[] = [];
    
    try {
        for (const record of records) {
            try {
                const result = await txn.create(new Table('items'))
                    .content(record);
                results.push(result);
            } catch (error) {
                errors.push({ record, error });
            }
        }
        
        // Only commit if all succeeded
        if (errors.length === 0) {
            await txn.commit();
            console.log(`Successfully created ${results.length} records`);
            return { success: true, results };
        } else {
            await txn.cancel();
            console.log(`Failed with ${errors.length} errors, rolled back`);
            return { success: false, errors };
        }
    } catch (error) {
        await txn.cancel();
        console.error('Transaction failed:', error);
        return { success: false, errors: [error] };
    }
}
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#best-practices)
###  1. Always handle errors[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#1-always-handle-errors)
Always use try-catch blocks to ensure transactions are properly canceled on errors:

```ts
const txn = await db.beginTransaction();
try {
    // Operations
    await txn.commit();
} catch (error) {
    await txn.cancel(); // Important!
    throw error;
}
```

###  2. Keep transactions short[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#2-keep-transactions-short)
Execute transactions quickly to avoid locking resources:

```ts
// Good: Short transaction
const txn = await db.beginTransaction();
await txn.update(recordId).merge(data);
await txn.commit();

// Avoid: Long-running operations in transactions
const txn = await db.beginTransaction();
await expensiveExternalApiCall(); // Bad!
await txn.update(recordId).merge(data);
await txn.commit();
```

###  3. Don't reuse transactions[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#3-dont-reuse-transactions)
Once a transaction is committed or canceled, create a new one for subsequent operations:

```ts
const txn1 = await db.beginTransaction();
await txn1.create(record1);
await txn1.commit();

// Create a new transaction for next operation
const txn2 = await db.beginTransaction();
await txn2.create(record2);
await txn2.commit();
```

###  4. Validate before transaction[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#4-validate-before-transaction)
Perform validation before starting a transaction when possible:

```ts
// Validate first
if (!isValidEmail(email)) {
    throw new Error('Invalid email');
}

// Then transact
const txn = await db.beginTransaction();
// ... operations
await txn.commit();
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/core/surreal-transaction#see-also)
  * •
[SurrealSession.beginTransaction()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session#begintransaction) - Creating transactions
  * •
[SurrealQueryable](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable) - Available query methods
  * •
[Query builders](https://surrealdb.com/docs/reference/javascript/api/queries/) - Query builder classes
