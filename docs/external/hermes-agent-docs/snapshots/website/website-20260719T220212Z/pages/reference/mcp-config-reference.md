# MCP Config Reference
This page is the compact reference companion to the main MCP docs.
For conceptual guidance, see:
  * [MCP (Model Context Protocol)](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
  * [Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes)

## Root config shape[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#root-config-shape "Direct link to Root config shape")

```
mcp_servers:  
  <server_name>:  
    command: "..."      # stdio servers  
    args: []  
    env: {}  
  
    # OR  
    url: "..."          # HTTP servers  
    headers: {}  
  
    # Optional HTTP/SSE TLS settings:  
    ssl_verify: true                # bool or path to a CA bundle (PEM)  
    client_cert: "/path/to/cert.pem"  # mTLS client certificate (see below)  
    # client_key: "/path/to/key.pem"  # optional, when key lives in a separate file  
  
    enabled: true  
    timeout: 120  
    connect_timeout: 60  
    supports_parallel_tool_calls: false  
    tools:  
      include: []  
      exclude: []  
      resources: true  
      prompts: true  

```

## Server keys[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#server-keys "Direct link to Server keys")  
| Key  | Type  | Applies to  | Meaning  |  
| --- | --- | --- | --- |  
| `command`  | string  | stdio  | Executable to launch  |  
| `args`  | list  | stdio  | Arguments for the subprocess  |  
| `env`  | mapping  | stdio  | Environment passed to the subprocess  |  
| `url`  | string  | HTTP  | Remote MCP endpoint  |  
| `headers`  | mapping  | HTTP  | Headers for remote server requests  |  
| `ssl_verify`  | bool or string  | HTTP  | TLS verification. `true` (default) uses system CAs, `false` disables verification (insecure), or a string path to a custom CA bundle (PEM)  |  
| `client_cert`  | string or list  | HTTP  | mTLS client certificate. String = path to a PEM file containing cert + key. List `[cert, key]` = separate files. List `[cert, key, password]` = encrypted key  |  
| `client_key`  | string  | HTTP  | Path to the client private key, when `client_cert` is a string and the key is in a separate file  |  
| `enabled`  | bool  | both  | Skip the server entirely when false  |  
| `timeout`  | number  | both  | Tool call timeout in seconds (default: `300`)  |  
| `connect_timeout`  | number  | both  | Initial connection timeout in seconds (default: `60`)  |  
| `supports_parallel_tool_calls`  | bool  | both  | Allow tools from this server to run concurrently  |  
| `skip_preflight`  | bool  | HTTP  | Bypass the fail-fast content-type probe for valid Streamable HTTP endpoints whose HEAD/GET answers a non-MCP content type (default: `false`)  |  
| `tools`  | mapping  | both  | Filtering and utility-tool policy  |  
| `auth`  | string  | HTTP  | Authentication method. Set to `oauth` to enable OAuth 2.1 with PKCE  |  
| `sampling`  | mapping  | both  | Server-initiated LLM request policy (see MCP guide)  |  
##  `tools` policy keys[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#tools-policy-keys "Direct link to tools-policy-keys")  
| Key  | Type  | Meaning  |  
| --- | --- | --- |  
| `include`  | string or list  | Whitelist server-native MCP tools  |  
| `exclude`  | string or list  | Blacklist server-native MCP tools  |  
| `resources`  | bool-like  | Enable/disable `list_resources` + `read_resource`  |  
| `prompts`  | bool-like  | Enable/disable `list_prompts` + `get_prompt`  |  
## Filtering semantics[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#filtering-semantics "Direct link to Filtering semantics")
###  `include`[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#include "Direct link to include")
If `include` is set, only those server-native MCP tools are registered.

```
tools:  
  include: [create_issue, list_issues]  

```

###  `exclude`[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#exclude "Direct link to exclude")
If `exclude` is set and `include` is not, every server-native MCP tool except those names is registered.

```
tools:  
  exclude: [delete_customer]  

```

### Precedence[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#precedence "Direct link to Precedence")
If both are set, `include` wins.

```
tools:  
  include: [create_issue]  
  exclude: [create_issue, delete_issue]  

```

Result:
  * `create_issue` is still allowed
  * `delete_issue` is ignored because `include` takes precedence

## Utility-tool policy[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#utility-tool-policy "Direct link to Utility-tool policy")
Hermes may register these utility wrappers per MCP server:
Resources:
  * `list_resources`
  * `read_resource`

Prompts:
  * `list_prompts`
  * `get_prompt`

### Disable resources[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#disable-resources "Direct link to Disable resources")

```
tools:  
  resources: false  

```

### Disable prompts[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#disable-prompts "Direct link to Disable prompts")

```
tools:  
  prompts: false  

```

### Capability-aware registration[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#capability-aware-registration "Direct link to Capability-aware registration")
Even when `resources: true` or `prompts: true`, Hermes only registers those utility tools if the MCP session actually exposes the corresponding capability.
So this is normal:
  * you enable prompts
  * but no prompt utilities appear
  * because the server does not support prompts

##  `enabled: false`[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#enabled-false "Direct link to enabled-false")

```
mcp_servers:  
  legacy:  
    url: "https://mcp.legacy.internal"  
    enabled: false  

```

Behavior:
  * no connection attempt
  * no discovery
  * no tool registration
  * config remains in place for later reuse

## Empty result behavior[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#empty-result-behavior "Direct link to Empty result behavior")
If filtering removes all server-native tools and no utility tools are registered, Hermes does not create an empty MCP runtime toolset for that server.
## Example configs[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#example-configs "Direct link to Example configs")
### Safe GitHub allowlist[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#safe-github-allowlist "Direct link to Safe GitHub allowlist")

```
mcp_servers:  
  github:  
    command: "npx"  
    args: ["-y", "@modelcontextprotocol/server-github"]  
    env:  
      GITHUB_PERSONAL_ACCESS_TOKEN: "***"  
    tools:  
      include: [list_issues, create_issue, update_issue, search_code]  
      resources: false  
      prompts: false  

```

### Stripe blacklist[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#stripe-blacklist "Direct link to Stripe blacklist")

```
mcp_servers:  
  stripe:  
    url: "https://mcp.stripe.com"  
    headers:  
      Authorization: "Bearer ***"  
    tools:  
      exclude: [delete_customer, refund_payment]  

```

### Resource-only docs server[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#resource-only-docs-server "Direct link to Resource-only docs server")

```
mcp_servers:  
  docs:  
    url: "https://mcp.docs.example.com"  
    tools:  
      include: []  
      resources: true  
      prompts: false  

```

### TLS client certificate (mTLS)[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#tls-client-certificate-mtls "Direct link to TLS client certificate \(mTLS\)")
For HTTP/SSE servers that require a client certificate, set `client_cert` (and optionally `client_key`):

```
mcp_servers:  
  # Combined cert + key in a single PEM file  
  internal_api:  
    url: "https://mcp.internal.example.com/mcp"  
    client_cert: "~/secrets/mcp-client.pem"  
  
  # Separate cert and key files  
  partner_api:  
    url: "https://mcp.partner.example.com/mcp"  
    client_cert: "~/secrets/client.crt"  
    client_key: "~/secrets/client.key"  
  
  # Encrypted key with a passphrase (3-element list form)  
  bank_api:  
    url: "https://mcp.bank.example.com/mcp"  
    client_cert: ["~/secrets/client.crt", "~/secrets/client.key", "my-passphrase"]  
  
  # Custom CA bundle (private CA / self-signed server)  
  lab_api:  
    url: "https://mcp.lab.local/mcp"  
    ssl_verify: "~/secrets/lab-ca.pem"  
    client_cert: "~/secrets/lab-client.pem"  

```

Notes:
  * Paths support `~` expansion. Missing files fail fast at connect time with a server-scoped error message.
  * `ssl_verify: false` disables server certificate verification entirely. Don't use this with real services.
  * Works on both Streamable HTTP and SSE transports.

## Reloading config[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#reloading-config "Direct link to Reloading config")
After changing MCP config, reload servers with:

```
/reload-mcp  

```

## Tool naming[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#tool-naming "Direct link to Tool naming")
Server-native MCP tools become:

```
mcp_<server>_<tool>  

```

Examples:
  * `mcp_github_create_issue`
  * `mcp_filesystem_read_file`
  * `mcp_my_api_query_data`

Utility tools follow the same prefixing pattern:
  * `mcp_<server>_list_resources`
  * `mcp_<server>_read_resource`
  * `mcp_<server>_list_prompts`
  * `mcp_<server>_get_prompt`

### Name sanitization[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#name-sanitization "Direct link to Name sanitization")
Hyphens (`-`) and dots (`.`) in both server names and tool names are replaced with underscores before registration. This ensures tool names are valid identifiers for LLM function-calling APIs.
For example, a server named `my-api` exposing a tool called `list-items.v2` becomes:

```
mcp_my_api_list_items_v2  

```

Keep this in mind when writing `include` / `exclude` filters — use the **original** MCP tool name (with hyphens/dots), not the sanitized version.
## OAuth 2.1 authentication[​](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference#oauth-21-authentication "Direct link to OAuth 2.1 authentication")
For HTTP servers that require OAuth, set `auth: oauth` on the server entry:

```
mcp_servers:  
  protected_api:  
    url: "https://mcp.example.com/mcp"  
    auth: oauth  

```

Behavior:
  * Hermes uses the MCP SDK's OAuth 2.1 PKCE flow (metadata discovery, dynamic client registration, token exchange, and refresh)
  * On first connect, a browser window opens for authorization
  * Tokens are persisted to `~/.hermes/mcp-tokens/<server>.json` and reused across sessions
  * Token refresh is automatic; re-authorization only happens when refresh fails
  * Only applies to HTTP/StreamableHTTP transport (`url`-based servers)
