---
title: "https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands"
url: "https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands

Source: https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands

The integration adds two Artisan commands for managing your [Surqlize schema](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema). Both read the model list from `config('surqlize.models')`.
##  Dumping the schema[](https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands#dumping-the-schema)
`surqlize:schema-dump` prints the schema definitions for the configured models without executing them.

```bash
php artisan surqlize:schema-dump
```

Pass `--connection` to indicate which connection the dump is intended for.

```bash
php artisan surqlize:schema-dump --connection=analytics
```

##  Applying the schema[](https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands#applying-the-schema)
`surqlize:schema-apply` runs the schema definitions against the database.

```bash
php artisan surqlize:schema-apply
```
  
| Option  | Description  |  
| --- | --- |  
| `--dry-run`  | Print the schema DDL instead of executing it  |  
| `--dump`  | Alias of `--dry-run`  |  
| `--connection=`  | The SurrealDB connection to apply to  |  

```bash
php artisan surqlize:schema-apply --dry-run

php artisan surqlize:schema-apply --connection=analytics
```

Note
Register every model that should take part in schema commands in `config('surqlize.models')`. The commands fail if a configured class does not extend `Surqlize\Model\Model`.
##  Learn more[](https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands#learn-more)
  * •
[Schema](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema) for defining tables and fields
  * •
[Configuration](https://surrealdb.com/docs/reference/php/frameworks/laravel/configuration#orm-configuration) for the model list
  * •
[Surqlize CLI](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/code-generation-and-cli) for the framework-agnostic commands
