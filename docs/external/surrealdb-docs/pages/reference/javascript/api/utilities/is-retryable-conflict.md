---
title: "https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict"
url: "https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict

Source: https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict

The `isRetryableConflict()` function is the default predicate used by [`.retry()`](https://surrealdb.com/docs/reference/javascript/api/queries/query#retry) to decide whether a failed query should be retried. SurrealDB does not currently expose a structured retryable error kind, so the predicate matches on the error message.
**Import:**

```ts
import { isRetryableConflict } from 'surrealdb';
```

**Source:** [utils/index.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/utils/index.ts)
##  Function signature[](https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict#function-signature)

```ts
function isRetryableConflict(error: Error): boolean
```

####  Parameters[](https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict#parameters)  
| Parameter  | Type  | Description  |  
| --- | --- | --- |  
| `error`  | `Error`  | The error thrown by a failed query.  |  
####  Returns[](https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict#returns)
`boolean` - `true` if the error looks like a retryable write conflict (its message contains "conflict" or "can be retried"), `false` otherwise
##  Overriding the default predicate[](https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict#overriding-the-default-predicate)
Pass a custom `retryable` function in [`RetryOptions`](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions) to change what counts as retryable, optionally reusing `isRetryableConflict` as a base:

```ts
import { isRetryableConflict } from 'surrealdb';

await db.query('UPDATE counter:c SET n += 1 RETURN n')
    .retry({
        attempts: 5,
        retryable: (error) => isRetryableConflict(error) || error.message.includes('busy')
    })
    .collect();
```

Note
Confirm the exact conflict message against the SurrealDB server version you target — the heuristic matches on message text rather than a structured error kind.
##  See also[](https://surrealdb.com/docs/reference/javascript/api/utilities/is-retryable-conflict#see-also)
  * •
[Query.retry()](https://surrealdb.com/docs/reference/javascript/api/queries/query#retry) - Retry queries on write conflict
  * •
[RetryOptions](https://surrealdb.com/docs/reference/javascript/api/types/#retryoptions) - Retry configuration type
  * •
[Error handling](https://surrealdb.com/docs/reference/javascript/concepts/error-handling) - Handling SDK errors
