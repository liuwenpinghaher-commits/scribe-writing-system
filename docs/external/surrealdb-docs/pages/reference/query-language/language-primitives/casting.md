---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/casting"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/casting"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/casting

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/casting

In the SurrealDB type system, values can be converted to other values efficiently. This is useful if input is specified in a query which must be of a certain type, or if a user may have provided a parameter with an incorrect type.  
| Type  | Description  |  
| --- | --- |  
| [`<array>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#array)  | Casts the subsequent value into an array  |  
| [`<array<T>>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#arrayt)  |  Casts the subsequent value into an array of `T`(some indicated type)  |  
| [`<bool>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#bool)  | Casts the subsequent value into a boolean  |  
| [`<datetime>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#datetime)  | Casts the subsequent value into a datetime  |  
| [`<decimal>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#decimal)  | Casts the subsequent value into a decimal  |  
| [`<duration>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#duration)  | Casts the subsequent value into a duration  |  
| [`<float>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#float)  | Casts the subsequent value into a float  |  
| [`<int>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#int)  | Casts the subsequent value into a int  |  
| [`<number>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#number)  | Casts the subsequent value into a decimal  |  
| [`<record>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#record)  | Casts the subsequent value into a record  |  
| [`<record<T>>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#recordt)  |  Casts the subsequent value into a record of `T`(some indicated type)  |  
| [`<set>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#set)  | Casts the subsequent value into a set  |  
| [`<string>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#string)  | Casts the subsequent value into a string  |  
| [`<regex>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#regex)  | Casts the subsequent value into a regular expression  |  
| [`<uuid>`](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#uuid)  | Casts the subsequent value into a UUID  |  
##  `<array>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#array)
The `` casting function converts a range into an array.

```surql
<array>1..=3;
-- Output:
[1, 2, 3]
```

##  `<array<T>>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#arrayt)
The `>` casting function converts a value into an array of the specified type.
Note
When using this casting function, the value must be an array and each element in the array will be cast to the specified type. 

```surql
<array<int>>["42", "314", "271", "137", "141"];
-- Output:
[42, 314, 271, 137, 141]
```

```surql
<array<string>> [42, 314, 271, 137, 141];
-- Output:
['42', '314', '271', '137', '141']
```

A cast into an array of more than one possible type can also be used. In this case, the cast will attempt to cast into the possible types in order. As such, the `string` in the first query below will be cast into a `datetime` but not in the second.

```surql
[
  <array<datetime|string>>["2020-09-09", "21 Jan 2020"],
  <array<string|datetime>>["2020-09-09", "21 Jan 2020"]
];
```

Output

```surql
[
	[
		d'2020-09-09T00:00:00Z',
		'21 Jan 2020'
	],
	[
		'2020-09-09',
		'21 Jan 2020'
	]
]
```

An example of even more complex casting which attempts to cast each item in the input array into a `record`, then `record`, then `array>`, and finally `string`.

```surql
<array<record<user | person> | array<record<user>> | string>> [
	'person:one',
	'user:two',
	[
		'user:three',
		'user:four'
	],
	'not_a_person_or_user'
];
```

Output

```surql
[
	person:one,
	user:two,
	[
		user:three,
		user:four
	],
	'not_a_person_or_user'
]
```

##  `<bool>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#bool)
The `<bool` casting function converts a value into a boolean.

```surql
<bool>"true";
-- Output:
true
```

```surql
<bool>"false";
-- Output:
false
```

##  `<datetime>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#datetime)
The `` casting function converts a value into a datetime.

```surql
<datetime>"2025-06-07";
-- Output:
d'2025-06-07T00:00:00Z'
```

##  `<decimal>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#decimal)
The `` casting function converts a value into a decimal which allows for 128 bits of precision.

```surql
<decimal>"13.5729484672938472938410938456";
-- Output:
13.572948467293847293841093846dec
```

Decimal casting should generally not be used to convert from floats with a large number of digits after the decimal point, because the input to the right will first be turned into a less precise float before the cast is performed.

```surql
<decimal>13.572948467293847293841093845679289;
-- Output:
13.57294846729385dec

<decimal>1.193847193847193847193487E11;
-- Output:
119384719384.7194dec
```

In this case, the `dec` suffix is preferable as it will instruct the database to treat the **input** as a decimal, rather than create a float to then cast into a decimal.

```surql
13.572948467293847293841093845679289dec;
-- Output:
13.572948467293847293841093846dec

1.193847193847193847193487E11dec;
-- Output:
1.193847193847193847193487E11dec;
```

##  `<duration>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#duration)
The `` casting function converts a value into a duration.

```surql
<duration>"1h30m";
-- Output:
1h30m
```

  

##  `<float>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#float)
The `` casting function converts a value into a floating point number. Floating point numbers by nature have a limited amount of precision.

```surql
<float>13.572948467293847293841093845679289;
-- Output:
13.572948467293847f
```

```surql
<float>"13.572948467293847293841093845679289";
-- Output:
13.572948467293847
```

##  `<int>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#int)
The `` casting function converts a value into an integer.

```surql
<int>53;
-- Output:
53
```

##  `<number>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#number)
The `` casting function converts a value into a `number`.

```surql
<number>13.572948467293847293841093845679289;
-- Output:
"13.572948467293847293841093845679289"
```

```surql
<number>"13.572948467293847293841093845679289";
-- Output:
"13.572948467293847293841093845679289"
```

```surql
<number>1.193847193847193847193487E11;
-- Output:
"119384719384.7193847193487"
```

##  `<record>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#record)
The `` casting function converts a value into a record.
Keep in mind when using this casting function that if the equivalent record id does not exist, it will not return anything.

```surql
SELECT id FROM <record>"person:hrebrffwm4sr2yifglta";
```

Output

```surql
{ id: person:hrebrffwm4sr2yifglta }
```

##  `<record<T>>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#recordt)
The `>` casting function converts a value into a record.
Keep in mind when using this casting function that if the equivalent record id does not exist, it will not return anything.

```surql
SELECT id FROM <record>"person:hrebrffwm4sr2yifglta";
-- Output:
{ id: person:hrebrffwm4sr2yifglta }
```

A cast into a number of possible record types can also be used.

```surql
[
  <record<user|person>>"user:one",
  <array<record<user|person>>>["person:one", "user:two"]
];
```

Output

```surql
[
	user:one,
	[
		person:one,
		user:two
	]
]
```

##  `<set>` and `<set<T>>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#set-and-sett)
The `` casting function converts a value into a set.

```surql
[
  <set<datetime|string>>["2020-09-09", "21 Jan 2020"],
  <set<string|datetime>>["2020-09-09", "21 Jan 2020"]
];
```

Output

```surql
[
	[
		d'2020-09-09T00:00:00Z',
		'21 Jan 2020'
	],
	[
		'2020-09-09',
		'21 Jan 2020'
	]
]
```

##  `<string>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#string)
The `` casting function converts a value into a string.

```surql
<string>true;
-- Output:
'true'
```

```surql
<string>1.3463;
-- Output:
'1.3463f'
```

```surql
<string>false;
-- Output:
"false"
```

##  `<regex>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#regex)
The `` casting function converts a value into a regular expression.

```surql
<regex> "a|b" = "a";
-- Output:
true
```

```surql
<regex> "a|b" = "c";
-- Output:
false
```

##  `<uuid>`[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#uuid)
The `` casting function converts a value into a UUID.

```surql
SELECT id FROM <uuid> "a8f30d8b-db67-47ec-8b38-ef703e05ad1b";
-- Output:
[ u'a8f30d8b-db67-47ec-8b38-ef703e05ad1b' ]
```

##  General notes on casting[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#general-notes-on-casting)
###  Syntax and order[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#syntax-and-order)
As the parser ignores spaces and new lines, casting syntax can include spaces or new lines as desired.

```surql
-- Surrealist formatted syntax
 <array<bool | string | float>> [
	'9.1',
	'true',
	15h
];

-- Maybe someone's preferred syntax?
<array
        <bool | string | float>
      >
[ '9.1', 'true', 15h ];
```

When more than one cast type is specified, SurrealDB will attempt to convert into the type in the order specified. In the example above, while the input `'9.1'` could have been converted to a float, the type `string` comes first in the cast syntax and thus `'9.1'` remains as a string.
Output

```surql
[
	'9.1',
	true,
	'15h'
]
```

###  Casting vs. affixes[](https://surrealdb.com/docs/reference/query-language/language-primitives/casting#casting-vs-affixes)
SurrealDB uses a number of affixes to force the parser to treat an input as a certain type instead of another. These affixes may seem at first glance to be identical to casts, as the following queries show.

```surql
-- All return a record person:one
r"person:one";
<record>"person:one";
<record<person>>"person:one";
-- Returns a string 'person:one'
'person:one';

-- Both return a decimal 98dec
98dec;
<decimal>98;

-- Returns an int 98
98;
```

However, casts and affixes work in different ways:
  * •
A cast is a way to convert from one type into another.
  * •
An affix is an instruction to the parser to treat an input as a certain type.

These differences become clear when working with input that is less than ideal or does not work with a certain type. For example, floats by nature become imprecise after a certain number of digits.

```surql
[
  8.888,
  8.8888888888888888
];
```

Output

```surql
[
	8.888f,
	8.88888888888889f
]
```

In this case, a `decimal` can be used which will allow a greater number of digits after the decimal point. However, casting the above numbers into a `decimal` will result in the same inaccurate output.

```surql
[
	<decimal>8.888,
	<decimal>8.888888888888888
];
```

Output

```surql
[
	8.888dec,
	8.88888888888889dec
]
```

This is because the parser will first treat the number as a float and then cast it into a `decimal`.
However, using the `dec` suffix will inform the parser that the entire input is to be treated as a `decimal` and it will never pass through a stage in which it is a float.

```surql
[
	8.888dec,
	8.888888888888888dec
];
```

Output

```surql
[
	8.888dec,
	8.888888888888888dec
]
```

Similarly, an attempt to cast a number that is too large for an `int` into a `decimal` will not work, as the parser will first attempt to handle the number on the right before moving on to the cast.

```surql
<decimal>9999999999999999999;
```

Output

```surql
'Failed to parse number: number cannot fit within a 64bit signed integer'
```

However, if the same number is followed by the `dec` suffix, the parser will be aware that the input is meant to be treated as a `decimal` from the outset and the query will succeed.

```surql
9999999999999999999dec;
```
