---
title: "https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions"
url: "https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions

Source: https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions

In Laravel you query SurrealDB three ways: through Surqlize models, through the raw SDK client, and through the `SurrealDB` manager facade. The integration registers the executor, so model queries work without passing one.
##  Model queries[](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions#model-queries)
Define [Surqlize models](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/models) and query them directly. They run through the Laravel-managed connection.

```php
$users = User::select(fn ($user) => [$user->id, $user->name])
    ->where(fn ($user) => $user->name->eq('beau'))
    ->collectModels();

$user = User::create(['name' => 'Tobie', 'age' => 32], id: 'tobie');
```

See [Querying](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/querying) and [Mutations](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/mutations) for the full model API.
##  Raw SDK access[](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions#raw-sdk-access)
Resolve the SDK client for lower-level access.

```php
use SurrealDB\SDK\Surreal;

$result = app(Surreal::class)->run('RETURN $message', ['message' => 'hello']);
```

##  The manager facade[](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions#the-manager-facade)
The `SurrealDB` facade runs SurrealQL with lifecycle helpers around the same client, and targets a named connection with the `connection:` argument.

```php
use SurrealDB\Laravel\Facades\SurrealDB;

SurrealDB::health();

$result = SurrealDB::run('RETURN $message', ['message' => 'hello']);

$analytics = SurrealDB::run(
    'RETURN $message',
    ['message' => 'hello'],
    connection: 'analytics',
);
```

##  Transactions[](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions#transactions)
The `Surqlize` facade runs a transaction over the executor. Run each query inside the callback through the transaction it passes you, with the `executor:` argument or `withExecutor()`. The transaction commits when the callback returns and rolls back if it throws.

```php
use SurrealDB\Laravel\Facades\Surqlize;

Surqlize::transaction(function ($transaction): void {
    User::createQuery(['name' => 'beau'], executor: $transaction)->execute();
});

Surqlize::transaction(
    fn ($transaction) => User::createQuery(['name' => 'beau'], executor: $transaction)->execute(),
    connection: 'analytics',
);
```

Note
`Surqlize::transaction()` uses Surqlize's executor-based SurrealQL transaction batching. SDK-native transaction ids are not exposed through the Laravel facade yet, because they depend on the WebSocket transport and server feature support.
##  Learn more[](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions#learn-more)
  * •
[Container and facades](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades) for the facade method reference
  * •
[Surqlize transactions](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/transactions) for the batching mechanism
  * •
[Testing](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing) for asserting the queries your code sends
