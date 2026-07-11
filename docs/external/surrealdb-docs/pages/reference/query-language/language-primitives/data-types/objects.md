---
title: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects"
url: "https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects

Source: https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects

An object is a collection of named fields and values.
As a record is essentially an object with a required [`id` field](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/record-ids) that can be created, updated, or deleted, they can be worked with in almost exactly the same way as a standalone object.
A field of an object can be of any value type, including another object or array at multiple levels of depth. This allows objects and arrays to be stored within each other in order to model complex data scenarios.

```surql
CREATE person SET metadata = {
	interest_level: 83.67,
	information: {
		age: 23,
		gender: 'm',
	},
	marketing: true,
	activities: [
		"clicked link",
		"contact form",
		"read email",
		"viewed website",
		"viewed website",
		"viewed website",
		"read email",
	]
};
```

##  Field names[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects#field-names)
###  Valid field names[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects#valid-field-names)
Similar to record IDs, field names can be constructed from ASCII characters, underscores, and numbers. To create a field name with complex characters, backticks can be used.
When you combine backticks with dotted paths for nested fields, keep any periods used to denote a nested path **outside** the backticks. Anything inside backticks is treated as a single literal field name, including a `.` inside the backticks. For definitions and concrete examples (including non-ASCII identifiers), see [`DEFINE FIELD`](https://surrealdb.com/docs/reference/query-language/statements/define/field#example-usage).

```surql
CREATE ONLY user SET my_name = 'name';
CREATE ONLY user SET `mi_nómine😊` = 'name';
```

Output

```surql
-------- Query --------

{
	id: user:nronupvxvdm7r1n5hlzm,
	my_name: 'name'
}

-------- Query 2 --------

{
	id: user:eb5pu7u9g67dy773hsv9,
	"mi_nómine😊": 'name'
}
```

Inside a standalone object, non-ASCII field names can also be set by using a string.

```surql
SELECT * FROM ONLY {
    "mi nómine": "Edgar"
};
```

Output

```surql
{
	"mi nómine": 'Edgar'
}
```

###  Automatically generated field names[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects#automatically-generated-field-names)
A field created from an operation will have a field name that represents the operation(s) used to construct it.

```surql
SELECT
    math::mean(temps),
    [ math::min(temps), math::max(temps) ]
FROM { temps: [-5, 8, 9] };
```

Output

```surql
[
    {
        "[math::min(temps), math::max(temps)]": [
            -5,
            9
        ],
        "math::mean": 4f
    }
]
```

Using `AS` allows these automatically calculated field names to be replaced with custom names.

```surql
SELECT
    math::mean(temps) AS mean_temps,
    [ math::min(temps), math::max(temps) ] AS avg_temps
FROM { temps: [-5, 8, 9] };
```

Output

```surql
[
    {
        "avg_temps": [
            -5,
            9
        ],
        "mean_temps": 4
    }
]
```

##  Extending objects and removing fields[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects#extending-objects-and-removing-fields)
Available since: v3.0.0
Two objects can be merged by using either the `+` operator or the `object::extend()` function. Any fields in the second object will be added to the first object, thereby updating any existing fields and adding new fields to those that were not present.

```surql
{ name: "Venus", radius: 6000 } + { radius: 6051.8, orbital_period: 1y31w1d22h };
{ name: "Venus", radius: 6000 }.extend({ radius: 6051.8, orbital_period: 1y31w1d22h });
```

Output

```surql
-------- Query 1 --------

{
	name: 'Venus',
	orbital_period: 1y31w1d22h,
	radius: 6051.8f
}

-------- Query 2 --------

{
	name: 'Venus',
	orbital_period: 1y31w1d22h,
	radius: 6051.8f
}
```

Fields of an object can be removed with the `object::remove()` function, which takes either a single string or an array of strings of the field names to remove.

```surql
{ name: 'Venus', orbital_period: 1y31w1d22h, radius: 6051.8 }.remove("radius");
{ name: 'Venus', orbital_period: 1y31w1d22h, radius: 6051.8 }.remove(["radius", "orbital_period"]);
```

Output

```surql
-------- Query 1 --------

{
	name: 'Venus',
	orbital_period: 1y31w1d22h
}

-------- Query 2 --------

{
	name: 'Venus'
}
```

##  See also[](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/objects#see-also)
  * •
[Object functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/object)
  * •
[Destructuring nested objects](https://surrealdb.com/docs/reference/query-language/language-primitives/idioms#destructuring)
