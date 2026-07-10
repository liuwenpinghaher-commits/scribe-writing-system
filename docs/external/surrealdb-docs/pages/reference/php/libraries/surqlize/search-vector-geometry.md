---
title: "https://surrealdb.com/docs/reference/php/libraries/surqlize/search-vector-geometry"
url: "https://surrealdb.com/docs/reference/php/libraries/surqlize/search-vector-geometry"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/libraries/surqlize/search-vector-geometry

Source: https://surrealdb.com/docs/reference/php/libraries/surqlize/search-vector-geometry

Surqlize provides field helpers that compile SurrealDB's full-text search, vector, and geometry expressions. Mark the relevant properties with the matching attribute, then use the field helper in a `where()` or projection.

```php
use Surqlize\Attributes\Geometry;
use Surqlize\Attributes\Search;
use Surqlize\Attributes\Table;
use Surqlize\Attributes\Vector;
use Surqlize\Model\Model;

#[Table('searchable_article')]
final class SearchableArticle extends Model
{
    public string $title;

    #[Search]
    public string $body;

    /** @var list<float> */
    #[Vector(dimension: 3)]
    public array $embedding = [];

    /** @var list<float> */
    #[Geometry]
    public array $location = [];
}
```

##  Full-text search[](https://surrealdb.com/docs/reference/php/libraries/surqlize/search-vector-geometry#full-text-search)
`SearchField` compiles search predicates and helpers. `matches()` builds the `@@` operator, `score()` returns the relevance score, and `highlight()` marks matched terms.

```php
use Surqlize\Query\Fields\SearchField;

$body = new SearchField('body');

SearchableArticle::select(['title', $body->score()->as('score')])
    ->where(fn () => $body->matches('surreal orm'))
    ->orderBy('score', 'DESC')
    ->compile();
// SELECT title, search::score(1) AS score FROM searchable_article
// WHERE body @@ 'surreal orm' ORDER BY score DESC
```

`score()` and `highlight()` take an optional match reference (default `1`) that ties the helper to the matching predicate.
##  Vector search[](https://surrealdb.com/docs/reference/php/libraries/surqlize/search-vector-geometry#vector-search)
`VectorField` compiles a K-nearest-neighbour query. `nearest()` builds the KNN predicate, and `knnDistance()` projects the computed distance.

```php
use Surqlize\Query\Fields\VectorField;

$embedding = new VectorField('embedding');

SearchableArticle::select(['title', $embedding->knnDistance()->as('distance')])
    ->where(fn () => $embedding->nearest([0.1, 0.2, 0.3], k: 10, effort: 40))
    ->orderBy('distance')
    ->compile();
```

`nearest()` takes the query vector and the number of neighbours `k`, with an optional `effort` for the HNSW search.
##  Geometry[](https://surrealdb.com/docs/reference/php/libraries/surqlize/search-vector-geometry#geometry)
`GeometryField` compiles spatial predicates and distance projections.

```php
use Surqlize\Query\Fields\GeometryField;

$location = new GeometryField('location');

SearchableArticle::select(['*', $location->distanceTo([4.9, 52.3])->as('distance')])
    ->where(fn () => $location->withinMeters([4.9, 52.3], 5000))
    ->orderBy('distance')
    ->compile();
```

The helper also provides `inside()`, `intersects()`, and `containsGeometry()` predicates.
##  Learn more[](https://surrealdb.com/docs/reference/php/libraries/surqlize/search-vector-geometry#learn-more)
  * •
[Models](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/models) for the `#[Search]`, `#[Vector]`, and `#[Geometry]` attributes
  * •
[Schema](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema) to define search analysers and vector indexes
  * •
[Querying](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/querying) for the query builder these helpers plug into
