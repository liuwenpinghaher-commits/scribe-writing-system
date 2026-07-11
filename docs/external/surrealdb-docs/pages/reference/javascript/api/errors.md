---
title: "https://surrealdb.com/docs/reference/javascript/api/errors"
url: "https://surrealdb.com/docs/reference/javascript/api/errors"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/api/errors

Source: https://surrealdb.com/docs/reference/javascript/api/errors

The SDK defines specific error classes for different failure scenarios. All error classes extend the base `SurrealError` class, allowing you to catch and handle specific error types.
##  Base error[](https://surrealdb.com/docs/reference/javascript/api/errors#base-error)
###  `SurrealError`[](https://surrealdb.com/docs/reference/javascript/api/errors#surrealerror)
Base class for all SDK errors.
**Extends:** `Error`
**Example:**

```ts
try {
    await db.select(new RecordId('users', 'john'));
} catch (error) {
    if (error instanceof SurrealError) {
        console.error('SDK error:', error.message);
    }
}
```

##  Connection errors[](https://surrealdb.com/docs/reference/javascript/api/errors#connection-errors)
###  `ConnectionUnavailableError`[](https://surrealdb.com/docs/reference/javascript/api/errors#connectionunavailableerror)
Thrown when attempting an operation without an active connection.
**Message:** `"You must be connected to a SurrealDB instance before performing this operation"`
**Example:**

```ts
const db = new Surreal();

try {
    await db.select(new Table('users')); // Not connected
} catch (error) {
    if (error instanceof ConnectionUnavailableError) {
        console.error('Not connected to database');
        await db.connect('ws://localhost:8000');
    }
}
```

* * *
###  `HttpConnectionError`[](https://surrealdb.com/docs/reference/javascript/api/errors#httpconnectionerror)
Thrown when an HTTP connection fails.
**Properties:**
  * •
`status` (number) - HTTP status code
  * •
`statusText` (string) - HTTP status text
  * •
`buffer` (ArrayBuffer) - Response buffer

**Example:**

```ts
try {
    await db.connect('http://localhost:8000/rpc');
} catch (error) {
    if (error instanceof HttpConnectionError) {
        console.error(`HTTP ${error.status}: ${error.statusText}`);
    }
}
```

* * *
###  `CallTerminatedError`[](https://surrealdb.com/docs/reference/javascript/api/errors#callterminatederror)
Thrown when a call is terminated because the connection was closed.
**Message:** `"The call has been terminated because the connection was closed"`
**Example:**

```ts
try {
    const promise = db.query('SELECT SLEEP(10s)');
    await db.close(); // Close connection while query running
    await promise; // Will throw CallTerminatedError
} catch (error) {
    if (error instanceof CallTerminatedError) {
        console.error('Connection closed during operation');
    }
}
```

* * *
###  `UnexpectedConnectionError`[](https://surrealdb.com/docs/reference/javascript/api/errors#unexpectedconnectionerror)
Thrown when an unexpected connection error occurs.
**Properties:**
  * •
`cause` (unknown) - The underlying error cause

**Example:**

```ts
try {
    await db.connect('ws://invalid:8000');
} catch (error) {
    if (error instanceof UnexpectedConnectionError) {
        console.error('Connection error:', error.cause);
    }
}
```

* * *
###  `UnsupportedEngineError`[](https://surrealdb.com/docs/reference/javascript/api/errors#unsupportedengineerror)
Thrown when attempting to use an unsupported or unconfigured engine.
**Properties:**
  * •
`engine` (string) - The unsupported engine name

**Example:**

```ts
try {
    await db.connect('custom://localhost:8000');
} catch (error) {
    if (error instanceof UnsupportedEngineError) {
        console.error(`Engine "${error.engine}" is not supported`);
    }
}
```

##  Reconnection errors[](https://surrealdb.com/docs/reference/javascript/api/errors#reconnection-errors)
###  `ReconnectExhaustionError`[](https://surrealdb.com/docs/reference/javascript/api/errors#reconnectexhaustionerror)
Thrown when reconnect attempts have been exhausted.
**Message:** `"The reconnect attempts have been exhausted"`
**Example:**

```ts
db.subscribe('error', (error) => {
    if (error instanceof ReconnectExhaustionError) {
        console.error('Failed to reconnect after multiple attempts');
    }
});
```

