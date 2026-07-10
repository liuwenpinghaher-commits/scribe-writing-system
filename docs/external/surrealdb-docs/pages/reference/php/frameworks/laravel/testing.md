---
title: "https://surrealdb.com/docs/reference/php/frameworks/laravel/testing"
url: "https://surrealdb.com/docs/reference/php/frameworks/laravel/testing"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/frameworks/laravel/testing

Source: https://surrealdb.com/docs/reference/php/frameworks/laravel/testing

The integration provides a fake executor so you can assert the queries your code sends without a live database, plus a trait that resets Surqlize's global caches between tests.
##  Resetting state between tests[](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing#resetting-state-between-tests)
Surqlize keeps global state in its `ConnectionManager` and metadata caches. The `RefreshSurqlizeState` trait resets it so tests do not leak state into one another.

```php
use SurrealDB\Laravel\Testing\RefreshSurqlizeState;

final class UserTest extends TestCase
{
    use RefreshSurqlizeState;

    protected function tearDown(): void
    {
        $this->resetSurqlizeState();

        parent::tearDown();
    }
}
```

The trait also offers `useSurqlizeExecutor()` to set a specific executor, `fakeSurrealDB()` to fake the managed executor, and `resetSurrealDBFakes()` to clear fakes.
##  Faking the executor[](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing#faking-the-executor)
`SurrealDB::fake()` swaps the managed executor for a `FakeQueryExecutor` that records queries instead of running them. Assert what was sent with `assertSurrealQuerySent()`, or on the returned fake with `assertQuerySent()`.

```php
use SurrealDB\Laravel\Facades\SurrealDB;

$fake = SurrealDB::fake();

SurrealDB::run('RETURN true;');

SurrealDB::assertSurrealQuerySent('RETURN true;');
$fake->assertQuerySent('RETURN true;');
```

The fake also provides `assertNothingSent()` for asserting that no queries were sent.
##  Named fakes[](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing#named-fakes)
Fakes are scoped by connection name, so you can fake one connection and leave the others untouched.

```php
SurrealDB::fake('analytics');

SurrealDB::run('RETURN true;', connection: 'analytics');

SurrealDB::assertSurrealQuerySent('RETURN true;', connection: 'analytics');
```

##  Unit testing without the container[](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing#unit-testing-without-the-container)
For unit tests that do not boot the application, pass a `FakeQueryExecutor` directly to a Surqlize query through `withExecutor()`, or register it globally with `useSurqlizeExecutor()` from the trait.

```php
use SurrealDB\Laravel\Testing\FakeQueryExecutor;

$fake = new FakeQueryExecutor();

User::query()->withExecutor($fake)->collect();

$fake->assertQuerySent('SELECT * FROM user');
```

##  Learn more[](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing#learn-more)
  * •
[Container and facades](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades) for the facade testing helpers
  * •
[Queries and transactions](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions) for the queries under test
  * •
[Surqlize connections](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/connections) for executor injection
