---
title: "https://surrealdb.com/docs/reference/php/frameworks/laravel"
url: "https://surrealdb.com/docs/reference/php/frameworks/laravel"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/frameworks/laravel

Source: https://surrealdb.com/docs/reference/php/frameworks/laravel

The [Laravel integration](https://github.com/surrealdb/surrealdb.laravel) connects SurrealDB to a Laravel application. It wires [version 2 of the SDK](https://surrealdb.com/docs/reference/php/v2) and the [Surqlize ORM](https://surrealdb.com/docs/reference/php/ecosystem/surqlize) into Laravel's config, service container, facades, and Artisan commands.
Query execution and the database protocol are delegated to the SDK. Models, query compilation, graph relations, and schema definitions are delegated to Surqlize. The integration adds the Laravel glue: publishable config, container bindings, facades, schema commands, and testing helpers.
Important
The integration is published as `0.0.1-alpha.1` and is in early development. It requires PHP `8.4` and Laravel `11`, `12`, or `13`, and depends on the alpha SDK and ORM.
It does not replace Laravel's SQL database. SurrealDB runs alongside your existing connections, and the integration does not use Eloquent or `config/database.php`.
##  Getting started[](https://surrealdb.com/docs/reference/php/frameworks/laravel#getting-started)
[Installation Install the package and publish its configuration.](https://surrealdb.com/docs/reference/php/frameworks/laravel/installation)[Configuration Set connection details, auth modes, and multiple connections.](https://surrealdb.com/docs/reference/php/frameworks/laravel/configuration)
##  Using the integration[](https://surrealdb.com/docs/reference/php/frameworks/laravel#using-the-integration)
[Container and facades The service providers, container bindings, and the SurrealDB, Surreal, and Surqlize facades.](https://surrealdb.com/docs/reference/php/frameworks/laravel/container-and-facades)[Queries and transactions Run model queries, raw SurrealQL, and transactions in Laravel.](https://surrealdb.com/docs/reference/php/frameworks/laravel/queries-and-transactions)[Schema commands Dump and apply your Surqlize schema with Artisan.](https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands)[Testing Fake the executor and assert the queries your code sends.](https://surrealdb.com/docs/reference/php/frameworks/laravel/testing)
##  Sources[](https://surrealdb.com/docs/reference/php/frameworks/laravel#sources)
  * •
[GitHub repository](https://github.com/surrealdb/surrealdb.laravel)
  * •
[Surqlize ORM](https://surrealdb.com/docs/reference/php/ecosystem/surqlize) for models and queries
  * •
[PHP SDK v2](https://surrealdb.com/docs/reference/php/v2) for the underlying client
