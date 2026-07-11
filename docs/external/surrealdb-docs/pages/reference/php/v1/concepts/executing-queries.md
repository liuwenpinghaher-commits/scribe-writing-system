---
title: "https://surrealdb.com/docs/reference/php/v1/concepts/executing-queries"
url: "https://surrealdb.com/docs/reference/php/v1/concepts/executing-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/v1/concepts/executing-queries

Source: https://surrealdb.com/docs/reference/php/v1/concepts/executing-queries

The methods below are used to interact with the database and perform CRUD operations.  
You can also use the [`query`](https://surrealdb.com/docs/reference/php/v1/methods/query) method to run [SurrealQL statements](https://surrealdb.com/docs/reference/query-language/statements/overview) against the database.
##  Creating records[](https://surrealdb.com/docs/reference/php/v1/concepts/executing-queries#creating-records)
If we wish to create a new record in the database, we can use the [`create`](https://surrealdb.com/docs/reference/php/v1/methods/create) method. The first argument  
is the table name and the second argument is an associative array with the column names and values.

```php
$person = $db->create("person:tobie", [
	"name" => "Tobie",
	"lastname" => "Morgan Hitchcock",
	"age" => 30,
	"hobbies" => ["reading", "coding"]
]);
```

##  Selecting records[](https://surrealdb.com/docs/reference/php/v1/concepts/executing-queries#selecting-records)
After when you created a record, you can now use the [`select`](https://surrealdb.com/docs/reference/php/v1/methods/select) method to fetch the newly created person.  
The first argument is the newly created person's ID or a string which is the table name.

```php
$person = $db->select($person->id);
```

Or you can fetch it manually by using the RecordID or RecordStringId.

```php
// using the StringRecordId
$id = StringRecordId::create("person:tobie");
$person = $db->select($id);

// using the RecordId
$id = RecordId::create("person", "tobie");
$person = $db->select($id);
```

##  Updating records[](https://surrealdb.com/docs/reference/php/v1/concepts/executing-queries#updating-records)
To update a record, you can use the [`update`](https://surrealdb.com/docs/reference/php/v1/methods/update) method. The first argument is the RecordID or a StringRecordId,  
and the second argument is an associative array with the column names and values. Updating a record can be done if 3 ways:
updatemergepatch
The [`update`](https://surrealdb.com/docs/reference/php/v1/methods/update) method will replace the entire record with the new values. So make sure you include all the columns in the associative array.

```php
$person = $db->update($person->id, [
	"name" => "Tobie",
	"lastname" => "Morgan Hitchcock",
	"age" => 31
]);
```

You can find more information about updating a record using the update method [here](https://surrealdb.com/docs/reference/query-language/statements/update).
The [`merge`](https://surrealdb.com/docs/reference/query-language/statements/update#merge-clause) method will merge the new values with the existing record. If the column already exists, it will be replaced with the new value.

```php
$person = $db->merge($person->id, [
	"age" => 31
]);
```

You can find more information about updating a record using the merge method [here](https://surrealdb.com/docs/reference/rest-api/rpc-protocol#merge).
The [`patch`](https://surrealdb.com/docs/reference/php/v1/methods/patch) method will update a field in a single or multiple record(s) based on the path provided.

```php
$person = $db->patch($person->id, [
	"path" => "/hobbies/0",
	"op" => "replace",
	"value" => "writing"
]);
```

You can find more information about updating a record using the patch method [here](https://surrealdb.com/docs/reference/query-language/statements/update).
##  Deleting records[](https://surrealdb.com/docs/reference/php/v1/concepts/executing-queries#deleting-records)
To delete a record, you can use the [`delete`](https://surrealdb.com/docs/reference/php/v1/methods/delete) method. The first argument is the RecordID or a StringRecordId.

```php
$db->delete($person->id);
```

or we can use the RecordId or StringRecordId to delete the record.

```php
$id = StringRecordId::create("person:tobie");
$db->delete($id);

$id = RecordId::create("person", "tobie");
$db->delete($id);
```
