---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding

These functions can be used to encode and decode data into other formats, such as `base64` and [`CBOR`](https://surrealdb.com/docs/reference/rest-api/cbor-protocol) (Concise Binary Object Representation). It is particularly used when that data needs to be stored and transferred over media that are designed to deal with text. This encoding and decoding helps to ensure that the data remains intact without modification during transport.
Tip
For an overview of serialisation, parsing, analysis, and other representation transformations, see [Representations and codecs](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs).  
| Function  | Description  |  
| --- | --- |  
| [`encoding::base64::decode()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingbase64decode)  | Decodes a base64-encoded string into bytes.  |  
| [`encoding::base64::encode()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingbase64encode)  | Encodes bytes into a base64 string, with optional padding.  |  
| [`encoding::cbor::decode()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingcbordecode)  | Decodes CBOR-formatted bytes into a SurrealQL value.  |  
| [`encoding::cbor::encode()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingcborencode)  | Encodes a SurrealQL value into CBOR-formatted bytes.  |  
| [`encoding::json::decode()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingjsondecode)  | Decodes a JSON string into a SurrealQL value.  |  
| [`encoding::json::encode()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingjsonencode)  | Encodes a SurrealQL value into a JSON string.  |  
  

##  `encoding::base64::decode()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingbase64decode)
The `encoding::base64::decode()` function decodes a string into bytes.
API DEFINITION

```surql
encoding::base64::decode(string) -> bytes
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN encoding::base64::decode("MjMyMw");

-- b"32333233"
```

You can also verify that the output of the encoded value matches the original value. 

```surql
RETURN encoding::base64::decode("aGVsbG8") = <bytes>"hello";

-- true
```

  
  

##  `encoding::base64::encode()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingbase64encode)
The `encoding::base64::encode()` function encodes a bytes to base64 with optionally padded output.
API DEFINITION (before 2.3.0)API DEFINITION (after 2.3.0)

```surql
encoding::base64::encode(bytes) -> string
```

```surql
encoding::base64::encode(bytes, $pad_output: option<bool>) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN encoding::base64::encode(<bytes>"");

-- ''
```

```surql
RETURN encoding::base64::encode(<bytes>"2323");

-- 'MjMyMw'
```

```surql
RETURN encoding::base64::encode(<bytes>"hello");

-- 'aGVsbG8'
```

You can pass `true` as the second argument to enable padded base64 outputs:

```surql
RETURN encoding::base64::encode(<bytes>"", true);

-- ""
```

```surql
RETURN encoding::base64::encode(<bytes>"2323", true);

"MjMyMw=="
```

```surql
RETURN encoding::base64::encode(<bytes>"hello", true);

"aGVsbG8="
```

  

##  `encoding::cbor::decode()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingcbordecode)
Available since: v3.0.0
The `encoding::cbor::decode()` function decodes bytes in valid CBOR format into a SurrealQL value.
API DEFINITION

```surql
encoding::cbor::decode(string) -> any
```

```surql
LET $some_bytes = encoding::base64::decode("omRjYm9yaGVuY29kaW5nYmlza3ByZXR0eSBuZWF0");
encoding::cbor::decode($some_bytes);
```

Output

```surql
{
	cbor: 'encoding',
	is: 'pretty neat'
}
```

  
  

##  `encoding::cbor::encode()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingcborencode)
Available since: v3.0.0
The `encoding::cbor::encode()` function encodes any SurrealQL value into bytes in CBOR format.
API DEFINITION

```surql
encoding::cbor::encode(any) -> bytes
```

```surql
encoding::cbor::encode({
    cbor: "encoding",
    is: "pretty neat"
});
```

Output

```surql
b"A26463626F7268656E636F64696E676269736B707265747479206E656174"
```

##  `encoding::json::decode()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingjsondecode)
Available since: v3.1.0
The `encoding::json::decode()` function decodes a JSON string into a SurrealQL value.
API DEFINITION

```surql
encoding::json::decode(string) -> any
```

Examples of use:

```surql
encoding::json::decode('NONE');

LET $json = '{"user":{"name":"Tobie","tags":["admin","user"]}}';
encoding::json::decode($json);
```

Output

```surql
-------- Query --------
NONE

-------- Query --------
{
	user: {
		name: 'Tobie',
		tags: [
			'admin',
			'user'
		]
	}
}
```

##  `encoding::json::encode()`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingjsonencode)
Available since: v3.1.0
The `encoding::json::encode()` function encodes a SurrealQL value into a JSON string.
API DEFINITION

```surql
encoding::json::encode(any) -> string
```

Examples of use:

```surql
encoding::json::encode("8.8");

encoding::json::encode({ some: "data"});
```

Output

```surql
-------- Query --------
'"8.8"'

-------- Query --------
'{"some":"data"}'
```

As JSON has fewer data types than SurrealDB, note that a round trip from SurrealQL to JSON and back to SurrealQL is not guaranteed to be the same type.

```surql
encoding::json::decode(encoding::json::encode(NONE));
-- NULL
```

If a round trip is required, a combination of JSON and CBOR functions can be used.

```surql
-- Value is '[198,246]'
-- (array from CBOR byte representation of NONE)
LET $json_byte_array = encoding::json::encode(
    <array>encoding::cbor::encode(NONE)
);

-- Value is b"C6F6"
-- (CBOR byte representation of NONE)
LET $byte_string = <bytes>encoding::json::decode($json_byte_array);

-- Returns NONE, not NULL
encoding::cbor::decode($byte_string);
```

##  See also[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#see-also)
  * •
[Representations and codecs](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs)
  * •
[CBOR protocol](https://surrealdb.com/docs/reference/rest-api/cbor-protocol)
