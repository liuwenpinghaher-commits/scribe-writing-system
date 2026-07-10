---
title: "https://surrealdb.com/docs/learn/querying/graphql/sample-queries"
url: "https://surrealdb.com/docs/learn/querying/graphql/sample-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/graphql/sample-queries

Source: https://surrealdb.com/docs/learn/querying/graphql/sample-queries

Available since: v3.1.0
From SurrealDB 3.1.0, SurrealDB’s GraphQL layer uses **Apollo-style** names: a **pluralised list** field (for example `people` for table `person`), a **singular fetch** field `person(id: …)`, and `people_aggregate` for aggregates. Under the hood these map to SurrealQL-style reads (typically `SELECT`). The SurrealQL here is a rough equivalent for the same or similar data shape. See [GraphQL overview](https://surrealdb.com/docs/learn/querying/graphql/overview#schema-naming) for the full naming table.
Before trying the examples, enable GraphQL and define data in the current namespace and database (see [GraphQL overview](https://surrealdb.com/docs/learn/querying/graphql/overview) using [`DEFINE CONFIG GRAPHQL AUTO`](https://surrealdb.com/docs/reference/query-language/statements/define/config)). The snippets below assume:
  * •
Namespace **`main`**, database**`main`**
  * •
Root authentication **`root`**/**`secret`**
  * •
A `person` table with `name` and `age`, and records `person:simon` and `person:marcus` as in [GraphQL via HTTP](https://surrealdb.com/docs/learn/querying/graphql/via-http)

Schema and sample data

```surql
DEFINE TABLE person SCHEMAFULL;
DEFINE FIELD name ON TABLE person TYPE string;
DEFINE FIELD age ON TABLE person TYPE number;
CREATE person:simon SET name = "Simon", age = 23;
CREATE person:marcus SET name = "Marcus", age = 28;
DEFINE CONFIG GRAPHQL AUTO;
```

##  List records and choose fields[](https://surrealdb.com/docs/learn/querying/graphql/sample-queries#list-records-and-choose-fields)
GraphQL here returns a list of objects, similar to `SELECT` without `ONLY`.
GraphQLSurrealQLcURL (HTTP)
Query

```graphql
query {
	people {
		name
		age
	}
}
```

Output

```graphql
{
	"data": {
		"people": [
			{
				"age": 28,
				"name": "Marcus"
			},
			{
				"age": 23,
				"name": "Simon"
			}
		]
	}
}
```

Query

```surql
SELECT name, age FROM person;
```

Output

```surql
[
	{
		age: 28,
		name: 'Marcus'
	},
	{
		age: 23,
		name: 'Simon'
	}
]
```

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d '{ "query": "query { people { name age } }" }' http://localhost:8000/graphql
```

##  Fetch a single record by id[](https://surrealdb.com/docs/learn/querying/graphql/sample-queries#fetch-a-single-record-by-id)
Use **`person(id: …)`**with the**record key** (`simon`, not `person:simon` in the argument). The GraphQL `id` field on the result is the full record id.
GraphQLSurrealQLcURL (HTTP)
Query

```graphql
query {
	person(id: "simon") {
		id
		name
		age
	}
}
```

Output

```graphql
{
	"data": {
		"person": {
			"id": "person:simon",
			"name": "Simon",
			"age": 23
		}
	}
}
```

Query

```surql
SELECT * FROM ONLY person:simon;
```

Output

```surql
{
	age: 23,
	id: person:simon,
	name: 'Simon'
}
```

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d '{ "query": "query { person(id: \"simon\") { id name age } }" }' http://localhost:8000/graphql
```

##  Limit how many records are returned[](https://surrealdb.com/docs/learn/querying/graphql/sample-queries#limit-how-many-records-are-returned)
GraphQL uses **`limit`**(and optional**`start`**for offset). SurrealQL uses`LIMIT` / `START` and `ONLY` to return a single record as opposed to an array containing a single record.
GraphQLSurrealQLcURL (HTTP)
Query

```graphql
query {
	people(limit: 1) {
		name
		age
	}
}
```

Output

```graphql
{
	"data": {
		"people": [
			{
				"age": 28,
				"name": "Marcus"
			}
		]
	}
}
```

Query

```surql
SELECT name, age FROM ONLY person LIMIT 1;
```

Output

```surql
{
	age: 28,
	name: 'Marcus'
}
```

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d '{ "query": "query { people(limit: 1) { name age } }" }' http://localhost:8000/graphql
```

##  Filter records[](https://surrealdb.com/docs/learn/querying/graphql/sample-queries#filter-records)
GraphQL accepts **`filter`**or**`where`**with the generated input type for the table. For a scalar field, use comparison keys such as**`eq`**,**`ne`**,**`gt`**, and**`lt`**where the schema allows them.
GraphQLSurrealQLcURL (HTTP)
Query

```graphql
query {
	people(where: { age: { eq: 23 } }) {
		name
	}
}
```

Output

```graphql
{
	"data": {
		"people": [
			{
				"name": "Simon"
			}
		]
	}
}
```

Query

```surql
SELECT name FROM person WHERE age = 23;
```

Output

```surql
[
	{
		name: 'Simon'
	}
]
```

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d '{ "query": "query { people(where: { age: { eq: 23 } }) { name } }" }' http://localhost:8000/graphql
```

##  Order results[](https://surrealdb.com/docs/learn/querying/graphql/sample-queries#order-results)
Use an **`order`**argument with**`asc`**or**`desc`**and a field name.
GraphQLSurrealQLcURL (HTTP)
Query

```graphql
query {
	people(order: { asc: age }) {
		name
		age
	}
}
```

Output

```graphql
{
	"data": {
		"people": [
			{
				"age": 23,
				"name": "Simon"
			},
			{
				"age": 28,
				"name": "Marcus"
			}
		]
	}
}
```

Query

```surql
SELECT name, age FROM person ORDER BY name ASC;
```

Output

```surql
[
	{
		age: 23,
		name: 'Simon'
	},
	{
		age: 28,
		name: 'Marcus'
	}
]
```

```bash
curl -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" \
  -H "Accept: application/json"
  -d '{ "query": "query { people(order: { asc: age }) { name age } }" }' http://localhost:8000/graphql
```

##  Next steps[](https://surrealdb.com/docs/learn/querying/graphql/sample-queries#next-steps)
  * •
Query the same endpoint from HTTP clients: [GraphQL via HTTP](https://surrealdb.com/docs/learn/querying/graphql/via-http)
  * •
Optional: [Bruno](https://surrealdb.com/docs/learn/querying/graphql/via-bruno) or [Surrealist](https://surrealdb.com/docs/learn/querying/graphql/via-surrealist)

For the full configuration surface (tables, functions, limits), see [`DEFINE CONFIG GRAPHQL`](https://surrealdb.com/docs/reference/query-language/statements/define/config).
