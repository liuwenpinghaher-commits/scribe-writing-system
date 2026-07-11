---
title: "https://surrealdb.com/docs/explore/surrealist/advanced-topics/url-intents"
url: "https://surrealdb.com/docs/explore/surrealist/advanced-topics/url-intents"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/surrealist/advanced-topics/url-intents

Source: https://surrealdb.com/docs/explore/surrealist/advanced-topics/url-intents

Surrealist provides a low-level system for triggering actions within the interface through a URL. For example, you can use it to open specific dialogs, switch views, or even run queries.  
The intent system is used under the hood to power the command palette so most commands found there can be triggered via intents.
##  Usage[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/url-intents#usage)
Intents can be configured using the `intent` query argument. A simple example of an intent to open the connections dialog would look like this:

```
https://app.surrealdb.com/?intent=open-connections
```

A more advanced example of an intent can contain additional arguments. These are key-value pairs separated by `=` and are appended after the intent name suffixed by a colon `:`.  
This is an example of an intent to open the settings page and switch to the appearance tab:

```
https://app.surrealdb.com/?intent=open-settings:tab=appearance
```

You can also trigger intents for the Desktop App by using the Surrealist URI protocol. This will open a new Surrealist window  
if one is not already open. Here is an example of an intent to toggle database serving:

```
surrealist://?intent=toggle-serving
```

Additionally, certain intents are bound to a specific view. In this case Surrealist will automatically switch to the correct view when the intent is triggered.
##  List of intents[](https://surrealdb.com/docs/explore/surrealist/advanced-topics/url-intents#list-of-intents)
  

  
  
| Name  | View  | Description  |  
| --- | --- | --- |  
| `open-command-palette`  |   | Open the command palette dialog.  |  
| `open-connections`  |   | Open the connection list dialog.  |  
| `open-help`  |   | Open the help and support dialog.  |  
| `open-news`  |   | Opens the news drawer.  |  
| `open-changelog`  |   | Opens the changelog dialog.  |  
| `open-settings`  |   | Opens the settings dialog. You can specify a tab to open using the `tab` argument.  |  
| `open-embedder`  |   | Opens the embedder dialog.  |  
| `open-desktop-download`  |   | Opens the Surrealist Desktop download dialog. Only applicable to the web app.  |  
| `open-keymap`  |   | Opens the keymap dialog.  |  
| `new-connection`  |   | Opens the connection creator.  |  
| `new-table`  |   | Opens the table creator.  |  
| `toggle-serving`  |   | Toggles database serving. Only applicable to the desktop app.  |  
| `open-serving-console`  |   | Reveals the database serving console drawer. Only applicable to the desktop app.  |  
| `increase-window-scale`  |   | Increases the window zoom level. Only applicable to the desktop app.  |  
| `decrease-window-scale`  |   | Decreases the window zoom level. Only applicable to the desktop app.  |  
| `increase-editor-scale`  |   | Increases the font size of text editors.  |  
| `decrease-editor-scale`  |   | Decreases the font size of text editors.  |  
| `toggle-pinned`  |   | Toggle whether the window is always on top. Only applicable to the desktop app.  |  
| `highlight-tool`  |   | Opens a developer tool used to generate clipboard compatible SurrealQL highlighting  |  
| `new-query`  | Query  | Creates a new query tab.  |  
| `run-query`  | Query  | Executes the current query  |  
| `save-query`  | Query  | Open the query save dialog for the active query  |  
| `format-query`  | Query  | Formats the current query  |  
| `toggle-variables`  | Query  | Toggles the visibility of the variables panel  |  
| `infer-variables`  | Query  | Infer variables from the currently active query  |  
| `open-saved-queries`  | Query  | Opens the saved queries drawer  |  
| `open-query-history`  | Query  | Opens the query history drawer  |  
| `explore-table`  | Explorer  | Opens a table in the Explorer view. Requires a `table` argument with the table name.  |  
| `import-database`  | Explorer  | Opens the data importing dialog.  |  
| `export-database`  | Explorer  | Opens the data exporting dialog.  |  
| `design-table`  | Designer  | Opens a table in the Designer view. Requires a `table` argument with the table name.  |  
| `create-user`  | Authentication  | Opens the user creation dialog. Requires a `level` argument set to either ROOT, NAMESPACE, or DATABASE.  |  
| `create-scope`  | Authentication  | Opens the scope creation dialog.  |  
| `register-user`  | Authentication  | Opens the scope user registration dialog. Requires a `scope` argument with the scope name.  |  
| `docs-switch-language`  | API Docs  | Changes the language used for the code snippets. Requires a `lang` argument with a valid language code.  |