* * *
###  `ReconnectIterationError`[](https://surrealdb.com/docs/reference/javascript/api/errors#reconnectiterationerror)
Thrown when a reconnect iterator fails to iterate.
**Message:** `"The reconnect iterator failed to iterate"`
##  Server errors[](https://surrealdb.com/docs/reference/javascript/api/errors#server-errors)
Server errors represent structured errors returned by the SurrealDB server. They form a class hierarchy rooted at `ServerError`, which replaces the former `ResponseError` class.
###  `ErrorKind`[](https://surrealdb.com/docs/reference/javascript/api/errors#errorkind)
Known error kinds returned by the SurrealDB server. Use these constants for matching against `ServerError.kind`.

```ts
const ErrorKind = {
    Validation: "Validation",
    Configuration: "Configuration",
    Thrown: "Thrown",
    Query: "Query",
    Serialization: "Serialization",
    NotAllowed: "NotAllowed",
    NotFound: "NotFound",
    AlreadyExists: "AlreadyExists",
    Connection: "Connection",
    Internal: "Internal",
} as const;
```

* * *
###  `ServerError`[](https://surrealdb.com/docs/reference/javascript/api/errors#servererror)
Base class for all errors originating from the SurrealDB server. Each error carries structured information about the failure.
**Extends:** `SurrealError`
**Properties:**
  * •
`kind` (string) - The error category (e.g. `"NotAllowed"`, `"NotFound"`)
  * •
`code` (number) - Legacy JSON-RPC numeric error code (0 when unavailable)
  * •
`details` (ErrorDetail | undefined) - Kind-specific structured details from the server
  * •
`cause` (ServerError | undefined) - Optional inner `ServerError` forming a recursive error chain

**Example:**

```ts
try {
    await db.query('INVALID QUERY');
} catch (error) {
    if (error instanceof ServerError) {
        console.error(`Server error [${error.kind}]: ${error.message}`);
        if (error.cause) {
            console.error('Caused by:', error.cause.message);
        }
    }
}
```

* * *
###  `ValidationError`[](https://surrealdb.com/docs/reference/javascript/api/errors#validationerror)
Thrown on validation failures such as parse errors, invalid requests, or invalid parameters.
**Extends:** `ServerError` (kind: `"Validation"`)
**Convenience getters:**
  * •
`isParseError` (boolean) - True if this is a SurrealQL parse error
  * •
`parameterName` (string | undefined) - The name of the invalid parameter, if applicable

**Example:**

```ts
try {
    await db.query('SELEC * FROM users'); // Typo
} catch (error) {
    if (error instanceof ValidationError) {
        if (error.isParseError) {
            console.error('SurrealQL syntax error:', error.message);
        }
    }
}
```

* * *
###  `ConfigurationError`[](https://surrealdb.com/docs/reference/javascript/api/errors#configurationerror)
Thrown when a feature or configuration is not supported by the server (e.g. live queries, GraphQL).
**Extends:** `ServerError` (kind: `"Configuration"`)
**Convenience getters:**
  * •
`isLiveQueryNotSupported` (boolean) - True if live queries are not supported by the server configuration

* * *
###  `ThrownError`[](https://surrealdb.com/docs/reference/javascript/api/errors#thrownerror)
Thrown when a user-thrown error is raised via `THROW` in SurrealQL.
**Extends:** `ServerError` (kind: `"Thrown"`)
**Example:**

```ts
try {
    await db.query('THROW "something went wrong"');
} catch (error) {
    if (error instanceof ThrownError) {
        console.error('SurrealQL THROW:', error.message);
    }
}
```

* * *
###  `QueryError`[](https://surrealdb.com/docs/reference/javascript/api/errors#queryerror)
Thrown on query execution failures such as timeouts, cancellations, or skipped statements.
**Extends:** `ServerError` (kind: `"Query"`)
**Convenience getters:**
  * •
`isNotExecuted` (boolean) - True if the query was not executed (e.g. due to a prior error in the batch)
  * •
`isTimedOut` (boolean) - True if the query timed out
  * •
`isCancelled` (boolean) - True if the query was cancelled
  * •
`timeout` (`{ secs: number, nanos: number } | undefined`) - The timeout duration, if this is a timeout error

**Example:**

```ts
try {
    await db.query('SELECT * FROM heavy_table TIMEOUT 1s');
} catch (error) {
    if (error instanceof QueryError) {
        if (error.isTimedOut) {
            console.error('Query timed out after', error.timeout?.secs, 'seconds');
        } else if (error.isNotExecuted) {
            console.error('Query was not executed');
        }
    }
}
```

