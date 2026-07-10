---
title: "https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades"
url: "https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades

Source: https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades

The integration registers two service providers, binds the SDK and ORM into the container, and exposes three facades.
##  Service providers[](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades#service-providers)
Laravel auto-discovers both providers.
  * •
`SurrealDB\Laravel\SurrealDBServiceProvider` owns the SDK configuration, client construction, and the `surrealdb` container alias.
  * •
`SurrealDB\Laravel\SurqlizeServiceProvider` owns the ORM configuration, the schema commands, Surqlize's executor binding, and `ConnectionManager` setup.

##  Container bindings[](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades#container-bindings)
The SDK provider binds:
  * •
`SurrealDB\SDK\Surreal` and the `surrealdb` alias for the raw SDK client.
  * •
`SurrealDB\Laravel\SurrealDBManager` plus the `surrealdb.manager` and `surrealdb.connection` aliases for the Laravel lifecycle helpers.

The ORM provider binds:
  * •
`SurrealDB\SDK\Contracts\QueryExecutor` for Surqlize query execution.
  * •
`Surqlize\Model\SchemaManager` for schema definitions and application.
  * •
`SurrealDB\Laravel\SurqlizeManager` and the `surqlize` alias for the Laravel-friendly ORM helpers.

The ORM provider also registers Surqlize's global `ConnectionManager` with a lazy executor that resolves the configured `surqlize.executor` binding only when a query runs. By default that points at `surrealdb.connection`, so model queries use the Laravel-managed connection and connect lazily.

```php
use SurrealDB\SDK\Surreal;

$client = app(Surreal::class);
```

##  Facades[](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades#facades)
The integration ships three facades in the `SurrealDB\Laravel\Facades` namespace.
###  `SurrealDB`[](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades#surrealdb)
The manager facade. It manages named connections, runs SurrealQL, and exposes lifecycle and testing helpers. Most methods take an optional connection name.  
| Method  | Description  |  
| --- | --- |  
| `run($surql, $bindings, $connection?)`  | Run raw SurrealQL  |  
| `query($query, $connection?)`  | Run a [`BoundQuery`](https://surrealdb.com/docs/reference/php/v2/api/utilities#boundquery)  |  
|  `client($name?)` / `connection($name?)`  | Resolve the SDK client or its controller  |  
|  `connect()` / `disconnect()` / `reconnect()` / `isConnected()`  | Manage the connection lifecycle  |  
|  `health()` / `version()`  | Check the server  |  
| `using($connection)`  | Get an executor scoped to a connection  |  
|  `fake()` / `assertSurrealQuerySent()` / `resetFakes()`  |  [Testing](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing) helpers  |  

```php
use SurrealDB\Laravel\Facades\SurrealDB;

SurrealDB::health();

$result = SurrealDB::run('RETURN $message', ['message' => 'hello']);
```

###  `Surreal`[](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades#surreal)
Resolves the underlying SDK [`Surreal`](https://surrealdb.com/docs/reference/php/v2/api/core) client for direct, lower-level access.

```php
use SurrealDB\Laravel\Facades\Surreal;

$result = Surreal::run('RETURN true;');
```

###  `Surqlize`[](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades#surqlize)
Exposes the ORM manager: the executor, schema helpers, and transactions.  
| Method  | Description  |  
| --- | --- |  
| `executor()`  | The configured Surqlize executor  |  
| `schemaDefinitions($models?)`  | The schema statements for the models  |  
| `applySchema($models?, $executor?)`  | Apply the schema  |  
| `transaction($callback, $executor?, $connection?)`  | Run a [transaction](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions#transactions)  |  

```php
use SurrealDB\Laravel\Facades\Surqlize;

Surqlize::transaction(function ($transaction): void {
    User::createQuery(['name' => 'beau'], executor: $transaction)->execute();
});
```

##  Learn more[](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades#learn-more)
  * •
[Configuration](https://surrealdb.com/docs/reference/php/frameworks/laravel/configuration) for the settings these bindings read
  * •
[Queries and transactions](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions) for using the facades
  * •
[Testing](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing) for the fake executor
