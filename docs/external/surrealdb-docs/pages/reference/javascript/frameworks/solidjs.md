---
title: "https://surrealdb.com/docs/reference/javascript/frameworks/solidjs"
url: "https://surrealdb.com/docs/reference/javascript/frameworks/solidjs"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/frameworks/solidjs

Source: https://surrealdb.com/docs/reference/javascript/frameworks/solidjs

[SolidJS](https://docs.solidjs.com/) is a modern JavaScript framework for building responsive and high-performing user interfaces. The SurrealDB SDK for JavaScript can be used in your SolidJS applications to interact with your SurrealDB instance.
This guide walks you through setting up a connection provider and executing queries in a SolidJS project.
##  Prerequisites[](https://surrealdb.com/docs/reference/javascript/frameworks/solidjs#prerequisites)
  * •
A basic understanding of SolidJS
  * •
A running [SurrealDB instance](https://surrealdb.com/docs/start)
  * •
The [JavaScript SDK installed](https://surrealdb.com/docs/reference/javascript/installation) in your project

##  Installing dependencies[](https://surrealdb.com/docs/reference/javascript/frameworks/solidjs#installing-dependencies)
In addition to `surrealdb`, this guide uses [@tanstack/solid-query](https://tanstack.com/query/latest/docs/framework/solid) to manage the asynchronous connection state. Install it alongside the SDK:
npmyarnpnpm

```bash
npm install --save surrealdb @tanstack/solid-query
```

```bash
yarn add surrealdb @tanstack/solid-query
```

```bash
pnpm install surrealdb @tanstack/solid-query
```

Follow the [installation guide](https://surrealdb.com/docs/reference/javascript/installation) for more information on how to install the SDK in your project.
##  Creating the connection provider[](https://surrealdb.com/docs/reference/javascript/frameworks/solidjs#creating-the-connection-provider)
We recommend initializing the SDK in a [Context Provider](https://docs.solidjs.com/concepts/context) so the `Surreal` client is accessible anywhere in your component tree. The provider below manages the connection lifecycle, tracks connection status via TanStack Query, and cleans up automatically.
The `params` prop accepts the same options as [`.connect()`](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#connection-options), including `namespace`, `database`, and [`authentication`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#providing-credentials-on-connect).

```tsx
import { Surreal } from "surrealdb";
import { useContext, createContext, JSX, createEffect, onCleanup, Accessor, onMount } from "solid-js";
import { createMutation } from "@tanstack/solid-query";
import { createStore } from "solid-js/store";

interface SurrealProviderProps {
    children: JSX.Element;
    endpoint: string;
    client?: Surreal;
    params?: Parameters<Surreal["connect"]>[1];
    autoConnect?: boolean;
}

interface SurrealProviderState {
    client: Accessor<Surreal>;
    isConnecting: Accessor<boolean>;
    isSuccess: Accessor<boolean>;
    isError: Accessor<boolean>;
    error: Accessor<unknown | null>;
    connect: () => Promise<void>;
    close: () => Promise<true>;
}

interface SurrealProviderStore {
    instance: Surreal;
    status: "connecting" | "connected" | "disconnected";
}

const SurrealContext = createContext<SurrealProviderState>();

export function SurrealProvider(props: SurrealProviderProps) {
    const [store, setStore] = createStore<SurrealProviderStore>({
        instance: props.client ?? new Surreal(),
        status: "disconnected",
    });

    const { mutateAsync, isError, error, reset } = createMutation(() => ({
        mutationFn: async () => {
            setStore("status", "connecting");
            await store.instance.connect(props.endpoint, props.params);
        },
    }));

    createEffect(() => {
        if (props.autoConnect !== false) mutateAsync();

        onCleanup(() => {
            reset();
            store.instance.close();
        });
    });

    onMount(() => {
        store.instance.subscribe("connected", () => {
            setStore("status", "connected");
        });

        store.instance.subscribe("disconnected", () => {
            setStore("status", "disconnected");
        });
    });

    const value: SurrealProviderState = {
        client: () => store.instance,
        close: () => store.instance.close(),
        connect: mutateAsync,
        error: () => error,
        isConnecting: () => store.status === "connecting",
        isError: () => isError,
        isSuccess: () => store.status === "connected",
    };

    return (
        <SurrealContext.Provider value={value}>
            {props.children}
        </SurrealContext.Provider>
    );
}

export function useSurreal(): SurrealProviderState {
    const context = useContext(SurrealContext);
    if (!context) throw new Error("useSurreal must be used within a SurrealProvider");
    return context;
}

export function useSurrealClient() {
    return useSurreal().client;
}
```

##  Wrapping your application[](https://surrealdb.com/docs/reference/javascript/frameworks/solidjs#wrapping-your-application)
In your top-level component, wrap the root with `QueryClientProvider` and `SurrealProvider`. Pass the endpoint and any [connection options](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#connection-options) through the `params` prop.

```tsx
import type { Component } from "solid-js";
import { QueryClient, QueryClientProvider } from "@tanstack/solid-query";
import { SurrealProvider } from "./SurrealProvider";
import App from "./App";

const queryClient = new QueryClient();

const Root: Component = () => {
    return (
        <QueryClientProvider client={queryClient}>
            <SurrealProvider
                endpoint="ws://127.0.0.1:8000"
                params={{
                    namespace: "surrealdb",
                    database: "docs",
                    authentication: {
                        username: "root",
                        password: "root",
                    },
                }}
            >
                <App />
            </SurrealProvider>
        </QueryClientProvider>
    );
};

export default Root;
```

##  Executing queries[](https://surrealdb.com/docs/reference/javascript/frameworks/solidjs#executing-queries)
Use the `useSurrealClient()` hook to access the `Surreal` instance from any component. All [query methods](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries) are available on the client, including `.query()`, `.select()`, `.create()`, and more.

```tsx
import { createResource, For, Show } from "solid-js";
import { Table } from "surrealdb";
import { useSurreal, useSurrealClient } from "./SurrealProvider";

interface User {
    id: string;
    name: string;
    email: string;
}

export function UserList() {
    const { isConnecting, isError, error } = useSurreal();
    const client = useSurrealClient();

    const [users] = createResource(async () => {
        return client().select<User>(new Table("users"));
    });

    return (
        <Show when={!isConnecting()} fallback={<p>Connecting...</p>}>
            <Show when={!isError()} fallback={<p>Connection failed: {String(error())}</p>}>
                <ul>
                    <For each={users()}>
                        {(user) => <li>{user.name} ({user.email})</li>}
                    </For>
                </ul>
            </Show>
        </Show>
    );
}
```

##  Handling authentication[](https://surrealdb.com/docs/reference/javascript/frameworks/solidjs#handling-authentication)
You can build an authentication layer on top of the provider using the SDK's [`.signin()`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-in-users) and [`.signup()`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-up-users) methods. The example below shows a minimal hook for record access authentication.

```tsx
import { useSurrealClient } from "./SurrealProvider";

export function useAuth() {
    const client = useSurrealClient();

    async function login(email: string, password: string) {
        return client().signin({
            namespace: "surrealdb",
            database: "docs",
            access: "account",
            variables: { email, password },
        });
    }

    async function register(email: string, password: string) {
        return client().signup({
            namespace: "surrealdb",
            database: "docs",
            access: "account",
            variables: { email, password },
        });
    }

    async function logout() {
        return client().invalidate();
    }

    return { login, register, logout };
}
```

##  Learn more[](https://surrealdb.com/docs/reference/javascript/frameworks/solidjs#learn-more)
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
