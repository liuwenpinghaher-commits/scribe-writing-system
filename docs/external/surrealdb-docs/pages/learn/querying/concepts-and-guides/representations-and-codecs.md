---
title: "https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs"
url: "https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs

Source: https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs

Available since: v3.2.0
Many SurrealDB built-ins do the same broad job: take a value in **representation A** and produce a value in **representation B**. As these tend to be found over various parts of the documentation, this page is a map to introduce them in a single location and help you pick the right one.
##  Quick overview[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs#quick-overview)  
| I want to…  | Use  | Reference  |  
| --- | --- | --- |  
| Serialise a value to JSON or CBOR (or Base64 bytes)  |  `encoding::json::*`, `encoding::cbor::*`, `encoding::base64::*`  | [Encoding functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding)  |  
| Parse JSON/CBOR bytes back into SurrealQL values  |  `encoding::json::decode`, `encoding::cbor::decode`  | [Encoding functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding)  |  
| Preview how an analyzer tokenizes text  | `search::analyze`  | [Search functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/search#searchanalyze)  |  
| Extract part of an email or URL string  |  `parse::email::*`, `parse::url::*`  | [Parse functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse)  |  
| Diff or patch a value with JSON Patch  |  `value::diff`, `value::patch`  | [Value functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value)  |  
| Coerce or inspect types  |  `type::*`, casts (`<datetime>`, `<bytes>`, …)  | [Type functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/type)  |  
| **Run a query string at runtime**  |  `eval::surql`, `eval::gql`  | [Eval functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval)  |  
##  Serialisation (`encoding::*`)[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs#serialisation-encoding)
**Reversible codecs** for wire formats and storage:
  * •
[`encoding::json::encode`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingjsonencode) / [`decode`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingjsondecode) — JSON text
  * •
[`encoding::cbor::encode`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingcborencode) / [`decode`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingcbordecode) — [CBOR](https://surrealdb.com/docs/reference/rest-api/cbor-protocol) bytes
  * •
[`encoding::base64::encode`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingbase64encode) / [`decode`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/encoding#encodingbase64decode) — Base64 text for binary payloads

Typical uses: [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api) request bodies, file bucket payloads, and SDK interchange. Round-trip is the mental model.

```surql
LET $payload = { event: 'signup', user: 'tobie' };

-- Value → JSON text → value again
encoding::json::decode(encoding::json::encode($payload));
-- { event: 'signup', user: 'tobie' }
```

Related one-way or format-specific helpers elsewhere include `string::html::encode`, `geo::hash::encode`, and [`crypto::*`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/crypto) hashes.
##  Text analysis (`search::analyze`)[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs#text-analysis-searchanalyze)
[`search::analyze`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/search#searchanalyze) runs a named [`DEFINE ANALYZER`](https://surrealdb.com/docs/reference/query-language/statements/define/analyzer) pipeline on a string and returns an array of tokens. It is **lossy** (stemming, filtering) and mirrors what full-text indexing does — useful for debugging analyzers before you index.
The "format" here is not JSON or CBOR; it is whatever pipeline you defined on the analyzer.

```surql
DEFINE ANALYZER demo_blank TOKENIZERS blank;

search::analyze("demo_blank", "SurrealDB graph queries");
-- ['SurrealDB', 'graph', 'queries']
```

Compare the tokens above with what you get after adding `FILTERS lowercase, snowball(english)` — the same input string produces a different token list, which is why `search::analyze` is handy when tuning an analyzer before you create a [`FULLTEXT`](https://surrealdb.com/docs/reference/query-language/statements/define/indexes) index.
##  Structured parsing (`parse::*`)[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs#structured-parsing-parse)
[`parse::url::*`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse) and [`parse::email::*`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/parse) extract one component from a structured string. There is no round-trip — you get a field value, not a reassembled URL.

```surql
{
	domain: parse::url::domain("https://surrealdb.com/docs"),
	user: parse::email::user("tobie@surrealdb.com"),
};
-- { domain: 'surrealdb.com', user: 'tobie' }
```

##  In-value transforms (`value::*`)[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs#in-value-transforms-value)
[`value::diff`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valuediff) and [`value::patch`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/value#valuepatch) move between a SurrealQL value and JSON Patch operations. They pair naturally with [changefeeds](https://surrealdb.com/docs/learn/querying/real-time/changefeeds) and [`LIVE SELECT DIFF`](https://surrealdb.com/docs/learn/querying/real-time/live-queries).

```surql
LET $before = { title: 'Weekly update', status: 'draft' };
LET $after = { title: 'Weekly update', status: 'published' };
LET $patch = value::diff($before, $after);

value::patch($before, $patch);
-- { title: 'Weekly update', status: 'published' }
```

`value::diff` produced the patch; `value::patch` applied it. The same pair works when you receive patch operations from a client or a live diff stream.
##  Dynamic evaluation (`eval::*`)[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs#dynamic-evaluation-eval)
Available since: v3.2.0
[`eval::surql`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval#evalsurql) and [`eval::gql`](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval#evalgql) parse and **execute** query text in the caller's transaction. That is fundamentally different from encoding:
  * •
Input is **executable** SurrealQL or [ISO GQL](https://surrealdb.com/docs/learn/querying/gql/overview), not a static wire format.
  * •
**Denied by default** — requires [`allow-eval-query`](https://surrealdb.com/docs/learn/security/authorization/capabilities#eval-queries) and the [arbitrary-query](https://surrealdb.com/docs/learn/security/authorization/capabilities#arbitrary-queries) gate.
  * •
Nested writes affect the caller's transaction; transaction-control statements are rejected.

Use `eval::*` when the query string is only known at runtime. Prefer [`DEFINE FUNCTION`](https://surrealdb.com/docs/reference/query-language/statements/define/function), [`DEFINE API`](https://surrealdb.com/docs/reference/query-language/statements/define/api), or normal client queries when the shape of the work is fixed at deploy time.

```surql
-- Query text from a table, config row, or user input (requires allow-eval-query)
LET $template = "$greeting + ', ' + $name";
eval::surql($template, { greeting: 'Hello', name: 'world' });
-- 'Hello, world'
```

For [ISO GQL](https://surrealdb.com/docs/learn/querying/gql/overview) strings, use `eval::gql` instead — same bindings object, plus the `gql` experimental capability. See [Eval functions](https://surrealdb.com/docs/reference/query-language/functions/database-functions/eval) for setup and examples.
##  See also[](https://surrealdb.com/docs/learn/querying/concepts-and-guides/representations-and-codecs#see-also)
  * •
[Database functions catalogue](https://surrealdb.com/docs/reference/query-language/functions/database-functions)
  * •
[Parameterised queries](https://surrealdb.com/docs/learn/querying/concepts-and-guides/parameterised-queries) — `$parameters` at the SurrealQL layer (contrast with `eval` bindings)
  * •
[Capabilities](https://surrealdb.com/docs/learn/security/authorization/capabilities)