* * *
###  `SerializationError`[](https://surrealdb.com/docs/reference/javascript/api/errors#serializationerror)
Thrown on serialization or deserialization failures.
**Extends:** `ServerError` (kind: `"Serialization"`)
**Convenience getters:**
  * •
`isDeserialization` (boolean) - True if this is a deserialization error (as opposed to serialization)

* * *
###  `NotAllowedError`[](https://surrealdb.com/docs/reference/javascript/api/errors#notallowederror)
Thrown when a permission is denied, a method is not allowed, or a function/scripting call is blocked.
**Extends:** `ServerError` (kind: `"NotAllowed"`)
**Convenience getters:**
  * •
`isTokenExpired` (boolean) - True if the auth token has expired
  * •
`isInvalidAuth` (boolean) - True if authentication credentials are invalid
  * •
`isScriptingBlocked` (boolean) - True if scripting is blocked
  * •
`methodName` (string | undefined) - The method name that is not allowed, if applicable
  * •
`functionName` (string | undefined) - The function name that is not allowed, if applicable

**Example:**

```ts
try {
    await db.query('SELECT * FROM protected_table');
} catch (error) {
    if (error instanceof NotAllowedError) {
        if (error.isTokenExpired) {
            console.error('Token expired, re-authenticate');
        } else if (error.isInvalidAuth) {
            console.error('Invalid credentials');
        }
    }
}
```

* * *
###  `NotFoundError`[](https://surrealdb.com/docs/reference/javascript/api/errors#notfounderror)
Thrown when a resource is not found (table, record, namespace, method, etc.).
**Extends:** `ServerError` (kind: `"NotFound"`)
**Convenience getters:**
  * •
`tableName` (string | undefined) - The table name that was not found
  * •
`recordId` (string | undefined) - The record ID that was not found
  * •
`methodName` (string | undefined) - The RPC method name that was not found
  * •
`namespaceName` (string | undefined) - The namespace name that was not found
  * •
`databaseName` (string | undefined) - The database name that was not found

**Example:**

```ts
try {
    await db.query('SELECT * FROM nonexistent');
} catch (error) {
    if (error instanceof NotFoundError) {
        if (error.tableName) {
            console.error(`Table "${error.tableName}" does not exist`);
        } else if (error.recordId) {
            console.error(`Record "${error.recordId}" not found`);
        }
    }
}
```

* * *
###  `AlreadyExistsError`[](https://surrealdb.com/docs/reference/javascript/api/errors#alreadyexistserror)
Thrown when a duplicate resource is encountered (record, table, namespace, etc.).
**Extends:** `ServerError` (kind: `"AlreadyExists"`)
**Convenience getters:**
  * •
`recordId` (string | undefined) - The record ID that already exists
  * •
`tableName` (string | undefined) - The table name that already exists

**Example:**

```ts
try {
    await db.create(new RecordId('users', 'john'), { name: 'John' });
} catch (error) {
    if (error instanceof AlreadyExistsError) {
        if (error.recordId) {
            console.error(`Record "${error.recordId}" already exists`);
        }
    }
}
```

