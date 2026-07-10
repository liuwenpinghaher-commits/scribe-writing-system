---
title: "https://surrealdb.com/docs/reference/query-language/statements/explain"
url: "https://surrealdb.com/docs/reference/query-language/statements/explain"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/explain

Source: https://surrealdb.com/docs/reference/query-language/statements/explain

Available since: v3.0.0
Note
The output for the `EXPLAIN` statement is for informational purposes and subject to change. Be sure not to develop tools around it that rely on a single predictible output.
The `EXPLAIN` statement is used to display the query planner for a statement.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/explain#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
EXPLAIN [ ANALYZE ] [ FORMAT TEXT | JSON ] @statement
```

EXPLAINANALYZEFORMATTEXTJSON@statement
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/explain#example-usage)
An `EXPLAIN` statement is one that can be appended to another statement that does not modify database resources, i.e. a `SELECT` statement or another statement that returns a value.
The two main decisions to make when using an `EXPLAIN` statement are:
  * •
Use default text format or add `FORMAT JSON` to output the format in JSON?
  * •
Add the `ANALYZE` clause after `EXPLAIN`

The following example shows the four possible types of output when followed by a simple string.

```surql
EXPLAIN "yourself!";
EXPLAIN ANALYZE "yourself!";
EXPLAIN FORMAT JSON "yourself!";
EXPLAIN ANALYZE FORMAT JSON "yourself!";
```

As the output shows, the `ANALYZE` clause adds information on the metrics and total rows.
Output

```surql
-------- Query --------

"Expr [ctx: Rt] [expr: 'yourself!']"

-------- Query --------

"Expr [ctx: Rt] [expr: 'yourself!'] {rows: 0, batches: 0, elapsed: 0ns}

Total rows: 1"

-------- Query --------

{
	attributes: {
		expr: "'yourself!'"
	},
	context: 'Rt',
	expressions: [
		{
			role: 'expr',
			sql: "'yourself!'"
		}
	],
	operator: 'Expr'
}

-------- Query --------

{
	attributes: {
		expr: "'yourself!'"
	},
	context: 'Rt',
	expressions: [
		{
			role: 'expr',
			sql: "'yourself!'"
		}
	],
	metrics: {
		elapsed_ns: 0,
		output_batches: 0,
		output_rows: 0
	},
	operator: 'Expr',
	total_rows: 1
}
```

###  Context[](https://surrealdb.com/docs/reference/query-language/statements/explain#context)
The `context` field in an `EXPLAIN` statement refers to the minimum context level for an operation: `Rt` (root), `Ns` (namespace), or `Db` (database) level.
###  Operator types[](https://surrealdb.com/docs/reference/query-language/statements/explain#operator-types)
The `operator` field in the output of an `EXPLAIN` statement is the most relevant area to take note of. Here is a list of many of the operator types you will see in the statement output.

```text
Aggregate
Compute
CountScan
Explain
ExplainAnalyze
Expr
Fetch
Filter
Foreach
FullTextScan
GraphEdgeScan
IfElse
IndexCountScan
IndexScan
KnnScan
Let
Limit
ProjectValue
Project
SelectProject
ReferenceScan
Return
Scan
Sequence
Sleep
SourceExpr
Split
Union
UnwrapExactlyOne
InfoDatabase
InfoIndex
InfoNamespace
InfoRoot
InfoTable
InfoUser
ExternalSort
Sort
SortByKey
RandomShuffle
SortTopK
SortTopKByKey
```

This allows you to get an insight into exactly what sort of work is being performed by the database when a query is executed.
For example, take the following simple example in which one `person` record has a single friend. The final two queries return the same result, but one is a `SELECT...FROM ONLY` query while the other is a direct destructuring of the link from its record id.

```surql
CREATE person:one, person:two;
RELATE person:one->friend->person:two;

EXPLAIN SELECT ->friend->person AS friends FROM ONLY person:one;
EXPLAIN person:one.{ friends: ->friend->person };
```

Not only is the second query faster, but we can see why as the first query is doing more work with four operations instead of one.
Output

```surql
-------- Query 1 --------

