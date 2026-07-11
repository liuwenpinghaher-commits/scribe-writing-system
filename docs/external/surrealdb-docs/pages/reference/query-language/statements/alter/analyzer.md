---
title: "https://surrealdb.com/docs/reference/query-language/statements/alter/analyzer"
url: "https://surrealdb.com/docs/reference/query-language/statements/alter/analyzer"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/query-language/statements/alter/analyzer

Source: https://surrealdb.com/docs/reference/query-language/statements/alter/analyzer

Available since: v3.0.5
The `ALTER ANALYZER` statement can be used to modify an existing defined [analyzer](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer).
##  Statement syntax[](https://surrealdb.com/docs/reference/query-language/statements/alter/analyzer#statement-syntax)
SurrealQL SyntaxRailroad Diagram
SurrealQL Syntax

```syntax
ALTER ANALYZER [ IF EXISTS ] @name
  [ FUNCTION fn::@function | DROP FUNCTION ]
  [ TOKENIZERS @tokenizer, ... | DROP TOKENIZERS ]
  [ FILTERS @filter, ... | DROP FILTERS ]
  [ COMMENT @string | DROP COMMENT ]
```

ALTER ANALYZERIFEXISTS@nameFUNCTION@functionDROPFUNCTIONTOKENIZERS@tokenizer,@tokenizerDROPTOKENIZERSFILTERS@filter,@filterDROPFILTERSCOMMENT@stringDROPCOMMENT
##  Example usage[](https://surrealdb.com/docs/reference/query-language/statements/alter/analyzer#example-usage)

```surql
-- Define an analyzer
DEFINE ANALYZER example_edgengram TOKENIZERS class FILTERS
  edgengram(1,3);

-- Shorten the edgengram
ALTER ANALYZER example_edgengram FILTERS edgengram(1,2);

-- Check the output
search::analyze("example_edgengram", "Apple banana!!");
```

Output

```surql
[
	'A',
	'Ap',
	'b',
	'ba',
	'!',
	'!!'
]
```
