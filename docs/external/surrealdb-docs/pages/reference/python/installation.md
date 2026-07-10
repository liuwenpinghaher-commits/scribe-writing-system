---
title: "https://surrealdb.com/docs/reference/python/installation"
url: "https://surrealdb.com/docs/reference/python/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/python/installation

Source: https://surrealdb.com/docs/reference/python/installation

In this section, you will learn how to install the Python SDK in your project.
###  Install the SDK[](https://surrealdb.com/docs/reference/python/installation#install-the-sdk)
Install the [SurrealDB SDK](https://pypi.org/project/surrealdb/) from PyPI:

```bash
pip install surrealdb
```

If you want [pydantic](https://docs.pydantic.dev/) validation and serialization support for `RecordID`, install the optional extra:

```bash
pip install surrealdb[pydantic]
```

###  Import the SDK into your project[](https://surrealdb.com/docs/reference/python/installation#import-the-sdk-into-your-project)
The SDK provides two entry points depending on whether you need synchronous or asynchronous access.

```python
from surrealdb import Surreal
```

For asynchronous applications using `asyncio`:

```python
from surrealdb import AsyncSurreal
```

Both `Surreal` and `AsyncSurreal` are factory functions that accept a connection URL and return the appropriate connection class based on the protocol scheme.
##  Next steps[](https://surrealdb.com/docs/reference/python/installation#next-steps)
  * •
[Getting started](https://surrealdb.com/docs/languages/python) for a complete working example
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/python/concepts/connecting-to-surrealdb) for connection options and protocols
  * •
[Authentication](https://surrealdb.com/docs/reference/python/concepts/authentication) for signing in and managing credentials
