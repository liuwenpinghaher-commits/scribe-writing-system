---
title: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/array"
url: "https://surrealdb.com/docs/reference/query-language/functions/database-functions/array"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/functions/database-functions/array

Source: https://surrealdb.com/docs/reference/query-language/functions/database-functions/array

These functions can be used when working with, and manipulating arrays of data.  
| Function  | Description  |  
| --- | --- |  
| [`array::add()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayadd)  | Adds an item to an array if it doesn't exist  |  
| [`array::all()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayall)  | Checks whether all array values are truthy, or equal to a condition  |  
| [`array::any()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayany)  | Checks whether any array value is truthy, or equal to a condition  |  
| [`array::at()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayat)  | Returns value for X index, or in reverse for a negative index  |  
| [`array::append()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayappend)  | Appends an item to the end of an array  |  
| [`array::boolean_and()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayboolean_and)  |  Perform the [AND](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND)[](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND)[bitwise operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND)on two arrays  |  
| [`array::boolean_or()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayboolean_or)  |  Perform the [OR](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_OR)[](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_OR)[bitwise operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_OR)on two arrays  |  
| [`array::boolean_xor()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayboolean_xor)  |  Perform the [XOR](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_XOR)[](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_XOR)[bitwise operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_XOR)on two arrays  |  
| [`array::boolean_not()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayboolean_not)  |  Perform the [NOT](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_NOT)[](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_NOT)[bitwise operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_NOT)on an array  |  
| [`array::combine()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraycombine)  | Combines all values from two arrays together  |  
| [`array::complement()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraycomplement)  | Returns the complement of two arrays  |  
| [`array::clump()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayclump)  | Returns the original array split into multiple arrays of X size  |  
| [`array::concat()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayconcat)  | Returns the merged values from two arrays  |  
| [`array::difference()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraydifference)  | Returns the difference between two arrays  |  
| [`array::distinct()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraydistinct)  | Returns the unique items in an array  |  
| [`array::fill()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfill)  | Fills an existing array of the same value  |  
| [`array::filter()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfilter)  | Filters out values that do not match a pattern  |  
| [`array::filter_index()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfilter_index)  | Returns the indexes of all occurrences of all matching X value  |  
| [`array::find()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfind)  | Returns the first matching value  |  
| [`array::find_index()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfind_index)  | Returns the index of the first occurrence of X value  |  
| [`array::first()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfirst)  | Returns the first item in an array  |  
| [`array::flatten()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayflatten)  | Flattens multiple arrays into a single array  |  
| [`array::fold()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfold)  | Applies an operation on an initial value plus every element in the array, returning the final result.  |  
| [`array::group()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraygroup)  | Flattens and returns the unique items in an array  |  
| [`array::insert()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayinsert)  | Inserts an item at the end of an array, or in a specific position  |  
| [`array::intersect()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayintersect)  | Returns the values which intersect two arrays  |  
| [`array::is_empty()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayis_empty)  | Checks if an array is empty  |  
| [`array::join()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayjoin)  | Returns concatenated value of an array with a string in between.  |  
| [`array::last()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylast)  | Returns the last item in an array  |  
| [`array::len()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylen)  | Returns the length of an array  |  
| [`array::logical_and()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylogical_and)  |  Performs the [AND](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND)[](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND)[logical operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND)on two arrays  |  
| [`array::logical_or()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylogical_or)  |  Performs the [OR](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR)[](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR)[logical operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR)on two arrays  |  
| [`array::logical_xor()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylogical_xor)  |  Performs the [XOR](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR)[](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR)[logical operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR)on two arrays  |  
| [`array::map()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymap)  | Applies an operation to every item in an array and passes it on  |  
| [`array::max()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymax)  | Returns the greatest item from an array  |  
| [`array::matches()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymatches)  | Returns an array of booleans indicating which elements of the input array contain a specified value.  |  
| [`array::min()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymin)  | Returns the least item from an array  |  
| [`array::pop()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraypop)  | Returns the last item from an array  |  
| [`array::prepend()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayprepend)  | Prepends an item to the beginning of an array  |  
| [`array::push()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraypush)  | Appends an item to the end of an array  |  
| [`array::range()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayrange)  | Creates a number array from a range (start to end)  |  
| [`array::reduce()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayreduce)  | Applies an operation on every element in the array, returning the final result.  |  
| [`array::remove()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayremove)  | Removes an item at a specific position from an array  |  
| [`array::repeat()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayrepeat)  | Creates an array a given size with a specified value used for each element.  |  
| [`array::reverse()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayreverse)  | Reverses the sorting order of an array  |  
| [`array::sequence()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayshuffle)  | Creates an array of sequential integers  |  
| [`array::shuffle()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayshuffle)  | Randomly shuffles the contents of an array  |  
| [`array::slice()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayslice)  | Returns a slice of an array  |  
| [`array::sort()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysort)  | Sorts the values in an array in ascending or descending order  |  
| [`array::sort_lexical()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysort_lexical)  | Sorts the values in an array, with strings sorted lexically  |  
| [`array::sort_natural()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysort_natural)  | Sorts the values in an array, with numeric strings sorted numerically  |  
| [`array::sort_natural_lexical()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysort_natural_lexical)  | Sorts the values in an array, applying both natural numeric and lexical ordering to strings  |  
| [`array::sort::asc()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysortasc)  | Sorts the values in an array in ascending order  |  
| [`array::sort::desc()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysortdesc)  | Sorts the values in an array in descending order  |  
| [`array::swap()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayswap)  | Swaps two items in an array  |  
| [`array::transpose()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraytranspose)  | Performs 2d array transposition on arrays  |  
| [`array::union()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayunion)  | Returns the unique merged values from two arrays  |  
| [`array::windows()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraywindows)  | Returns a number of arrays of length `size` created by moving one index at a time down the original array  |  
##  `array::add`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayadd)
The `array::add` function adds an item to an array only if it doesn't exist.
API DEFINITION

```surql
array::add(array, $new_val: value) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::add(["one", "two"], "three");

-- ['one', 'two', 'three']
```

If the item to add is an array, it will add each item of the array instead of the array itself as a separate value.

```surql
[1,2,3].add([2,3,4]);

-- [1, 2, 3, 4]
```

  

##  `array::all`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayall)
When called on an array without any extra arguments, the `array::all` function checks whether all array values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).
API DEFINITION

```surql
array::all(array) -> bool
array::all(array, $predicate: value) -> bool
array::all(array, $predicate: closure) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::all([ 1, 2, 3, NONE, 'SurrealDB', 5 ]);
-- false

RETURN ["all", "clear"].all();
-- true
```

