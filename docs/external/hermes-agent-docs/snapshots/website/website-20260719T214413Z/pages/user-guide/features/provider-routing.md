# Provider Routing
When using [OpenRouter](https://openrouter.ai) or [Nous Portal](https://hermes-agent.nousresearch.com/docs/integrations/nous-portal) as your LLM provider, Hermes Agent supports **provider routing** — fine-grained control over which underlying AI providers handle your requests and how they're prioritized.
OpenRouter routes requests to many providers (e.g., Anthropic, Google, AWS Bedrock, Together AI). Provider routing lets you optimize for cost, speed, quality, or enforce specific provider requirements.
tip
Traffic routed through Nous Portal respects the same provider preferences — and Portal subscribers get 10% off token-billed providers.
## Configuration[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#configuration "Direct link to Configuration")
Add a `provider_routing` section to your `~/.hermes/config.yaml`:

```
provider_routing:  
  sort: "price"           # How to rank providers  
  only: []                # Whitelist: only use these providers  
  ignore: []              # Blacklist: never use these providers  
  order: []               # Explicit provider priority order  
  require_parameters: false  # Only use providers that support all parameters  
  data_collection: null   # Control data collection ("allow" or "deny")  

```

info
Provider routing only applies when using OpenRouter or Nous Portal. It has no effect with direct provider connections (e.g., connecting directly to the Anthropic API).
## Options[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#options "Direct link to Options")
###  `sort`[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#sort "Direct link to sort")
Controls how OpenRouter ranks available providers for your request.  
| Value  | Description  |  
| --- | --- |  
| `"price"`  | Cheapest provider first  |  
| `"throughput"`  | Fastest tokens-per-second first  |  
| `"latency"`  | Lowest time-to-first-token first  |  

```
provider_routing:  
  sort: "price"  

```

###  `only`[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#only "Direct link to only")
Whitelist of provider slugs. When set, **only** these providers will be used. All others are excluded. Use the lowercase slug shown by OpenRouter for each provider.

```
provider_routing:  
  only:  
    - "anthropic"  
    - "google"  

```

###  `ignore`[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#ignore "Direct link to ignore")
Blacklist of provider names. These providers will **never** be used, even if they offer the cheapest or fastest option.

```
provider_routing:  
  ignore:  
    - "together"  
    - "deepinfra"  

```

###  `order`[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#order "Direct link to order")
Explicit priority order. Providers listed first are preferred. Unlisted providers are used as fallbacks.

```
provider_routing:  
  order:  
    - "anthropic"  
    - "google"  
    - "amazon-bedrock"  

```

###  `require_parameters`[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#require_parameters "Direct link to require_parameters")
When `true`, OpenRouter will only route to providers that support **all** parameters in your request (like `temperature`, `top_p`, `tools`, etc.). This avoids silent parameter drops.

```
provider_routing:  
  require_parameters: true  

```

###  `data_collection`[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#data_collection "Direct link to data_collection")
Controls whether providers can use your prompts for training. Options are `"allow"` or `"deny"`.

```
provider_routing:  
  data_collection: "deny"  

```

## Practical Examples[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#practical-examples "Direct link to Practical Examples")
### Optimize for Cost[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#optimize-for-cost "Direct link to Optimize for Cost")
Route to the cheapest available provider. Good for high-volume usage and development:

```
provider_routing:  
  sort: "price"  

```

### Optimize for Speed[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#optimize-for-speed "Direct link to Optimize for Speed")
Prioritize low-latency providers for interactive use:

```
provider_routing:  
  sort: "latency"  

```

### Optimize for Throughput[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#optimize-for-throughput "Direct link to Optimize for Throughput")
Best for long-form generation where tokens-per-second matters:

```
provider_routing:  
  sort: "throughput"  

```

### Lock to Specific Providers[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#lock-to-specific-providers "Direct link to Lock to Specific Providers")
Ensure all requests go through a specific provider for consistency:

```
provider_routing:  
  only:  
    - "anthropic"  

```

### Avoid Specific Providers[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#avoid-specific-providers "Direct link to Avoid Specific Providers")
Exclude providers you don't want to use (e.g., for data privacy):

```
provider_routing:  
  ignore:  
    - "together"  
    - "lepton"  
  data_collection: "deny"  

```

### Preferred Order with Fallbacks[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#preferred-order-with-fallbacks "Direct link to Preferred Order with Fallbacks")
Try your preferred providers first, fall back to others if unavailable:

```
provider_routing:  
  order:  
    - "anthropic"  
    - "google"  
  require_parameters: true  

```

## How It Works[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#how-it-works "Direct link to How It Works")
Provider routing preferences are passed to OpenRouter or Nous Portal on agent chat requests and iteration-limit summaries via the `extra_body.provider` field. (`extra_body` is the OpenAI Python SDK argument; it becomes the top-level `provider` object in the JSON request.) Auxiliary tasks such as compression and title generation are configured independently under `auxiliary.<task>.extra_body`.
  * **CLI mode** — configured in `~/.hermes/config.yaml`, loaded at startup
  * **Gateway mode** — same config file, loaded when the gateway starts

The routing config is read from `config.yaml` and passed as parameters when creating the `AIAgent`:

```
providers_allowed  ← from provider_routing.only  
providers_ignored  ← from provider_routing.ignore  
providers_order    ← from provider_routing.order  
provider_sort      ← from provider_routing.sort  
provider_require_parameters ← from provider_routing.require_parameters  
provider_data_collection    ← from provider_routing.data_collection  

```

tip
You can combine multiple options. For example, sort by price but exclude certain providers and require parameter support:

```
provider_routing:  
  sort: "price"  
  ignore: ["together"]  
  require_parameters: true  
  data_collection: "deny"  

```

## Default Behavior[​](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing#default-behavior "Direct link to Default Behavior")
When no `provider_routing` section is configured (the default), the aggregator uses its own default routing logic, which generally balances cost and availability automatically.
Provider Routing vs. Fallback Models
Provider routing controls which **sub-providers behind OpenRouter or Nous Portal** handle your requests. For automatic failover to an entirely different provider when your primary model fails, see [Fallback Providers](https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers).
