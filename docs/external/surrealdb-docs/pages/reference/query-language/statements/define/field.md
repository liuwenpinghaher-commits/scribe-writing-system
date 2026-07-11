---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/field"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/field"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/field

Source: https://surrealdb.com/docs/reference/query-language/statements/define/field

The `DEFINE FIELD` statement allows you to instantiate a named field on a table, enabling you to set the field's data type, set a default value, apply assertions to protect data consistency, and set permissions specifying what operations can be performed on the field.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/define/field#requirements)
  * •
You must be authenticated as a root owner or editor, namespace owner or editor, or database owner or editor before you can use the `DEFINE FIELD` statement.
  * •
[You must select your namespace and database](https://surrealdb.com/docs/reference/query-language/statements/use) before you can use the `DEFINE FIELD` statement.

##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/field#statement-syntax)
Regular Field SyntaxComputed Field SyntaxRailroad Diagram (Regular)Railroad Diagram (Computed)
###  Regular fields[](https://surrealdb.com/docs/reference/query-language/statements/define/field#regular-fields)
SurrealQL Syntax

```syntax
DEFINE FIELD [ OVERWRITE | IF NOT EXISTS ] @name ON [ TABLE ] @table
	[ TYPE @type [ FLEXIBLE ] ]
	[ REFERENCE 
		[ ON DELETE REJECT | 
			ON DELETE CASCADE | 
			ON DELETE IGNORE |
			ON DELETE UNSET | 
			ON DELETE THEN @expression ]
	]
	[ DEFAULT [ALWAYS] @expression ]
  [ READONLY ]
	[ VALUE @expression ]
	[ ASSERT @expression ]
	[ PERMISSIONS [ NONE | FULL
		| FOR select @expression
		| FOR create @expression
		| FOR update @expression
	] ]
  [ COMMENT @string ]
```

###  Computed fields[](https://surrealdb.com/docs/reference/query-language/statements/define/field#computed-fields)
Available since: v3.0.0
Note
In versions of SurrealDB before 3.0.0, `COMPUTED` fields were implemented using a data type called a `future`. Please see [the page on futures](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/futures) in this case.
A `COMPUTED` field is one that is not stored but computed every time it is accessed. Such fields have a more limited set of clauses that can be used. Furthermore, a `COMPUTED` field cannot be defined on the `id` field of a record, nor any nested fields (i.e. a field `metadata` can be defined as computed, but not `medatata.can_drive`).
SurrealQL Syntax

```syntax
DEFINE FIELD [ OVERWRITE | IF NOT EXISTS ] @name ON [ TABLE ] @table
	COMPUTED @expression
	[ TYPE @type ]
	[ PERMISSIONS [ NONE | FULL
		| FOR select @expression
		| FOR create @expression
		| FOR update @expression
	] ]
  [ COMMENT @string ]
```

DEFINEFIELDOVERWRITEIFNOTEXISTS@nameONTABLE@tableTYPE@typeFLEXIBLEREFERENCEONDELETEREJECTONDELETECASCADEONDELETEIGNOREONDELETEUNSETONDELETETHEN@expressionDEFAULTALWAYS@expressionREADONLYVALUE@expressionASSERT@expressionPERMISSIONSNONEFULLFORselect@expressionFORcreate@expressionFORupdate@expressionCOMMENT@string
DEFINEFIELDOVERWRITEIFNOTEXISTS@nameONTABLE@tableCOMPUTED@expressionTYPE@typePERMISSIONSNONEFULLFORselect@expressionFORcreate@expressionFORupdate@expressionCOMMENT@string
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/define/field#example-usage)
The following expression shows the simplest way to use the `DEFINE FIELD` statement.

```surql
-- Declare the name of a field.
DEFINE FIELD email ON TABLE user;
```

The fields of an object and the items in an array can be defined individually using the `.` operator for objects, or the indexing operator for arrays.

```surql
-- Define nested object property types
DEFINE FIELD emails.address ON TABLE user TYPE string;
DEFINE FIELD emails.primary ON TABLE user TYPE bool;

-- Define individual fields on an array
DEFINE FIELD metadata[0] ON person TYPE datetime;
DEFINE FIELD metadata[1] ON person TYPE int;
```

Non-unicode fields can be defined and set using backticks where necessary. Be sure that any periods to indicate nested fields are not inside the backticks, as anything enclosed in backticks will be treated as a literal string.

```surql
DEFINE FIELD name.first    ON user TYPE string;
DEFINE FIELD `nómine`.prim ON user TYPE string;
DEFINE FIELD `nómine.prim` ON user TYPE string;

CREATE user:one SET 
	// Nested field
    name.first = "Billy",
	// Also nested
    `nómine`.prim = "Billy",
	// Not nested
    `nómine.prim` = "Billy";
```

As the output shows, the `.` enclosed inside backticks in the last field results in a single non-nested field name that includes the period, while the one immediately preceding it is nested.

```surql
[
	{
		id: user:one,
		name: {
			first: 'Billy'
		},
		"nómine": {
			prim: 'Billy'
		},
		"nómine.prim": 'Billy'
	}
]
```

##  Defining data types[](https://surrealdb.com/docs/reference/query-language/statements/define/field#defining-data-types)
The `DEFINE FIELD` statement allows you to set the data type of a field. For a full list of supported data types, see [Data types](https://surrealdb.com/docs/reference/query-language/datamodel).
When defining nested fields, if both the parent and the nested fields have types defined, those types must agree. Mismatching types are rejected to prevent impossible schema states.
For example, the following will fail:

```surql
DEFINE FIELD OVERWRITE fd ON c TYPE { a: string, b: number };
DEFINE FIELD OVERWRITE fd.* ON c TYPE number;
```

The above will fail with the following error:

```surql
'Cannot set field `fd.*` with type `number` as it mismatched with field `fd` with type `{ a: string, b: number }`'
```

###  Simple data types[](https://surrealdb.com/docs/reference/query-language/statements/define/field#simple-data-types)

```surql
-- Set a field to have the string data type
DEFINE FIELD email ON TABLE user TYPE string;

-- Set a field to have the datetime data type
DEFINE FIELD created ON TABLE user TYPE datetime;

-- Set a field to have the bool data type
DEFINE FIELD locked ON TABLE user TYPE bool;

-- Set a field to have the number data type
DEFINE FIELD login_attempts ON TABLE user TYPE number;
```

A `|` vertical bar can be used to allow a field to be one of a set of types. The following example shows a field that can be a [`UUID`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/uuids) or an [`int`](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/numbers#integer-numbers), perhaps for `user` records that have varying data due to two diffent legacy ID types.

```surql
-- Set a field to have either the uuid or int type
DEFINE FIELD user_id ON TABLE user TYPE uuid|int;
```

###  Array type[](https://surrealdb.com/docs/reference/query-language/statements/define/field#array-type)
You can also set a field to have the array data type. The array data type can be used to store a list of values. You can also set the data type of the array's contents, as well as the required number of items that it must hold.

```surql
-- Set a field to have the array data type
DEFINE FIELD roles ON TABLE user TYPE array<string>;

-- Set a field to have the array data type, equivalent to `array<any>`
DEFINE FIELD posts ON TABLE user TYPE array;

-- Set a field to have the array object data type
DEFINE FIELD emails ON TABLE user TYPE array<object>;

-- Set a field that holds exactly 640 bytes
DEFINE FIELD bytes ON TABLE data TYPE array<int, 640> ASSERT $value.all(|$val| $val IN 0..=255);

-- Field for a block in a game showing the possible distinct directions a character can move next.
-- The array can contain no more than four directions
DEFINE FIELD next_paths ON TABLE block 
  TYPE array<"north" | "east" | "south" | "west"> 
  VALUE $value.distinct() 
  ASSERT $value.len() <= 4;
```

###  Making a field optional[](https://surrealdb.com/docs/reference/query-language/statements/define/field#making-a-field-optional)
You can make a field optional by wrapping the inner type in an `option`, which allows you to store `NONE` values in the field.

```surql
-- A user may enter a biography, but it is not required.
-- By using the option type you also allow for NONE values.
DEFINE FIELD biography ON TABLE user TYPE option<string>;
```

The example below shows how to define a field `user` on a `POST` table. The field is of type [record](/docs/reference/query-language/language-primitives/record-links). This means that the field can store a `record` or `NONE`.

```surql
DEFINE FIELD user ON TABLE post TYPE option<record<user>>;
```

###  Flexible data types[](https://surrealdb.com/docs/reference/query-language/statements/define/field#flexible-data-types)
On a `SCHEMAFULL` table, every `object` is schemafull by default, meaning that only fields you define with nested `DEFINE FIELD` statements are allowed. The `FLEXIBLE` field clause relaxes that rule for a single field. It must appear immediately after `TYPE`, and it applies to **every `object` reachable in that field's type** — including objects inside `array`, `option`, union arms, and object literals.
`FLEXIBLE` is not part of the type expression. Writing `TYPE object FLEXIBLE` declares a field of type `object`, then sets the field's flexible flag. The same applies to `TYPE array FLEXIBLE`: the stored type is `array`, and each object element accepts arbitrary keys.
The field's type must contain at least one `object`. `FLEXIBLE` cannot be used with types such as `any` or `number` that do not include `object`.

```surql
DEFINE TABLE user SCHEMAFULL;
DEFINE FIELD name ON TABLE user TYPE string;
DEFINE FIELD metadata ON TABLE user TYPE object FLEXIBLE;
DEFINE FIELD metadata.user_id ON TABLE user TYPE int;
```

You can still define nested fields such as `metadata.user_id`. Defined subfields keep their types and assertions; `FLEXIBLE` only allows **additional** keys that are not declared in the schema.
Taking the following `CREATE` statement:

```surql
CREATE ONLY user SET
  name = "User1",
  metadata = {
      user_id: 8876687,
      country_code: "ee",
      time_zone: "EEST",
      age: 25
};
```

Without `FLEXIBLE`, the `metadata` field is a schemafull object and only declared subfields such as `metadata.user_id` are accepted.
In versions of SurrealDB before 3.0, the result of the above statement was a record in which the `metadata` field was only able to populate the `user_id` field.

```surql
{
	id: user:ke8w4u38gbm3ofp2u8fb,
	metadata: {
		user_id: 8876687
	},
  name: "User1"
}
```

As of version 3.0, the statement now returns an error upon finding the first field that was not defined in the schema.

```surql
"Found field 'metadata.age', but no such field exists for table 'user'"
```

With `FLEXIBLE`, the field accepts any extra keys on `metadata` while still requiring `name` and a valid `metadata.user_id`.
Response

```surql
{
	id: user:lsdk473e279oik1k484b,
	metadata: {
		age: 25,
		country_code: 'ee',
		time_zone: 'EEST',
		user_id: 8876687
	},
	name: 'User1'
}
```

The same field clause works when objects are nested inside other types. For example, `TYPE array FLEXIBLE` makes every object in the array schemaless, while nested `DEFINE FIELD` paths such as `items.*.num` still type-check declared subfields:

```surql
DEFINE TABLE test SCHEMAFULL;
DEFINE FIELD items ON test TYPE array<object> FLEXIBLE;
DEFINE FIELD items.*.num ON test TYPE number;

CREATE test:1 SET items = [{ num: 1 }];
CREATE test:2 SET items = [{ num: 2, extra: 'allowed' }];
-- Fails: 'extra' is allowed but 'num' must be a number, not a string
CREATE test:3 SET items = [{ num: '3', extra: 'allowed' }];
```

###  Using the `DEFAULT` clause to set a default value[](https://surrealdb.com/docs/reference/query-language/statements/define/field#using-the-default-clause-to-set-a-default-value)
You can set a default value for a field using the `DEFAULT` clause. The default value will be used if no value is provided for the field.

```surql
-- A user is not locked by default.
DEFINE FIELD locked ON TABLE user TYPE bool
-- Set a default value if empty
  DEFAULT false;
```

###  Using the `DEFAULT` and `ALWAYS` clauses[](https://surrealdb.com/docs/reference/query-language/statements/define/field#using-the-default-and-always-clauses)
Available since: v2.2.0
`DEFAULT ALWAYS` applies a default on `CREATE` and on `UPDATE` when the value is `NONE`. The `ALWAYS` keyword distinguishes this from plain `DEFAULT`, which only runs on `CREATE`.

```surql
DEFINE TABLE product SCHEMAFULL;
-- Set a default value of 123.456 for the primary field
DEFINE FIELD primary ON product TYPE number DEFAULT ALWAYS 123.456;
```

With the above definition, the `primary` field will be set to `123.456` when a new `product` is created without a value for the `primary` field or with a value of `NONE`, and when an existing `product` is updated if the value is specified the result will be the new value.
In the case of `NULL` or a mismatching type, an error will be returned.

```surql
-- This will return an error
CREATE product:test SET primary = NULL;

-- result 
"Couldn't coerce value for field `primary` of `product:test`: Expected `number` but found `NULL`"
```

On the other hand, if a valid number is provided during creation or update, that number will be used instead of the default value. In this case, `123.456`.

```surql
-- This will set the value of the `primary` field to `123.456`
CREATE product:test;

-- This will set the value of the `primary` field to `463.456`
UPSERT product:test SET primary = 463.456;

-- This will set the value of the `primary` field to `123.456`
UPSERT product:test SET primary = NONE;

```

Query

```surql
DEFINE TABLE post SCHEMAFULL;
DEFINE FIELD tags ON post TYPE array<object> DEFAULT ALWAYS [];
DEFINE FIELD tags.*.color ON post TYPE string DEFAULT ALWAYS 'red';
DEFINE FIELD tags.*.name ON post TYPE string;
--
CREATE post:test;
UPSERT post:test SET tags += { name: 'test' };
UPSERT post:test SET tags += { name: 'test', color: 'blue' };
```

Response

```surql
[{ id: post:test, tags: [] }]

[{ id: post:test, tags: [{ color: 'red', name: 'test' }] }]

[{ id: post:test, tags: [{ color: 'red', name: 'test' }, { color: 'blue', name: 'test' }] }]
```

###  Using the `VALUE` clause to set a field's value[](https://surrealdb.com/docs/reference/query-language/statements/define/field#using-the-value-clause-to-set-a-fields-value)
The `VALUE` clause differs from `DEFAULT` in that a default value is calculated if no other is indicated, otherwise accepting the value given in a query.

```surql
DEFINE FIELD updated ON TABLE user DEFAULT time::now();

-- Set `updated` to the year 1900
CREATE user SET updated = d"1900-01-01";
-- Then set to the year 1910
UPDATE user SET updated = d"1910-01-01";
```

A `VALUE` clause, on the other hand, will ignore attempts to set the field to any other value.

```surql
DEFINE FIELD updated ON TABLE user VALUE time::now();

-- Ignores 1900 date, sets `updated` to current time
CREATE user SET updated = d"1900-01-01";
-- Ignores again, updates to current time
UPDATE user SET updated = d"1900-01-01";
```

As the example above shows, a `VALUE` clause sets the value every time a record is modified (created or updated). However, the value will not be recalculated in a `SELECT` statement, which simply accesses the current set value.

```surql
DEFINE FIELD updated ON TABLE user VALUE time::now();

CREATE user:one;
SELECT * FROM ONLY user:one;
-- Sleep for one second
SLEEP 1s;
-- `updated` is still the same
SELECT * FROM ONLY user:one;
```

To create a field that is calculated each time it is accessed, a [`computed field`](https://surrealdb.com/docs/reference/query-language/statements/define/field#computed-fields) can be used.

```surql
DEFINE FIELD accessed_at ON TABLE user COMPUTED time::now();

CREATE user:one;
SELECT * FROM ONLY user:one;
-- Sleep for one second
SLEEP 1s;
-- `accessed_at` is a different value now
SELECT * FROM ONLY user:one;
```

###  Altering a passed value[](https://surrealdb.com/docs/reference/query-language/statements/define/field#altering-a-passed-value)
You can alter a passed value using the `VALUE` clause. This is useful for altering the value of a field before it is stored in the database.
In the example below, the `VALUE` clause is used to ensure that the email address is always stored in lowercase characters by using the [`string::lowercase`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/string#stringlowercase) function.

```surql
-- Ensure that an email address is always stored in lowercase characters
DEFINE FIELD email ON TABLE user TYPE string
  VALUE string::lowercase($value);
```

##  Asserting rules on fields[](https://surrealdb.com/docs/reference/query-language/statements/define/field#asserting-rules-on-fields)
You can take your field definitions even further by using asserts. Assert can be used to ensure that your data remains consistent. For example you can use asserts to ensure that a field is always a valid email address, or that a number is always positive.

```surql
-- Give the user table an email field. Store it in a string
DEFINE FIELD email ON TABLE user TYPE string
  -- Check if the value is a properly formatted email address
  ASSERT string::is_email($value);
```

As the `ASSERT` clause expects an expression that returns a boolean, an assertion with a custom message can be manually created by returning `true` in one case and using a [`THROW`](https://surrealdb.com/docs/reference/query-language/statements/throw) clause otherwise.

```surql
DEFINE FIELD num ON data TYPE int ASSERT {
    IF $input % 2 = 0 {
        RETURN true
    } ELSE {
        THROW "Tried to make a " + <string>$this + " but `num` field requires an even number"
    }
};

CREATE data:one SET num = 11;
```

Error output

```surql
'An error occurred: Tried to make a { id: data:one, num: 11 } but `num` field requires an even number'
```

###  Making a field `READONLY`[](https://surrealdb.com/docs/reference/query-language/statements/define/field#making-a-field-readonly)
The `READONLY` clause can be used to prevent any updates to a field. This is useful for fields that are automatically updated by the system. To make a field `READONLY`, add the `READONLY` clause to the `DEFINE FIELD` statement. As seen in the example below, the `created` field is set to `READONLY`.

```surql
DEFINE FIELD created ON resource VALUE time::now() READONLY;
```

##  Using `IF NOT EXISTS` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/field#using-if-not-exists-clause)
The `IF NOT EXISTS` clause can be used to define a field only if it does not already exist. You should use the `IF NOT EXISTS` clause when defining a field in SurrealDB if you want to ensure that the field is only created if it does not already exist. If the field already exists, the `DEFINE FIELD` statement will return an error.
It's particularly useful when you want to safely attempt to define a field without manually checking its existence first.
On the other hand, you should not use the `IF NOT EXISTS` clause when you want to ensure that the field definition is updated regardless of whether it already exists. In such cases, you might prefer using the `OVERWRITE` clause, which allows you to define a field and overwrite an existing one if it already exists, ensuring that the latest version of the definition is always in use

```surql
-- Create a field if it does not already exist
DEFINE FIELD IF NOT EXISTS email ON TABLE user TYPE string;
```

##  Using `OVERWRITE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/field#using-overwrite-clause)
The `OVERWRITE` clause can be used to define a field and overwrite an existing one if it already exists. You should use the `OVERWRITE` clause when you want to modify an existing field definition. If the field already exists, the `DEFINE FIELD` statement will overwrite the existing definition with the new one.

```surql
-- Overwrite the current field definition if it already exists
DEFINE FIELD OVERWRITE example ON TABLE user TYPE string;
```

##  Setting permissions on fields[](https://surrealdb.com/docs/reference/query-language/statements/define/field#setting-permissions-on-fields)
By default, the permissions on a field will be set to FULL unless otherwise specified.

```surql
DEFINE FIELD some_info ON TABLE some_table TYPE string;
INFO FOR TABLE some_table;
```

Response

```surql
{
	events: {},
	fields: {
		info: 'DEFINE FIELD info ON some_table TYPE string PERMISSIONS FULL'
	},
	indexes: {},
	lives: {},
	tables: {}
}
```

You can set permissions on fields to control who can perform operations on them using the `PERMISSIONS` clause. The `PERMISSIONS` clause can be used to set permissions for `SELECT`, `CREATE`, and `UPDATE` operations. The `DELETE` operation only relates to records and, as such, is not available for fields.

```surql
-- Set permissions for the email field
DEFINE FIELD email ON TABLE user
  PERMISSIONS
    FOR select WHERE published=true OR user=$auth.id
    FOR update WHERE user=$auth.id OR $auth.role="admin";
```

##  Array with allowed values[](https://surrealdb.com/docs/reference/query-language/statements/define/field#array-with-allowed-values)
By using an Access Control List as an example we can show how we can restrict what values can be stored in an array. In this example we are using an array to store the permissions for a user on a resource. The permissions are restricted to a specific set of values.

```surql
-- An ACL can be applied to any kind of resource (record)
DEFINE FIELD resource ON TABLE acl TYPE record;
-- We associate the acl with a user using record<user>
DEFINE FIELD user ON TABLE acl TYPE record<user>;

-- The permissions for the user+resource will be stored in an array.
DEFINE FIELD permissions ON TABLE acl TYPE array
  -- The array must not be empty because at least one permission is required to make a valid ACL
  -- The items in the array must also be restricted to specific permissions
  ASSERT
      array::len($value) > 0
      AND $value ALLINSIDE ["create", "read", "write", "delete"];

-- SEE IT IN ACTION
-- 1: Add users
CREATE user:tobie SET firstName = 'Tobie', lastName = 'Hitchcock',
  email = 'Tobie.Hitchcock@surrealdb.com';
CREATE user:abc SET firstName = 'A', lastName = 'B',
  email = 'c@d.com';
CREATE user:efg SET firstName = 'E', lastName = 'F',
  email = 'g@h.com';

-- 2: Create a resource
CREATE document:SurrealDB_whitepaper SET
  name = "some messaging queue";

-- 3: Associate with ACL
CREATE acl SET user = user:tobie, resource = document:SurrealDB_whitepaper, permissions = ["create", "write", "read"];
CREATE acl SET user = user:abc, resource = document:SurrealDB_whitepaper, permissions = ["read", "delete"];

-- Test Asserts using failure examples
-- A: Create ACL without permissions field
CREATE acl:invalid SET
  user = user:efg,
  permissions = [], # FAIL - permissions must not be empty
  resource = document:SurrealDB_whitepaper;
-- B: Create acl with invalid permisson
CREATE acl:also_invalid SET
  user = user:efg,
  permissions = ["all"], # FAIL - This value is not allowed in the array
  resource = document:SurrealDB_whitepaper;
```

##  Using regex to validate a string[](https://surrealdb.com/docs/reference/query-language/statements/define/field#using-regex-to-validate-a-string)
You can use the `ASSERT` clause to apply a regular expression to a field to ensure that it matches a specific pattern. In the example below, the `ASSERT` clause is used to ensure that the `countrycode` field is always a valid ISO-3166 country code.

```surql
-- Specify a field on the user table
DEFINE FIELD countrycode ON user TYPE string
	-- Ensure country code is ISO-3166
	ASSERT $value = /[A-Z]{3}/
	-- Set a default value if empty
	VALUE $value OR $before OR 'GBR'
;
```

##  Interacting with other fields of the same record[](https://surrealdb.com/docs/reference/query-language/statements/define/field#interacting-with-other-fields-of-the-same-record)
While a `DEFINE TABLE` statement represents a template for any subsequent records to be created, a `DEFINE FIELD` statement pertains to concrete field data of a record. As such, a `DEFINE FIELD` statement gives access to the record's other fields through their names, as well as the current field through the [`$value`](https://surrealdb.com/docs/reference/query-language/language-primitives/parameters#value) parameter.

```surql
DEFINE TABLE person SCHEMAFULL;

DEFINE FIELD first_name
  ON TABLE person TYPE string VALUE string::lowercase($value);
DEFINE FIELD last_name 
  ON TABLE person TYPE string VALUE string::lowercase($value);
DEFINE FIELD name      
  ON TABLE person             VALUE first_name + ' ' + last_name;

// Creates a `person` with the name "bob bobson"
CREATE person SET first_name = "BOB", last_name = "BOBSON";
```

The `$this` parameter gives access to the entire record on which a field is defined.

```surql
DEFINE FIELD extra_self ON TABLE person VALUE $this;
CREATE person:one SET name = "Little person", age = 6;
```

Output

```surql
[
	{
		age: 6,
		extra_self: {
			age: 6,
			id: person:one,
			name: 'Little person'
		},
		id: person:one,
		name: 'Little person'
	}
]
```

##  Order of operations when setting a field's value[](https://surrealdb.com/docs/reference/query-language/statements/define/field#order-of-operations-when-setting-a-fields-value)
As `DEFINE FIELD` statements are computed in alphabetical order, be sure to keep this in mind when using fields that rely on the values of others.
The following example is identical to the above except that `full_name` has been chosen for the previous field `name`. The `full_name` field will be calculated after `first_name`, but before `last_name`.

```surql
DEFINE TABLE person SCHEMAFULL;

DEFINE FIELD first_name
  ON TABLE person TYPE string VALUE string::lowercase($value);
DEFINE FIELD last_name 
  ON TABLE person TYPE string VALUE string::lowercase($value);
DEFINE FIELD full_name 
  ON TABLE person             VALUE first_name + ' ' + last_name;

// Creates a `person` with `full_name` of "bob BOBSON", not "bob bobson"
CREATE person SET first_name = "Bob", last_name = "BOBSON";
```

A good rule of thumb is to organise your `DEFINE FIELD` statements in alphabetical order so that the field definitions show up in the same order as that in which they are computed.
##  Defining a literal on a field[](https://surrealdb.com/docs/reference/query-language/statements/define/field#defining-a-literal-on-a-field)
A field can also be defined as a [literal type](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/literals), by specifying one or more possible values and/or permitted types.

```surql
DEFINE FIELD coffee
  ON TABLE order TYPE "regular" | "large" | { special_order: string };

CREATE order:good SET coffee = { special_order: "Venti Quadruple Ristretto Half-Decaf Soy Latte with 4 pumps of sugar-free vanilla syrup" };
CREATE order:bad SET coffee = "small";
```

Response

```surql
-------- Query --------

[
	{
		coffee: {
			special_order: 'Venti Quadruple Ristretto Half-Decaf Soy Latte with 4 pumps of sugar-free vanilla syrup'
		},
		id: order:good
	}
]

-------- Query --------
"Found 'small' for field `coffee`, with record `order:bad`, but expected a 'regular' | 'large' | { special_order: string }"
```

One more example of a literal containing settings for a [full text search](https://surrealdb.com/docs/learn/data-models/full-text-search/overview) filter:

```surql
DEFINE FIELD filter ON TABLE search_settings TYPE
      "None"
    | { type: "Ascii" }
    | { type: "EdgeNgram", from: int, to: int }
    | { type: "Lowercase" }
    | { type: "Ngram", from: int, to: int }
    | { type: "Snowball", language: string }
    | { type: "Uppercase" };
```

##  Defining a `TYPE` for the `id` field[](https://surrealdb.com/docs/reference/query-language/statements/define/field#defining-a-type-for-the-id-field)
The `DEFINE FIELD` statement can be defined for the `id` field to specify the acceptable type of ID.

```surql
DEFINE FIELD id ON TABLE something TYPE string;
DEFINE FIELD id ON TABLE something TYPE int;
DEFINE FIELD id ON TABLE something TYPE uuid;
```

Complex IDs can be specified as well.

```surql
-- using multiple data types for a Complex Record ID
DEFINE FIELD id
  ON TABLE log TYPE [record, "info" | "warn" | "error", datetime];

-- Incorrect ID format, generates an error
CREATE log:bad SET level = "info", time = time::now(), message = "Database started";

-- Acceptable ID format
CREATE log:[user:one, "info", time::now()] SET message = "Database started";
```

###  `ASSERT` and `DEFAULT` on `id`[](https://surrealdb.com/docs/reference/query-language/statements/define/field#assert-and-default-on-id)
Available since: v3.2.0
`ASSERT` on the `id` field is evaluated like any other field assertion. Inside the assertion, `$value` is the whole record id; use `id.id()` (or `record::id($value)`) to inspect the key portion. Assertions run on create for generated, default-supplied, and explicitly supplied ids, and are skipped on update and under `OPTION IMPORT`.
`DEFAULT` supplies the record id when none is given in `CREATE` or `INSERT`, evaluated in the session context and coerced to the declared type. An explicit id in the statement always wins. `DEFAULT ALWAYS` is not allowed on `id`.

```surql
DEFINE FIELD id ON user TYPE string DEFAULT rand::ulid() ASSERT id.id().is_ulid();
CREATE user SET name = 'Ada';
```

`VALUE`, `REFERENCE`, `COMPUTED`, `READONLY`, `FLEXIBLE`, and non-key `TYPE` clauses are forbidden on `id`, a restriction which apple to [`ALTER FIELD`](https://surrealdb.com/docs/reference/query-language/statements/alter/field) statements as well.
Output

```surql
-------- Query --------

"Couldn't coerce value for field `id` of `log:bad`: Expected `[record, 'info' | 'warn' | 'error', datetime]` but found `'bad'`"

-------- Query --------

[
	{
		id: log:[
			user:one,
			'info',
			d'2025-03-25T03:36:16.323Z'
		],
		message: 'Database started'
	}
]
```

##  Defining a reference[](https://surrealdb.com/docs/reference/query-language/statements/define/field#defining-a-reference)
Available since: v2.2.0
A field that is a record link (type `record`, `option`, `array>`, and so on) can be defined as a `REFERENCE`. If this clause is used, any linked to record will be able to define a field of its own of type `references` which will be aware of the incoming links.
For more information, see [the page in the datamodel section on references](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/references).