The `array::all` function can also be followed with a value or a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) to check if all elements conform to a condition.

```surql
RETURN ["same", "same", "same"].all("same");
-- true

[
  "What's",
  "it",
  "got",
  "in",
  "its",
  "pocketses??"
].all(|$s| $s.len() > 1);
-- true

[1, 2, "SurrealDB"].all(|$var| $var.is_string());
-- false
```

The `array::all` function can also be called using its alias `array::every`.

```surql
[1, 2, 3].every(|$num| $num > 0);
-- true
```

  

##  `array::any`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayany)
The `array::any` function checks whether any array values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).
API DEFINITION

```surql
array::any(array) -> bool
array::any(array, $predicate: value) -> bool
array::any(array, $predicate: closure) -> bool
```

When called on an array without any extra arguments, the `array::any` function checks whether any array values are [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness).

```surql
RETURN array::any([ 1, 2, 3, NONE, 'SurrealDB', 5 ]);
-- true

["", 0, NONE, NULL, [], {}].any();
-- false
```

The `array::any` function can also be followed with a value or a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) to check if any elements conform to a condition.

```surql
RETURN ["same", "same?", "Dude, same!"].any("same");
-- true

[
  "What's",
  "it",
  "got",
  "in",
  "its",
  "pocketses??"
].any(|$s| $s.len() > 15);
-- false

[1, 2, "SurrealDB"].any(|$var| $var.is_string());
-- true
```

The `array::any` function can also be called using the aliases `array::some` and `array::includes`.

```surql
[1, 2, 3].some(|$num| $num > 2);
-- true

[1999, 2001, 2002].includes(2000);
-- false
```

  

##  `array::at`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayat)
The `array::at` function returns the value at the specified index, or in reverse for a negative index.
API DEFINITION

```surql
array::at(array, $index: int) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::at(['s', 'u', 'r', 'r', 'e', 'a', 'l'], 2);

-- 'r'
```

You can also pass a negative index. This will perform the lookup in reverse:

```surql
RETURN array::at(['s', 'u', 'r', 'r', 'e', 'a', 'l'], -3);

-- 'e'
```

  

##  `array::append`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayappend)
The `array::append` function appends a value to the end of an array.
API DEFINITION

```surql
array::append(array, $new_val: value) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::append([1, 2, 3, 4], 5);

-- [1, 2, 3, 4, 5]
```

  

##  `array::boolean_and`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayboolean_and)
The `array::boolean_and` function performs the [`AND` `bitwise operations`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND) on the input arrays per-element based on the element's truthiness.  
If one array is shorter than the other it is considered null and thus false.
API DEFINITION

```surql
array::boolean_and($lh: array, $rh: array)
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::boolean_and(["true",
  "false",
  1,
  1],
  ["true",
  "true",
  0,
  "true"]);

-- [true, true, false, true]
```

For those that take two arrays, missing elements (if one array is shorter than the other) are considered `null` and thus false.

```surql
RETURN array::boolean_and([true, true], [false]);

-- [ false, false ]
```

  

##  `array::boolean_or`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayboolean_or)
The `array::boolean_or` function performs the [OR bitwise operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_OR) on the input arrays per-element based on the element's truthiness.  
It takes two arrays and if one array is shorter than the other or missing, the output is considered null and thus false.
API DEFINITION

```surql
array::boolean_or($lh: array, $rh: array)
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::boolean_or([false,
  true,
  false,
  true],
  [false,
  false,
  true,
  true]);

-- [false, true, true, true]
```

  

##  `array::boolean_xor`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayboolean_xor)
The `array::boolean_xor` function performs the [XOR bitwise operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR).
API DEFINITION

```surql
array::boolean_xor($lh: array, $rh: array)
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::boolean_xor([false,
  true,
  false,
  true],
  [false,
  false,
  true,
  true]);

-- [false, true, true, false]
```

  

##  `array::boolean_not`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayboolean_not)
The `array::boolean_not` function performs the [`NOT bitwise operations`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_NOT) on the input array(s) per-element based on the element's truthiness.  
It takes in one array and it returns false if its single operand can be converted to true.
API DEFINITION

```surql
array::boolean_not(array)
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::boolean_not([ false, true, 0, 1 ]);

-- [true, false, true, false]
```

  

##  `array::combine`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraycombine)
The `array::combine` function combines all values from two arrays together, returning an array of arrays.
API DEFINITION

```surql
array::combine(array, $other: array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::combine([1, 2], [2, 3]);

-- [ [1, 2], [1, 3], [2, 2], [2, 3] ]
```

  

##  `array::complement`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraycomplement)
The `array::complement` function returns the complement of two arrays, returning a single array containing items which are not in the second array.
API DEFINITION

```surql
array::complement(array, $other: array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::complement([1, 2, 3, 4], [3, 4, 5, 6]);

-- [1, 2]
```

  

##  `array::concat`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayconcat)
The `array::concat` function merges an array with one or more arrays, returning an array which may contain duplicate values. If you want to remove duplicate values from two merged arrays, then use the [`array::union()`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayunion) function.
API DEFINITION

```surql
array::concat(array, $other: array, ..) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::concat([1, 2, 3, 4], [3, 4, 5, 6]);
-- [1, 2, 3, 4, 3, 4, 5, 6]

RETURN [1,2].concat([3,4], [4,3])
-- [1, 2, 3, 4, 4, 3]
```

As of SurrealDB 3.0.0, the behaviour of this function can also be achieved using the `+` operator.

```surql
RETURN [1, 2, 3, 4] + [3, 4, 5, 6];

-- [ 1, 2, 3, 4, 3, 4, 5, 6 ]
```

  

##  `array::clump`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayclump)
The `array::clump` function returns the original array split into sub-arrays of `size`. The last sub-array may have a length less than the length of `size` if `size` does not divide equally into the original array.
API DEFINITION

```surql
array::clump(array, $size: int) -> array
```

