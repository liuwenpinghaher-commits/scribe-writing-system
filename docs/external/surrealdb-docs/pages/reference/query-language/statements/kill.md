---
title: "https://surrealdb.com/docs/reference/query-language/statements/kill"
url: "https://surrealdb.com/docs/reference/query-language/statements/kill"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/kill

Source: https://surrealdb.com/docs/reference/query-language/statements/kill

The `KILL` statement is used to terminate a running live query.
While the `KILL` statement does accept a value type, this value must resolve to a UUID. Consequently, it will accept a string literal of a UUID or a param.
###  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/kill#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
KILL @value;
```

KILL@value;
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/kill#example-usage)
###  Basic usage[](https://surrealdb.com/docs/reference/query-language/statements/kill#basic-usage)
The `KILL` statement expects the UUID of a running [live select](https://surrealdb.com/docs/reference/query-language/statements/live-select) query to be passed. This UUID can be found in the output of the `LIVE` statement, and can thereafter be passed into a `KILL` statement once it is no longer needed.

```surql
LIVE SELECT DIFF FROM person;
-- output: u'0189d6e3-8eac-703a-9a48-d9faa78b44b9'

-- Some time later...
KILL u"0189d6e3-8eac-703a-9a48-d9faa78b44b9";
```

The `KILL` statement also allows for parameters to be used.

```surql
-- Define the parameter
LET $live_query_id = u"0189d6e3-8eac-703a-9a48-d9faa78b44b9";
-- Use the parameter
KILL $live_query_id;
```

Using the `KILL` statement on a UUID that does not correspond to a running live query will generate an error.

```surql
LET $rand = rand::uuid();
KILL $rand;
KILL u'9276b05b-e59a-49cd-9dd1-17c6fd15c28f';
```

Output

```surql
"Can not execute KILL statement using id '$rand'"
"Can not execute KILL statement using id 'u'9276b05b-e59a-49cd-9dd1-17c6fd15c28f''"
```

##  Kill notifications[](https://surrealdb.com/docs/reference/query-language/statements/kill#kill-notifications)
Available since: v3.0.0
A separate notification is sent out when a `KILL` statement is enacted on a live query ID.

```surql
LIVE SELECT * FROM person;

-- Output is a UUID:
-- u'cf447091-9463-4d75-b32a-08513eb2a07c'

KILL u'cf447091-9463-4d75-b32a-08513eb2a07c';
```

Output

```surql
-- Query 1
NONE

-- Notification (action: Killed, live query ID: cf447091-9463-4d75-b32a-08513eb2a07c)
NONE
```
