---
title: "https://surrealdb.com/docs/reference/java/api/values/value"
url: "https://surrealdb.com/docs/reference/java/api/values/value"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/java/api/values/value

Source: https://surrealdb.com/docs/reference/java/api/values/value

The `Value` class is the untyped representation of any SurrealDB value. It provides methods to check the underlying type and extract the value as a native Java type or SDK class. You can also convert a `Value` to a Java POJO using `.get(Class)`.
**Source:** [surrealdb.java](https://github.com/surrealdb/surrealdb.java)
* * *
##  Type checking methods[](https://surrealdb.com/docs/reference/java/api/values/value#type-checking)
Each method returns `true` when the `Value` holds the corresponding SurrealDB type.  
| Method  | Returns `true` when  |  
| --- | --- |  
| `isNone()`  | Value is `NONE`  |  
| `isNull()`  | Value is `NULL`  |  
| `isBoolean()`  | Value is a boolean  |  
| `isDouble()`  | Value is a float/double  |  
| `isLong()`  | Value is an integer/long  |  
| `isBigDecimal()`  | Value is a decimal  |  
| `isString()`  | Value is a string  |  
| `isUuid()`  | Value is a UUID  |  
| `isArray()`  | Value is an array  |  
| `isObject()`  | Value is an object  |  
| `isGeometry()`  | Value is a geometry  |  
| `isDateTime()`  | Value is a datetime  |  
| `isDuration()`  | Value is a duration  |  
| `isBytes()`  | Value is binary data  |  
| `isRecordId()`  | Value is a record ID  |  
| `isFile()`  | Value is a file reference  |  
| `isRange()`  | Value is a range  |  
| `isTable()`  | Value is a table name  |  
* * *
##  Getter methods[](https://surrealdb.com/docs/reference/java/api/values/value#getters)
Each getter extracts the underlying value. Call the corresponding type check method first to avoid unexpected results.  
| Method  | Return Type  |  
| --- | --- |  
| `getBoolean()`  | `boolean`  |  
| `getDouble()`  | `double`  |  
| `getLong()`  | `long`  |  
| `getBigDecimal()`  | `BigDecimal`  |  
| `getString()`  | `String`  |  
| `getUuid()`  | `UUID`  |  
| `getArray()`  | [`Array`](https://surrealdb.com/docs/reference/java/api/values/value#array)  |  
| `getObject()`  | [`Object`](https://surrealdb.com/docs/reference/java/api/values/value#object)  |  
| `getGeometry()`  | [`Geometry`](https://surrealdb.com/docs/reference/java/api/values/geometry)  |  
| `getDateTime()`  | `ZonedDateTime`  |  
| `getDuration()`  | `Duration`  |  
| `getBytes()`  | `byte[]`  |  
| `getRecordId()`  | [`RecordId`](https://surrealdb.com/docs/reference/java/api/values/record-id)  |  
| `getFile()`  | [`FileRef`](https://surrealdb.com/docs/reference/java/api/values/file-ref)  |  
| `getRangeStart()`  | `Optional<Value>`  |  
| `getRangeEnd()`  | `Optional<Value>`  |  
| `getTable()`  | `String`  |  
* * *
##  POJO conversion[](https://surrealdb.com/docs/reference/java/api/values/value#pojo-conversion)
###  `.get(type)`[](https://surrealdb.com/docs/reference/java/api/values/value#get)
Converts the value to a Java POJO. The target class must have a public no-argument constructor. Fields are matched by name between the SurrealDB object and the Java class.
Method Syntax

```java
<T> T get(Class<T> type)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `type`  | `Class<T>`  | The target class to deserialize into.  |  
**Returns:** `T`
Example

```java
public class Person {
    public RecordId id;
    public String name;
    public long age;
}

Response response = db.query("SELECT * FROM person:tobie");
Value value = response.take(0);
Person person = value.get(Person.class);
```

* * *
##  `Array`[](https://surrealdb.com/docs/reference/java/api/values/value#array)
The `Array` class represents a SurrealDB array value. It implements `Iterable` and provides both untyped and typed iteration.
###  Methods[](https://surrealdb.com/docs/reference/java/api/values/value#methods)
####  `.get(idx)`[](https://surrealdb.com/docs/reference/java/api/values/value#array-get)
Returns the value at the specified index.
Method Syntax

```java
array.get(idx)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `idx`  | `int`  | The zero-based index of the element.  |  
**Returns:** `Value`
####  `.len()`[](https://surrealdb.com/docs/reference/java/api/values/value#array-len)
Returns the number of elements in the array.
Method Syntax

```java
array.len()
```

**Returns:** `int`
####  `.iterator()`[](https://surrealdb.com/docs/reference/java/api/values/value#array-iterator)
Returns an iterator over the array elements as `Value` instances.
Method Syntax

```java
array.iterator()
```

**Returns:** `Iterator`
####  `.iterator(clazz)`[](https://surrealdb.com/docs/reference/java/api/values/value#array-typed-iterator)
Returns a typed iterator that deserializes each element into the specified class.
Method Syntax

```java
array.iterator(clazz)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `clazz`  | `Class<T>`  | The class to deserialize each element into.  |  
**Returns:** `Iterator`
####  `.synchronizedIterator()`[](https://surrealdb.com/docs/reference/java/api/values/value#array-sync-iterator)
Returns a thread-safe iterator over the array elements.
Method Syntax

```java
array.synchronizedIterator()
```

**Returns:** `Iterator`
####  `.synchronizedIterator(clazz)`[](https://surrealdb.com/docs/reference/java/api/values/value#array-sync-typed-iterator)
Returns a thread-safe typed iterator that deserializes each element into the specified class.
Method Syntax

```java
array.synchronizedIterator(clazz)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `clazz`  | `Class<T>`  | The class to deserialize each element into.  |  
**Returns:** `Iterator`
Example

```java
Response response = db.query("SELECT * FROM person");
Value result = response.take(0);
Array array = result.getArray();

for (Value item : array) {
    String name = item.getObject().get("name").getString();
}

Iterator<Person> people = array.iterator(Person.class);
while (people.hasNext()) {
    Person person = people.next();
}
```

* * *
##  `Object`[](https://surrealdb.com/docs/reference/java/api/values/value#object)
The `Object` class represents a SurrealDB object value. It implements `Iterable` and provides key-based access to its fields.
###  Methods[](https://surrealdb.com/docs/reference/java/api/values/value#methods-1)
####  `.get(key)`[](https://surrealdb.com/docs/reference/java/api/values/value#object-get)
Returns the value associated with the specified key.
Method Syntax

```java
object.get(key)
```
  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `key`  | `String`  | The field name to look up.  |  
**Returns:** `Value`
####  `.len()`[](https://surrealdb.com/docs/reference/java/api/values/value#object-len)
Returns the number of key-value pairs in the object.
Method Syntax

```java
object.len()
```

**Returns:** `int`
####  `.iterator()`[](https://surrealdb.com/docs/reference/java/api/values/value#object-iterator)
Returns an iterator over the object's key-value pairs as `Entry` instances.
Method Syntax

```java
object.iterator()
```

**Returns:** `Iterator`
####  `.synchronizedIterator()`[](https://surrealdb.com/docs/reference/java/api/values/value#object-sync-iterator)
Returns a thread-safe iterator over the object's key-value pairs.
Method Syntax

```java
object.synchronizedIterator()
```

**Returns:** `Iterator`
Example

```java
Response response = db.query("SELECT * FROM person:tobie");
Value result = response.take(0);
Object obj = result.getObject();

Value name = obj.get("name");
int fieldCount = obj.len();

for (Entry entry : obj) {
    String key = entry.getKey();
    Value value = entry.getValue();
}
```

* * *
##  `Entry`[](https://surrealdb.com/docs/reference/java/api/values/value#entry)
The `Entry` class represents a key-value pair in a SurrealDB object.
###  Methods[](https://surrealdb.com/docs/reference/java/api/values/value#methods-2)
####  `.getKey()`[](https://surrealdb.com/docs/reference/java/api/values/value#entry-key)
Returns the field name of this entry.
Method Syntax

```java
entry.getKey()
```

**Returns:** `String`
####  `.getValue()`[](https://surrealdb.com/docs/reference/java/api/values/value#entry-value)
Returns the value of this entry.
Method Syntax

```java
entry.getValue()
```

**Returns:** `Value`
* * *
##  See also[](https://surrealdb.com/docs/reference/java/api/values/value#see-also)
  * •
[Value types](https://surrealdb.com/docs/reference/java/concepts/value-types) — Type mapping overview
  * •
[RecordId](https://surrealdb.com/docs/reference/java/api/values/record-id) — Record identifiers
  * •
[SurrealQL data model](https://surrealdb.com/docs/reference/query-language/datamodel) — SurrealDB data types and structures
