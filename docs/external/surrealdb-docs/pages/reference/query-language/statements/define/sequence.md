---
title: "https://surrealdb.com/docs/reference/query-language/statements/define/sequence"
url: "https://surrealdb.com/docs/reference/query-language/statements/define/sequence"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/define/sequence

Source: https://surrealdb.com/docs/reference/query-language/statements/define/sequence

Available since: v3.0.0
A sequence is used to generate reliable, monotonically increasing numeric sequences in both single-node and clustered SurrealDB deployments. It uses a batch-allocation strategy to minimise coordination while guaranteeing global uniqueness.
The key features of a sequence are as follows:
  * •
Batch allocation: Nodes request ranges of sequence values at once, reducing network chatter and coordination overhead.
  * •
Node ownership tagging: Every batch is tagged with the requesting node's UUID to prevent overlap between nodes.
  * •
Durable Persistence: Sequence metadata is stored in the underlying key-value store to survive restarts and network partitions.
  * •
Concurrent, thread-safe access: A DashMap caches active sequences, allowing lock-free reads on the hot path.
  * •
Exponential back-off with full jitter: When a batch-allocation attempt fails, the node retries with an exponential delay that includes full jitter to avoid thundering-herd effects across the cluster.
  * •
Automatic cleanup: Listens for namespace and database-removal events and purges the corresponding sequence state.

The sequence implementation avoids contention by having each node reserve a range of sequence values, allowing it to serve multiple requests locally without requiring distributed coordination for every request. When a node exhausts its allocated range, it acquires a new batch from the distributed store.
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/define/sequence#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
DEFINE SEQUENCE [ OVERWRITE | IF NOT EXISTS ] @name [ BATCH @batch ] [ START @start ] [ TIMEOUT @duration ]
```

DEFINESEQUENCEOVERWRITEIFNOTEXISTS@nameBATCH@batchSTART@startTIMEOUT@duration
##  Examples[](https://surrealdb.com/docs/reference/query-language/statements/define/sequence#examples)
A sequence can be created with nothing more than a name.

```surql
DEFINE SEQUENCE mySeq;
```

The `BATCH`, `START`, and `TIMEOUT` clauses can be included to configure the sequence.

```surql
DEFINE SEQUENCE mySeq2 BATCH 1000 START 100 TIMEOUT 5s;
sequence::nextval('mySeq2');
-- Output: 100

DEFINE SEQUENCE mySeq3 BATCH 1000 START 100 TIMEOUT 0ns;
sequence::nextval('mySeq3');
-- Possible output: 'The query was not executed because it exceeded the timeout'
```

Sequences are never rolled back, even in a failed transaction. This differs from an approach like a single record with a manually incrementing value.

```surql
DEFINE SEQUENCE seq;
CREATE my:counter SET val = 0;
sequence::nextval("seq");        -- 0
my:counter.val;                  -- 0

BEGIN TRANSACTION;
sequence::nextval("seq");        -- 0
UPDATE my:counter SET val += 1;  -- my:counter.val = 1
CANCEL TRANSACTION;
-- my:counter.val now rolled back to 0

sequence::nextval("seq");        -- 2
UPDATE my:counter SET val += 1;  -- 1
```

##  See also[](https://surrealdb.com/docs/reference/query-language/statements/define/sequence#see-also)
  * •
[Sequence functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/sequence)
