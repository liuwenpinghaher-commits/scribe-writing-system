---
title: "https://surrealdb.com/docs/reference/javascript/api/queries/run-promise"
url: "https://surrealdb.com/docs/reference/javascript/api/queries/run-promise"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/queries/run-promise

Source: https://surrealdb.com/docs/reference/javascript/api/queries/run-promise

The `RunPromise` class provides an interface for executing SurrealDB functions and SurrealML models. It extends `Promise`, allowing you to `await` it directly or use configuration methods.
**Returned by:** [`SurrealQueryable.run()`](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#run)
**Source:** [query/run.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/query/run.ts)
##  Type parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#type-parameters)
  * •
`T` - The return type of the function
  * •
`J` - Boolean indicating if result is JSON (default: `false`)

##  Configuration methods[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#configuration-methods)
###  `.json()`[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#json)
Configure the query to return the result as a JSON string.
Method Syntax

```ts
runPromise.json()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#returns)
`RunPromise` - Promise returning JSON string
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#example)

```ts
const jsonResult = await db.run('fn::calculate', [10, 20]).json();
console.log(typeof jsonResult); // 'string'
```

* * *
###  `.retry()`[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#retry)
Retry the operation with exponential backoff if it fails due to a write conflict. Off by default; passing an options object (or calling with no arguments) opts the operation in.
This overrides the connection-wide default set via the [`retry`](https://surrealdb.com/docs/reference/javascript/api/types/#connectoptions) option on `ConnectOptions`.
Method Syntax

```ts
runPromise.retry(options?)
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `options`  |  Partial [RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions)  | Retry configuration. If omitted, retry is enabled with the default configuration.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#returns-1)
`RunPromise` - Chainable promise
####  Example[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#example-1)

```ts
await db.run('fn::allocate_inventory', [productId, 10]).retry({ attempts: 3 });
```

* * *
###  `.compile()`[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#compile)
Compile the query into a BoundQuery.
Method Syntax

```ts
runPromise.compile()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#returns-2)
`BoundQuery` - The compiled query
* * *
###  `.stream()`[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#stream)
Stream the function result.
Method Syntax

```ts
runPromise.stream()
```

####  Returns[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#returns-3)
`AsyncIterableIterator>` - Async iterator
##  Complete examples[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#complete-examples)
###  Built-in functions[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#built-in-functions)

```ts
import { Surreal } from 'surrealdb';

const db = new Surreal();
await db.connect('ws://localhost:8000');

// Time functions
const now = await db.run('time::now');
console.log('Current time:', now);

const timestamp = await db.run('time::unix');
console.log('Unix timestamp:', timestamp);

// Array functions
const unique = await db.run('array::distinct', [[1, 2, 2, 3, 3, 3]]);
console.log('Unique values:', unique); // [1, 2, 3]

// String functions
const upper = await db.run('string::uppercase', ['hello world']);
console.log(upper); // 'HELLO WORLD'

// Math functions
const rounded = await db.run('math::round', [3.14159]);
console.log(rounded); // 3

// Crypto functions
const hash = await db.run('crypto::md5', ['password123']);
console.log('Hash:', hash);
```

###  Custom functions[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#custom-functions)

```ts
// First, define a custom function in SurrealDB
await db.query(`
    DEFINE FUNCTION fn::calculate_total($items: array) {
        RETURN array::sum($items.map(|$item| $item.price * $item.quantity));
    };
`).collect();

// Then call it
const items = [
    { price: 10, quantity: 2 },
    { price: 5, quantity: 3 }
];

const total = await db.run('fn::calculate_total', [items]);
console.log('Total:', total); // 35
```

###  SurrealML models[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#surrealml-models)

```ts
// Run a machine learning model
const prediction = await db.run(
    'ml::predict_sentiment',
    '1.0.0', // Model version
    ['This is a great product!']
);

console.log('Sentiment:', prediction);
```

###  With type safety[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#with-type-safety)

```ts
interface CalculationResult {
    sum: number;
    average: number;
    count: number;
}

const result = await db.run<CalculationResult>(
    'fn::calculate_stats',
    [[10, 20, 30, 40, 50]]
);

console.log('Sum:', result.sum);
console.log('Average:', result.average);
console.log('Count:', result.count);
```

###  Complex function arguments[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#complex-function-arguments)

```ts
// Function with multiple arguments
const result = await db.run('fn::process_order', [
    new RecordId('users', 'john'),
    new RecordId('products', 'widget'),
    {
        quantity: 5,
        shipping_address: '123 Main St',
        payment_method: 'credit_card'
    }
]);
```

###  Parameterised functions[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#parameterised-functions)

```ts
// Function that uses session variables
await db.set('discount_rate', 0.1);

const total = await db.run('fn::calculate_price', [
    100, // base price
    // Function can access $discount_rate
]);
```

###  Error handling[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#error-handling)

```ts
try {
    const result = await db.run('fn::risky_operation', [data]);
} catch (error) {
    if (error instanceof ResponseError) {
        console.error('Function failed:', error.message);
    }
}
```

###  Batch function calls[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#batch-function-calls)

```ts
const results = await db.query(`
    RETURN fn::process(${data1});
    RETURN fn::process(${data2});
    RETURN fn::process(${data3});
`).collect();

console.log('Batch results:', results);
```

###  With transaction[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#with-transaction)

```ts
const txn = await db.beginTransaction();

try {
    // Call function within transaction
    const result = await txn.run('fn::allocate_inventory', [
        new RecordId('products', 'widget'),
        10
    ]);
    
    // Other transaction operations
    await txn.create(new Table('orders')).content({
        product: result.product,
        allocated: result.quantity
    });
    
    await txn.commit();
} catch (error) {
    await txn.cancel();
}
```

###  Scheduled functions[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#scheduled-functions)

```ts
// Define a scheduled function
await db.query(`
    DEFINE FUNCTION fn::cleanup_old_records() {
        DELETE FROM logs WHERE created_at < time::now() - 30d;
    };
`).collect();

// Run manually
await db.run('fn::cleanup_old_records');
```

###  Recursive functions[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#recursive-functions)

```ts
await db.query(`
    DEFINE FUNCTION fn::factorial($n: number) {
        IF $n <= 1 THEN
            RETURN 1
        ELSE
            RETURN $n * fn::factorial($n - 1)
        END
    };
`).collect();

const result = await db.run('fn::factorial', [5]);
console.log('5! =', result); // 120
```

###  Data transformation[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#data-transformation)

```ts
// Define transformation function
await db.query(`
    DEFINE FUNCTION fn::format_user($user: record) {
        RETURN {
            full_name: string::concat($user.first_name, ' ', $user.last_name),
            email: string::lowercase($user.email),
            age: time::year(time::now()) - time::year($user.birth_date)
        };
    };
`).collect();

// Use it
const user = await db.select(new RecordId('users', 'john'));
const formatted = await db.run('fn::format_user', [user]);
console.log(formatted);
```

###  ML model versions[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#ml-model-versions)

```ts
// Run specific model version
const v1Result = await db.run('ml::classify_image', '1.0.0', [imageData]);
const v2Result = await db.run('ml::classify_image', '2.0.0', [imageData]);

console.log('v1 prediction:', v1Result);
console.log('v2 prediction:', v2Result);
```

###  Validation functions[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#validation-functions)

```ts
await db.query(`
    DEFINE FUNCTION fn::validate_email($email: string) {
        RETURN string::is::email($email);
    };
`).collect();

const isValid = await db.run('fn::validate_email', ['user@example.com']);

if (isValid) {
    // Proceed with user creation
}
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#best-practices)
###  1. Type function results[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#1-type-function-results)

```ts
// Good: Type the result
interface Stats {
    count: number;
    average: number;
}

const stats = await db.run<Stats>('fn::calculate_stats', [data]);
stats.count; // TypeScript knows this exists

// Avoid: Untyped
const stats = await db.run('fn::calculate_stats', [data]);
stats.count; // No type safety
```

###  2. Handle function errors[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#2-handle-function-errors)

```ts
// Good: Handle errors
try {
    const result = await db.run('fn::risky_operation', [data]);
} catch (error) {
    console.error('Function failed:', error);
}

// Consider: Implement error handling in the function itself
await db.query(`
    DEFINE FUNCTION fn::safe_operation($data: any) {
        TRY {
            RETURN fn::risky_operation($data);
        } CATCH {
            RETURN { error: true, message: 'Operation failed' };
        }
    };
`).collect();
```

###  3. Validate function names[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#3-validate-function-names)
Function names must follow the pattern: `namespace::function_name`

```ts
// Good: Valid function names
await db.run('fn::my_function', []);
await db.run('custom::calculate', []);
await db.run('ml::predict', '1.0.0', []);

// Invalid: Will throw error
await db.run('invalid name', []); // No namespace
await db.run('fn:bad-name', []); // Invalid characters
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/queries/run-promise#see-also)
  * •
[SurrealQueryable.run()](https://surrealdb.com/docs/reference/javascript/api/core/surreal-queryable#run) - Method that returns RunPromise
  * •
[Functions](https://surrealdb.com/docs/reference/query-language/statements/define/function) - SurrealQL function definitions
  * •
[Query overview](https://surrealdb.com/docs/reference/javascript/api/queries/) - All query builder classes