The following examples show this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
LET $array = [1, 2, 3, 4];
RETURN array::clump($array, 2);
RETURN array::clump($array, 3);
```

Response

```surql
-- [ [ 1, 2], [3, 4] ]
-- [ [1, 2, 3], [4] ]
```

  

##  `array::difference`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraydifference)
The `array::difference` function determines the difference between two arrays, returning a single array containing items which are not in both arrays.
API DEFINITION

```surql
array::difference(array, $other: array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::difference([1, 2, 3, 4], [3, 4, 5, 6]);

-- [ 1, 2, 5, 6 ]
```

  

##  `array::distinct`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraydistinct)
The `array::distinct` function calculates the unique values in an array, returning a single array.
API DEFINITION

```surql
array::distinct(array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::distinct([ 1, 2, 1, 3, 3, 4 ]);

-- [ 1, 2, 3, 4 ]
```

  

##  `array::fill`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfill)
The `array::fill` function replaces all values of an array with a new value.
API DEFINITION

```surql
array::fill(array, $with: any) -> array
```

The function also accepts a third and a fourth parameter which allows you to replace only a portion of the source array.
API DEFINITION

```surql
array::fill(array, $with: any, $start: int, $end: int) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::fill([ 1, 2, 3, 4, 5 ], 10);

-- [ 10, 10, 10, 10, 10 ]
```

The following example shows how you can use this function with a starting position, and an ending position, which in this example will replace one item from the array:

```surql
RETURN array::fill([ 1, NONE, 3, 4, 5 ], 10, 1, 2);

-- [ 1, 10, 3, 4, 5 ]
```

The following example shows how you can use this function with starting and ending negative positions, which in this example will replace one item from the array:

```surql
RETURN array::fill([ 1, 2, NONE, 4, 5 ], 10, -3, -2);

-- [ 1, 2, 10, 4, 5 ]
```

  

##  `array::filter`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfilter)
The `array::filter` function filters out values in an array that do not match a pattern, returning only the ones that do match.
API DEFINITION

```surql
array::filter(array, $predicate: value) -> array
array::filter(array, $predicate: closure) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::filter([ 1, 2, 1, 3, 3, 4 ], 1);
-- [ 1, 1 ]

RETURN [true, false, false, false, true, true].filter(true);
-- [ true, true, true ]
```

The `array::filter` function can also take a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) for more customized filtering.

```surql
 [
    { importance: 10,
      message: "I need some help with this query..." }
    { importance: 0, message: "TEST Is this thing on?" },
    { importance: 5, message: "I have an idea. What if we..."},
    { importance: 100,
      message: "Stuck on an island with two hours of battery life left. Can you..."}
].filter(|$v| $v.importance > 5);
```

Response

```surql
[
	{
		importance: 10,
		message: 'I need some help with this query...'
	},
	{
		importance: 100,
		message:
		  'Stuck on an island with two hours of battery life left. Can you...'
	}
]
```

Note that the function checks whether the output of the inner closure [is truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness), as opposed to only expecting a `bool`. As any and all values can be checked for truthiness, simply passing the closure argument as its output is enough to filter out values that are not truthy, such as `NONE` values and empty arrays.

```surql
[1,2,3,NONE,0,"",{},[]].filter(|$v| $v);

-- [1, 2, 3]
```

A more real-life example of this pattern in which only the `person` records that have been seen by another are returned:

```surql
CREATE person:one, person:two;
RELATE person:one->sees->person:two;

(SELECT 
  id, 
  <-sees<-person AS is_seen_by
FROM person)
    .filter(|$person| $person.is_seen_by);
```

Response

```surql
[
	{
		id: person:two,
		is_seen_by: [
			person:one
		]
	}
]
```

  

##  `array::filter_index`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfilter_index)
The `array::filter_index` function returns the indexes of all occurrences of all matching values.
API DEFINITION

```surql
array::filter_index(array, $predicate: value) -> array
array::filter_index(array, $predicate: closure) -> array
```

The following examples show this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::filter_index(['a', 'b', 'c', 'b', 'a'], 'b');
-- [ 1, 3 ]

RETURN [0, 0, 1, 0, 0, 5, 1].filter_index(0);
-- [ 0, 1, 3, 4 ]
```

The `array::filter_index` function can also take a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) for more customized filtering.

```surql
 [
    { importance: 10,
      message: "I need some help with this query..." }
    { importance: 0, message: "TEST Is this thing on?" },
    { importance: 5, message: "I have an idea. What if we..."},
    { importance: 100,
      message: "Stuck on an island with two hours of battery life left. Can you..."}
].filter_index(|$v| $v.importance > 5);
```

Response

```surql
[0, 3]
```

  

##  `array::find`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfind)
The `array::find` function returns the first occurrence of `value` in the array or `NONE` if `array` does not contain `value`.
API DEFINITION

```surql
array::find(array, $predicate: value)   -> value | NONE
array::find(array, $predicate: closure) -> value | NONE
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::find(['a', 'b', 'c', 'b', 'a'], 'b');
-- b

RETURN [1, 2, 3].find(4);
-- [NONE]
```

The `array::find` function is most useful when a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) is passed in which allows for customized searching.

```surql
-- Find one number 3 or greater
RETURN [1, 2, 5].find(|$num| $num >= 3);

-- Find the first adventurer good enough for the task
[
    { strength: 15, intelligence: 6,  name: "Dom the Magnificent" },
    { strength: 10, intelligence: 15, name: "Mardine"             },
    { strength: 20, intelligence: 3,  name: "Gub gub"             },
    { strength: 10, intelligence: 18, name: "Lumin695"            }
].find(|$c| $c.strength > 9 AND $c.intelligence > 9);
```

Response

```surql
-------- Query --------

5

-------- Query --------

{
	intelligence: 15,
	name: 'Mardine',
	strength: 10
}
```

  

##  `array::find_index`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfind_index)
The `array::find_index` function returns the index of the first occurrence of `value` in the array or `NONE` if `array` does not contain `value`.
API DEFINITION

```surql
array::find_index(array, $predicate: value)   -> number | NONE
array::find_index(array, $predicate: closure) -> number | NONE
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::find_index(['a', 'b', 'c', 'b', 'a'], 'b');
-- 1

RETURN [1, 2, 3].find_index(4);
-- NONE
```

The `array::find_index` function can also take a [closure](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) for more customized searching.

```surql
RETURN [1, 2, 3].find_index(|$num| $num > 2);
-- 2
```

The `array::find_index` function also be called using the alias `array::index_of`.

```surql
["cat", "badger", "dog", "octopus"].index_of("octopus");
-- 3
```

  

##  `array::first`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfirst)
The `array::first` function returns the first value from an array.
API DEFINITION

```surql
array::first(array) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::first([ 's', 'u', 'r', 'r', 'e', 'a', 'l' ]);

-- 's'
```

  

##  `array::flatten`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayflatten)
The `array::flatten` function flattens an array of arrays, returning a new array with all sub-array elements concatenated into it.
API DEFINITION

```surql
array::flatten(array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::flatten([ [1,
  2],
  [3,
  4],
  'SurrealDB',
  [5,
  6,
  [7,
  8]] ]);
```

Response

```surql
[ 1, 2, 3, 4, 'SurrealDB', 5, 6, [7, 8] ]
```

  

