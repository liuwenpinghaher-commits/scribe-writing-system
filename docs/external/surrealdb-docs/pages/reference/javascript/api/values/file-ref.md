---
title: "https://surrealdb.com/docs/reference/javascript/api/values/file-ref"
url: "https://surrealdb.com/docs/reference/javascript/api/values/file-ref"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/values/file-ref

Source: https://surrealdb.com/docs/reference/javascript/api/values/file-ref

The `FileRef` class represents a reference to a file stored in SurrealDB. File references are returned when querying records that contain [file fields](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files) and provide access to file metadata such as the bucket, key, and media type.
**Import:**

```ts
import { FileRef } from 'surrealdb';
```

**Source:** [value/file-ref.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/value/file-ref.ts)
##  Constructor[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#constructor)

```ts
new FileRef(bucket: string, key: string)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `bucket`  | `string`  | The name of the storage bucket.  |  
| `key`  | `string`  | The unique key identifying the file within the bucket.  |  
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#example)

```ts
const fileRef = new FileRef('avatars', 'profile-photo.png');

await db.create(new RecordId('users', 'john')).content({
    name: 'John',
    avatar: fileRef
});
```

##  Properties[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#properties)
###  `bucket`[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#bucket)
The name of the storage bucket containing the file.
**Type:** `string`
**Example:**

```ts
console.log(fileRef.bucket); // "avatars"
```

###  `key`[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#key)
The unique key identifying the file within its bucket.
**Type:** `string`
**Example:**

```ts
console.log(fileRef.key); // "profile-photo.png"
```

##  Instance methods[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#instance-methods)
###  `.toString()`[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#tostring)
Returns the string representation of the file reference.
Method Syntax

```ts
fileRef.toString()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#returns)
`string` - The file reference as a string
* * *
###  `.toJSON()`[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#tojson)
Serializes the file reference for JSON output.
Method Syntax

```ts
fileRef.toJSON()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#returns-1)
`string` - The JSON-safe representation
* * *
###  `.equals(other)`[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#equals)
Compares this file reference with another for equality.
Method Syntax

```ts
fileRef.equals(other)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#parameters-1)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `other`  | `unknown`  | The value to compare against.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#returns-2)
`boolean` - True if both file references point to the same file
####  Example[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#example-1)

```ts
const ref1 = record1.avatar;
const ref2 = record2.avatar;

if (ref1.equals(ref2)) {
    console.log('Same file');
}
```

##  Examples[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#examples)
###  Reading file references from records[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#reading-file-references-from-records)

```ts
const user = await db.select(new RecordId('users', 'john'));

if (user.avatar instanceof FileRef) {
    console.log('Bucket:', user.avatar.bucket);
    console.log('Key:', user.avatar.key);
}
```

###  Querying records with file fields[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#querying-records-with-file-fields)

```ts
const [records] = await db.query<[{ avatar: FileRef }[]]>(
    'SELECT avatar FROM users WHERE avatar IS NOT NONE'
);

for (const record of records) {
    console.log(record.avatar.key);
}
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/values/file-ref#see-also)
  * •
[Value types](https://surrealdb.com/docs/reference/javascript/concepts/value-types) - Overview of all value types
  * •
[File uploads](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/files) - Working with files in SurrealDB
  * •
[Data types](https://surrealdb.com/docs/reference/javascript/api/values/) - All custom data types
