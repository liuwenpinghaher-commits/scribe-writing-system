---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/namespace"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/namespace"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/namespace

Source: https://surrealdb.com/docs/reference/query-language/statements/define/namespace

SurrealDB has a multi-tenancy model which allows you to scope databases to a namespace. There is no limit to the number of databases that can be in a namespace, nor is there a limit to the number of namespaces allowed. Only users with root access are authorized to create namespaces.
Let's say that you're using SurrealDB to create a multi-tenant SaaS application. You can guarantee that the data of each tenant will be kept separate from other tenants if you put each tenant's databases into separate namespaces. In other words, this will ensure that information will remain siloed so user will only have access the information in the namespace they are a member of.
##  Requirements[](https://surrealdb.com/docs/reference/query-language/statements/define/namespace#requirements)
  * •
You must be authenticated as a root owner or editor before you can use the `DEFINE NAMESPACE` statement.

##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/namespace#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
DEFINE NAMESPACE [ OVERWRITE | IF NOT EXISTS ] @name [ COMMENT @string ]
```

DEFINENAMESPACEOVERWRITEIFNOTEXISTS@nameCOMMENT@string
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/define/namespace#example-usage)
Below shows how you can create a namespace using the `DEFINE NAMESPACE` statement.

```surql
-- Namespace for Abcum Ltd.
DEFINE NAMESPACE abcum;
```

##  Using `IF NOT EXISTS` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/namespace#using-if-not-exists-clause)
The `IF NOT EXISTS` clause can be used to define a namespace only if it does not already exist. You should use the `IF NOT EXISTS` clause when defining a namespace in SurrealDB if you want to ensure that the namespace is only created if it does not already exist. If the namespace already exists, the `DEFINE NAMESPACE` statement will return an error.
It's particularly useful when you want to safely attempt to define a namespace without manually checking its existence first.
On the other hand, you should not use the `IF NOT EXISTS` clause when you want to ensure that the namespace definition is updated regardless of whether it already exists. In such cases, you might prefer using the `OVERWRITE` clause, which allows you to define a namespace and overwrite an existing one if it already exists, ensuring that the latest version of the namespace definition is always in use

```surql
-- Create a NAMESPACE if it does not already exist
DEFINE NAMESPACE IF NOT EXISTS example;
```

##  Using `OVERWRITE` clause[](https://surrealdb.com/docs/reference/query-language/statements/define/namespace#using-overwrite-clause)
The `OVERWRITE` clause can be used to define a namespace and overwrite an existing one if it already exists. You should use the `OVERWRITE` clause when you want to modify an existing namespace definition. If the namespace already exists, the `DEFINE NAMESPACE` statement will overwrite the existing namespace definition with the new one.

```surql
-- Create an NAMESPACE and overwrite if it already exists
DEFINE NAMESPACE OVERWRITE example;
```
