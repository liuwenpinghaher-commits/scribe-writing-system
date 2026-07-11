---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/set"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/set"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/set

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/set

Available since: v3.0.0
#  Set functions[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#set-functions)
These functions can be used when working with, and manipulating sets of data.  
| Function  | Description  |  
| --- | --- |  
| [`set::add()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setadd)  | Adds an item to a set if it does not exist  |  
| [`set::all()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setall)  | Checks if all elements in a set match a condition  |  
| [`set::any()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setany)  | Checks if any elements in a set match a condition  |  
| [`set::at()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setat)  | Accesses the element at a specific position in a set  |  
| [`set::complement()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setcomplement)  | Returns the complement of two sets  |  
| [`set::contains()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setcontains)  | Checks to see if a value is present in a set  |  
| [`set::difference()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setdifference)  | Returns the difference between two sets  |  
| [`set::filter()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfilter)  | Filters elements in a set that match a condition  |  
| [`set::find()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfind)  | Finds the first element in a set that matches a condition  |  
| [`set::find()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfirst)  | Gets the first element in a set  |  
| [`set::flatten()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setflatten)  | Flattens nested sets and arrays into a single set  |  
| [`set::fold()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfold)  | Folds over a set with an accumulator  |  
| [`set::intersect()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setintersect)  | Returns the values which intersect two sets  |  
| [`set::is_empty()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setis_empty)  | Checks if a set is empty  |  
| [`set::join()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setjoin)  | Joins set elements into a string with a separator  |  
| [`set::last()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setlast)  | Gets the last element in a set  |  
| [`set::len()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setlen)  | Returns the length of a set  |  
| [`set::map()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setmap)  | Maps over the elements of a set to return a new set  |  
| [`set::max()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setmax)  | Returns the greatest value from a set  |  
| [`set::min()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setmin)  | Returns the least value from a set  |  
| [`set::reduce()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setreduce)  | Reduces a set via a closure  |  
| [`set::remove()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setremove)  | Removes an item at a specific position from a set  |  
| [`set::slice()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setslice)  | Removes an item at a specific position from a set  |  
| [`set::union()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setunion)  | Returns the unique merged values from two sets  |  
##  `set::add`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setadd)
The `set::add` function adds an item to a set only if it does not already exist.
API DEFINITION

```surql
set::add(set, $new_val: value) -> set
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::add({"one", "two"}, "three");
-- {'one', 'three', 'two'}
```

A set can also be extended with the contents of an array or another set.

```surql
RETURN {1, 2}.add([2, 3, 4]);
-- {1, 2, 3, 4}

RETURN {1, 2, 3}.add({3, 4, 5});
-- {1, 2, 3, 4, 5}
```

##  `set::all`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setall)
When called on a set without any extra arguments, the `set::all` function checks whether all set values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).
API DEFINITION

```surql
set::all(set) -> bool
set::all(set, $predicate: value) -> bool
set::all(set, $predicate: closure) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::all({ 1, 2, 3, NONE, 'SurrealDB', 5 });
-- false
RETURN {'all', 'clear'}.all();
-- true
```

The `set::all` function can also be followed with a value or a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) to check whether all elements conform to a condition.

```surql
RETURN {'same',}.all('same');
-- true

RETURN {"What's", 'it', 'got', 'in', 'its', 'pocketses??'}.all(|$s| $s.len() > 1);
-- true

RETURN {1, 2, 'SurrealDB'}.all(|$var| $var.is_string());
-- false
```

##  `set::any`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setany)
The `set::any` function checks whether any set values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).
API DEFINITION

```surql
set::any(set) -> bool
set::any(set, $predicate: value) -> bool
set::any(set, $predicate: closure) -> bool
```

When called on a set without any extra arguments, the `set::any` function checks whether any set values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).

```surql
RETURN set::any({ 1, 2, 3, NONE, 'SurrealDB', 5 });
-- true

RETURN {'', 0, NONE, NULL, [], {}}.any();
-- false
```

The `set::any` function can also be followed with a value or a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) to check whether any elements conform to a condition.

```surql
RETURN {'same', 'different'}.any('same');
-- true

RETURN {'ant', 'bear', 'cat'}.any(|$s| $s.len() > 3);
-- true

RETURN {1, 2, 3}.any(|$num| $num > 10);
-- false
```

##  `set::at`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setat)
The `set::at` function returns the value at the specified only, or in reverse for a negative index.
Because sets are ordered, the position of the item is based on the set's sorted order.
API DEFINITION

```surql
set::at(set, $index: int) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::at({3, 1, 2}, 1);
-- 2
```

You can also pass in a negative index.

