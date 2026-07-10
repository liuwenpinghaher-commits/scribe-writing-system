---
title: "https://surrealdb.com/docs/reference/golang/concepts/live-queries"
url: "https://surrealdb.com/docs/reference/golang/concepts/live-queries"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/reference/golang/concepts/live-queries

Source: https://surrealdb.com/docs/reference/golang/concepts/live-queries

Live queries allow your application to receive real-time notifications whenever records in a table are created, updated, or deleted. The Go SDK delivers notifications through Go channels, making it easy to integrate with goroutines and concurrent patterns.
Live queries require a WebSocket connection (`ws://` or `wss://`). They are available on [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db) and [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session) but not on [`*Transaction`](https://surrealdb.com/docs/reference/golang/api/core/transaction).
##  API references[](https://surrealdb.com/docs/reference/golang/concepts/live-queries#api-references)  
| Function  | Description  |  
| --- | --- |  
| [`surrealdb.Live(ctx, s, table, diff)`](https://surrealdb.com/docs/reference/golang/api/core/db#live)  | Starts a live query on a table and returns its UUID  |  
| [`surrealdb.Kill(ctx, s, id)`](https://surrealdb.com/docs/reference/golang/api/core/db#kill)  | Stops a live query and closes its notification channel  |  
| [`db.LiveNotifications(id)`](https://surrealdb.com/docs/reference/golang/api/core/db#livenotifications)  | Returns the notification channel for a live query  |  
| [`db.CloseLiveNotifications(id)`](https://surrealdb.com/docs/reference/golang/api/core/db#closelivenotifications)  | Closes the notification channel without killing the server-side query  |  
##  Starting a live query[](https://surrealdb.com/docs/reference/golang/concepts/live-queries#starting-a-live-query)
Use the [`Live`](https://surrealdb.com/docs/reference/golang/api/core/db#live) function to subscribe to changes on a table. It returns a [`UUID`](https://surrealdb.com/docs/reference/golang/api/values/uuid) that identifies the live query.

```go
liveID, err := surrealdb.Live(ctx, db, models.Table("persons"), false)
if err != nil {
	log.Fatal(err)
}
```

The `diff` parameter controls notification format. When `false`, notifications contain the full record. When `true`, they contain JSON Patch diffs instead.
##  Receiving notifications[](https://surrealdb.com/docs/reference/golang/concepts/live-queries#receiving-notifications)
After starting a live query, call [`.LiveNotifications()`](https://surrealdb.com/docs/reference/golang/api/core/db#livenotifications) on the [`*DB`](https://surrealdb.com/docs/reference/golang/api/core/db) or [`*Session`](https://surrealdb.com/docs/reference/golang/api/core/session) to get a channel that receives [`Notification`](https://surrealdb.com/docs/reference/golang/api/types#notification) values.

```go
ch, err := db.LiveNotifications(liveID.String())
if err != nil {
	log.Fatal(err)
}

for notification := range ch {
	fmt.Printf("Action: %s, Result: %v\n", notification.Action, notification.Result)
}
```

Each notification includes:  
| Field  | Type  | Description  |  
| --- | --- | --- |  
| `ID`  | `*models.UUID`  | The live query UUID  |  
| `Action`  | `Action`  | One of `CREATE`, `UPDATE`, or `DELETE`  |  
| `Result`  | `interface{}`  | The record data or JSON Patch diff  |  
##  Processing notifications in a goroutine[](https://surrealdb.com/docs/reference/golang/concepts/live-queries#processing-notifications-in-a-goroutine)
A common pattern is to process live query notifications in a separate goroutine while the main goroutine continues other work.

```go
liveID, err := surrealdb.Live(ctx, db, models.Table("persons"), false)
if err != nil {
	log.Fatal(err)
}

ch, err := db.LiveNotifications(liveID.String())
if err != nil {
	log.Fatal(err)
}

go func() {
	for n := range ch {
		switch n.Action {
		case "CREATE":
			fmt.Println("New record:", n.Result)
		case "UPDATE":
			fmt.Println("Updated record:", n.Result)
		case "DELETE":
			fmt.Println("Deleted record:", n.Result)
		}
	}
}()
```

##  Stopping a live query[](https://surrealdb.com/docs/reference/golang/concepts/live-queries#stopping-a-live-query)
Use the [`Kill`](https://surrealdb.com/docs/reference/golang/api/core/db#kill) function to terminate a live query on the server and close its notification channel.

```go
if err := surrealdb.Kill(ctx, db, liveID.String()); err != nil {
	log.Fatal(err)
}
```

[`Kill`](https://surrealdb.com/docs/reference/golang/api/core/db#kill) both sends the kill RPC to the server and closes the local notification channel. If you only want to close the channel without killing the server-side query, use [`.CloseLiveNotifications()`](https://surrealdb.com/docs/reference/golang/api/core/db#closelivenotifications) instead.
##  Learn more[](https://surrealdb.com/docs/reference/golang/concepts/live-queries#learn-more)
  * •
[DB API reference](https://surrealdb.com/docs/reference/golang/api/core/db) for complete function signatures and parameters
  * •
[Connecting to SurrealDB](https://surrealdb.com/docs/reference/golang/concepts/connecting-to-surrealdb) for WebSocket connection requirements
  * •
[Multiple sessions](https://surrealdb.com/docs/reference/golang/concepts/multiple-sessions) for session-scoped live queries
  * •
[Reliable connections](https://surrealdb.com/docs/reference/golang/concepts/reliable-connections) for live queries that persist across reconnections
  * •
[SurrealQL LIVE statement](https://surrealdb.com/docs/reference/query-language/statements/live-select) for the underlying query language syntax
