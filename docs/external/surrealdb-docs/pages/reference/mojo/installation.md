---
title: "https://surrealdb.com/docs/reference/mojo/installation"
url: "https://surrealdb.com/docs/reference/mojo/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/mojo/installation

Source: https://surrealdb.com/docs/reference/mojo/installation

In this section, you will learn how to install the SurrealDB Mojo SDK and add it to your project.
##  Requirements[](https://surrealdb.com/docs/reference/mojo/installation#requirements)
The only runtime dependency is Mojo itself, pinned to `0.26.1.x`. The project uses [pixi](https://pixi.sh/) to manage the Mojo toolchain.  
| Platform  | Architecture  | Status  |  
| --- | --- | --- |  
| macOS  | arm64  | Tested  |  
| Linux  | x86_64  | Tested  |  
| Linux  | aarch64  | Tested  |  
| Windows  | n/a  | Use WSL2; Mojo has no native Windows toolchain  |  
##  Install the SDK[](https://surrealdb.com/docs/reference/mojo/installation#install-the-sdk)
Clone the repository and install the toolchain with pixi:

```bash
git clone https://github.com/surrealdb/surrealdb.mojo
cd surrealdb.mojo
pixi install
```

To use the SDK from your own project, either vendor `src/surrealdb` into your Mojo package path, or build it into a `.mojopkg`:

```bash
pixi run check     # produces build/surrealdb.mojopkg
```

##  Import the SDK into your project[](https://surrealdb.com/docs/reference/mojo/installation#import-the-sdk-into-your-project)
Import the client and connection options from the `surrealdb` package:

```python
from surrealdb import AsyncSurrealClient, ConnectOptions
from std.collections import Optional
```

For the blocking client, import `SurrealClient` instead:

```python
from surrealdb import SurrealClient
```

##  Run your program[](https://surrealdb.com/docs/reference/mojo/installation#run-your-program)
Run a Mojo file with the SDK source on the include path:

```bash
pixi run mojo run -I src yourfile.mojo
```

##  Build with HTTPS[](https://surrealdb.com/docs/reference/mojo/installation#build-with-https)
The TLS code sits behind a compile-time gate, so `mojo run` invocations without HTTPS keep working with no OpenSSL on the system. To connect over `https://` or `wss://`, build your program with `mojo build`, define the `HTTPS` flag, and link against `libssl` and `libcrypto` from the pixi environment:

```bash
PIXI_ENV=$(pwd)/.pixi/envs/default
pixi run mojo build -I src -o app \
  -D HTTPS=1 \
  -Xlinker -L$PIXI_ENV/lib \
  -Xlinker -lssl -Xlinker -lcrypto \
  yourfile.mojo

DYLD_LIBRARY_PATH=$PIXI_ENV/lib ./app  # macOS
LD_LIBRARY_PATH=$PIXI_ENV/lib ./app    # Linux
```

If you use an `https://` URL without `-D HTTPS=1`, the SDK raises a `ConnectionError` that names the build flags you need.
##  Next steps[](https://surrealdb.com/docs/reference/mojo/installation#next-steps)
  * •
[Getting started](https://surrealdb.com/docs/languages/mojo) for a complete working example.
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/mojo/concepts/connecting-to-surrealdb) for connection options and transports.
  * •
[Authentication](https://surrealdb.com/docs/reference/mojo/concepts/authentication) for signing in and managing credentials.