* * *
###  `InternalError`[](https://surrealdb.com/docs/reference/javascript/api/errors#internalerror)
Thrown on unexpected or unknown internal server errors. Also used as the fallback for unrecognized `kind` strings from newer servers.
**Extends:** `ServerError` (kind: `"Internal"`)
* * *
###  `ResponseError` (Deprecated)[](https://surrealdb.com/docs/reference/javascript/api/errors#responseerror)
`ResponseError` is a deprecated alias for [`ServerError`](https://surrealdb.com/docs/reference/javascript/api/errors#servererror). It exists for backward compatibility.

```ts
// ResponseError is the same as ServerError
import { ResponseError } from 'surrealdb';
// Equivalent to:
import { ServerError } from 'surrealdb';
```

* * *
###  `UnexpectedServerResponseError`[](https://surrealdb.com/docs/reference/javascript/api/errors#unexpectedserverresponseerror)
Thrown when the server returns a response in an unexpected format.
**Properties:**
  * •
`response` (unknown) - The unexpected response received

**Example:**

```ts
try {
    await db.query(complexQuery);
} catch (error) {
    if (error instanceof UnexpectedServerResponseError) {
        console.error('Unexpected response:', error.response);
    }
}
```

##  Authentication errors[](https://surrealdb.com/docs/reference/javascript/api/errors#authentication-errors)
###  `AuthenticationError`[](https://surrealdb.com/docs/reference/javascript/api/errors#authenticationerror)
Thrown when authentication fails.
**Message:** `"Authentication did not succeed"`
**Properties:**
  * •
`cause` (unknown) - The underlying error cause

**Example:**

```ts
try {
    await db.signin({
        username: 'user',
        password: 'wrongpassword'
    });
} catch (error) {
    if (error instanceof AuthenticationError) {
        console.error('Authentication failed:', error.cause);
    }
}
```

* * *
###  `MissingNamespaceDatabaseError`[](https://surrealdb.com/docs/reference/javascript/api/errors#missingnamespacedatabaseerror)
Thrown when a namespace and/or database is required but not selected.
**Message:** `"There is no namespace and/or database selected"`
**Example:**

```ts
const db = new Surreal();
await db.connect('ws://localhost:8000');

try {
    await db.select(new Table('users')); // No namespace/database set
} catch (error) {
    if (error instanceof MissingNamespaceDatabaseError) {
        await db.use({ namespace: 'main', database: 'main' });
    }
}
```

##  Live query errors[](https://surrealdb.com/docs/reference/javascript/api/errors#live-query-errors)
###  `LiveSubscriptionError`[](https://surrealdb.com/docs/reference/javascript/api/errors#livesubscriptionerror)
Thrown when a live subscription fails to listen.
**Constructor:** `new LiveSubscriptionError(messageOrCause?: string | unknown)`
When called with a string, it is used as the error message. When called with any other value (or no argument), the default message `"Live subscription failed to listen"` is used and the argument is set as `cause`.
**Example:**

```ts
try {
    const subscription = await db.live(new Table('users'));
} catch (error) {
    if (error instanceof LiveSubscriptionError) {
        console.error('Live query failed:', error.cause);
    }
}
```

##  Version errors[](https://surrealdb.com/docs/reference/javascript/api/errors#version-errors)
###  `UnsupportedVersionError`[](https://surrealdb.com/docs/reference/javascript/api/errors#unsupportedversionerror)
Thrown when the connected SurrealDB version is not supported by the SDK.
**Properties:**
  * •
`version` (string) - The unsupported version
  * •
`minimum` (string) - Minimum supported version (inclusive)
  * •
`maximum` (string) - Maximum supported version (exclusive)

**Example:**

```ts
try {
    await db.connect('ws://localhost:8000', {
        versionCheck: true
    });
} catch (error) {
    if (error instanceof UnsupportedVersionError) {
        console.error(
            `Version ${error.version} not supported. ` +
            `Requires: >= ${error.minimum} < ${error.maximum}`
        );
    }
}
```

##  Expression errors[](https://surrealdb.com/docs/reference/javascript/api/errors#expression-errors)
###  `ExpressionError`[](https://surrealdb.com/docs/reference/javascript/api/errors#expressionerror)
Thrown when a SurrealQL expression fails to compile or execute.
**Constructor:** `new ExpressionError(messageOrCause?: string | unknown)`
When called with a string, it is used as the error message. When called with any other value (or no argument), the default message `"Failed to parse invalid expression"` is used and the argument is set as `cause`.
**Example:**

```ts
try {
    const invalid = expr(() => {
        throw new Error('Invalid expression');
    });
} catch (error) {
    if (error instanceof ExpressionError) {
        console.error('Expression error:', error.message);
    }
}
```

##  Event errors[](https://surrealdb.com/docs/reference/javascript/api/errors#event-errors)
###  `PublishError`[](https://surrealdb.com/docs/reference/javascript/api/errors#publisherror)
Thrown when one or more event subscribers throw an error during publication.
**Properties:**
  * •
`causes` (unknown[]) - The errors thrown by subscribers
  * •
`message` (string) - Summary message including the cause messages

**Example:**

```ts
db.subscribe('auth', () => {
    throw new Error('Handler failed');
});
// When the event fires, a PublishError may be emitted
```

##  Date and time errors[](https://surrealdb.com/docs/reference/javascript/api/errors#date-and-time-errors)
###  `InvalidDateError`[](https://surrealdb.com/docs/reference/javascript/api/errors#invaliddateerror)
Thrown when a parsed date or datetime is invalid.
**Constructor:** `new InvalidDateError(dateOrMessage: Date | string)`
When called with a `Date`, the message is `"The provided date is invalid: "`. When called with a string, the string is used directly as the error message.
**Example:**

```ts
try {
    new DateTime('not-a-date');
} catch (error) {
    if (error instanceof InvalidDateError) {
        console.error('Invalid date:', error.message);
    }
}
```

##  Feature errors[](https://surrealdb.com/docs/reference/javascript/api/errors#feature-errors)
###  `UnsupportedFeatureError`[](https://surrealdb.com/docs/reference/javascript/api/errors#unsupportedfeatureerror)
Thrown when attempting to use a feature not supported by the configured engine.
**Properties:**
  * •
`feature` (Feature) - The unsupported feature

**Example:**

```ts
try {
    await db.live(new Table('users')); // Not supported by engine
} catch (error) {
    if (error instanceof UnsupportedFeatureError) {
        console.error(`Feature "${error.feature.name}" not supported`);
    }
}
```

* * *
###  `UnavailableFeatureError`[](https://surrealdb.com/docs/reference/javascript/api/errors#unavailablefeatureerror)
Thrown when attempting to use a feature not available in the connected SurrealDB version.
**Properties:**
  * •
`feature` (Feature) - The unavailable feature
  * •
`version` (string) - The connected SurrealDB version

**Example:**

```ts
try {
    await db.connect('http://localhost:8000/rpc');
    await db.live(new Table('users'));
} catch (error) {
    if (error instanceof UnavailableFeatureError) {
        console.error(`Feature "${error.feature.name}" not available in version ${error.version}`);
    }
}
```

##  API errors[](https://surrealdb.com/docs/reference/javascript/api/errors#api-errors)
###  `UnsuccessfulApiError`[](https://surrealdb.com/docs/reference/javascript/api/errors#unsuccessfulapierror)
Thrown when a user-defined API call fails.
**Properties:**
  * •
`path` (string) - The API path that was invoked
  * •
`method` (string) - The HTTP method used
  * •
`response` (ApiResponse) - The error response from the API (includes `body?`, `headers?`, `status?`)
  * •
`message` (string) - Human-readable message (inherited from Error; includes path, method, and status)

**Example:**

```ts
try {
    await db.api().get('/users/999');
} catch (error) {
    if (error instanceof UnsuccessfulApiError) {
        console.error(`API error: ${error.message}`);
        console.error(`Status: ${error.response.status}`);
    }
}
```

##  Session errors[](https://surrealdb.com/docs/reference/javascript/api/errors#session-errors)
###  `InvalidSessionError`[](https://surrealdb.com/docs/reference/javascript/api/errors#invalidsessionerror)
Thrown when attempting to use an invalid or disposed session.
**Properties:**
  * •
`session` (Session) - The invalid session identifier

**Example:**

```ts
const session = await db.newSession();
await session.closeSession();

try {
    await session.select(new Table('users')); // Session closed
} catch (error) {
    if (error instanceof InvalidSessionError) {
        console.error('Session is no longer valid');
    }
}
```

##  Value validation errors[](https://surrealdb.com/docs/reference/javascript/api/errors#value-validation-errors)
###  `InvalidRecordIdError`[](https://surrealdb.com/docs/reference/javascript/api/errors#invalidrecordiderror)
Thrown when a `RecordId` or `RecordIdRange` is constructed with invalid parts.
**Example:**

```ts
try {
    new RecordId('', 'id'); // Invalid table name
} catch (error) {
    if (error instanceof InvalidRecordIdError) {
        console.error('Invalid record ID:', error.message);
    }
}
```

* * *
###  `InvalidDurationError`[](https://surrealdb.com/docs/reference/javascript/api/errors#invaliddurationerror)
Thrown when a `Duration` string cannot be parsed or a duration operation is invalid.
**Example:**

```ts
try {
    new Duration('not-a-duration');
} catch (error) {
    if (error instanceof InvalidDurationError) {
        console.error('Invalid duration:', error.message);
    }
}
```

* * *
###  `InvalidDecimalError`[](https://surrealdb.com/docs/reference/javascript/api/errors#invaliddecimalerror)
Thrown when a `Decimal` operation fails (e.g. division by zero, invalid input).
**Example:**

```ts
try {
    new Decimal('not-a-number');
} catch (error) {
    if (error instanceof InvalidDecimalError) {
        console.error('Invalid decimal:', error.message);
    }
}
```

* * *
###  `InvalidTableError`[](https://surrealdb.com/docs/reference/javascript/api/errors#invalidtableerror)
Thrown when a `Table` or `StringRecordId` is constructed with an invalid value.
**Example:**

```ts
try {
    new Table(''); // Empty table name
} catch (error) {
    if (error instanceof InvalidTableError) {
        console.error('Invalid table:', error.message);
    }
}
```

##  Error handling patterns[](https://surrealdb.com/docs/reference/javascript/api/errors#error-handling-patterns)
###  Basic error handling[](https://surrealdb.com/docs/reference/javascript/api/errors#basic-error-handling)

```ts
try {
    const result = await db.select(new Table('users'));
} catch (error) {
    if (error instanceof SurrealError) {
        // Handle all SDK errors
        console.error('SDK error:', error.message);
    } else {
        // Handle other errors
        console.error('Unexpected error:', error);
    }
}
```

###  Specific error handling[](https://surrealdb.com/docs/reference/javascript/api/errors#specific-error-handling)

```ts
try {
    await db.connect('ws://localhost:8000');
    await db.use({ namespace: 'main', database: 'main' });
    await db.signin({ username: 'user', password: 'pass' });
} catch (error) {
    if (error instanceof ConnectionUnavailableError) {
        console.error('Cannot connect to database');
    } else if (error instanceof AuthenticationError) {
        console.error('Invalid credentials');
    } else if (error instanceof UnsupportedVersionError) {
        console.error('Database version incompatible');
    } else {
        console.error('Unknown error:', error);
    }
}
```

###  Error recovery[](https://surrealdb.com/docs/reference/javascript/api/errors#error-recovery)

```ts
async function executeWithRetry(fn: () => Promise<any>, maxRetries = 3) {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            if (error instanceof ConnectionUnavailableError) {
                // Reconnect and retry
                await db.connect('ws://localhost:8000');
                continue;
            } else if (error instanceof ServerError && attempt < maxRetries - 1) {
                // Retry on server errors
                continue;
            }
            throw error;
        }
    }
}

const result = await executeWithRetry(() => 
    db.select(new Table('users'))
);
```

###  Global error handler[](https://surrealdb.com/docs/reference/javascript/api/errors#global-error-handler)

```ts
db.subscribe('error', (error) => {
    if (error instanceof ReconnectExhaustionError) {
        // Handle reconnection failure
        notifyUser('Connection lost. Please check your network.');
    } else if (error instanceof UnexpectedConnectionError) {
        // Log unexpected errors
        logger.error('Unexpected connection error:', error.cause);
    }
});
```

##  Best practices[](https://surrealdb.com/docs/reference/javascript/api/errors#best-practices)
###  1. Catch specific errors[](https://surrealdb.com/docs/reference/javascript/api/errors#1-catch-specific-errors)
Handle specific error types for better error recovery:

```ts
// Good: Specific handling
try {
    await operation();
} catch (error) {
    if (error instanceof AuthenticationError) {
        redirectToLogin();
    } else if (error instanceof ConnectionUnavailableError) {
        showConnectionError();
    }
}

// Avoid: Generic handling
try {
    await operation();
} catch (error) {
    console.error(error); // Lost context
}
```

###  2. Use type guards[](https://surrealdb.com/docs/reference/javascript/api/errors#2-use-type-guards)
TypeScript type guards provide better type safety:

```ts
function isConnectionError(error: unknown): error is ConnectionUnavailableError {
    return error instanceof ConnectionUnavailableError;
}

if (isConnectionError(error)) {
    // TypeScript knows error is ConnectionUnavailableError
    await reconnect();
}
```

###  3. Log error details[](https://surrealdb.com/docs/reference/javascript/api/errors#3-log-error-details)
Include error details in logs for debugging:

```ts
catch (error) {
    if (error instanceof ServerError) {
        logger.error('Query failed', {
            kind: error.kind,
            code: error.code,
            message: error.message,
            details: error.details,
        });
    }
}
```

###  4. Clean up on error[](https://surrealdb.com/docs/reference/javascript/api/errors#4-clean-up-on-error)
Ensure resources are cleaned up even when errors occur:

```ts
const session = await db.newSession();
try {
    await session.select(new Table('users'));
} finally {
    await session.closeSession(); // Always clean up
}
```

##  See also[](https://surrealdb.com/docs/reference/javascript/api/errors#see-also)
  * •
[Core Classes](https://surrealdb.com/docs/reference/javascript/api/core/) - Classes that may throw errors
  * •
[Surreal](https://surrealdb.com/docs/reference/javascript/api/core/surreal) - Connection methods that may throw errors
  * •
[SurrealSession](https://surrealdb.com/docs/reference/javascript/api/core/surreal-session) - Session methods that may throw errors

**Source:** [errors.ts](https://github.com/surrealdb/surrealdb.js/blob/main/packages/sdk/src/errors.ts)