##  `array::fold`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfold)
The `array::fold` function returns a final value from the elements of an array by allowing an operation to be performed at each step of the way as each subsequent item in the array is encountered. To use `array::fold`, pass in an initial value, followed by parameter names for the current value and the next value and an operation to perform on them. If you only want to perform an operation on each item and do not need an initial value, use the [`array::reduce`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayreduce) function instead.
API DEFINITION

```surql
array::fold(array, $initial_value: value, $operator: closure) -> value
```

This function is commonly used to sum or subtract the items in an array from an initial value.

```surql
-- Returns 53
[10,12,10,15].fold(100, |$a, $b| $a - $b);
```

The function will then perform the following operation for each step of the way.
  * •
`$a` = 100 (initial value), `$b` = 10 (first item in the array). Operation `$a - $b` = 90. 90 is passed on.
  * •
`$a` = 90, `$b` = 12. Operation `$a - $b` = 78. 78 is passed on.
  * •
`$a` = 84, `$b` = 10. Operation `$a - $b` = 74. 68 is passed on.
  * •
`$a` = 74, `$b` = 15. Operation `$a - $b` = 53. No more items to operate on in the array, 53 is returned.

Another example showing `array::fold()` used to reverse a `string`:

```surql
"I am a forwards string"
  .split('')
  .fold("", |$one, $two| $two + $one);
```

Output

```surql
'gnirts sdrawrof a ma I'
```

Or to modify a string in some other way.

```surql
"I don't like whitespace"
  .split(" ")
  .fold("", |$one, $two| $one + "_" + $two);
```

Output

```surql
"_I_don't_like_whitespace"
```

As the output above shows, it is often nice to know which item of the array one is working with. This function allows a third parameter to be passed in that keeps track of the index of the current item.

```surql
"I don't like whitespace"
  .split(" ")
  .fold("",
    |$one,
    $two,
    $index| IF $index = 0 { $one + $two } ELSE { $one + "_" + $two });
```

Output

```surql
"I_don't_like_whitespace"
```

