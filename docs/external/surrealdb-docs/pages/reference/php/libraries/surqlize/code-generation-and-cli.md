---
title: "https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli"
url: "https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli

Source: https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli

Typed callbacks work through `FieldSet` classes. Surqlize infers a model's fields at runtime, and can also generate explicit field adapter classes for better IDE completion and stricter static analysis.
##  Field adapters[](https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli#field-adapters)
A generated field adapter is a `FieldSet` subclass that declares each property as a typed field. It makes the closures in `select()`, `where()`, and the other builder methods fully analysable.

```php
use App\Models\User;
use Surqlize\Query\Fields\FieldSet;
use Surqlize\Query\Fields\NumericField;
use Surqlize\Query\Fields\RecordIdField;
use Surqlize\Query\Fields\RecordLinkField;
use Surqlize\Query\Fields\StringField;

final class UserFields extends FieldSet
{
    public readonly RecordIdField $id;
    public readonly StringField $name;
    public readonly NumericField $age;
    public readonly RecordLinkField $address;

    public function __construct()
    {
        parent::__construct(User::class);

        $this->id = new RecordIdField('id', table: 'user');
        $this->name = new StringField('name');
        $this->age = new NumericField('age');
        $this->address = new RecordLinkField('address');
    }
}
```

You write these by hand only if you want to. The generator produces them for you.
##  Configuration[](https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli#configuration)
The CLI reads a config file, by convention `surqlize.config.php`, that returns an array. For field generation it lists the models and where to write the adapters.

```php
use App\Models\Address;
use App\Models\HasAddress;
use App\Models\User;

return [
    'models' => [
        User::class,
        Address::class,
        HasAddress::class,
    ],
    'fields_namespace' => 'App\\Models\\Fields',
    'fields_path' => __DIR__ . '/src/Models/Fields',
];
```

For `schema:apply`, the config provides the models plus an SDK executor.

```php
return [
    'models' => [User::class, Address::class],
    'executor' => $surreal,
];
```

##  CLI commands[](https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli#cli-commands)
Surqlize ships a Composer binary named `surqlize`.

```bash
vendor/bin/surqlize generate:fields [config-path]
vendor/bin/surqlize schema:apply [config-path]
vendor/bin/surqlize memory:footprint [--iterations=1000] [--output=path]
```

In a source checkout without Composer's bin proxy, run the binary directly with `php bin/surqlize ...`.
###  generate:fields[](https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli#generatefields)
Generates the `*Fields` classes and `*FieldTyping` traits for the configured models, into the configured namespace and path.

```bash
vendor/bin/surqlize generate:fields surqlize.config.php
```

###  schema:apply[](https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli#schema-apply)
Applies the [schema](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema) definitions for the configured models through the configured executor.

```bash
vendor/bin/surqlize schema:apply surqlize.config.php
```

###  memory:footprint[](https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli#memoryfootprint)
Generates a JSON memory report across the built-in scenarios (metadata reflection, field-set resolution, query compilation, hydration, graph traversal, and more), with retained, peak, and real memory deltas and durations.

```bash
vendor/bin/surqlize memory:footprint --iterations=5000 --output=memory-report.json
```

##  Learn more[](https://surrealdb.com/docs/reference/php/libraries/surqlize/code-generation-and-cli#learn-more)
  * •
[Querying](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/querying) for the typed callbacks adapters support
  * •
[Schema](https://surrealdb.com/docs/reference/php/ecosystem/surqlize/schema) for the definitions `schema:apply` runs
  * •
[Laravel integration](https://surrealdb.com/docs/reference/php/frameworks/laravel/schema-commands) for the Artisan schema commands
