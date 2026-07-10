---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/sequence"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/sequence"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/sequence

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/sequence

Available since: v3.0.0
The `ALTER SEQUENCE` statement is used to modify a defined sequence.
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER SEQUENCE [ IF EXISTS ] @name [ TIMEOUT @duration ]
```

ALTER SEQUENCEIFEXISTS@nameTIMEOUT@duration
##  Examples[](https://surrealdb.com/docs/reference/query-language/statements/alter/sequence#examples)
The timeout of a sequence can be modified via an `ALTER SEQUENCE` statement. For example, a sequence can be included in the schema but effectively disabled if given a timeout of 0ns, after which `ALTER SEQUENCE` can be used to modify the timeout to make it available.

```surql
DEFINE SEQUENCE mySeq3 BATCH 1000 START 100 TIMEOUT 0ns;
INFO FOR DB.sequences;
sequence::nextval('mySeq3');

ALTER SEQUENCE mySeq3 TIMEOUT 100ms;
sequence::nextval('mySeq3');
```

Output

```surql
-------- Query --------
{ mySeq3: 'DEFINE SEQUENCE mySeq3 BATCH 1000 START 100 TIMEOUT 0ns' },

-------- Query --------
'Thrown error: The query was not executed because it exceeded the timeout: 0ns'

-------- Query --------
100
```

##  See also[](https://surrealdb.com/docs/reference/query-language/statements/alter/sequence#see-also)
  * •
[`DEFINE SEQUENCE`](https://surrealdb.com/docs/reference/query-language/statements/define/sequence)
