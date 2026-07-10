---
title: "https://surrealdb.com/docs/explore/surrealist/concepts/designing-the-database-schema"
url: "https://surrealdb.com/docs/explore/surrealist/concepts/designing-the-database-schema"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/surrealist/concepts/designing-the-database-schema

Source: https://surrealdb.com/docs/explore/surrealist/concepts/designing-the-database-schema

The Designer view allows you to graphically visualise, design, and modify your database schema in real time. This view can speed up the creation of tables, indexes, fields, and more. Additionally it will plot your current schema into a diagram representation to view the structure of your database and relationships between its tables.
![Surrealist designer view](https://surrealdb.com/docs/explore/surrealist/concepts/~/assets/img/image/surrealist/designer.png)
###  Table graph panel[](https://surrealdb.com/docs/explore/surrealist/concepts/designing-the-database-schema#table-graph-panel)
The table graph renders an interactive diagram representation of your schema. You can use your mouse to move and zoom around the canvas and press any table to modify it. Surrealist will make a best effort to correctly and clearly visualise your tables automatically.
When rendering the diagram, Surrealist will attempt to detect whether a table is a regular table or an edge table. It does so by checking for the presence of an `in` and `out` field. Surrealist expects these two fields to be configured as `record` types and correctly define the table(s) they point to. This works for both schemafull and schemaless tables.
On the top right of this panel you will find a + button which allows you to easily create new tables and edge tables, similar to the one found in the Explorer view.
The Settings icon ⚙ provides the option to alter the appearance of tables in the diagram. This can either be set to `fields` when you want to display all defined fields, `summary` for showing condensed stats for each table, or `simple` when you only want to display the name of each table.
###  Table designer panel[](https://surrealdb.com/docs/explore/surrealist/concepts/designing-the-database-schema#table-designer-panel)
Clicking any table in the table graph will open the table designer panel. This is where you can visually update the structure of a table, including permissions, fields, indexes, events, and more.
In addition, you can press the delete button in the top right to remove a table from your database.
###  Accessing underlying schema information[](https://surrealdb.com/docs/explore/surrealist/concepts/designing-the-database-schema#accessing-underlying-schema-information)
The Designer view is built on top of the powerful [INFO FOR DB](https://surrealdb.com/docs/reference/query-language/statements/info#database-information) and [INFO FOR TABLE](https://surrealdb.com/docs/reference/query-language/statements/info#table-information) statements, which you can utilize yourself to programmatically extract schema information from the database.
