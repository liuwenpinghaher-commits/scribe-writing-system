---
title: "https://surrealdb.com/docs/reference/php/libraries/surqlize/models"
url: "https://surrealdb.com/docs/reference/php/libraries/surqlize/models"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/libraries/surqlize/models

Source: https://surrealdb.com/docs/reference/php/libraries/surqlize/models

A Surqlize model is a PHP class that maps to a SurrealDB table. It extends `Surqlize\Model\Model`, declares its table with the `#[Table]` attribute, and exposes the record's fields as typed properties.

```php
use Surqlize\Attributes\Id;
use Surqlize\Attributes\Table;
use Surqlize\Model\Model;
use SurrealDB\SDK\Types\RecordId;

#[Table('user')]
final class User extends Model
{
    #[Id]
    public RecordId $id;

    public string $name;
    public int $age;
}
```

The property marked `#[Id]` holds the record's [`RecordId`](https://surrealdb.com/docs/reference/php/v2/api/data-types#recordid) from the SDK. Property names map to SurrealDB field names directly, so a `name` property reads and writes the `name` field.
##  Attributes[](https://surrealdb.com/docs/reference/php/libraries/surqlize/models#attributes)
Surqlize describes a model through attributes in the `Surqlize\Attributes` namespace.  
| Attribute  | Target  | Purpose  |  
| --- | --- | --- |  
| `#[Table('user')]`  | class  | Maps the model to a table  |  
| `#[Id]`  | property  | Marks the record id property (a `RecordId`)  |  
| `#[Cast(Address::class)]`  | property  | Hydrates a nested value as another model  |  
| `#[Schema(UserSchema::class)]`  | class  | Links the model to a [schema](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema) definition  |  
| `#[Search(analyzer: 'english')]`  | property  | Marks a [full-text search](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/search-vector-geometry) field  |  
| `#[Vector(dimension: 3)]`  | property  | Marks a [vector](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/search-vector-geometry) field and its dimension  |  
| `#[Geometry]`  | property  | Marks a [geometry](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/search-vector-geometry) field  |  
| `#[Edge('has_address', in: User::class, out: Address::class)]`  | class  | Defines a graph [edge](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/edges-and-graph) model  |  
The `#[Vector]` attribute also accepts a `distance` (default `cosine`), `#[Geometry]` accepts a `type` (default `geometry`), and `#[Search]` accepts an optional `analyzer`.
##  Nested models[](https://surrealdb.com/docs/reference/php/libraries/surqlize/models#nested-models)
Use `#[Cast]` to hydrate an embedded object or a record link as another model. The nested class is itself a model.

```php
use Surqlize\Attributes\Cast;
use Surqlize\Attributes\Table;
use Surqlize\Model\Model;

#[Table('address')]
final class Address extends Model
{
    public string $street;
    public int $number;
    public string $postcode;
}

#[Table('user')]
final class User extends Model
{
    #[Id]
    public RecordId $id;

    public string $name;

    #[Cast(Address::class)]
    public ?Address $address = null;
}
```

##  What a model gives you[](https://surrealdb.com/docs/reference/php/libraries/surqlize/models#what-a-model-gives-you)
Extending `Model` provides static query entry points and instance data operations.  
| Method  | Purpose  |  
| --- | --- |  
| `select()`  | Start a `SELECT` with fields or a typed callback  |  
| `query()`  | Start `SELECT *` for the table  |  
| `selectValue()`  | Start a `SELECT VALUE` query  |  
| `fields()`  | Resolve the model's typed field set  |  
| `relate()`  | Start a model-first [relation](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/edges-and-graph) builder  |  
|  `create()`, `createQuery()`, `upsert()`, `save()`, `delete()`  |  [Persist](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/mutations) a record  |  
|  `all()`, `find()`, `findOrFail()`, `count()`, `exists()`, `refresh()`  | Read or reload records  |  
| `toArray()`  | Serialise the initialised properties to an array  |  
These are covered in [Querying](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/querying) and [Mutations](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/mutations).
##  Learn more[](https://surrealdb.com/docs/reference/php/libraries/surqlize/models#learn-more)
  * •
[Connections](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/connections) to register the executor models run through
  * •
[Querying](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/querying) for the typed query builder
  * •
[Schema](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema) to define tables and fields in the database