```surql
RETURN {1, 2, 3}.at(-1);
-- 3

RETURN {1, 2, 3}.at(-4);
-- NONE
```

##  `set::complement`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setcomplement)
The `set::complement` function returns the complement of two sets, namely a single set containing items that are in the first set but not in the second set.
API DEFINITION

```surql
set::complement(set, $other: set) -> set
```

Example with output

```surql
{1, 2, 3, 4}.complement({3, 4, 5, 6});
-- {1, 2}
```

##  `set::contains`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setcontains)
The `set::contains` function checks to see if a value is contained within a set.
API DEFINITION

```surql
set::contains(set, $other: value) -> bool
```

Example with output

```surql
{1, 2, 3}.contains(3);
-- true
```

##  `set::difference`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setdifference)
The `set::difference` function determines the symmetric difference between two sets, returning a single set containing items that are not shared between them.
API DEFINITION

```surql
set::difference(set, $other: set) -> set
```

Example with output

```surql
{1, 2, 3, 4}.difference({3, 4, 5, 6});
-- {1, 2, 5, 6}
```

##  `set::filter`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfilter)
The `set::filter` function filters out values that do not match a pattern.
API DEFINITION

```surql
set::filter(set, $predicate: value) -> set
set::filter(set, $predicate: closure) -> set
```

The following example shows a simple use of `set::filter()` with a closure.

```surql
{1, 2, 3, NONE, 0, '', [], {}}.filter(|$v| $v.is_int());
-- {0, 1, 2, 3}
```

You can also pass a value to keep only exact matches.

```surql
{'a', 'b', 'c'}.filter('a');
-- {'a',}
```

##  `set::find`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfind)
The `set::find` function returns the first matching value from a set.
Because sets are ordered, the first matching value is the first match in the set's sorted order.
API DEFINITION

```surql
set::find(set, $predicate: value) -> value | NONE
set::find(set, $predicate: closure) -> value | NONE
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::find({'a', 'b', 'c'}, 'b');
-- 'b'

RETURN {1, 2, 3}.find(4);
-- NONE
```

The `set::find` function is most useful when a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) is passed in, which allows for customized searching.

```surql
{1, 2, 5}.find(|$num| $num >= 3);
-- 5

{
	{ strength: 15, intelligence: 6, name: 'Dom the Magnificent' },
	{ strength: 10, intelligence: 15, name: 'Mardine' },
	{ strength: 20, intelligence: 3, name: 'Gub gub' },
	{ strength: 10, intelligence: 18, name: 'Lumin695' }
}.find(|$c| $c.strength > 9 AND $c.intelligence > 9);
-- { intelligence: 15, name: 'Mardine', strength: 10 }
```

##  `set::first`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfirst)
The `set::first` function returns the first value from a set.
Because sets are ordered, this returns the least value in the set's sorted order.
API DEFINITION

```surql
set::first(set) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::first({ 3, 1, 2 });
-- 1
```

##  `set::flatten`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setflatten)
The `set::flatten` function flattens nested sets and arrays into a single set.
API DEFINITION

```surql
set::flatten(set) -> set
```

Note that this function will remove a single layer of nesting, and may need to be called more than once if you have a set with another set or array inside it.

```surql
-- Flattens everything except the array contained inside an inner set
({ {1, 2}, [3, 4], 'SurrealDB', {5, 6, [7, 8]} }).flatten();

-- Call twice: flattens everything including the nested array
({ {1, 2}, [3, 4], 'SurrealDB', {5, 6, [7, 8]} }).flatten().flatten();
```

Output

```surql
-- Flattened once
{1, 2, 3, 4, 5, 6, 'SurrealDB', [
	7,
	8
]}

-- Flattened twice
{1, 2, 3, 4, 5, 6, 7, 8, 'SurrealDB'}
```

##  `set::fold`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfold)
The `set::fold` function applies an operation on an initial value and every element in the set, returning the final result.
API DEFINITION

```surql
set::fold(set, $initial: value, $operator: closure) -> value
```

This function is commonly used to sum or otherwise accumulate values from a set.

```surql
{1, 2, 3, 4}.fold(0, |$acc, $val| $acc + $val);
-- 10
```

Because `set::fold()` takes an explicit initial value, it is useful when the result type should differ from the type of the set values.

```surql
{1, 2, 3}.fold('', |$acc, $val| $acc + <string>$val);
-- '123'
```

##  `set::intersect`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setintersect)
The `set::intersect` function calculates the values which intersect two sets, returning a single set containing the values which are in both sets.
API DEFINITION

```surql
set::intersect(set, $other: set) -> set
```

Example with output

