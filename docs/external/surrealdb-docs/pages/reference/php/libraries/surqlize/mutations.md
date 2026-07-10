---
title: "https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations"
url: "https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations

Source: https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations

Surqlize exposes mutations two ways. Model helpers such as `create()` and `save()` cover the common cases and return hydrated models. The mutation builder gives full control over the payload, the return clause, and conditional updates.
##  Model helpers[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#model-helpers)
###  Create[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#create)
`create()` inserts a record and returns the model. Pass an `id` to set a specific record id.

```php
$user = User::create(['name' => 'beau', 'age' => 27]);

$user = User::create(['name' => 'beau', 'age' => 27], id: 'beau');
```

###  Save[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#save)
`save()` creates the record when the model has no `RecordId`, and updates it when it does.

```php
$user = User::findOrFail('beau');
$user->age = 28;
$user = $user->save();
```

###  Upsert[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#upsert)
`upsert()` creates the record if it does not exist, or updates it if it does. It requires an id.

```php
$user = User::upsert(['name' => 'beau', 'age' => 27], id: 'beau');
```

###  Delete[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#delete)
`delete()` removes the record the model points at.

```php
$user = User::findOrFail('beau');
$user->delete();
```

###  Reading records[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#reading-records)
The read helpers return models or scalars.  
| Method  | Purpose  |  
| --- | --- |  
| `all()`  | Fetch every record as models  |  
| `find($id)`  | Find one model by id, or `null`  |  
| `findOrFail($id)`  | Find one model by id, or throw `ModelNotFoundException`  |  
| `count($where?)`  | Count records, optionally filtered  |  
| `exists($where?)`  | Whether at least one matching record exists  |  
| `refresh()`  | Reload the model instance from the database  |  

```php
$count = User::count(fn ($user) => $user->age->gte(18));

if (User::exists(fn ($user) => $user->name->eq('beau'))) {
    // ...
}
```

##  The mutation builder[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#the-mutation-builder)
For more control, build the mutation explicitly. `createQuery()` returns a builder instead of running immediately, and `updateWhere()` and `deleteWhere()` target records by predicate.

```php
$query = User::createQuery(['name' => 'beau', 'age' => 27], id: 'beau');
$query->compile();
// CREATE user:beau CONTENT {"name":"beau","age":27} RETURN AFTER
```

Update or delete records that match a condition.

```php
User::updateWhere(fn ($user) => $user->age->gte(18))
    ->merge(['verified' => true])
    ->returnAfter()
    ->execute();

User::deleteWhere(fn ($user) => $user->age->lt(13))
    ->returnBefore()
    ->execute();
```

###  Payload modes[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#payload-modes)  
| Method  | SurrealQL  |  
| --- | --- |  
| `content($data)`  | `CONTENT`  |  
| `merge($data)`  | `MERGE`  |  
| `replace($data)`  | `REPLACE`  |  
| `patch($patches)`  | `PATCH`  |  
###  Return modes[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#return-modes)  
| Method  | SurrealQL  |  
| --- | --- |  
| `returnNone()`  | `RETURN NONE`  |  
| `returnBefore()`  | `RETURN BEFORE`  |  
| `returnAfter()`  | `RETURN AFTER`  |  
| `returnDiff()`  | `RETURN DIFF`  |  
| `returning($fields)`  | Return selected fields  |  
| `returningValue($field)`  | Return one selected value  |  
###  Running the mutation[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#running-the-mutation)
`timeout($amount, $unit = 's')` adds a statement timeout. To run the mutation, call one of:  
| Method  | Result  |  
| --- | --- |  
| `execute()`  | The raw SDK result  |  
| `executeModels()`  | A list of hydrated models  |  
| `firstModel()`  | The first hydrated model, or `null`  |  
| `compile()`  | A literal SurrealQL string  |  
| `toBoundQuery()`  | An SDK [`BoundQuery`](https://surrealdb.com/docs/reference/php/v2/api/utilities#boundquery)  |  

```php
$user = User::createQuery(['name' => 'beau'])
    ->returnAfter()
    ->firstModel();
```

##  Learn more[](https://surrealdb.com/docs/reference/php/libraries/surqlize/mutations#learn-more)
  * •
[Querying](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/querying) for reading records
  * •
[Transactions](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/transactions) for grouping mutations atomically
  * •
[Connections](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/connections) for per-query executor injection