The `array::fold()` function can be used to generate an array of values that can then be passed on to statements like [`INSERT`](https://surrealdb.com/docs/reference/query-language/statements/insert) for bulk insertion.

```surql
INSERT INTO person (
  -- Create 1000 objects with a random ULID and incrementing number
    (<array>0..1000).fold([], |$v, $_, $i| {
    $v.append( { 
      id: rand::ulid(),
      person_num: $i
      });
    })
) RETURN NONE;
```

This function is also useful for aggregating the results of graph queries. The following shows a graph table called `to` that holds the distance from one city to another. The `array::fold()` function can then be used to pass an object along that tracks the first and last city, while accumulating the distance and number of trips along the way.

```surql
CREATE city:one, city:two, city:three;
RELATE city:one -> to -> city:two SET distance = 25.5;
RELATE city:two -> to -> city:three SET distance = 4.1;
[
	city:one,
	city:two,
	city:three
].map(|$v| { {
	city: $v,
	distance: 0,
	from: NONE,
	to: NONE,
	trips: 0
} }).fold({
	city: NONE,
	distance: 0,
	from: NONE,
	to: NONE,
	trips: 0
}, |$acc, $val, $i| {
	RETURN IF $i = 0 {
		{
			city: $val.city,
			distance: 0,
			from: $val.city,
			to: NONE,
			trips: $acc.trips + 1
		}
  }
	ELSE {
		{
			city: $val.city,
			distance: (SELECT VALUE distance FROM ONLY to WHERE in = $acc.city
			  AND out = $val.city LIMIT 1) + $acc.distance,
			from: $acc.from,
			to: $val.city,
			trips: $acc.trips + 1
		}
  };
}).chain(|$v| { {
	distance: $v.distance,
	from: $v.from,
	to: $v.to,
	trips: $v.trips
} });
```

Final result:

```surql
{
	distance: 29.6f,
	from: city:one,
	to: city:three,
	trips: 3
}
```

##  `array::group`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraygroup)
The `array::group` function flattens and returns the unique items in an array.
API DEFINITION

```surql
array::group(array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::group([1,
  2,
  3,
  4,
  [3,
  5,
  6],
  [2,
  4,
  5,
  6],
  7,
  8,
  8,
  9]);

-- [ 1, 2, 3, 4, 5, 6, 7, 8, 9 ]
```

  

##  `array::insert`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayinsert)
The `array::insert` function inserts a value into an array.
API DEFINITION

```surql
array::insert(array, $insert: value) -> array
array::insert(array, $insert: value, $position: int) -> array
```

When only a value is used as the second argument, it will be appended to the end of the array.

```surql
array::insert([1, 2, 3, 4], 'and me');
-- [1, 2, 3, 4, 'and me']
```

If the value to append is followed by an index, this will be used as the location for the new value. A negative index can also be used to index from the end instead of from the beginning of an array.

```surql
array::insert([1, 2, 3, 4], 'and me', 0);
-- ['and me', 1, 2, 3, 4]

array::insert([1, 2, 3, 4], 'and me', -1);
-- [1, 2, 3, 'and me', 4]
```

A negative index can be provided to specify a position relative to the end of the array.
  

##  `array::intersect`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayintersect)
The `array::intersect` function calculates the values which intersect two arrays, returning a single array containing the values which are in both arrays.
API DEFINITION

```surql
array::intersect(array, $other: array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::intersect([1, 2, 3, 4], [3, 4, 5, 6]);

-- [ 3, 4 ]
```

  

##  `array::is_empty`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayis_empty)
The `array::is_empty` function checks whether the array contains values.
API DEFINITION

```surql
array::is_empty(array) -> bool
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:
An array that contain values

```surql
RETURN array::is_empty([1, 2, 3, 4]);

-- false
```

An empty array

```surql
RETURN array::is_empty([]);

-- true
```

  

##  `array::join`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayjoin)
The `array::join` function takes an array and a string as parameters and returns a concatenated string.
API DEFINITION

```surql
array::join(array, $concat_with: string) -> string
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::join(["again", "again", "again"], " and ");

-- "again and again and again"
```

  

##  `array::last`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylast)
The `array::last` function returns the last value from an array. You can also use the [`[$]` idiom](https://surrealdb.com/docs/reference/query-language/language-primitives/idioms#last-element) on array values (for example, `my_array[$]`).
API DEFINITION

```surql
array::last(array) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::last([ 's', 'u', 'r', 'r', 'e', 'a', 'l' ]);

-- 'l'
```

  

##  `array::len`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylen)
The `array::len` function calculates the length of an array, returning a number. This function includes all items when counting the number of items in the array. If you want to only count [truthy](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#values-and-truthiness) values, then use the [count()](https://surrealdb.com/docs/reference/query-language/functions/database-functions/count) function.
API DEFINITION

```surql
array::len(array) -> number
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::len([ 1, 2, 1, null, "something", 3, 3, 4, 0 ]);

-- 9
```

  

##  `array::logical_and`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylogical_and)
The `array::logical_and` function performs the [`AND` logical operation](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND) element-wise between two arrays.  
The resulting array will have a length of the longer of the two input arrays, where each element is the result of the logical `AND` operation performed between an element from the left hand side array and an element from the right hand side array.
When both of the compared elements are truthy, the resulting element will have the type and value of one of the two truthy values, prioritizing the value and type of the element from the left hand side (the first array).
When one or both of the compared elements are not truthy, the resulting element will have the type and value of one of the non-truthy value(s), prioritizing the value and type of the element from the left hand side (the first array).
API DEFINITION

```surql
array::logical_and($lh: array, $rh: array)
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::logical_and([true,
  false,
  true,
  false],
  [true,
  true,
  false,
  false]);

-- [ true, false, false, false ]
```

For those that take two arrays, missing elements (if one array is shorter than the other) are considered `null` and thus false.

```surql
RETURN array::logical_and([0, 1], [])

-- [ 0, NULL ]
```

  

##  `array::logical_or`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylogical_or)
The `array::logical_or` function performs the [`OR` logical operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR) element-wise between two arrays.
The resulting array will have a length of the longer of the two input arrays, where each element is the result of the logical `OR` operation performed between an element from the left hand side array and an element from the right hand side array.
When one or both of the compared elements are truthy, the resulting element will have the type and value of one of the two truthy value(s), prioritizing the value and type of the element from the left hand side (the first array).
When both of the compared elements are not truthy, the resulting element will have the type and value of one of the non-truthy values, prioritizing the value and type of the element from the left hand side (the first array).
API DEFINITION

```surql
array::logical_or($lh: array, $rh: array)
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::logical_or([true,
  false,
  true,
  false],
  [true,
  true,
  false,
  false]);

-- [ true, true, true, false ]
```

If one of the arrays is empty, the first array is returned.

```surql
RETURN array::logical_or([0, 1], []);

[ 0, 1 ]
```

  

##  `array::logical_xor`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraylogical_xor)
The `array::logical_xor` function performs the [`XOR` logical operations](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_OR) element-wise between two arrays.
The resulting array will have a length of the longer of the two input arrays, where each element is the result of the logical `XOR` operation performed between an element from the left hand side array and an element from the right hand side array.
When exactly one of the compared elements is truthy, the resulting element will have the type and value of the truthy value.
When both of the compared elements are truthy, the resulting element will be the `bool` value `false`.
When neither of the compared elements are truthy, the resulting element will have the type and value of one of the non-truthy values, prioritizing the value and type of the element from the left hand side (the first array).
API DEFINITION

```surql
array::logical_xor($lh: array, $rh: array)
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::logical_xor([true,
  false,
  true,
  false],
  [true,
  true,
  false,
  false]);

-- [ false, true, true, false ]
```

If one of the array is empty, the first array is returned.

```surql
RETURN array::logical_xor([0, 1], [])

-- [ 0, 1 ]
```

  

##  `array::map`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymap)
The `array::map` function allows the user to call an [anonymous function](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/closures) (closure) that is performed on every item in the array before passing it on.
API DEFINITION

```surql
array::map(array, $operator: closure) -> array;
```

The most basic use of `array::map` involves choosing a parameter name for each item in the array and a desired output. The following example gives each item the parameter name `$v`, which can then be used to double the value.

```surql
[1, 2, 3].map(|$v| $v * 2);
```

Response

```surql
[
  2,
  4,
  6
]
```

An example of a longer operation that uses `{}` to allow the closure to take multiple lines of code:

```surql
["1", "2", "3"].map(|$val| {
  LET $num = <number>$val;
  LET $is_even = IF $num % 2 = 0 { true } ELSE { false };
  {
    value: $num,
    is_even: $is_even
  }
});
```

Response

```surql
[
	{
		is_even: false,
		value: 1
	},
	{
		is_even: true,
		value: 2
	},
	{
		is_even: false,
		value: 3
	}
]

```

The types for the closure arguments and output can be annotated for extra type safety. Take the following simple closure:

```surql
[1, 2, 3].map(|$num| $num + 1.1);
```

The output is `[2.1f, 3.1f, 4.1f]`.
However, if the `1.1` inside the function was actually a typo and should have been the integer 11, the following would have prevented it from running.

```surql
[1, 2, 3].map(|$num: int| -> int { $num + 1.1 });
```

Response

```surql
"Couldn 't coerce return value from function `ANONYMOUS`: Expected
  `int` but found `2.1f`"
```

The `array::map` function also allows access to the index of each item if a second parameter is added.

```surql
[
  ": first used in the year 876",
  ": the number of moons in the sky",
  ": also called a pair"
]
  .map(|$item, $index| <string>$index + $item);
```

Response

```surql
[
	'0: first used in the year 876',
	'1: the number of moons in the sky',
	'2: also called a pair'
]
```

The `array::map()` function can be used to generate an array of values that can then be passed on to statements like [`INSERT`](https://surrealdb.com/docs/reference/query-language/statements/insert) for bulk insertion.

```surql
INSERT INTO person ((<array>0..=1000).map(|| {id: rand::ulid()}));
```

For a similar function that allows using a closure on entire values instead of each item in an array, see the [chain](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#chain) method.
##  `array::max`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymax)
The `array::max` function returns the greatest value from an array of values.
API DEFINITION

```surql
array::max(array<any>) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::max([0, 1, 2]);

-- 2
```

As any value can be compared with another value, the array can be an array of any SurrealQL value.

```surql
array::max([NONE, NULL, 9, 9.9]);

-- 9.9f
```

See also:
  * •
[`math::max`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmax), which extracts the greatest number from an array of numbers
  * •
[`time::max`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemax), which extracts the greatest datetime from an array of datetimes
  * •
[How values are compared and ordered in SurrealDB](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#comparing-and-ordering-values)

##  `array::matches`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymatches)
The `array::matches` function returns an array of booleans indicating which elements of the input array contain a specified value.
API DEFINITION

```surql
array::matches(array, $predicate: value) -> array<bool>
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::matches([0, 1, 2], 1);

-- [false, true, false]
```

The following example shows this function when the array contains objects.

```surql
RETURN array::matches([{id: r"ohno:0"},
  {id: r"ohno:1"}],
  {id: r"ohno:1"});

-- [false, true]
```

  

##  `array::min`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraymin)
The `array::min` function returns the least value from an array of values.
API DEFINITION

```surql
array::min(array<any>) -> any
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::min([0, 1, 2]);

-- 0
```

As any value can be compared with another value, the array can be an array of any SurrealQL value.

```surql
array::min([NONE, NULL, 9, 9.9]);

NONE
```

See also:
  * •
[`math::min`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/math#mathmin), which extracts the least number from an array of numbers
  * •
[`time::min`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/time#timemin), which extracts the least datetime from an array of datetimes
  * •
[How values are compared and ordered in SurrealDB](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values#comparing-and-ordering-values)

##  `array::pop`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraypop)
The `array::pop` function removes a value from the end of an array and returns it. If the array is empty, NONE is returned.
API DEFINITION

```surql
array::pop(array) -> value
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::pop([ 1, 2, 3, 4 ]);

-- 4
```

  

##  `array::prepend`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayprepend)
The `array::prepend` function prepends a value to the beginning of an array.
API DEFINITION

```surql
array::prepend(array, $new_val: value) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::prepend([1, 2, 3, 4], 5);

-- [ 5, 1, 2, 3, 4 ]
```

  

##  `array::push`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraypush)
The `array::push` function appends a value to the end of an array.
API DEFINITION

```surql
array::push(array, $new_val: value) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::push([1, 2, 3, 4], 5);

-- [ 1, 2, 3, 4, 5 ]
```

  

##  `array::range`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayrange)
The `array::range` function creates an array of numbers from a given range.
API DEFINITION

```surql
array::range($start: int, $end: int) -> array
-- Also since 3.0.0
array::range(range) -> array;
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::range(1, 10);

-- [ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 ]
```

```surql
RETURN array::range(1..=5);

[ 1, 2, 3, 4, 5 ]
```

  

##  `array::reduce`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayreduce)
The `array::reduce` function reduces the elements of an array to a single final value by allowing an operation to be performed at each step of the way as each subsequent item in the array is encountered. To use `array::reduce`, pass in parameter names for the current value and the next value and an operation to perform on them. If you need an initial value to pass in before the other items are operated on, use the [`array::fold`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfold) function instead.
API DEFINITION

```surql
array::reduce(array, $operator: closure) -> value
```

This function is commonly used to sum or perform some other mathematical operation on the items in an array.

```surql
[10,20,30,40].reduce(|$a, $b| $a + $b);
```

The function will then perform the following operation for each step of the way.
  * •
`$a` = 10, `$b` = 20. Operation `$a + $b` = 30. 30 is passed on.
  * •
`$a` = 30, `$b` = 30. Operation `$a + $b` = 60. 60 is passed on.
  * •
`$a` = 60, `$b` = 40. Operation `$a + $b` = 100. No more items to operate on in the array, 100 is returned.

Another example showing `array::reduce()` used to reverse a `string`:

```surql
"I am a forwards string"
  .split('')
  .reduce(|$one, $two| $two + $one);
```

Output

```surql
'gnirts sdrawrof a ma I'
```

Or to modify a string in some other way.

```surql
"I don't like whitespace"
  .split(" ")
  .reduce(|$one, $two| $one + "_" + $two);
```

Output

```surql
"I_don't_like_whitespace"
```

It is often nice to know which item of the array one is working with. The following example shows a reduce operation performed on an array, but only up to index 2. For any further indexes, the value is simply passed on.

```surql
[
    {
        name: "Daughter",
        money: 100
    },
    {
        name: "Father",
        money: 1000
    },
    {
        name: "Grandfather",
        money: 550
    },
    {
        name: "Great-grandmother",
        money: 10000
    }
].reduce(|$one, $two, $index| IF $index > 2 { $one } ELSE {
    {
        name: $one.name + " and " + $two.name,
        money: $one.money + $two.money
    }
});
```

Output

```surql
{
	money: 1650,
	name: 'Daughter and Father and Grandfather'
}
```

##  `array::remove`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayremove)
The `array::remove` function removes an item from a specific position in an array. A negative index can be provided to specify a position relative to the end of the array.
API DEFINITION

```surql
array::remove(array, $index: number) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::remove([1, 2, 3, 4, 5], 2);

-- [ 1, 2, 4, 5 ]
```

The following examples shows this function using a negative index.

```surql
RETURN array::remove([1, 2, 3, 4, 5], -2);

-- [ 1, 2, 3, 5 ]
```

  

##  `array::repeat`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayrepeat)
The `array::repeat` function creates an array of a given size contain the specified value for each element. The `count` argument must be non-negative; negative values return an error.
API DEFINITION

```surql
array::repeat(any, $count: int) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::repeat(1, 10);

-- [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 ]
```

```surql
RETURN array::repeat("hello", 2);

-- [ "hello", "hello" ]
```

  

##  `array::reverse`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayreverse)
The `array::reverse` function reverses the sorting order of an array.
API DEFINITION

```surql
array::reverse(array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::reverse([ 1, 2, 3, 4, 5 ]);

-- [ 5, 4, 3, 2, 1 ]
```

  

##  `array::sequence`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysequence)
Available since: v3.0.0
The `array::sequence` function creates an array of sequential integers.
API DEFINITION

```surql
array::sequence($length: int) -> array
array::sequence($start: int, $length: int) -> array
```

A single number passed in as an argument will create an array beginning at 0 with a length of the number indicated.

```surql
array::sequence(5);
-- [0, 1, 2, 3, 4]
```

If a second argument is passed into this function, the first argument will be used as the starting point for the array and the second for the length.

```surql
array::sequence(-5, 6);
-- [-5, -4, -3, -2, -1, 0]
```

##  `array::shuffle`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayshuffle)
The `array::shuffle` function randomly shuffles the items of an array.
API DEFINITION

```surql
array::shuffle(array) -> array
```

The following example shows this function, and its possible output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::shuffle([ 1, 2, 3, 4, 5 ]);

-- [ 2, 1, 4, 3, 5 ]
```

  

##  `array::slice`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayslice)
The `array::slice` function returns a slice of an array, based on a starting position, and a length or negative position.
API DEFINITION

```surql
array::slice(array, $start: int, $len: int) -> array
-- Also since 3.0.0
array::slice(array, $slice: range) -> array;
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::slice([ 1, 2, 3, 4, 5 ], 1, 3);

-- [2, 3]
```

The following example shows how you can use this function with a starting position, and a negative position, which will slice off the first and last element from the array:

```surql
RETURN array::slice([ 1, 2, 3, 4, 5 ], 1, -1);

[ 2, 3, 4 ]
```

The following example shows how you can use this function with just a starting position, which will only slice from the beginning of the array:

```surql
RETURN array::slice([ 1, 2, 3, 4, 5 ], 2);

-- [ 3, 4, 5 ]
```

The following example shows how you can use this function with just a negative position, which will only slice from the end of the array:

```surql
RETURN array::slice([ 1, 2, 3, 4, 5 ], -2);

-- [ 4, 5 ]
```

The following example shows how you can use this function with a negative position, and a length of the slice:

```surql
RETURN array::slice([ 1, 2, 3, 4, 5 ], -3, 2);

[ 3, 4 ]
```

An example of post SurrealDB 3.0 syntax in which the function can also take a range:

```surql
['a', 'b', 'c', 'd', 'e'].slice(2..=3);

-- [ 'c', 'd' ]
```

  

##  `array::sort`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysort)
The `array::sort` function sorts the values in an array in ascending or descending order.
API DEFINITION

```surql
array::sort(array) -> array
```

The function also accepts a second boolean parameter which determines the sorting direction. The second parameter can be `true` for ascending order, or `false` for descending order.
API DEFINITION

```surql
array::sort(array, $asc: bool) -> array
```

The function also accepts a second string parameter which determines the sorting direction. The second parameter can be `'asc'` for ascending order, or `'desc'` for descending order.
API DEFINITION

```surql
array::sort(array, $order: string) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::sort([ 1, 2, 1, null, "something", 3, 3, 4, 0 ]);

-- [ null, 0, 1, 1, 2, 3, 3, 4, "something" ]
```

```surql
RETURN array::sort([1, 2, 1, null, "something", 3, 3, 4, 0], false);

-- [ "something", 4, 3, 3, 2, 1, 1, 9, null ]
```

```surql
RETURN array::sort([1, 2, 1, null, "something", 3, 3, 4, 0], "asc");

-- [ null, 0, 1, 1, 2, 3, 3, 4, "something" ]
```

```surql
RETURN array::sort([1, 2, 1, null, "something", 3, 3, 4, 0], "desc");

[ "something", 4, 3, 3, 2, 1, 1, 9, null ]
```

##  `array::sort_lexical`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysort_lexical)
The `array::sort_natural_lexical` function sorts the values in an array in ascending or descending order, with alphabetical strings sorted in lexical order instead of unicode list order.
API DEFINITION

```surql
array::sort_lexical(array) -> array
```

The function also accepts a second boolean parameter which determines the sorting direction. The second parameter can be `true` for ascending order, or `false` for descending order.
API DEFINITION

```surql
array::sort_lexical(array, $asc: bool) -> array
```

The function also accepts a second string parameter which determines the sorting direction. The second parameter can be `'asc'` for ascending order, or `'desc'` for descending order.
API DEFINITION

```surql
array::sort_lexical(array, $order: string) -> array
```

The following example shows that `array::sort_lexical` will sort strings in lexical (alphabetical) order instead of Unicode list order. As an accented 'Á' is listed later in Unicode than regular ASCII letters, the function `array::sort` will show the name 'Álvares' listed after the word 'senhor', but `array::sort_lexical` will show the name at the front of the array instead.

```surql
['Obrigado', 'senhor', 'Álvares'].sort();
['Obrigado', 'senhor', 'Álvares'].sort_lexical();
```

Output

```surql
-------- Query 1 --------

[ 'Obrigado', 'senhor', 'Álvares' ]

-------- Query 2 --------

[ 'Álvares', 'Obrigado', 'senhor' ]
```

##  `array::sort_natural`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysort_natural)
The `array::sort_natural` function sorts the values in an array in ascending or descending order, with numeric strings sorted in numeric order instead of regular string order.
API DEFINITION

```surql
array::sort_natural(array) -> array
```

The function also accepts a second boolean parameter which determines the sorting direction. The second parameter can be `true` for ascending order, or `false` for descending order.
API DEFINITION

```surql
array::sort_natural(array, $asc: bool) -> array
```

The function also accepts a second string parameter which determines the sorting direction. The second parameter can be `'asc'` for ascending order, or `'desc'` for descending order.
API DEFINITION

```surql
array::sort_natural(array, $order: string) -> array
```

The following example shows that `array::sort_natural` will sort numeric strings as if they were numbers. The `array::sort` function, on the other hand, treats a string like '3' as greater than '11' due to the first character in '3' being greater than '1'.
Note that strings sorted in numeric order will still appear after actual numbers, as [a string will always be greater than a number](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/values).

```surql
[8, 9, 10, '3', '2.2', '11'].sort();
[8, 9, 10, '3', '2.2', '11'].sort_natural();
```

Output

```surql
-------- Query --------

[ 8, 9, 10, '11', '2.2', '3' ]

-------- Query 2 (332.667µs) --------

[ 8, 9, 10, '2.2', '3', '11' ]
```

##  `array::sort_natural_lexical`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysort_natural_lexical)
The `array::sort_natural_lexical` function sorts the values in an array in ascending or descending order, while sorting numeric strings in numeric order and alphabetical strings in lexical order.
API DEFINITION

```surql
array::sort_natural_lexical(array) -> array
```

The function also accepts a second boolean parameter which determines the sorting direction. The second parameter can be `true` for ascending order, or `false` for descending order.
API DEFINITION

```surql
array::sort_natural_lexical(array, $asc: bool) -> array
```

The function also accepts a second string parameter which determines the sorting direction. The second parameter can be `'asc'` for ascending order, or `'desc'` for descending order.
API DEFINITION

```surql
array::sort_natural_lexical(array, $order: string) -> array
```

The following example shows that `array::sort_natural_lexical` will sort numeric strings as if they were numbers, and alphabetical strings in lexical order instead of Unicode order. The `array::sort` function, on the other hand, treats a string like '3' as greater than '11' due to the first character in '3' being greater than '1', and sorts the name 'Álvares' after the string 'senhor' because the 'Á' character comes after regular ASCII characters in Unicode.

```surql
['Obrigado', 'senhor', 'Álvares', 8, 9, 10, '3', '2.2', '11'].sort();
['Obrigado',
  'senhor',
  'Álvares',
  8,
  9,
  10,
  '3',
  '2.2',
  '11'].sort_natural_lexical();
```

Output

```surql
-------- Query --------

[ 8, 9, 10, '11', '2.2', '3', 'Obrigado', 'senhor', 'Álvares' ]

-------- Query 2 (332.667µs) --------

[ 8, 9, 10, '2.2', '3', '11', 'Álvares', 'Obrigado', 'senhor' ]
```

##  `array::sort::asc`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysortasc)
The `array::sort::asc` function is a shorthand convenience function for the `array::sort` function, to sort values in an array in ascending order.
API DEFINITION

```surql
array::sort::asc(array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::sort::asc([ 1, 2, 1, null, "something", 3, 3, 4, 0 ]);

-- [ null, 0, 1, 1, 2, 3, 3, 4, "something" ]
```

  

##  `array::sort::desc`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraysortdesc)
The `array::sort::desc` function is a shorthand convenience function for the `array::sort` function, to sort values in an array in descending order.
API DEFINITION

```surql
array::sort::desc(array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::sort::desc([ 1, 2, 1, null, "something", 3, 3, 4, 0 ]);

-- [ "something", 4, 3, 3, 2, 1, 1, 9, null ]
```

  

##  `array::swap`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayswap)
The `array::swap` function swaps two values of an array based on indexes.
API DEFINITION

```surql
array::swap(array, $from: int, $to: int) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::swap(["What's",
  "its",
  "got",
  "in",
  "it",
  "pocketses?"],
  1,
  4);
```

Output

```surql
[
	"What's",
	'it',
	'got',
	'in',
	'its',
	'pocketses?'
]
```

The following example shows how you can use this function with a positive index, and a negative index, which will swap the first and last element from the array:

```surql
RETURN array::swap([ 1, 2, 3, 4, 5 ], 0, -1);

-- [ 5, 2, 3, 4, 1 ]
```

An error will be returned if any of the indexes are invalid that informs of range of possible indexes that can be used.

```surql
RETURN array::swap([0, 1], 100, 1000000);
```

Output

```surql
'Incorrect arguments for function array::swap(). Argument 1 is out of range. Expected a number between -2 and 2'
```

  

##  `array::transpose`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraytranspose)
The `array::transpose` function is used to perform 2d array transposition. It is similar to zipping in other programming languages except that when arrays of differing sizes are transposed they are 'layered' on top of each other, producing an output with the same length as the longer array instead of stopping at the length of the smaller array.
API DEFINITION

```surql
array::transpose(array<array>) -> array<array>
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::transpose([[0, 1], [2, 3]]);

-- [ [0, 2], [1, 3] ]
```

The layering of the above example can be visualised as follows.

```text
0 1
2 3
↓ ↓ 
0 1   
2 3
```

Imagining a Rubik's Cube is another easy way to conceptualize this function.

```surql
RETURN array::transpose([
    ['🟦', '🟥', '🟩'],
    ['⬜', '🟦', '🟨'],
    ['🟧', '🟧', '🟥']
]);
```

The output shows the same blocks, but lined up top to bottom instead of left to right.

```surql
[
	[
		'🟦',
		'⬜',
		'🟧'
	],
	[
		'🟥',
		'🟦',
		'🟧'
	],
	[
		'🟩',
		'🟨',
		'🟥'
	]
]
```

Another example of the function used for the statistics of two people:

```surql
[["Name", "Age"], ["Billy", 25], ["Alice", 30]].transpose();
```

Output

```surql
[
	[
		'Name',
		'Billy',
		'Alice'
	],
	[
		'Age',
		25,
		30
	]
]
```

When the input arrays differ in length, `NONE` is added at indices where no item is found. Take the following movies for example, in which one — Groundhog Day — does not have a bad guy.

```surql
[
    ['Movie', 'Bad guy'], 
    ['Avengers: Infinity War', 'Thanos'], 
    ['Groundhog Day'],
    ['Star Wars', 'Palpatine']
].transpose();
```

Output since 2.2Output before 2.2

```surql
[
	[
		'Movie',
		'Avengers: Infinity War',
		'Groundhog Day',
		'Star Wars'
	],
	[
		'Bad guy',
		'Thanos',
		NONE,
		'Palpatine'
	]
]
```

```surql
[
	[
		'Movie',
		'Avengers: Infinity War',
		'Groundhog Day',
		'Star Wars'
	],
	[
		'Bad guy',
		'Thanos',
		'Palpatine'
	]
]
```

This new behaviour allows transposed arrays to be transposed once more to restore the original output, except with `NONE` added in all the indexes that lack in any array.

```surql
[
	[
		'Movie',
		'Bad guy'
	],
	[
		'Avengers: Infinity War',
		'Thanos'
	],
	[
		'Groundhog Day'
	],
	[
		'Star Wars',
		'Palpatine'
	]
].transpose().transpose();
```

Output

```surql
[
	[
		'Movie',
		'Bad guy'
	],
	[
		'Avengers: Infinity War',
		'Thanos'
	],
	[
		'Groundhog Day',
		NONE
	],
	[
		'Star Wars',
		'Palpatine'
	]
]
```

##  `array::union`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayunion)
The `array::union` function combines two arrays together, removing duplicate values, and returning a single array.
API DEFINITION

```surql
array::union(array, $other: array) -> array
```

The following example shows this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
RETURN array::union([1, 2, 1, 6], [1, 3, 4, 5, 6]);

-- [ 1, 2, 6, 3, 4, 5 ]
```

  
  

##  `array::windows`[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arraywindows)
API DEFINITION

```surql
array::windows(array, $window_size: int) -> array
```

The `array::windows` function returns a number of arrays of length `size` created by moving one index at a time down the original array. The arrays returned are guaranteed to be of length `size`. As a result, the function will return an empty array if the length of the original array is not large enough to create a single output array.
The following examples show this function, and its output, when used in a [`RETURN`](https://surrealdb.com/docs/reference/query-language/statements/return) statement:

```surql
LET $array = [1, 2, 3, 4];
RETURN array::windows($array, 2);
RETURN array::windows($array, 5);
```

Response

```surql
[ [1, 2], [2, 3], [3, 4] ];
[];
```

An example of the same function used in a `RELATE` statement:

```surql
CREATE person:grandfather, person:father, person:son;

FOR $pair IN array::windows(["grandfather", "father", "son"], 2) {
    LET $first = type::record("person", $pair[0]);
    LET $second = type::record("person", $pair[1]);
    RELATE $first->father_of->$second;
};

SELECT 
  id, 
  ->father_of->person AS sons,
  ->father_of->person->father_of->person AS grandsons
FROM person;
```

##  Method chaining[](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#method-chaining)
Method chaining allows functions to be called using the `.` dot operator on a value of a certain type instead of the full path of the function followed by the value.

```surql
-- Traditional syntax
array::push(["Again", "again"], "again");

-- Method chaining syntax
["Again", "again"].push("again");
```

Response

```surql
["Again", "again", "again"]
```

This is particularly useful for readability when a function is called multiple times.

```surql
-- Traditional syntax
array::join(array::push(["Again", "again"], "again"), " and ");

-- Method chaining syntax
["Again", "again"].push("again").join(" and ");
```

Response

```surql
"Again and again and again"
```
