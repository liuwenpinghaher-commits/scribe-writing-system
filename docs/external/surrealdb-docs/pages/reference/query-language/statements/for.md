---
title: "https://surrealdb.com/docs/reference/query-language/statements/for"
url: "https://surrealdb.com/docs/reference/query-language/statements/for"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/for

Source: https://surrealdb.com/docs/reference/query-language/statements/for

The `FOR` statement can be used to iterate over the values of an array, and to perform certain actions with those values.
Note
A `FOR` loop currently cannot modify items outside its own scope, such as variables declared before the loop.
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
FOR @item IN @iterable {
@block
};
```

FOR@itemIN@iterable{@block};
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/for#example-usage)
The following query shows example usage of this statement.

```surql
-- Create a person for everyone in the array
FOR $name IN ['Tobie', 'Jaime'] {
	CREATE type::record('person', $name) CONTENT {
		name: $name
	};
};
```

The following query shows the `FOR` statement being used update a property on every user matching certain criteria.

```surql
-- Set can_vote to true for every person over 18 years old.
FOR $person IN (SELECT VALUE id FROM person WHERE age >= 18) {
	UPDATE $person SET can_vote = true;
};
```

##  Ranges in FOR loops[](https://surrealdb.com/docs/reference/query-language/statements/for#ranges-in-for-loops)
A `FOR` loop can also be made out of a [range UUID](https://surrealdb.com/docs/reference/query-language/language-primitives/data-types/ranges) of integers.

```surql
FOR $year IN 0..=2024 {
    CREATE historical_events SET
        for_year = $year,
        events = "To be added";
};
```

##  Limitations of FOR loops[](https://surrealdb.com/docs/reference/query-language/statements/for#limitations-of-for-loops)
Parameters declared outside of a `FOR` loop can be used inside the loop.

```surql
LET $table1 = "person";
LET $table2 = "cat";

FOR $key in 0..4 {
    CREATE type::record($table1, $key);
	  CREATE type::record($table2, $key);
};
```

However, they currently cannot be modified inside a loop, making an operation like the following impossible.

```surql
LET $init = [];

FOR $num IN 1..=3 {
	$init += $num;
};
-- Error: 'assignment operators are only allowed in SET and DUPLICATE KEY UPDATE clauses'

RETURN $init;
```

In this case, the [`array::fold`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayfold) and [`array::reduce`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/array#arrayreduce) functions can often be used to accomplish the intended behaviour.

```surql
(<array>1..=3).reduce(|$one, $two| $one + $two);
```

Output

```surql
6
```
