---
title: "https://surrealdb.com/docs/learn/querying/gql/sample-queries"
url: "https://surrealdb.com/docs/learn/querying/gql/sample-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/gql/sample-queries

Source: https://surrealdb.com/docs/learn/querying/gql/sample-queries

Available since: v3.2.0
The examples below use the same **person / knows / city** seed graph as the GQL language tests. SurrealQL snippets return the **same or equivalent row shape** , but are not a mechanical translation of the GQL compiler; they are idiomatic reads you can compare while learning.
##  Prerequisites[](https://surrealdb.com/docs/learn/querying/gql/sample-queries#prerequisites)
Start a local instance with GQL enabled and load the seed graph — see [GQL via HTTP](https://surrealdb.com/docs/learn/querying/gql/via-http#load-sample-data).
You can run the GQL examples in either of these ways:  
| Approach  | How  |  
| --- | --- |  
| **HTTP**  | cURL to `POST /gql` (shown in each GQL tab) — server needs `--allow-experimental gql`  |  
| **REPL**  |  [`eval::gql("…")`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval#evalgql) in `surreal sql` or Surrealist — also needs [`--allow-eval-query`](https://surrealdb.com/docs/learn/security/authorization/capabilities#eval-queries) on the process that runs the engine (embedded `surreal sql`, or `surreal start` for remote)  |  
Example REPL equivalent for the first query:

```surql
eval::gql("MATCH (n:person) RETURN n.name AS name ORDER BY name");
-- [{ name: 'A' }, { name: 'B' }, { name: 'C' }]
```

##  List nodes by label[](https://surrealdb.com/docs/learn/querying/gql/sample-queries#list-nodes-by-label)
GQLSurrealQL
Query

```gql
MATCH (n:person) RETURN n.name AS name ORDER BY name
```

cURL

```bash
curl -sS -X POST -u "root:secret" \
  -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json" -H "Content-Type: text/plain" \
  -d 'MATCH (n:person) RETURN n.name AS name ORDER BY name' \
  http://localhost:8000/gql
```

Output

```json
[
	{ "name": "A" },
	{ "name": "B" },
	{ "name": "C" }
]
```

Query

```surql
SELECT name FROM person ORDER BY name;
```

Output

```surql
[
	{ name: 'A' },
	{ name: 'B' },
	{ name: 'C' }
]
```

##  Traverse an edge with a property filter[](https://surrealdb.com/docs/learn/querying/gql/sample-queries#traverse-an-edge-with-a-property-filter)
Only **person → person** `knows` edges with `since > 2020`.
GQLSurrealQL
Query

```gql
MATCH (a:person)-[k:knows]->(b:person)
WHERE k.since > 2020
RETURN a.name, b.name
ORDER BY a.name
```

cURL

```bash
curl -sS -X POST -u "root:secret" \
  -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json" -H "Content-Type: text/plain" \
  -d 'MATCH (a:person)-[k:knows]->(b:person) WHERE k.since > 2020 RETURN a.name, b.name ORDER BY a.name' \
  http://localhost:8000/gql
```

Output

```json
[
	{ "a.name": "A", "b.name": "B" }
]
```

Query

```surql
SELECT in.name AS `a.name`, out.name AS `b.name`
FROM knows
WHERE since > 2020 AND record::tb(out) = 'person'
ORDER BY in.name;
```

Output

```surql
[
	{ 'a.name': 'A', 'b.name': 'B' }
]
```

##  Optional match[](https://surrealdb.com/docs/learn/querying/gql/sample-queries#optional-match)
Every `person`, with an optional `knows` edge to a `city` when one exists.
GQLSurrealQL
Query

```gql
MATCH (a:person)
OPTIONAL MATCH (a)-[k:knows]->(b:city)
RETURN a.name AS name, b.name AS city
ORDER BY name
```

cURL

```bash
curl -sS -X POST -u "root:secret" \
  -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json" -H "Content-Type: text/plain" \
  -d 'MATCH (a:person) OPTIONAL MATCH (a)-[k:knows]->(b:city) RETURN a.name AS name, b.name AS city ORDER BY name' \
  http://localhost:8000/gql
```

Output

```json
[
	{ "name": "A", "city": "London" },
	{ "name": "B", "city": null },
	{ "name": "C", "city": null }
]
```

Query

```surql
SELECT name, array::first(->knows->city.name) AS city
FROM person
ORDER BY name;
```

Output

```surql
[
	{ name: 'A', city: 'London' },
	{ name: 'B', city: NONE },
	{ name: 'C', city: NONE }
]
```

##  Aggregation with GROUP BY[](https://surrealdb.com/docs/learn/querying/gql/sample-queries#aggregation-with-group-by)
Count outgoing **person → person** `knows` edges per person.
GQLSurrealQL
Query

```gql
MATCH (a:person)-[:knows]->(b:person)
RETURN a.name AS name, count(*) AS c
GROUP BY a.name
ORDER BY name
```

cURL

```bash
curl -sS -X POST -u "root:secret" \
  -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json" -H "Content-Type: text/plain" \
  -d 'MATCH (a:person)-[:knows]->(b:person) RETURN a.name AS name, count(*) AS c GROUP BY a.name ORDER BY name' \
  http://localhost:8000/gql
```

Output

```json
[
	{ "name": "A", "c": 1 },
	{ "name": "B", "c": 2 },
	{ "name": "C", "c": 1 }
]
```

Query

```surql
SELECT in.name AS name, count() AS c
FROM knows
WHERE record::tb(out) = 'person'
GROUP BY in.name
ORDER BY name;
```

Output

```surql
[
	{ name: 'A', c: 1 },
	{ name: 'B', c: 2 },
	{ name: 'C', c: 1 }
]
```

##  What to try next[](https://surrealdb.com/docs/learn/querying/gql/sample-queries#what-to-try-next)
The language-test corpus under `language-tests/tests/opengql/` in the SurrealDB repository covers variable-length quantifiers (`->{1,3}`, `->*`), path search (`ALL SHORTEST`, `SHORTEST k`), multi-pattern comma joins, and [mutations](https://surrealdb.com/docs/learn/querying/gql/mutations). Variable-length and path patterns have no single-line SurrealQL equivalent — they are the main reason to reach for GQL for reads; mutations are the ISO-native way to change graph data in the same program as `MATCH`.
