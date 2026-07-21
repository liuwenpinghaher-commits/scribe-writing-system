# BlueBubbles (iMessage)
Connect Hermes to Apple iMessage via [BlueBubbles](https://bluebubbles.app/) — a free, open-source macOS server that bridges iMessage to any device.
## Prerequisites[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#prerequisites "Direct link to Prerequisites")
  * A **Mac** (always on) running [BlueBubbles Server](https://bluebubbles.app/)
  * Apple ID signed into Messages.app on that Mac
  * BlueBubbles Server v1.0.0+ (webhooks require this version)
  * Network connectivity between Hermes and the BlueBubbles server

## Setup[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#setup "Direct link to Setup")
### 1. Install BlueBubbles Server[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#1-install-bluebubbles-server "Direct link to 1. Install BlueBubbles Server")
Download and install from [bluebubbles.app](https://bluebubbles.app/). Complete the setup wizard — sign in with your Apple ID and configure a connection method (local network, Ngrok, Cloudflare, or Dynamic DNS).
### 2. Get your Server URL and Password[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#2-get-your-server-url-and-password "Direct link to 2. Get your Server URL and Password")
In BlueBubbles Server → **Settings → API** , note:
  * **Server URL** (e.g., `http://192.168.1.10:1234`)
  * **Server Password**

### 3. Configure Hermes[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#3-configure-hermes "Direct link to 3. Configure Hermes")
Run the setup wizard:

```
hermes gateway setup  

```

Select **BlueBubbles (iMessage)** and enter your server URL and password.
Or set environment variables directly in `~/.hermes/.env`:

```
BLUEBUBBLES_SERVER_URL=http://192.168.1.10:1234  
BLUEBUBBLES_PASSWORD=your-server-password  

```

#### Optional: Require mentions in group chats[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#optional-require-mentions-in-group-chats "Direct link to Optional: Require mentions in group chats")
By default, Hermes responds to every authorized BlueBubbles/iMessage DM or group message. To make group chats opt-in, enable mention gating:

```
platforms:  
  bluebubbles:  
    enabled: true  
    extra:  
      require_mention: true  

```

With `require_mention: true`, DMs still work normally, but group-chat messages are ignored unless they match a mention pattern. If you do not configure custom patterns, Hermes uses conservative defaults for `Hermes` and `@Hermes agent` variants.
For a custom agent name, set regex patterns:

```
platforms:  
  bluebubbles:  
    extra:  
      require_mention: true  
      mention_patterns:  
        - '(?<![\w@])@?amos\b[,:\-]?'  

```

### 4. Authorize Users[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#4-authorize-users "Direct link to 4. Authorize Users")
Choose one approach:
**DM Pairing (recommended):** When someone messages your iMessage, Hermes automatically sends them a pairing code. Approve it with:

```
hermes pairing approve bluebubbles <CODE>  

```

Use `hermes pairing list` to see pending codes and approved users.
**Pre-authorize specific users** (in `~/.hermes/.env`):

```
BLUEBUBBLES_ALLOWED_USERS=user@icloud.com,+15551234567  

```

**Open access** (in `~/.hermes/.env`):

```
BLUEBUBBLES_ALLOW_ALL_USERS=true  

```

### 5. Start the Gateway[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#5-start-the-gateway "Direct link to 5. Start the Gateway")

```
hermes gateway run  

```

Hermes will connect to your BlueBubbles server, register a webhook, and start listening for iMessage messages.
## How It Works[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#how-it-works "Direct link to How It Works")

```
iMessage → Messages.app → BlueBubbles Server → Webhook → Hermes  
Hermes → BlueBubbles REST API → Messages.app → iMessage  

```

  * **Inbound:** BlueBubbles sends webhook events to a local listener when new messages arrive. No polling — instant delivery.
  * **Outbound:** Hermes sends messages via the BlueBubbles REST API.
  * **Media:** Images, voice messages, videos, and documents are supported in both directions. Inbound attachments are downloaded and cached locally for the agent to process.

## Environment Variables[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#environment-variables "Direct link to Environment Variables")  
| Variable  | Required  | Default  | Description  |  
| --- | --- | --- | --- |  
| `BLUEBUBBLES_SERVER_URL`  | Yes  | —  | BlueBubbles server URL  |  
| `BLUEBUBBLES_PASSWORD`  | Yes  | —  | Server password  |  
| `BLUEBUBBLES_WEBHOOK_HOST`  | No  | `127.0.0.1`  | Webhook listener bind address  |  
| `BLUEBUBBLES_WEBHOOK_PORT`  | No  | `8645`  | Webhook listener port  |  
| `BLUEBUBBLES_WEBHOOK_PATH`  | No  | `/bluebubbles-webhook`  | Webhook URL path  |  
| `BLUEBUBBLES_HOME_CHANNEL`  | No  | —  | Phone/email for cron delivery  |  
| `BLUEBUBBLES_ALLOWED_USERS`  | No  | —  | Comma-separated authorized users  |  
| `BLUEBUBBLES_ALLOW_ALL_USERS`  | No  | `false`  | Allow all users  |  
| `BLUEBUBBLES_REQUIRE_MENTION`  | No  | `false`  | Require a mention pattern before responding in group chats  |  
| `BLUEBUBBLES_MENTION_PATTERNS`  | No  | Hermes wake words  | JSON array, newline-separated, or comma-separated regex patterns for group mention matching  |  
Auto-marking messages as read is controlled by the `send_read_receipts` key under `platforms.bluebubbles.extra` in `~/.hermes/config.yaml` (default: `true`). There is no corresponding environment variable.
## Features[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#features "Direct link to Features")
### Text Messaging[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#text-messaging "Direct link to Text Messaging")
Send and receive iMessages. Markdown is automatically stripped for clean plain-text delivery.
### Rich Media[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#rich-media "Direct link to Rich Media")
  * **Images:** Photos appear natively in the iMessage conversation
  * **Voice messages:** Audio files sent as iMessage voice messages
  * **Videos:** Video attachments
  * **Documents:** Files sent as iMessage attachments

### Tapback Reactions[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#tapback-reactions "Direct link to Tapback Reactions")
Love, like, dislike, laugh, emphasize, and question reactions. Requires the BlueBubbles [Private API helper](https://docs.bluebubbles.app/helper-bundle/installation).
### Typing Indicators[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#typing-indicators "Direct link to Typing Indicators")
Shows "typing..." in the iMessage conversation while the agent is processing. Requires Private API.
### Read Receipts[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#read-receipts "Direct link to Read Receipts")
Automatically marks messages as read after processing. Requires Private API.
### Chat Addressing[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#chat-addressing "Direct link to Chat Addressing")
You can address chats by email or phone number — Hermes resolves them to BlueBubbles chat GUIDs automatically. No need to use raw GUID format.
## Private API[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#private-api "Direct link to Private API")
Some features require the BlueBubbles [Private API helper](https://docs.bluebubbles.app/helper-bundle/installation):
  * Tapback reactions
  * Typing indicators
  * Read receipts
  * Creating new chats by address

Without the Private API, basic text messaging and media still work.
## Troubleshooting[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#troubleshooting "Direct link to Troubleshooting")
### "Cannot reach server"[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#cannot-reach-server "Direct link to "Cannot reach server"")
  * Verify the server URL is correct and the Mac is on
  * Check that BlueBubbles Server is running
  * Ensure network connectivity (firewall, port forwarding)

### Messages not arriving[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#messages-not-arriving "Direct link to Messages not arriving")
  * Check that the webhook is registered in BlueBubbles Server → Settings → API → Webhooks
  * Verify the webhook URL is reachable from the Mac
  * Check `hermes logs gateway` for webhook errors (or `hermes logs -f` to follow in real-time)

### "Private API helper not connected"[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/bluebubbles#private-api-helper-not-connected "Direct link to "Private API helper not connected"")
  * Install the Private API helper: [docs.bluebubbles.app](https://docs.bluebubbles.app/helper-bundle/installation)
  * Basic messaging works without it — only reactions, typing, and read receipts require it
