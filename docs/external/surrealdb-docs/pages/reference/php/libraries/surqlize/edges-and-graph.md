---
title: "https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph"
url: "https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph

Source: https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph

SurrealDB relation tables are represented by edge models. An edge model maps to a relation table and declares the models on each end, so traversals and `RELATE` statements are checked against your types.
##  Edge models[](https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph#edge-models)
An edge model extends `Surqlize\Edge\Edge` and uses the `#[Edge]` attribute with the relation table name and the `in` and `out` endpoint models.

```php
use Surqlize\Attributes\Edge;
use Surqlize\Attributes\Schema;
use Surqlize\Edge\Edge as EdgeModel;

#[Edge('has_address', in: User::class, out: Address::class)]
#[Schema(HasAddressSchema::class)]
final class HasAddress extends EdgeModel
{
}
```

Edge models inherit `RecordId $in` and `RecordId $out` endpoint properties from `Surqlize\Edge\Edge`.
##  Traversing in a SELECT[](https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph#traversing-in-a-select)
Use graph fields inside a model `SELECT` to traverse relations. `Edge::out()` and `Edge::in()` start a traversal in the given direction; chain another `out()` or `in()` to reach the far table, optionally with a predicate, then name it with `as()` and resolve it with `fetch()`.

```php
use App\Models\Address;
use App\Models\HasAddress;
use App\Models\User;
use Surqlize\Edge\Edge;

$query = User::select([
        'name',
        Edge::out(HasAddress::class)
            ->out(Address::class, fn ($address) => $address->postcode->includes('24'))
            ->as('address')
            ->fetch(),
    ])
    ->where(fn ($user) => $user->name->eq('beau'))
    ->fetch('address');

$query->compile();
// SELECT name, ->has_address->address[WHERE postcode INCLUDES '24'] AS address
// FROM user WHERE name = "beau" FETCH address
```

`Edge::out()` is a magic static call. If your static analysis setup struggles with it, use the explicit factory.

```php
use Surqlize\Edge\GraphSelectField;
use Surqlize\Query\Ast\GraphDirection;

GraphSelectField::fromEdge(HasAddress::class, GraphDirection::Out)
    ->out(Address::class)
    ->as('address');
```

##  Querying an edge's endpoints[](https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph#querying-an-edges-endpoints)
An edge instance can query its endpoint tables with `in()` and `out()`, which return model queries.

```php
$edge = new HasAddress();

$users = $edge->in()
    ->select(fn ($user) => [$user->name])
    ->where(fn ($user) => $user->age->gt(27))
    ->collectModels();

$addresses = $edge->out()
    ->select(fn ($address) => [$address->postcode])
    ->collectModels();
```

##  Creating relations[](https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph#creating-relations)
`Model::relate($from)` starts a `RELATE`. Chain `edge()` with the edge class, `with()` for the target, and `content()` for data on the edge.

```php
use Surqlize\Relate\Time;

User::relate($user)
    ->edge(HasAddress::class)
    ->with($address)
    ->content(['primary' => true])
    ->timeout(30, Time::Seconds)
    ->execute();
```

Both endpoint models must already have `RecordId` values. The builder validates that the source matches the edge's `in` endpoint and the target matches the `out` endpoint. Use `set($key, $value)` for a single field, and `compile()` or `toSdkQuery()` to inspect the statement instead of running it.
Note
`Model::relate($from)` is model-first only. The source model is the `in` endpoint and the `with()` target is the `out` endpoint.
##  Learn more[](https://surrealdb.com/docs/reference/php/libraries/surqlize/edges-and-graph#learn-more)
  * •
[Models](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/models) for the `#[Edge]` attribute
  * •
[Schema](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema) to define the relation table
  * •
[RELATE](https://surrealdb.com/docs/reference/query-language/statements/relate) for the SurrealQL statement