```surql
{1, 2, 3, 4}.intersect({3, 4, 5, 6});
-- {3, 4}
```

##  `set::is_empty`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setis_empty)
The `set::is_empty` function checks whether the set is empty or not.
API DEFINITION

```surql
set::is_empty(set) -> bool
```

Example with output

```surql
{1, 2, 3, 4}.is_empty();
-- false
```

##  `set::join`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setjoin)
The `set::join` function joins all values in a set together into a string, with a string separator in between each value.
Because sets are ordered, the joined string follows the set's sorted order.
API DEFINITION

```surql
set::join(set, $separator: string) -> string
```

```surql
RETURN set::join({3, 1, 2}, ' + ');
-- '1 + 2 + 3'
```

##  `set::last`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setlast)
The `set::last` function returns the last value from a set.
Because sets are ordered, this returns the greatest value in the set's sorted order.
API DEFINITION

```surql
set::last(set) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::last({ 3, 1, 2 });
-- 3
```

##  `set::len`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setlen)
The `set::len` function calculates the length of a set, returning a number. This function counts unique items only.
If you want to only count [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness) values, then use the [count()](https://surrealdb.com/docs/reference/query-language/functions/database-functions/count) function.
API DEFINITION

```surql
set::len(set) -> number
```

Example with output

```surql
{1, 2, 1, null, 'something', 3, 3, 4, 0}.len();
-- 7
```

##  `set::map`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setmap)
The `set::map` function allows the user to call an [anonymous function](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) (closure) that is performed on every item in the set before passing it on.
Because the result is also a set, duplicate mapped values are removed.
API DEFINITION

```surql
set::map(set, $operator: closure) -> set
```

The most basic use of `set::map` involves choosing a parameter name for each item in the set and a desired output.

```surql
{1, 2, 3}.map(|$v| $v * 2);
-- {2, 4, 6}
```

An example of mapping several values to the same result.

```surql
{1, 2, 3}.map(|$val| $val % 2 = 0);
-- {false, true}
```

##  `set::max`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setmax)
The `set::max` function returns the greatest value from a set of values.
API DEFINITION

```surql
set::max(set) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::max({0, 1, 2});
-- 2
```

As any value can be compared with another value, the set can contain any SurrealQL value.
##  `set::min`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setmin)
The `set::min` function returns the least value from a set of values.
API DEFINITION

```surql
set::min(set) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::min({0, 1, 2});
-- 0
```

As any value can be compared with another value, the set can contain any SurrealQL value.
##  `set::reduce`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setreduce)
The `set::reduce` function applies an operation on every element in the set, returning the final result.
If you need an initial value to pass in before the other items are operated on, use the [`set::fold`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setfold) function instead.
API DEFINITION

```surql
set::reduce(set, $operator: closure) -> value
```

This function is commonly used to sum or perform some other mathematical operation on the items in a set.

```surql
{1, 2, 3, 4}.reduce(|$one, $two| $one + $two);
-- 10
```

Another example showing `set::reduce()` used to build a string:

```surql
{1, 2, 3, 4}.reduce(|$one, $two| <string>$one + <string>$two);
-- '1234'
```

##  `set::remove`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setremove)
The `set::remove` function removes a value from a set.
API DEFINITION

```surql
set::remove(set, $remove: value) -> set
```

The following example removes the value `2` from a set.

```surql
{1, 2, 5}.remove(2);
-- {1, 5}
```

If the value does not exist, the untouched set will be returned.

```surql
{1, 2, 5}.remove(3);
-- {1, 2, 5}
```

You can also remove the contents of an array or another set.

```surql
RETURN {1, 2, 3, 4}.remove([2, 3]);
-- {1, 4}

RETURN {1, 2, 3, 4}.remove({2, 3, 4});
-- {1,}
```

##  `set::slice`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setslice)
The `set::slice` function returns a slice of a set by position.
Because sets are ordered, slicing is based on the set's sorted order.
API DEFINITION

```surql
set::slice(set) -> set
set::slice(set, $start: int) -> set
set::slice(set, $start: int, $end: int) -> set
set::slice(set, $range: range<int>) -> set
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN set::slice({4, 1, 3, 2}, 1, 3);
-- {2, 3}

RETURN {1, 2, 3, 4, 5}.slice(-3..);
-- {3, 4, 5}
```

##  `set::union`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/set#setunion)
The `set::union` function combines two sets together, removing duplicate values, and returning a single set.
API DEFINITION

```surql
set::union(set, $other: set) -> set
```

Example with output

```surql
{1, 2, 6}.union({1, 3, 4, 5, 6});
-- {1, 2, 3, 4, 5, 6}
```
