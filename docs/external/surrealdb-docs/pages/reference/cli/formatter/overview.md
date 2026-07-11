---
title: "https://surrealdb.com/docs/reference/cli/formatter/overview"
url: "https://surrealdb.com/docs/reference/cli/formatter/overview"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/cli/formatter/overview

Source: https://surrealdb.com/docs/reference/cli/formatter/overview

The `surqlfmt` tool reformats `.surql` files to follow a consistent style. It adjusts whitespace, indentation, and keyword casing so that SurrealQL code is easy to read and review.
##  Installation[](https://surrealdb.com/docs/reference/cli/formatter/overview#installation)
The tool can be installed through a single [npm install command](https://www.npmjs.com/package/@surrealdb/surql-fmt):

```bash
npm install -g @surrealdb/surql-fmt
```

##  Usage[](https://surrealdb.com/docs/reference/cli/formatter/overview#usage)
The tool outputs the reformatted file by default, and when the `--write` flag is passed in will reformat a `.surql` file in place.

```bash
# Format a single file
surqlfmt ./query.surql

# Check if files are formatted
surqlfmt --check ./src/**/*.surql

# Format from stdin
cat query.surql | surqlfmt --stdin

# Configure indentation and line length
surqlfmt --indent 4 --indent-char tab --max-line-length 120 *.surql

# Write files in-place
surqlfmt --write ./src/**/*.surql
```

##  When to use the formatter[](https://surrealdb.com/docs/reference/cli/formatter/overview#when-to-use-the-formatter)
  * •
**Before committing** — run `surreal fmt` on any `.surql` migration or seed files to keep diffs clean.
  * •
**In CI** — add a formatting check to catch inconsistencies early.
  * •
**During development** — pipe ad-hoc queries through the formatter for readability.

For the full list of command-line options, see the [CLI reference](https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview).
