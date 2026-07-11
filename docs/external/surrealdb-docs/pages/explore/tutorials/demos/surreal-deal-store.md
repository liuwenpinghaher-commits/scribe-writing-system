---
title: "https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store"
url: "https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store

Source: https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store

To further test out SurrealDB and SurrealQL functionality, we've included two demo datasets here in `.surql` files which you can download and [`import`](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import) into SurrealDB using the [CLI](https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview).
##  Surreal Deal Store - there is a lot in store for you![](https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store#surreal-deal-store---there-is-a-lot-in-store-for-you)
Surreal Deal Store is our new and improved demo dataset based on our [SurrealDB Store](https://surrealdb.store/).  
The dataset is made up of 12 tables using both [graph relations](https://surrealdb.com/docs/reference/query-language/statements/relate) and [record links](https://surrealdb.com/docs/reference/query-language/language-primitives/record-links).
In the diagram below, the nodes in pink are the [standard tables](https://surrealdb.com/docs/reference/query-language/statements/define/table), the ones in purple represent the [edge tables](https://surrealdb.com/docs/reference/query-language/statements/relate) which shows relationships between records and SurrealDB as a graph database. The nodes in grey are the [pre-computed table views](https://surrealdb.com/docs/reference/query-language/statements/define/table).
![](https://surrealdb.com/docs/explore/tutorials/demos/~/assets/img/image/light/surreal-deal-store-light.png)![](https://surrealdb.com/docs/explore/tutorials/demos/~/assets/img/image/dark/surreal-deal-store.png)
###  Download[](https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store#download)
SurrealDB 3.xSurrealDB 2.x  
| Dataset  | URL  |  
| --- | --- |  
| [Surreal Deal Store (mini)](https://datasets.surrealdb.com/datasets/surreal-deal-store/mini-v3.surql)  | <https://datasets.surrealdb.com/datasets/surreal-deal-store/mini-v3.surql>  |  
| Dataset  | URL  |  
| --- | --- |  
| [Surreal Deal Store](https://datasets.surrealdb.com/surreal-deal-store.surql)  | <https://datasets.surrealdb.com/surreal-deal-store.surql>  |  
| [Surreal Deal Store (mini)](https://datasets.surrealdb.com/surreal-deal-store-mini.surql)  | <https://datasets.surrealdb.com/surreal-deal-store-mini.surql>  |  
###  Import[](https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store#import)
Once one of the datasets has been downloaded, it's now time to [start the server](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/start).

```bash
# Create a new in-memory server
surreal start --user root --pass secret --allow-all
```

Lastly, use the [import command](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/import) to add the dataset.
Use the command below to import the [surreal deal store dataset](https://datasets.surrealdb.com/surreal-deal-store.surql):

```bash
surreal import --endpoint http://localhost:8000 --user root --pass secret \
  --ns main --db main surreal-deal-store.surql
```

To import the surreal downloaded the [Surreal Deal store (mini)](https://datasets.surrealdb.com/surreal-deal-store-mini.surql) use the command below:

```bash
surreal import --endpoint http://localhost:8000 --user root --pass secret \
  --ns main --db main surreal-deal-store-mini.surql
```

Please be aware that the import process might take a few seconds.
###  Using Curl[](https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store#using-curl)
First, start the SurrealDB server:

```bash
# Create a new in-memory server
surreal start --user root --pass secret --allow-all
```

Then download the file and load it into the database:

```bash
# Download the file
curl -L "https://datasets.surrealdb.com/surreal-deal-store.surql" -o surreal-deal-store.surql

# Load the file into the database using the rest endpoint
curl -v -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" --data-binary @surreal-deal-store.surql http://localhost:8000/import
```

If you want to use the mini version:

```bash
# Download the file
curl -L "https://datasets.surrealdb.com/surreal-deal-store-mini.surql" -o surreal-deal-store-mini.surql

# Load the file into the database using the rest endpoint
curl -v -X POST -u "root:secret" -H "Surreal-NS: main" -H "Surreal-DB: main" -H "Accept: application/json" --data-binary @surreal-deal-store-mini.surql http://localhost:8000/import
```

###  Sample queries[](https://surrealdb.com/docs/explore/tutorials/demos/surreal-deal-store#sample-queries)
Here are some sample queries you can run on the Surreal Deal Store dataset. We've also included a [Surrealist Mini](https://app.surrealdb.com/mini) below to help you run these queries.
Note
The query results below have been limited to 4 rows for brevity. If you remove the `LIMIT 4` clause from the queries, you'll see the full results.
