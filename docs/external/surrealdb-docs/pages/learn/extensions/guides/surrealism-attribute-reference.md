---
title: "https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference"
url: "https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference

Source: https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference

The `#[surrealism]` attribute controls which Rust items are exported from your module and how SurrealDB should treat them.
##  Basic export[](https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference#basic-export)
Use `#[surrealism]` on a function to expose it to SurrealQL:

```rust
use surrealism::surrealism;

#[surrealism]
fn can_drive(age: i64) -> bool {
    age >= 18
}
```

After packaging and `DEFINE MODULE`, this function is callable through your module path.
##  `writeable`[](https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference#writeable)
Mark functions that perform writes with `writeable`:

```rust
#[surrealism(writeable)]
fn kv_set_value(key: String, value: String) -> bool {
    // implementation snipped
    true
}
```

This metadata is used by the query planner so read-only and write-capable functions can be scheduled with appropriate transaction modes.
##  `comment = "..."`[](https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference#comment--)
Attach human-readable metadata to an export:

```rust
#[surrealism(comment = "Parses a decimal string into an integer")]
fn parse_number(input: String) -> Result<i64, String> {
    input.parse::<i64>().map_err(|e| e.to_string())
}
```

The comment appears in module metadata outputs such as:
  * •
`surreal module info`
  * •
`INFO FOR DB STRUCTURE` module export metadata

##  `init`[](https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference#init)
Register one initialisation hook that runs once after module instantiation:

```rust
#[surrealism(init)]
fn warm_cache() {
    // implementation omitted
}
```

Use this for one-time setup such as preloading attached files or priming in-module caches.
##  Namespaced modules[](https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference#namespaced-modules)
Apply `#[surrealism]` to modules to group exports under namespaces:

```rust
#[surrealism]
mod math {
    use surrealism::surrealism;

    #[surrealism]
    pub fn add(a: i64, b: i64) -> i64 {
        a + b
    }

    #[surrealism]
    pub mod util {
        use surrealism::surrealism;

        #[surrealism]
        pub fn negate(value: i64) -> i64 {
            -value
        }
    }
}
```

Exports are prefixed by namespace, for example:
  * •
`math::add`
  * •
`math::util::negate`

##  Related docs[](https://surrealdb.com/docs/learn/extensions/guides/surrealism-attribute-reference#related-docs)
  * •
[Creating custom modules](https://surrealdb.com/docs/learn/extensions/guides/creating-custom-modules)
  * •
[Module architecture](https://surrealdb.com/docs/learn/extensions/guides/module-architecture)
  * •
[Module command reference](https://surrealdb.com/docs/reference/cli/surrealdb-cli/commands/module)