'UnwrapExactlyOne [ctx: Db]
    Project [ctx: Db]
          field.lookup: GraphEdgeScan [ctx: Db] [direction: ->, tables: person, output: TargetId]
                    GraphEdgeScan [ctx: Db] [direction: ->, tables: friend, output: TargetId]
                                  CurrentValueSource [ctx: Rt]
                                          RecordIdScan [ctx: Db] [record_id: person:one]'

-------- Query 2 --------

'Expr [ctx: Db] [expr: (person:one).{ friends: ->friend->person }]'
```

Here is an example of output for a query of a complexity more similar to those seen in production applications.

```surql
EXPLAIN ANALYZE SELECT
  id as commentId,
  in.id as id,
  in.creationDate as creationDate
FROM is_comment_of
WHERE out = media_text_test:0
  AND in.creationDate < d'2026-01-09T00:00:00.000Z'
ORDER BY in.creationDate DESC
LIMIT 2;
```

Output

```surql
"Project [ctx: Db] {rows: 0, batches: 0, elapsed: 1.71µs}
    Limit [ctx: Db] [limit: 2] {rows: 0, batches: 0, elapsed: 13.92µs}
            SortTopKByKey [ctx: Db] [sort_keys: in.creationDate DESC, limit: 2] {rows: 0, batches: 0, elapsed: 7.50µs}
                        TableScan [ctx: Db] [table: is_comment_of, direction: Forward, predicate: out = media_text_test:0 AND in.creationDate < d'2026-01-09T00:00:00Z'] {rows: 0, batches: 0, elapsed: 361.42µs}
                        
                        Total rows: 0"
```

###  Filtered KNN and the `predicate` attribute on `KnnScan`[](https://surrealdb.com/docs/reference/query-language/statements/explain#filtered-knn-and-the-predicate-attribute-on-knnscan)
Available since: v3.1.5
When a [K-nearest neighbours search](https://surrealdb.com/docs/reference/query-language/language-primitives/operators#knn) over an indexed vector field is combined with an additional non-KNN condition, the planner pushes that residual condition _into_ the index search. Non-matching candidates are rejected during the graph traversal, before they can occupy one of the `K` result slots, rather than being filtered out after the neighbours have been retrieved.
This behaviour can be seen by appending the `EXPLAIN` clause to the end of a query to show its plan. Here, the `KnnScan` operator surfaces this pushed-down condition as a `predicate` attribute, in the same way that `TableScan` exposes its own `predicate`.

```surql
DEFINE INDEX idx_pt ON pts FIELDS point HNSW DIMENSION 4;
INSERT INTO pts [
	{ point: [1, 2, 3, 4], flag: true },
	{ point: [4, 3, 2, 1], flag: false },
	{ point: [3, 3, 3, 3], flag: true }
];

EXPLAIN SELECT id, flag, vector::distance::knn() AS distance FROM pts
	WHERE flag = true AND point <|2,40|> [2, 3, 4, 5]
	ORDER BY distance;
```

Output

```surql
'SelectProject [ctx: Db] [projections: id, flag, distance]
    SortByKey [ctx: Db] [sort_keys: distance ASC]
        Compute [ctx: Db] [fields: distance = vector::distance::knn(...)]
            Filter [ctx: Db] [predicate: flag = true]
                KnnScan [ctx: Db] [index: idx_pt, k: 2, ef: 40, dimension: 4, predicate: flag = true]'
```

The `KnnScan` line shows that the index `idx_pt` is searched for `k: 2` neighbours with an exploration factor of `ef: 40` (the two values of the `` operator), and that the `flag = true` condition is applied *inside* the search as a `predicate`. The same condition also appears on the `Filter` line above; the difference is that the `predicate` on `KnnScan` is what causes non-matching candidates to be discarded *during* the search rather than only afterwards. Without an extra condition the `predicate` attribute is absent. DISKANN indexes use the same `KnnScan` operator and render an identical line.
