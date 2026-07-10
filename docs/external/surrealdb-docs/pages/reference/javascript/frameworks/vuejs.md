---
title: "https://surrealdb.com/docs/reference/javascript/frameworks/vuejs"
url: "https://surrealdb.com/docs/reference/javascript/frameworks/vuejs"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/frameworks/vuejs

Source: https://surrealdb.com/docs/reference/javascript/frameworks/vuejs

[Vue.js](https://vuejs.org/) is a progressive JavaScript framework for building user interfaces. The SurrealDB SDK for JavaScript can be used in your Vue applications to interact with your SurrealDB instance.
This guide walks you through setting up a connection plugin and executing queries in a Vue 3 project using the Composition API.
##  Prerequisites[](https://surrealdb.com/docs/reference/javascript/frameworks/vuejs#prerequisites)
  * •
A basic understanding of Vue 3 and the Composition API
  * •
A running [SurrealDB instance](https://surrealdb.com/docs/start)
  * •
The [JavaScript SDK installed](https://surrealdb.com/docs/reference/javascript/installation) in your project

##  Installing dependencies[](https://surrealdb.com/docs/reference/javascript/frameworks/vuejs#installing-dependencies)
In addition to `surrealdb`, this guide uses [@tanstack/vue-query](https://tanstack.com/query/latest/docs/framework/vue) to manage the asynchronous connection state. Install both packages:
npmyarnpnpm

```bash
npm install --save surrealdb @tanstack/vue-query
```

```bash
yarn add surrealdb @tanstack/vue-query
```

```bash
pnpm install surrealdb @tanstack/vue-query
```

Follow the [installation guide](https://surrealdb.com/docs/reference/javascript/installation) for more information on how to install the SDK in your project.
##  Value classes[](https://surrealdb.com/docs/reference/javascript/frameworks/vuejs#value-classes)
Before you can use the SDK in your Vue application, you need to configure the codec options to mark all returned [value classes](https://surrealdb.com/docs/reference/javascript/concepts/value-types) as raw. This prevents Vue's reactivity system from being applied to them, and allows you to use them in your components without any issues.

```ts
import { Surreal, Value } from "surrealdb";
import { markRaw } from "vue";

const db = new Surreal({
	codecOptions: {
		valueDecodeVisitor: (value) => value instanceof Value ? markRaw(value) : value,
	},
});
```

The `valueDecodeVisitor` function is called for each value returned from the database. If the value is an instance of a value class, it is marked as raw so Vue's reactivity system is not triggered.
##  Creating the connection plugin[](https://surrealdb.com/docs/reference/javascript/frameworks/vuejs#creating-the-connection-plugin)
We recommend providing the `Surreal` client through Vue's [dependency injection](https://vuejs.org/guide/components/provide-inject) system so it is accessible in any component. The composable below manages the connection lifecycle, tracks status via TanStack Query, and cleans up when the component unmounts.
The `params` option accepts the same values as [`.connect()`](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#connection-options), including `namespace`, `database`, and [`authentication`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#providing-credentials-on-connect).

```ts
import { Surreal } from "surrealdb";
import { inject, onUnmounted, provide, type InjectionKey, type Ref } from "vue";
import { useMutation } from "@tanstack/vue-query";

interface SurrealOptions {
    endpoint: string;
    client?: Surreal;
    params?: Parameters<Surreal["connect"]>[1];
    autoConnect?: boolean;
}

interface SurrealState {
    client: Surreal;
    isConnecting: Ref<boolean>;
    isSuccess: Ref<boolean>;
    isError: Ref<boolean>;
    error: Ref<unknown>;
    connect: () => Promise<true>;
    close: () => Promise<true>;
}

const SurrealKey: InjectionKey<SurrealState> = Symbol("surreal");

export function provideSurreal(options: SurrealOptions) {
    const instance = options.client ?? new Surreal();

    const { mutateAsync, isPending, isSuccess, isError, error, reset } = useMutation({
        mutationFn: () => instance.connect(options.endpoint, options.params),
    });

    if (options.autoConnect !== false) {
        mutateAsync();
    }

    onUnmounted(() => {
        reset();
        instance.close();
    });

    const state: SurrealState = {
        client: instance,
        isConnecting: isPending,
        isSuccess,
        isError,
        error,
        connect: () => mutateAsync(),
        close: () => instance.close(),
    };

    provide(SurrealKey, state);
    return state;
}

export function useSurreal(): SurrealState {
    const state = inject(SurrealKey);
    if (!state) throw new Error("useSurreal() requires provideSurreal() in a parent component");
    return state;
}

export function useSurrealClient(): Surreal {
    return useSurreal().client;
}
```

##  Initializing the plugin[](https://surrealdb.com/docs/reference/javascript/frameworks/vuejs#initializing-the-plugin)
Register the TanStack Query plugin in your application entry point, then call `provideSurreal()` in your root component. Pass the endpoint and any [connection options](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#connection-options) through the `params` field.

```ts
import { createApp } from "vue";
import { VueQueryPlugin } from "@tanstack/vue-query";
import App from "./App.vue";

const app = createApp(App);
app.use(VueQueryPlugin);
app.mount("#app");
```

```vue
<script setup lang="ts">
import { provideSurreal } from "./surreal";

provideSurreal({
    endpoint: "ws://127.0.0.1:8000",
    params: {
        namespace: "surrealdb",
        database: "docs",
        authentication: {
            username: "root",
            password: "root",
        },
    },
});
</script>

<template>
    <router-view />
</template>
```

##  Executing queries[](https://surrealdb.com/docs/reference/javascript/frameworks/vuejs#executing-queries)
Use the `useSurrealClient()` composable to access the `Surreal` instance from any descendant component. All [query methods](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries) are available on the client, including `.query()`, `.select()`, `.create()`, and more.

```vue
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Table } from "surrealdb";
import { useSurreal, useSurrealClient } from "./surreal";

interface User {
    id: string;
    name: string;
    email: string;
}

const { isConnecting, isError, error } = useSurreal();
const client = useSurrealClient();
const users = ref<User[]>([]);

onMounted(async () => {
    users.value = await client.select<User>(new Table("users"));
});
</script>

<template>
    <p v-if="isConnecting">Connecting...</p>
    <p v-else-if="isError">Connection failed: {{ String(error) }}</p>
    <ul v-else>
        <li v-for="user in users" :key="String(user.id)">
            {{ user.name }} ({{ user.email }})
        </li>
    </ul>
</template>
```

##  Handling authentication[](https://surrealdb.com/docs/reference/javascript/frameworks/vuejs#handling-authentication)
You can build an authentication layer on top of the composable using the SDK's [`.signin()`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-in-users) and [`.signup()`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-up-users) methods. The example below shows a minimal composable for record access authentication.

```ts
import { useSurrealClient } from "./surreal";

export function useAuth() {
    const client = useSurrealClient();

    async function login(email: string, password: string) {
        return client.signin({
            namespace: "surrealdb",
            database: "docs",
            access: "account",
            variables: { email, password },
        });
    }

    async function register(email: string, password: string) {
        return client.signup({
            namespace: "surrealdb",
            database: "docs",
            access: "account",
            variables: { email, password },
        });
    }

    async function logout() {
        return client.invalidate();
    }

    return { login, register, logout };
}
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/frameworks/vuejs#learn-more)
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb) for connection protocols and reconnection behavior
  * •
[Authentication](https://surrealdb.com/docs/reference/javascript/concepts/authentication) for signing in, signing up, and token management
  * •
[Executing queries](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries) for query builders and raw SurrealQL
  * •
[Live queries](https://surrealdb.com/docs/reference/javascript/concepts/live-queries) for real-time subscriptions
  * •
[JavaScript SDK API reference](https://surrealdb.com/docs/reference/javascript/api/) for the complete method reference
