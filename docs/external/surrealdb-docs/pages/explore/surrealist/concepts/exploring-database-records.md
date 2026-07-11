---
title: "https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records"
url: "https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records

Source: https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records

The second view you can find in Surrealist is the Explorer view, which lists out tables and allows you to browse through all records. This view is especially useful when you want to effortlessly explore your data, compare records, or edit their contents.
![Surrealist explorer view](https://surrealdb.com/docs/explore/surrealist/concepts/~/assets/img/image/surrealist/explorer.png)
###  Tables panel[](https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records#tables-panel)
As the name implies, the tables panel will list out all tables in the database. The icon to the left indicates if a table is a normal table or an edge table. The + button in the top right of this panel allows you to quickly define new tables without switching to the Designer view.
Note
In the [Designer view](https://surrealdb.com/docs/explore/surrealist/concepts/designing-the-database-schema) section we will explain more in-depth about what constitutes tables as normal or edge tables.
###  Record explorer panel[](https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records#record-explorer-panel)
After selecting a table in the tables panel, the records in this table are listed out here, grouped into navigable pages. You can press any record to open it in the inspector panel where you can view and edit record contents and view its relationships.
Pressing the ▼ button in the top right of this panel expands an input in which you can enter a [WHERE](https://surrealdb.com/docs/reference/query-language/statements/select#filter-queries-using-the-where-clause) clause to filter down the displayed records on certain conditions.
Additionally, the + button can be used to manually create new records in the current table.
###  Inspector panel[](https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records#inspector-panel)
The inspector panel, although available globally, is mostly used in the Explorer view to view and edit the contents of a record. You can also use the inspector to view and follow the relationships of a record, as well as delete records.
##  Import files[](https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records#import-files)
Surrealist allows you to import files into your database in the Explorer view. This can be useful for importing data from other sources, or for importing data from one database to another.
###  Importing a CSV file[](https://surrealdb.com/docs/explore/surrealist/concepts/exploring-database-records#importing-a-csv-file)
To import CSV data into SurrealDB using Surrealist, navigate to the `Import database` button at the bottom of the Explorer view. This will open your default file explorer, where you can select the CSV file you want to import.
Once you have selected the file, you will be prompted to enter a table name. This is the name of the table that will be created in your database.
Surrealist will automatically convert the rows from your CSV file into records in the new table. The importer also handles SurrealQL compatible data like objects, arrays, and dates. 
![Surrealist import view](https://surrealdb.com/docs/explore/surrealist/concepts/~/assets/img/image/surrealist/import.png)
Here's a more detailed breakdown: 
  1. 1.
Locate the Importer: Open Surrealist and navigate to the Explorer view, then find the "Import database" option.
  2. 2.
Select CSV File: Browse and select the CSV file you want to import.
  3. 3.
Specify Table Name: Enter the name you want to give the new table that will be created from the CSV data.
  4. 4.
Automatic Conversion: Surrealist will automatically convert the rows from your CSV file into records in the new table.
     * ◦
If your table includes relationships, Surrealist will automatically create the necessary edges if you toggle the insert as a relationship option. 
  5. 5.
SurrealQL Compatibility: The importer is also designed to handle data types that are compatible with SurrealQL, such as objects, arrays, and dates.
  6. 6.
Additional Features: Surrealist also supports exporting data in SurrealQL format and importing SurrealQL files, as well as models from various machine learning libraries.
