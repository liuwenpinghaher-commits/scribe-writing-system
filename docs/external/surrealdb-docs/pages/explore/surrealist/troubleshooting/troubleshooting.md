---
title: "https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting"
url: "https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting

Source: https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting

If you experience issues or unintended behaviour when using Surrealist, please [open an issue](https://github.com/surrealdb/surrealist/issues/new/choose) on our GitHub repository.
If you are still running into issues you can attempt one of the following:
###  Opening the developer console[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#opening-the-developer-console)
The developer console may include hints to the cause of your problem. Include any errors you find inside with reported GitHub issues as it may significantly help the maintainers understand your problem.
You can open the developer tools panel using the following key combination
  * •
**Windows / Linux:** `Ctrl + Shift + i`
  * •
**macOS:** `Command + Option + i`

Once the developer tools are open, navigate to the console tab to view any errors or warnings. These may help you diagnose any issues.
###  Backing up / resetting the configuration file[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#backing-up--resetting-the-configuration-file)
Removing your configuration file may solve issues, however you will lose configured connections and other settings. It is recommended to backup the config file before deleting it.
The config file can be found at the following location
  * •
**Linux:** `$HOME/.config/SurrealDB/Surrealist/config.json`
  * •
**macOS:** `$HOME/Library/Application Support/SurrealDB/Surrealist/config.json`
  * •
**Windows:** `%AppData%\SurrealDB\Surrealist\config.json`

Note
Avoid sharing your config or uploading it to public locations as it contains the authentication details to your configured connections.
###  Viewing the logs[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#viewing-the-logs)
Surrealist outputs logfiles that may contain hints to the cause of the issue. You can find the logs at the following locations:
  * •
**Linux:** `$HOME/.config/SurrealDB/Surrealist/logs`
  * •
**macOS:** `$HOME/Library/Application Support/SurrealDB/Surrealist/logs`
  * •
**Windows:** `%AppData%\SurrealDB\Surrealist\logs`

Note
Logfiles should not contain any sensitive information, however please review them carefully before sharing them with others.
##  Connection issues[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#connection-issues)
Since Surrealist operates over a network connection it is possible to run into unexpected issues while attempting to connect to, or query, a database. While there are many reasons why a connection might fail, here are some common issues and their solutions:
###  Unsupported protocols[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#unsupported-protocols)
Some protocols might not always be supported by the network configuration. For example, some networks might block the WebSocket protocol. In this case, you can switch to the HTTP or HTTPS protocol to bypass the restriction.
###  SSL[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#ssl)
You might be connecting to an endpoint using the HTTPS or WSS protocol without a valid SSL certificate present on the server. In this case, you can switch to the HTTP or WS protocol to bypass the SSL verification.  
It is recommended to perform HTTP or WS connections through the desktop app, as web browsers might block these connections due to security reasons.
###  Firewall issues[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#firewall-issues)
Firewalls might block Surrealist from connecting to the internet. Make sure that Surrealist is allowed to connect to the internet by checking your firewall settings.
###  Browser restrictions[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#browser-restrictions)
Using the Web App you might find yourself restricted by browsers or browser extensions. Make sure to disable any browser extensions that might interfere with Surrealist, or switch to the desktop app.
###  Troubleshooting connection issues[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#troubleshooting-connection-issues)
Connection issues can be notoriously difficult to troubleshoot. Here are some steps you can take to diagnose the issue:
  * •
**Connect using the CLI** : Since Surrealist always runs in a secure environment, localhost or LAN connections may be blocked by a variety of reasons. Try connecting to the database using the [CLI](https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview) to see if the issue persists, as this is not subject to the same restrictions.
  * •
**Check the logs** : The Surrealist logfiles may contain hints to the cause of the issue. Check the logs for any errors or warnings that might help you diagnose the issue.
  * •
**Check the developer console** : You can open the developer console to reveal hidden errors or warnings that might help you diagnose the issue.
  * •
**Check the network tab** : The network tab in the developer console may contain information on the network requests that Surrealist is making. Check for any failed requests or errors that might help you diagnose the issue.

##  Known issues[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#known-issues)
###  Interface loading[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#interface-loading)
On certain platforms (particularly Linux with Nvidia GPUs or Wayland compositors), the desktop app may open to a blank white screen. This is caused by webview compatibility. Workarounds include updating your graphics drivers, trying the `--disable-gpu` flag, or using the web app instead.
###  Query formatting[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#query-formatting)
Formatting a query strips out comments and white space. This happens because the query is parsed by SurrealDB and pretty-printed; since the parser does not retain comments, these are lost. As a workaround, select only the portion of the query you want to format before pressing the format button.
##  Submitting feedback[](https://surrealdb.com/docs/explore/surrealist/troubleshooting/troubleshooting#submitting-feedback)
You are always welcome to share feedback and ask questions about Surrealist in the #surrealist channel in our [Discord](https://discord.gg/surrealdb) server.
If you have found a bug or would like to request a feature, please open an issue on our [GitHub repository](https://github.com/surrealdb/surrealist).
If you have any other questions or feedback, feel free to leave some feedback using the feedback button on the right-hand side of the screen.
