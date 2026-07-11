---
title: "https://surrealdb.com/docs/reference/php/libraries/surqlize/transactions"
url: "https://surrealdb.com/docs/reference/php/libraries/surqlize/transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/libraries/surqlize/transactions

Source: https://surrealdb.com/docs/reference/php/libraries/surqlize/transactions

`ConnectionManager::transaction()` runs a set of ORM queries inside one transaction. It passes a transaction executor to your callback; run your queries through that executor with `withExecutor()` or the `executor:` argument. The transaction commits when the callback returns, and rolls back if it throws.

```php
use Surqlize\Connection\ConnectionManager;

ConnectionManager::transaction(function ($transaction): void {
    User::select(['name'])
        ->where(fn ($user) => $user->name->eq('beau'))
        ->withExecutor($transaction)
        ->collect();

    User::createQuery([
        'name' => 'tobie',
        'age' => 30,
    ], executor: $transaction)->execute();
});
```

If the callback throws, the transaction is rolled back and the exception is rethrown, so the batch either applies in full or not at all.
Note
Every query inside the callback must use the transaction executor. A query that resolves the global executor instead runs outside the transaction.
##  Validation and errors[](https://surrealdb.com/docs/reference/php/libraries/surqlize/transactions#validation-and-errors)
Surqlize validates several contracts before it builds or executes a query, and raises typed exceptions when they fail.
  * •
Model classes must extend `Surqlize\Model\Model`, and edge classes must extend `Surqlize\Edge\Edge`.
  * •
Table and field identifiers are validated before compilation.
  * •
`findOrFail()` throws `Surqlize\Model\Exception\ModelNotFoundException` when no record matches.
  * •
Schema validation rules run before `create()` and `save()`, and a failing rule raises a `ValidationException`.
  * •
Persistence methods throw when a required `RecordId` is missing.
  * •
`RELATE` validates the edge endpoint classes and their record ids.

##  Learn more[](https://surrealdb.com/docs/reference/php/libraries/surqlize/transactions#learn-more)
  * •
[Connections](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/connections) for executor injection
  * •
[Mutations](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/mutations) for the queries you batch
  * •
[Transactions in the SDK](https://surrealdb.com/docs/reference/php/v2/concepts/transactions) for the underlying mechanism
