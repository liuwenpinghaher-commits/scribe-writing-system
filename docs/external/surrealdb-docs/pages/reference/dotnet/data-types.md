---
title: "https://surrealdb.com/docs/reference/dotnet/data-types"
url: "https://surrealdb.com/docs/reference/dotnet/data-types"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/dotnet/data-types

Source: https://surrealdb.com/docs/reference/dotnet/data-types

The .NET SDK translates datatypes native to SurrealQL into either datatypes native to .NET, or a custom implementation.  
This document describes all datatypes, and links to their respective documentation.
##  Data types overview[](https://surrealdb.com/docs/reference/dotnet/data-types#data-types-overview)  
| SurrealQL type  | Kind  | Documentation  |  
| --- | --- | --- |  
| `string`  | Native  | [`String`](https://learn.microsoft.com/en-us/dotnet/api/system.string)  |  
|  `int`, `float`  | Native  |  Any number type, e.g.[`Int32`](https://learn.microsoft.com/en-us/dotnet/api/system.int32),[`Single`](https://learn.microsoft.com/fr-fr/dotnet/api/system.single)  |  
| `bool`  | Native  | [`Boolean`](https://learn.microsoft.com/en-us/dotnet/api/system.boolean)  |  
| `null`  | Native  | [`null`](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/keywords/null)  |  
| `none`  | Custom  | [`None`](https://surrealdb.com/docs/reference/dotnet/data-types#none)  |  
| `array`  | Native  |  Any `IEnumerable`representation  |  
| `object`  | Native  |  Any `Object`representation  |  
| `set`  | Native  |  Any `HashSet`representation  |  
| `datetime`  | Native  |  [`DateTime`](https://learn.microsoft.com/fr-fr/dotnet/api/system.datetime)or[`DateOnly`](https://learn.microsoft.com/fr-fr/dotnet/api/system.dateonly)  |  
| `bytes`  | Native  | `byte[]`  |  
| `uuid`  | Native  | [`Guid`](https://learn.microsoft.com/fr-fr/dotnet/api/system.guid)  |  
| `duration`  | Native  |  [`TimeSpan`](https://learn.microsoft.com/fr-fr/dotnet/api/system.timespan)or[`TimeOnly`](https://learn.microsoft.com/fr-fr/dotnet/api/system.timeonly)  |  
| `decimal`  | Native  | [`Decimal`](https://learn.microsoft.com/fr-fr/dotnet/api/system.decimal)  |  
| `geometry`  | via  
[Microsoft.Spatial](https://www.nuget.org/packages/Microsoft.Spatial)  |  `Geometry`or `Geography`representations  |  
| `range`  | Custom  | [`Range`](https://surrealdb.com/docs/reference/dotnet/data-types#range)  |  
| `file`  | Custom  | [`SurrealFile`](https://surrealdb.com/docs/reference/dotnet/data-types#surrealfile)  |  
| `record`  | Custom  | [`RecordId`](https://surrealdb.com/docs/reference/dotnet/data-types#recordid)  |  
  
  
  

##  `None`[](https://surrealdb.com/docs/reference/dotnet/data-types#none)
The `None` type is a custom type that represents the absence of a value.
Signature

```csharp
public readonly struct None { }
```

###  Working with `None`[](https://surrealdb.com/docs/reference/dotnet/data-types#working-with-none)
Constructing

```csharp
var none = new None();

// Change the value of a record to None
var myRecord = new MyRecord();
myRecord.Value = new None();
```

  

##  `Range`[](https://surrealdb.com/docs/reference/dotnet/data-types#range)
A `Range` represents a bounded or unbounded range of values. Ranges are used in SurrealQL for selecting slices of records by ID or filtering numeric and temporal values.
Signature

```csharp
public readonly struct Range<TStart, TEnd>
{
    public RangeBound<TStart>? Start { get; }

    public RangeBound<TEnd>? End { get; }
}
```

A `RecordIdRange` is a specialization for querying a range of records from a table.
Signature

```csharp
public readonly struct RecordIdRange<TStart, TEnd>
{
    public string Table { get; }

    public Range<TStart, TEnd> Range { get; }
}
```

###  Working with `Range`[](https://surrealdb.com/docs/reference/dotnet/data-types#working-with-range)
Constructing

```csharp
var fullRange = Range.Full(); // Full range (no exclusion)

var startRange = Range.StartFrom<int>(new(1, RangeBoundType.Inclusive)); // Equivalent to 1..

var endRange = Range.EndTo<string>(new("x", RangeBoundType.Exclusive)); // Equivalent to .."x"

var explicitRange = Range.FromRange(2..10); // From C# Range
```

  

##  `SurrealFile`[](https://surrealdb.com/docs/reference/dotnet/data-types#surrealfile)
A `SurrealFile` represents a reference to a file stored in SurrealDB.
Signature

```csharp
public readonly struct SurrealFile
{
    public string Bucket { get; }
    public string Path { get; } = "/";
}
```

###  Working with `SurrealFile`[](https://surrealdb.com/docs/reference/dotnet/data-types#working-with-surrealfile)
Constructing

```csharp
var ref = new SurrealFile("bucket", "/some/key/to/a/file.txt");
```

File references are returned when working with [file uploads](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files) and contain metadata about the stored file.

```csharp
var user = await db.Select(("user", "john"));

Console.WriteLine(user.Avatar.Bucket);
Console.WriteLine(user.Avatar.Path);
```

  

##  `RecordId`[](https://surrealdb.com/docs/reference/dotnet/data-types#recordid)
When you receive a RecordId back from SurrealDB, it will always be represented as a `RecordId`.  
The class holds `Table` and `Id` fields, representing the table name, and a unique identifier for the record on that table.
Signature

```csharp
public class RecordId
{
    public string Table { get; }

    public T DeserializeId<T>();

    // ... The rest is omitted for brevity
}
```

The `RecordId` is a non-generic class, allowing you to extract the `Id` field by providing the output type via the `DeserializeId` method.  
This can helpful when the `RecordId` is used in a generic context, for when you store the `Id` as an Object or an Array for example.
For cases where you are aware of the type of the `Id` field, you can use the generic version of `RecordId` to avoid the need for manual deserialization.
Signature with generics

```csharp
public class RecordIdOf<T> : RecordId
{
    public T Id { get; }
}
```

The default type of an `Id` in SurrealDB being a `string`, you can choose to use the default provided type `RecordIdOfString`.
Default RecordId

```csharp
public class RecordIdOfString : RecordIdOf<string>
{
    // The available properties, inherited from `RecordId` and `RecordIdOf<string>`
    public string Table { get; }
    public string Id { get; }
}
```

###  Working with `RecordId`[](https://surrealdb.com/docs/reference/dotnet/data-types#working-with-recordid)
The simplest and most common way to construct a `RecordId` is with a tuple `(table, id)`.
Constructing

```csharp
// Table is "person"
// Unique identifier on the table is "john"
RecordId personId = ("person", "john");
// or
var personId = (RecordId)("person", "john");
```

This tuple is implicitly converted into a `RecordId` object.  
You can use it with all SDK methods:
Using RecordId

```csharp
await db.Select<Person>(("person", "john"));
await db.Delete(("person", "john"));
```

You are not exclusively limited to the `string` type for the `Id` part. Several overloads exist for different `id` types:
Constructing

```csharp
RecordId rid1 = ("person", "alice");           // string
RecordId rid2 = ("person", 123);               // int
RecordId rid3 = ("person", 123L);              // long
RecordId rid4 = ("person", (short)5);          // short
RecordId rid5 = ("person", (byte)7);           // byte
RecordId rid6 = ("person", Guid.NewGuid());    // Guid
```

###  Extracting data[](https://surrealdb.com/docs/reference/dotnet/data-types#extracting-data)
The .NET SDK handles serialization and deserialization of the `Table` and `Id` parts in Record Id.  
The serialization is done automatically when sending data to the server.  
However, deserialization may need to be done manually according to the data type of the `Id` field.  
Below are some examples:
Simple record id

```csharp
RecordId rid = ("person", "john");
string table = rid.Table; // "person"
string id = rid.DeserializeId<string>(); // "john"
```

Record id with simple data type (other than string)

```csharp
RecordId rid = ("table", 42);
string table = rid.Table; // "table"
int id = rid.DeserializeId<int>(); // 42
```

Record id with complex data types

```csharp
var rid = new RecordIdOf<CityId>("table", new CityId { City = "London" });
var id = rid.DeserializeId<CityId>(); // CityId { City = "London" }

var rid = new RecordIdOf<(string, int)>("table", ("London", 42));
var id = rid.DeserializeId<(string, int)>(); // ("London", 42)
```

###  Send back string[](https://surrealdb.com/docs/reference/dotnet/data-types#send-back-string)
If you need to send back a Record Id in string format, you can do so with the `StringRecordId` class.
We do not implement the parsing of Record Ids in the .NET SDK, as that would mean that we need to be able to parse any SurrealQL value, which comes with a cost.  
Instead you can send it over as a string with `StringRecordId`, allowing the server to handle the parsing.
Signature

```csharp
public class StringRecordId
{
    public string Value { get; }
}
```

###  Working with a `StringRecordId`[](https://surrealdb.com/docs/reference/dotnet/data-types#working-with-a-stringrecordid)
Constructing

```csharp
// Table is "person"
// Unique identifier on the table is "john"
var rid = new StringRecordId("person:john");

// Alternatively, a StringRecordId can be inferred explicitly from a string
var rid = (StringRecordId)"person:john";
await client.Select<Person>((StringRecordId)"person:john");
```

###  Working with `RecordIdOfString`[](https://surrealdb.com/docs/reference/dotnet/data-types#working-with-recordidofstring)
For string-based identifiers, you can also use the specialised type RecordIdOfString:
Using RecordIdOfString

```csharp
var rid = new RecordIdOfString("person", "john");
// or
Console.WriteLine(rid.Table); // "person"
Console.WriteLine(rid.Id);    // "john"
```

###  Working with `RecordIdOf<T>`[](https://surrealdb.com/docs/reference/dotnet/data-types#working-with-recordidoft)
For complex or structured identifiers, use the generic type RecordIdOf\:
Using RecordIdOf<T>

```csharp
public class CityId
{
    public string City { get; set; } = string.Empty;
}

var rid = new RecordIdOf<CityId>("city", new CityId { City = "London" });
```

This enables strongly-typed IDs that map directly to your domain objects.
###  Inheriting from record[](https://surrealdb.com/docs/reference/dotnet/data-types#inheriting-from-record)
If your model class inherits from Record, it will automatically include an Id property of type `RecordId`.
Inheriting from Record

```csharp
public class Person : Record
{
    public string Name { get; set; } = string.Empty;
}

// Example usage
var person = new Person { Name = "Alice" };
Console.WriteLine(person.Id); // RecordId ("person", "…")
```

###  Using data annotations[](https://surrealdb.com/docs/reference/dotnet/data-types#using-data-annotations)
The SDK supports attributes for serialization and deserialization.
####  CBOR serialization[](https://surrealdb.com/docs/reference/dotnet/data-types#cbor-serialization)
Use [CborProperty](https://github.com/dahomey-technologies/Dahomey.Cbor) to map C# properties to SurrealDB fields:
Using CborProperty

```csharp
[CborProperty("first_name")]
public string FirstName { get; set; } = string.Empty;
```

####  RecordIdJsonConverter[](https://surrealdb.com/docs/reference/dotnet/data-types#recordidjsonconverter)
Use RecordIdJsonConverter to indicate that a property should be serialised as a RecordId reference to another table:
Using RecordIdJsonConverter

```csharp
[RecordIdJsonConverter("payment_details")]
public RecordId? PaymentDetails { get; set; }

[RecordIdJsonConverter("payment_details")]
public RecordId? PaymentDetails { get; set; }
```

####  Combining attributes[](https://surrealdb.com/docs/reference/dotnet/data-types#combining-attributes)
You can combine both attributes on the same property:
Combining attributes

```csharp
[CborProperty("payment_details")]
[RecordIdJsonConverter("payment_details")]
public RecordId? PaymentDetails { get; set; }
```
