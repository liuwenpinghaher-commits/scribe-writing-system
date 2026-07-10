---
title: "https://surrealdb.com/docs/reference/dotnet/core/data-manipulation"
url: "https://surrealdb.com/docs/reference/dotnet/core/data-manipulation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/core/data-manipulation

Source: https://surrealdb.com/docs/reference/dotnet/core/data-manipulation

SurrealDB supports a number of methods for interacting with the database and performing CRUD operations.  
| Method  | Description  |  
| --- | --- |  
| [` db.Select() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#select)  | Selects all records in a table, or a specific record, from the database  |  
| [` db.Create() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#create)  | Creates a record in the database  |  
| [` db.Insert() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#insert)  | Inserts one or multiple records in the database  |  
| [` db.InsertRelation() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#insert_relation)  | Inserts one or multiple relations in the database  |  
| [` db.Update() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#update)  | Updates all records in a table, or a specific record, in the database  |  
| [` db.Upsert() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#upsert)  | Creates or updates a set of records in a table, or a specific record, in the database  |  
| [` db.Merge() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#merge)  | Modifies all records in a table, or a specific record, in the database  |  
| [` db.Patch() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#patch)  | Applies JSON Patch changes to all records, or a specific record, in the database  |  
| [` db.Delete() `](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#delete)  | Deletes all records in a table, or a specific record, from the database  |  
##  `.Select<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#select)
Selects all records in a table, or a specific record, from the database.
Method Syntax

```csharp
await db.Select<T>(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to select.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage)

```csharp
// Select all records from a table
var people = await db.Select<Person>("person");

// Select a specific record from a table
var person = await db.Select<Person>(("person",
    "h5wxrf2ewk8xjxosxtyc"));
var person = await db.Select<Person>(new StringRecordId("person:h5wxrf2ewk8xjxosxtyc"));

// Select a specific record from a table, given a non-string id
var person = await db.Select<Person>(("person",
    new Guid("8424486b-85b3-4448-ac8d-5d51083391c7")));
```

  

##  `.Create<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#create)
Creates a record in the database.
Method Syntax

```csharp
await db.Create<T>(resource, data)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments-1)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to create.  |  
| `data`  | The document / record data to insert.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage-1)

```csharp
// Create a record with a random ID
var person = await db.Create<Person>("person");

// Create a record with a random ID & specific fields
var person = await db.Create("person", new Person { Name = "Tobie" });

// Create a record with a specific ID
var personToCreate = new Person
{
    Id = ("person", "tobie"),
    Name = "Tobie",
    Settings = new Settings
    {
        Active = true,
        Marketing = true,
    },
};
var result = await db.Create(personToCreate);
```

  

##  `.Insert<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#insert)
Inserts one or multiple records in the database.
Method Syntax

```csharp
await db.Insert<T>(table, data)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments-2)  
| Arguments  | Description  |  
| --- | --- |  
| `table`  | Optionally pass along a table to insert into.  |  
| `data`  | Either a single document/record or an array of documents/records to insert  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage-2)

```csharp
var posts = new List<Post>
{
    new Post
    {
        Id = ("post", "First"),
        Title = "An article",
        Content = "This is the first article"
    },
    new Post
    {
        Id = ("post", "Second"),
        Title = "An article",
        Content = "This is the second article"
    }
};

await db.Insert("post", posts);
```

  

##  `.InsertRelation<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#insert_relation)
Inserts one or multiple relations in the database.
Method Syntax

```csharp
await db.InsertRelation<T>(table, data)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments-3)  
| Arguments  | Description  |  
| --- | --- |  
| `table`  | Optionally pass along a table to insert into.  |  
| `data`  | Either a single document/record or an array of documents/records to insert  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage-3)

```csharp
await db.InsertRelation(
    new WroteRelation
    {
        In = ("user", "u1"),
        Out = ("post", "p1"),
        CreatedAt = now,
        NumberOfPages = 144
    }
);
```

  

##  `.Update<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#update)
Updates all records in a table, or a specific record, in the database.
Method Syntax

```csharp
await db.Update<T>(thing, data)
```

Note
This function replaces the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments-4)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to update.  |  
| `data`  | The document / record data to update.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage-4)

```csharp
var post = new Post
{
    Id = ("post", "another"),
    Title = "A new article",
    Content = "This is a new article created using the .NET SDK"
};

// Updates a single record
await db.Update(post);

var data = new Person
{
    Name = "Tobie",
    Settings = new Settings
    {
        Active = true,
        Marketing = true,
    },
};

// Updates all records inside the "person" table
await db.Update("person", data);
```

  

##  `.Upsert<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#upsert)
Creates or updates a specific record.
Method Syntax

```csharp
await db.Upsert<T>(data)
```

Note
This function creates a new document / record or replaces the current one with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments-5)  
| Arguments  | Description  |  
| --- | --- |  
| `data`  | The document / record data to insert.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage-5)

```csharp
var person = new Person
{
        Id = ("person", "tobie"),
        // Id is mandatory to apply create or update
    Name = "Tobie",
    Settings = new Settings
    {
        Active = true,
        Marketing = true,
    },
};

// Create a new record when it doesn't exist
var created = await db.Upsert(person);

// Update an existing record when it does exist
var updated = await db.Upsert(person);
```

  

##  `.Merge<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#merge)
Modifies all records in a table, or a specific record.
Method Syntax

```csharp
await db.Merge<T>(resource, data)
```

Note
This function merges the current document / record data with the specified data.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments-6)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to merge.  |  
| `data`  | The data with which to modify the records.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage-6)
Merging data within a single record

