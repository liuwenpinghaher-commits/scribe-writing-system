---
title: "https://surrealdb.com/docs/reference/javascript/frameworks/react"
url: "https://surrealdb.com/docs/reference/javascript/frameworks/react"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/javascript/frameworks/react

Source: https://surrealdb.com/docs/reference/javascript/frameworks/react

[React](https://react.dev/) is a popular JavaScript library for building user interfaces. The SurrealDB SDK for JavaScript can be used in your React applications to interact with your SurrealDB instance.
This guide walks you through setting up a connection provider and executing queries in a React project.
##  Prerequisites[](https://surrealdb.com/docs/reference/javascript/frameworks/react#prerequisites)
  * •
A basic understanding of React
  * •
A running [SurrealDB instance](https://surrealdb.com/docs/start)
  * •
The [JavaScript SDK installed](https://surrealdb.com/docs/reference/javascript/installation) in your project

##  Installing dependencies[](https://surrealdb.com/docs/reference/javascript/frameworks/react#installing-dependencies)
In addition to `surrealdb`, this guide uses [@tanstack/react-query](https://tanstack.com/query/latest) to manage the asynchronous connection state. Install it alongside the SDK:
npmyarnpnpm

```bash
npm install --save surrealdb @tanstack/react-query
```

```bash
yarn add surrealdb @tanstack/react-query
```

```bash
pnpm install surrealdb @tanstack/react-query
```

Follow the [installation guide](https://surrealdb.com/docs/reference/javascript/installation) for more information on how to install the SDK in your project.
##  Creating the connection provider[](https://surrealdb.com/docs/reference/javascript/frameworks/react#creating-the-connection-provider)
We recommend initializing the SDK in a [Context Provider](https://react.dev/learn/passing-data-deeply-with-context) so the `Surreal` client is accessible anywhere in your component tree. The provider below manages the connection lifecycle, tracks connection status via TanStack Query, and cleans up on unmount.
The `params` prop accepts the same options as [`.connect()`](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#connection-options), including `namespace`, `database`, and [`authentication`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#providing-credentials-on-connect).

```tsx
import { Surreal } from "surrealdb";
import { useMutation } from "@tanstack/react-query";
import React, { createContext, useContext, useEffect, useMemo, useCallback, useState } from "react";

interface SurrealProviderProps {
    children: React.ReactNode;
    endpoint: string;
    client?: Surreal;
    params?: Parameters<Surreal["connect"]>[1];
    autoConnect?: boolean;
}

interface SurrealProviderState {
    client: Surreal;
    isConnecting: boolean;
    isSuccess: boolean;
    isError: boolean;
    error: unknown;
    connect: () => Promise<true>;
    close: () => Promise<true>;
}

const SurrealContext = createContext<SurrealProviderState | undefined>(undefined);

export function SurrealProvider({
    children,
    client,
    endpoint,
    params,
    autoConnect = true,
}: SurrealProviderProps) {
    const [instance] = useState(() => client ?? new Surreal());

    const {
        mutateAsync: connectMutation,
        isPending,
        isSuccess,
        isError,
        error,
        reset,
    } = useMutation({
        mutationFn: () => instance.connect(endpoint, params),
    });

    const connect = useCallback(() => connectMutation(), [connectMutation]);
    const close = useCallback(() => instance.close(), [instance]);

    useEffect(() => {
        if (autoConnect) connect();

        return () => {
            reset();
            instance.close();
        };
    }, [autoConnect, connect, reset, instance]);

    const value: SurrealProviderState = useMemo(
        () => ({ client: instance, isConnecting: isPending, isSuccess, isError, error, connect, close }),
        [instance, isPending, isSuccess, isError, error, connect, close],
    );

    return <SurrealContext.Provider value={value}>{children}</SurrealContext.Provider>;
}

export function useSurreal() {
    const context = useContext(SurrealContext);
    if (!context) throw new Error("useSurreal must be used within a SurrealProvider");
    return context;
}

export function useSurrealClient() {
    return useSurreal().client;
}
```

##  Wrapping your application[](https://surrealdb.com/docs/reference/javascript/frameworks/react#wrapping-your-application)
In your top-level component, wrap the root with `QueryClientProvider` and `SurrealProvider`. Pass the endpoint and any [connection options](https://surrealdb.com/docs/reference/javascript/concepts/connecting-to-surrealdb#connection-options) through the `params` prop.

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SurrealProvider } from "./SurrealProvider";
import App from "./App";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
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
    </React.StrictMode>,
);
```

##  Executing queries[](https://surrealdb.com/docs/reference/javascript/frameworks/react#executing-queries)
Use the `useSurrealClient()` hook to access the `Surreal` instance from any component. All [query methods](https://surrealdb.com/docs/reference/javascript/concepts/executing-queries) are available on the client, including `.query()`, `.select()`, `.create()`, and more.

```tsx
import { useState, useEffect } from "react";
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
    const [users, setUsers] = useState<User[]>([]);

    useEffect(() => {
        client.select<User>(new Table("users"))
            .then(setUsers)
            .catch(console.error);
    }, [client]);

    if (isConnecting) return <p>Connecting...</p>;
    if (isError) return <p>Connection failed: {String(error)}</p>;

    return (
        <ul>
            {users.map((user) => (
                <li key={String(user.id)}>{user.name} ({user.email})</li>
            ))}
        </ul>
    );
}
```

##  Handling authentication[](https://surrealdb.com/docs/reference/javascript/frameworks/react#handling-authentication)
You can build an authentication layer on top of the provider using the SDK's [`.signin()`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-in-users) and [`.signup()`](https://surrealdb.com/docs/reference/javascript/concepts/authentication#signing-up-users) methods. The example below shows a minimal hook for record access authentication.

```tsx
import { useSurrealClient } from "./SurrealProvider";

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

##  Learn more[](https://surrealdb.com/docs/reference/javascript/frameworks/react#learn-more)
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