```csharp
// Only changes the fields specified in the merge object
var merge = new PersonMerge
{
    Id = ("person", "tobie"),
    Settings = new Settings
    {
        Active = true,
        Marketing = false,
    },
};
var result = await db.Merge<PersonMerge, Person>(merge);

// Only changes the fields specified in the Dictionary
var data = new Dictionary<string, object>
{
    { "tags", new List<string> { "developer", "engineer" } }
};

var result = await db.Merge<Person>(("person", "tobie"), data);
```

Merging data for every record in a table

```csharp
// Only changes the fields specified in the merge object
var merge = new PersonMerge
{
    Settings = new Settings
    {
        Active = true,
        Marketing = false,
    },
};
var result = await db.Merge<PersonMerge, Person>("person", merge);

// Only changes the fields specified in the Dictionary
var data = new Dictionary<string, object>
{
    { "tags", new List<string> { "developer", "engineer" } }
};

var result = await db.Merge<Person>("person", data);
```

  

##  `.Patch<T>()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#patch)
Applies JSON Patch changes to all records, or a specific record, in the database.
Method Syntax

```csharp
await db.Patch<T>(resource, data)
```

Note
This function patches document / record data with the specified [JSON Patch](https://jsonpatch.com/) data.
###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments-7)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or the specific [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to patch.  |  
| `data`  | The JSON Patch data with which to patch the records.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage-7)

```csharp
// Update a record with a specific ID
var result = await db.Patch(("person", "tobie"), patches);

// Update all records in a table
var result = await db.Patch("person", patches);
```

  

##  `.Delete()`[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#delete)
Deletes all records in a table, or a specific record, from the database.
Method Syntax

```csharp
await db.Delete(resource)
```

###  Arguments[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#arguments-8)  
| Arguments  | Description  |  
| --- | --- |  
| `thing`  | The table name or a [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid) to delete.  |  
| `cancellationToken`  | The cancellationToken enables graceful cancellation of asynchronous operations.  |  
###  Example usage[](https://surrealdb.com/docs/reference/dotnet/core/data-manipulation#example-usage-8)

```csharp
// Delete all records from a table
await db.Delete("person");

// Delete a specific record from a table
await db.Delete(("person", "h5wxrf2ewk8xjxosxtyc"));
```
