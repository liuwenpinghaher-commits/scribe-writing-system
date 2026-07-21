# Slack Setup
Connect Hermes Agent to Slack as a bot using Socket Mode. Socket Mode uses WebSockets instead of public HTTP endpoints, so your Hermes instance doesn't need to be publicly accessible — it works behind firewalls, on your laptop, or on a private server.
Classic Slack Apps Deprecated
Classic Slack apps (using RTM API) were **fully deprecated in March 2025**. Hermes uses the modern Bolt SDK with Socket Mode. If you have an old classic app, you must create a new one following the steps below.
## Overview[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#overview "Direct link to Overview")  
| Component  | Value  |  
| --- | --- |  
| **Library**  |  `slack-bolt` / `slack_sdk` for Python (Socket Mode)  |  
| **Connection**  | WebSocket — no public URL required  |  
| **Auth tokens needed**  | Bot Token (`xoxb-`) + App-Level Token (`xapp-`)  |  
| **User identification**  | Slack Member IDs (e.g., `U01ABC2DEF3`)  |  
* * *
## Step 1: Create a Slack App[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-1-create-a-slack-app "Direct link to Step 1: Create a Slack App")
The fastest path is to paste a manifest Hermes generates for you. It declares every built-in slash command (`/btw`, `/stop`, `/model`, …), every required OAuth scope, every event subscription, and enables Socket Mode — all at once.
### Option A: From a Hermes-generated manifest (recommended)[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#option-a-from-a-hermes-generated-manifest-recommended "Direct link to Option A: From a Hermes-generated manifest \(recommended\)")
  1. Generate the manifest. New Slack apps must use Agent view:

```
hermes slack manifest --agent-view --write  

```

This writes `~/.hermes/slack-manifest.json` and prints paste-in instructions. Existing apps that still use Slack's legacy Assistant view can omit `--agent-view` until they are ready to migrate.
  2. Go to <https://api.slack.com/apps> → **Create New App** → **From an app manifest**
  3. Pick your workspace, paste the JSON contents, review, click **Next** → **Create**
  4. Skip ahead to **Step 6: Install App to Workspace**. The manifest handled scopes, events, and slash commands for you.

### Option B: From scratch (manual)[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#option-b-from-scratch-manual "Direct link to Option B: From scratch \(manual\)")
  1. Go to <https://api.slack.com/apps>
  2. Click **Create New App**
  3. Choose **From scratch**
  4. Enter an app name (e.g., "Hermes Agent") and select your workspace
  5. Click **Create App**

You'll land on the app's **Basic Information** page. Continue with Steps 2–6 below.
* * *
## Step 2: Configure Bot Token Scopes[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-2-configure-bot-token-scopes "Direct link to Step 2: Configure Bot Token Scopes")
Navigate to **Features → OAuth & Permissions** in the sidebar. Scroll to **Scopes → Bot Token Scopes** and add the following:  
| Scope  | Purpose  |  
| --- | --- |  
| `chat:write`  | Send messages as the bot  |  
| `app_mentions:read`  | Detect when @mentioned in channels  |  
| `channels:history`  | Read messages in public channels the bot is in  |  
| `channels:read`  | List and get info about public channels  |  
| `groups:history`  | Read messages in private channels the bot is invited to  |  
| `im:history`  | Read direct message history  |  
| `im:read`  | View basic DM info  |  
| `im:write`  | Open and manage DMs  |  
| `mpim:history`  | Read group direct message (multi-person DM) history  |  
| `mpim:read`  | View basic group DM info  |  
| `users:read`  | Look up user information  |  
| `files:read`  | Read and download attached files, including voice notes/audio  |  
| `files:write`  | Upload files (images, audio, documents)  |  
Missing scopes = missing features
Without `channels:history` and `groups:history`, the bot **will not receive messages in channels** — it will only work in DMs. Without `files:read`, Hermes can chat but **cannot reliably read user-uploaded attachments**. These are the most commonly missed scopes.
**Optional scopes:**  
| Scope  | Purpose  |  
| --- | --- |  
| `groups:read`  | List and get info about private channels  |  
| `assistant:write`  | Render the working-state status line ("is thinking…") next to the bot name while it processes a message. Without this scope the `assistant.threads.setStatus` call fails silently and Slack shows its own rotating generic placeholders instead ("Finding answers…", "Reviewing findings…", …) — Hermes never controls the text. Required for `typing_status_text` to have any visible effect.  |  
* * *
## Step 3: Enable Socket Mode[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-3-enable-socket-mode "Direct link to Step 3: Enable Socket Mode")
Socket Mode lets the bot connect via WebSocket instead of requiring a public URL.
  1. In the sidebar, go to **Settings → Socket Mode**
  2. Toggle **Enable Socket Mode** to ON
  3. You'll be prompted to create an **App-Level Token** :
     * Name it something like `hermes-socket` (the name doesn't matter)
     * Add the **`connections:write`**scope
     * Click **Generate**
  4. **Copy the token** — it starts with `xapp-`. This is your `SLACK_APP_TOKEN`

tip
You can always find or regenerate app-level tokens under **Settings → Basic Information → App-Level Tokens**.
* * *
## Step 4: Subscribe to Events[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-4-subscribe-to-events "Direct link to Step 4: Subscribe to Events")
This step is critical — it controls what messages the bot can see.
  1. In the sidebar, go to **Features → Event Subscriptions**
  2. Toggle **Enable Events** to ON
  3. Expand **Subscribe to bot events** and add:

  
| Event  | Required?  | Purpose  |  
| --- | --- | --- |  
| `message.im`  | **Yes**  | Bot receives direct messages  |  
| `message.mpim`  | **Yes**  | Bot receives messages in **group DMs** (multi-person DMs) it's added to  |  
| `message.channels`  | **Yes**  | Bot receives messages in **public** channels it's added to  |  
| `message.groups`  | **Recommended**  | Bot receives messages in **private** channels it's invited to  |  
| `app_mention`  | **Yes**  | Prevents Bolt SDK errors when bot is @mentioned  |  
  4. Click **Save Changes** at the bottom of the page

Missing event subscriptions is the #1 setup issue
If the bot works in DMs but **not in channels** , you almost certainly forgot to add `message.channels` (for public channels) and/or `message.groups` (for private channels). Without these events, Slack simply never delivers channel messages to the bot.
* * *
## Step 5: Enable the Messages Tab[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-5-enable-the-messages-tab "Direct link to Step 5: Enable the Messages Tab")
This step enables direct messages to the bot. Without it, users see **"Sending messages to this app has been turned off"** when trying to DM the bot.
  1. In the sidebar, go to **Features → App Home**
  2. Scroll to **Show Tabs**
  3. Toggle **Messages Tab** to ON
  4. Check **"Allow users to send Slash commands and messages from the messages tab"**

Without this step, DMs are completely blocked
Even with all the correct scopes and event subscriptions, Slack will not allow users to send direct messages to the bot unless the Messages Tab is enabled. This is a Slack platform requirement, not a Hermes configuration issue.
* * *
## Step 6: Install App to Workspace[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-6-install-app-to-workspace "Direct link to Step 6: Install App to Workspace")
  1. In the sidebar, go to **Settings → Install App**
  2. Click **Install to Workspace**
  3. Review the permissions and click **Allow**
  4. After authorization, you'll see a **Bot User OAuth Token** starting with `xoxb-`
  5. **Copy this token** — this is your `SLACK_BOT_TOKEN`

tip
If you change scopes or event subscriptions later, you **must reinstall the app** for the changes to take effect. The Install App page will show a banner prompting you to do so.
* * *
## Step 7: Find User IDs for the Allowlist[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-7-find-user-ids-for-the-allowlist "Direct link to Step 7: Find User IDs for the Allowlist")
Hermes uses Slack **Member IDs** (not usernames or display names) for the allowlist.
To find a Member ID:
  1. In Slack, click on the user's name or avatar
  2. Click **View full profile**
  3. Click the **⋮** (more) button
  4. Select **Copy member ID**

Member IDs look like `U01ABC2DEF3`. You need your own Member ID at minimum.
* * *
## Step 8: Configure Hermes[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-8-configure-hermes "Direct link to Step 8: Configure Hermes")
Add the following to your `~/.hermes/.env` file:

```
# Required  
SLACK_BOT_TOKEN=xoxb-your-bot-token-here  
SLACK_APP_TOKEN=xapp-your-app-token-here  
SLACK_ALLOWED_USERS=U01ABC2DEF3              # Comma-separated Member IDs  
  
# Optional  
SLACK_HOME_CHANNEL=C01234567890              # Default channel for cron/scheduled messages  
SLACK_HOME_CHANNEL_NAME=general              # Human-readable name for the home channel (optional)  

```

Or run the interactive setup:

```
hermes gateway setup    # Select Slack when prompted  

```

Then start the gateway:

```
hermes gateway              # Foreground  
hermes gateway install      # Install as a user service  
sudo hermes gateway install --system   # Linux only: boot-time system service  

```

Codex reasoning-effort safety
For Codex-backed Slack peer-agent channels, prefer `agent.reasoning_effort: high` or lower. `xhigh` can spend the entire turn in hidden reasoning and never produce visible assistant text; Hermes now suppresses those incomplete-turn warnings from the thread and keeps the diagnostics in gateway logs.
* * *
## Step 9: Invite the Bot to Channels[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#step-9-invite-the-bot-to-channels "Direct link to Step 9: Invite the Bot to Channels")
After starting the gateway, you need to **invite the bot** to any channel where you want it to respond:

```
/invite @Hermes Agent  

```

The bot will **not** automatically join channels. You must invite it to each channel individually.
* * *
## Slash Commands[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#slash-commands "Direct link to Slash Commands")
Every Hermes command (`/btw`, `/stop`, `/new`, `/model`, `/help`, ...) is a native Slack slash command — exactly the way they work on Telegram and Discord. Type `/` in Slack and the autocomplete picker lists every Hermes command with its description.
Under the hood: Hermes ships with a generated Slack app manifest (see Step 1, Option A) that declares every command in [`COMMAND_REGISTRY`](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/commands.py) as a slash command. In Socket Mode, Slack routes the command event through the WebSocket regardless of the manifest's `url` field.
### Agent messaging experience[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#agent-messaging-experience "Direct link to Agent messaging experience")
New Slack apps use Slack's **Agent** messaging experience. Existing Hermes Assistant apps can migrate by regenerating the manifest with `--agent-view`:

```
hermes slack manifest --agent-view --write  

```

Update the manifest in **Features → App Manifest** , then reinstall the app if Slack asks. Agent view cannot be reverted to Assistant view, and users may need to hard-refresh Slack after the switch. The generated Agent manifest subscribes to `message.im`, `app_home_opened`, and `app_context_changed`, so Hermes can identify a Messages-tab DM and receive the user's active Slack context with a turn. Hermes only supplies that context as a label; it does not read the viewed channel's history.
### Refreshing slash commands after updates[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#refreshing-slash-commands-after-updates "Direct link to Refreshing slash commands after updates")
When Hermes adds new commands (e.g. after `hermes update`), regenerate the manifest and update your Slack app:

```
hermes slack manifest --write  

```

Then in Slack:
  1. Open <https://api.slack.com/apps> → your Hermes app
  2. **Features → App Manifest → Edit**
  3. Paste the new contents of `~/.hermes/slack-manifest.json`
  4. **Save**. Slack will prompt to reinstall the app if scopes or slash commands changed.

### Legacy `/hermes <subcommand>` still works[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#legacy-hermes-subcommand-still-works "Direct link to legacy-hermes-subcommand-still-works")
For backward compatibility with older manifests, you can still type `/hermes btw run the tests` — Hermes routes it the same way as `/btw run the tests`. Free-form questions also work: `/hermes what's the weather?` is treated as a regular message.
### Using commands inside threads (the `!cmd` prefix)[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#using-commands-inside-threads-the-cmd-prefix "Direct link to using-commands-inside-threads-the-cmd-prefix")
Slack itself blocks native slash commands inside thread replies — try `/queue` in a thread and Slack responds with _"/queue is not supported in threads. Sorry!"_ There is no app-side setting that re-enables them; Slack never delivers them to Hermes.
As a workaround, Hermes recognises a leading `!` as an alternate command prefix that works in threads (and anywhere else). Type `!queue`, `!stop`, `!model gpt-5.4`, etc. as a regular thread reply — Hermes treats it identically to the slash form and replies in the same thread.
Only the first token is checked against the known command list, so casual messages like `!nice work` pass through to the agent unchanged.
Approval prompts (dangerous command / `execute_code` approval) normally render as interactive buttons. When buttons can't be delivered and Hermes falls back to a text prompt, the prompt instructs you to reply with `!approve` / `!deny` — the form that works inside threads.
### Advanced: emit only the slash-commands array[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#advanced-emit-only-the-slash-commands-array "Direct link to Advanced: emit only the slash-commands array")
If you maintain your Slack manifest by hand and just want the slash command list:

```
hermes slack manifest --slashes-only > /tmp/slashes.json  

```

Paste that array into the `features.slash_commands` key of your existing manifest.
* * *
## How the Bot Responds[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#how-the-bot-responds "Direct link to How the Bot Responds")
Understanding how Hermes behaves in different contexts:  
| Context  | Behavior  |  
| --- | --- |  
| **DMs**  | Bot responds to every message — no @mention needed  |  
| **Channels**  | Bot **only responds when @mentioned** (e.g., `@Hermes Agent what time is it?`). In channels, Hermes replies in a thread attached to that message.  |  
| **Threads**  | If you @mention Hermes inside an existing thread, it replies in that same thread. Once the bot has an active session in a thread, **subsequent replies in that thread do not require @mention** — the bot follows the conversation naturally.  |  
tip
In channels, always @mention the bot to start a conversation. Once the bot is active in a thread, you can reply in that thread without mentioning it. Outside of threads, messages without @mention are ignored to prevent noise in busy channels.
* * *
## Configuration Options[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#configuration-options "Direct link to Configuration Options")
Beyond the required environment variables from Step 8, you can customize Slack bot behavior through `~/.hermes/config.yaml`.
### Thread & Reply Behavior[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#thread--reply-behavior "Direct link to Thread & Reply Behavior")

```
platforms:  
  slack:  
    # Controls how multi-part responses are threaded  
    # "off"   — never thread replies to the original message  
    # "first" — first chunk threads to user's message (default)  
    # "all"   — all chunks thread to user's message  
    reply_to_mode: "first"  
  
    extra:  
      # Whether to reply in a thread (default: true).  
      # When false, channel messages get direct channel replies instead  
      # of threads. Messages inside existing threads still reply in-thread.  
      reply_in_thread: true  
  
      # Also post thread replies to the main channel  
      # (Slack's "Also send to channel" feature).  
      # Only the first chunk of the first reply is broadcast.  
      reply_broadcast: false  
  
      # Render agent messages as Slack Block Kit blocks (default: false).  
      # When true, the final agent message is sent with structured blocks —  
      # section headers, dividers, true nested lists (via rich_text), and  
      # native Block Kit tables — instead of flat mrkdwn text. A plain-text  
      # fallback is always sent alongside for notifications/accessibility.  
      # Tables exceeding Slack's limits (100 rows / 20 cols / 10k chars)  
      # gracefully fall back to aligned monospace.  
      rich_blocks: false  
  
      # Append Slack-native feedback controls to final Block Kit replies.  
      # Requires rich_blocks: true. Default: false.  
      feedback_buttons: false  
  
      # Suggested prompts pinned at the top of Agent view's Messages tab.  
      # Either a list of {title, message} rows, or a titled object:  
      # {title: "Start here", prompts: [{title: "Plan", message: "..."}]}  
      suggested_prompts: []  
  
      # Title Agent/Assistant DM threads from the first user message.  
      # Default: true. Set false to leave Slack's default thread titles.  
      assistant_thread_titles: true  
  
      # Continuable-cron delivery surface (default: "thread").  
      # "in_channel" delivers a continuable cron job FLAT into the channel  
      # (no dedicated thread); pair with reply_in_thread: false (and  
      # require_mention: false) so a plain reply continues the job.  
      # See the cron guide → "Flat, in-channel continuation".  
      cron_continuable_surface: thread  

```
  
| Key  | Default  | Description  |  
| --- | --- | --- |  
| `platforms.slack.reply_to_mode`  | `"first"`  | Threading mode for multi-part messages: `"off"`, `"first"`, or `"all"`  |  
| `platforms.slack.extra.reply_in_thread`  | `true`  | When `false`, channel messages get direct replies instead of threads. Messages inside existing threads still reply in-thread.  |  
| `platforms.slack.extra.reply_broadcast`  | `false`  | When `true`, thread replies are also posted to the main channel. Only the first chunk is broadcast.  |  
| `platforms.slack.extra.rich_blocks`  | `false`  | When `true`, agent messages are rendered as [Block Kit](https://docs.slack.dev/block-kit/) blocks (headers, dividers, true nested lists, and native tables). A plain-text fallback is always sent. Tables over Slack's limits fall back to aligned monospace. No app reinstall required — it's a send-side change only.  |  
| `platforms.slack.extra.feedback_buttons`  | `false`  | When `true` with `rich_blocks`, appends Slack-native feedback controls to final replies.  |  
| `platforms.slack.extra.suggested_prompts`  | `[]`  | Up to four `{title, message}` prompts for Agent/Assistant DM entry points; accepts either a list or `{title, prompts}`.  |  
| `platforms.slack.extra.assistant_thread_titles`  | `true`  | When `true`, names Agent/Assistant DM threads from the first user message.  |  
| `platforms.slack.extra.cron_continuable_surface`  | `"thread"`  | Delivery surface for [continuable cron jobs](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron#flat-in-channel-continuation-slack). `"thread"` opens a dedicated thread per delivery (default); `"in_channel"` delivers flat into the channel timeline. Pair `in_channel` with `reply_in_thread: false` (and `require_mention: false`) so a plain channel reply continues the job.  |  
### Working-State Status Line[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#working-state-status-line "Direct link to Working-State Status Line")
While the agent processes a message, Slack shows a status line next to the bot name in the thread. By default Hermes sets it to `is thinking...`; customize it with `typing_status_text` — e.g. a kitten assistant named Ada:

```
platforms:  
  slack:  
    # Custom working-state status line (default: "is thinking...").  
    typing_status_text: "is pouncing… 🐾"  

```
  
| Key  | Default  | Description  |  
| --- | --- | --- |  
| `platforms.slack.typing_status_text`  | `"is thinking..."`  | Text of the working-state status line shown while the agent processes a message. Requires the `assistant:write` scope — without it the status call fails silently and Slack renders its own generic placeholder, whatever this is set to. Set `typing_indicator: false` to disable the status line entirely.  |  
Where the status renders
The custom status appears in the **footer beneath the reply composer** ("_BotName_ is thinking…"), not inline in the message list. The inline "Generating response…" / "Finding answers…" lines Slack shows in the message area while an AI app works are **Slack's own rotating indicators** — `assistant.threads.setStatus` does not control those, and both can appear at the same time.
The same key customizes Google Chat's visible working-state marker message (`platforms.google_chat.typing_status_text`, default `"Hermes is thinking…"`) — note that on Google Chat it is a real posted message that gets patched into the reply, not an ephemeral status.
### Live Status (per-tool)[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#live-status-per-tool "Direct link to Live Status \(per-tool\)")
By default the status line updates **live as the agent works** : instead of a static `is thinking...`, it shows what the agent is doing right now — `is running pytest tests/…`, `is reading docs/api.md…`, `is searching the web for slack api limits…`. Between tool calls it reverts to the static text. This rides the existing status-refresh cadence, so it makes no additional Slack API calls, and it works even with `tool_progress: off` (Slack's default) — unlike progress bubbles, the status line is ephemeral and leaves nothing behind in the channel.
Control it with `display.live_status` (global or per-platform):

```
display:  
  platforms:  
    slack:  
      # full = verb + argument ("is running pytest…")   [default]  
      # verb = verb only ("is running…") — hides commands/paths,  
      #        useful in shared or customer-facing channels  
      # off  = static text (typing_status_text or "is thinking...")  
      live_status: full  

```
  
| Key  | Default  | Description  |  
| --- | --- | --- |  
| `display.live_status`  | `"full"`  | Live per-tool status line. `full` shows verb + argument preview; `verb` shows the verb only (keeps file paths and commands out of shared channels); `off` restores the static text. Requires the `assistant:write` scope, same as the static status line.  |  
### Session Isolation[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#session-isolation "Direct link to Session Isolation")

```
# Global setting — applies to Slack and all other platforms  
group_sessions_per_user: true  

```

When `true` (the default), each user in a shared channel gets their own isolated conversation session. Two people talking to Hermes in `#general` will have separate histories and contexts.
Set to `false` if you want a collaborative mode where the entire channel shares one conversation session. Be aware this means users share context growth and token costs, and one user's `/reset` clears the session for everyone.
### Mention & Trigger Behavior[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#mention--trigger-behavior "Direct link to Mention & Trigger Behavior")

```
slack:  
  # Require @mention in channels (this is the default behavior;  
  # the Slack adapter enforces @mention gating in channels regardless,  
  # but you can set this explicitly for consistency with other platforms)  
  require_mention: true  
  
  # Prevent thread auto-engagement: only reply to channel messages that  
  # contain an explicit @mention. With this OFF (default), Slack can  
  # "auto-engage" — remembering past mentions in a thread and following  
  # up on bot-message replies, and resuming active sessions without a  
  # fresh mention. With strict_mention ON, every new channel message  
  # must @mention the bot before Hermes will respond.  
  strict_mention: false  
  
  # Custom mention patterns that trigger the bot  
  # (in addition to the default @mention detection)  
  mention_patterns:  
    - "hey hermes"  
    - "hermes,"  
  
  # Text prepended to every outgoing message  
  reply_prefix: ""  

```

When to use `strict_mention`
Set this to `true` in busy workspaces where Slack's default "the bot remembers this thread" behavior surprises users — for example, a long tech-support thread where the bot helped at the start and you'd rather it stay silent unless explicitly pinged again. DMs and active interactive sessions are unaffected.
info
Slack supports both patterns: `@mention` required to start a conversation by default, but you can opt specific channels out via `SLACK_FREE_RESPONSE_CHANNELS` (comma-separated channel IDs) or `slack.free_response_channels` in `config.yaml`. Once the bot has an active session in a thread, subsequent thread replies do not require a mention. In **1:1 DMs** the bot always responds without needing a mention.
Group DMs (MPIMs) are shared surfaces, not 1:1 DMs
A **1:1 direct message** is a private conversation with one person, so it is mention-exempt. A **group DM (MPIM / multi-person DM)** is a _shared surface_ — multiple people can see and trigger the bot — so it obeys the same operator controls as a channel: `require_mention`, `strict_mention`, `free_response_channels`, and `allowed_channels` all apply, and the bot only adds `:eyes:`/`:white_check_mark:` reactions when it is actually `@mentioned`. To let the bot respond freely in a specific group DM, add its channel ID (starts with `G`) to `free_response_channels`.
### Channel allowlist (`allowed_channels`)[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#channel-allowlist-allowed_channels "Direct link to channel-allowlist-allowed_channels")
Restrict the bot to a fixed set of Slack channels — useful when the bot is invited to many channels but should only respond in a few. When set, messages from channels NOT in this list are **silently ignored** , even if the bot is `@mentioned`.
**1:1 DMs are exempt** from this filter, so authorized users can always reach the bot in a direct message. **Group DMs (MPIMs) are not exempt** — like channels, an MPIM must be on the allowlist (its ID starts with `G`) or its messages are dropped.

```
slack:  
  allowed_channels:  
    - "C0123456789"   # #ops  
    - "C0987654321"   # #incident-response  

```

Or via env var (comma-separated):

```
SLACK_ALLOWED_CHANNELS="C0123456789,C0987654321"  

```

Behavior:
  * Empty / unset → no restriction (fully backward compatible).
  * Non-empty → channel ID must be on the list, or the message is dropped before any other gating (mention requirement, `free_response_channels`, etc.) runs.
  * Slack channel IDs start with `C` (public), `G` (private), or `D` (DM). Look them up via the Slack UI's "Open channel details" → "About" panel, or via the API.

See also: [admin/user slash command split](https://hermes-agent.nousresearch.com/docs/reference/slash-commands#permissions-and-adminuser-split).
### Unauthorized User Handling[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#unauthorized-user-handling "Direct link to Unauthorized User Handling")

```
slack:  
  # What happens when an unauthorized user (not in SLACK_ALLOWED_USERS) DMs the bot  
  # "pair"   — prompt them for a pairing code (default)  
  # "ignore" — silently drop the message  
  unauthorized_dm_behavior: "pair"  

```

You can also set this globally for all platforms:

```
unauthorized_dm_behavior: "pair"  

```

The platform-specific setting under `slack:` takes precedence over the global setting.
### Voice Transcription[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#voice-transcription "Direct link to Voice Transcription")

```
# Global setting — enable/disable automatic transcription of incoming voice messages  
stt_enabled: true  

```

When `true` (the default), incoming audio messages are automatically transcribed using the configured STT provider before being processed by the agent.
### Full Example[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#full-example "Direct link to Full Example")

```
# Global gateway settings  
group_sessions_per_user: true  
unauthorized_dm_behavior: "pair"  
stt_enabled: true  
  
# Slack-specific settings  
slack:  
  require_mention: true  
  unauthorized_dm_behavior: "pair"  
  
# Platform config  
platforms:  
  slack:  
    reply_to_mode: "first"  
    extra:  
      reply_in_thread: true  
      reply_broadcast: false  

```

* * *
## Home Channel[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#home-channel "Direct link to Home Channel")
Set `SLACK_HOME_CHANNEL` to a channel ID where Hermes will deliver scheduled messages, cron job results, and other proactive notifications. To find a channel ID:
  1. Right-click the channel name in Slack
  2. Click **View channel details**
  3. Scroll to the bottom — the Channel ID is shown there

```
SLACK_HOME_CHANNEL=C01234567890  

```

Make sure the bot has been **invited to the channel** (`/invite @Hermes Agent`).
* * *
## Multi-Workspace Support[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#multi-workspace-support "Direct link to Multi-Workspace Support")
Hermes can connect to **multiple Slack workspaces** simultaneously using a single gateway instance. Each workspace is authenticated independently with its own bot user ID.
### Configuration[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#configuration "Direct link to Configuration")
Provide multiple bot tokens as a **comma-separated list** in `SLACK_BOT_TOKEN`:

```
# Multiple bot tokens — one per workspace  
SLACK_BOT_TOKEN=xoxb-workspace1-token,xoxb-workspace2-token,xoxb-workspace3-token  
  
# A single app-level token is still used for Socket Mode  
SLACK_APP_TOKEN=xapp-your-app-token  

```

Or in `~/.hermes/config.yaml`:

```
platforms:  
  slack:  
    token: "xoxb-workspace1-token,xoxb-workspace2-token"  

```

### OAuth Token File[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#oauth-token-file "Direct link to OAuth Token File")
In addition to tokens in the environment or config, Hermes also loads tokens from an **OAuth token file** at:

```
~/.hermes/slack_tokens.json  

```

This file is a JSON object mapping team IDs to token entries:

```
{  
  "T01ABC2DEF3": {  
    "token": "xoxb-workspace-token-here",  
    "team_name": "My Workspace"  
  }  
}  

```

Tokens from this file are merged with any tokens specified via `SLACK_BOT_TOKEN`. Duplicate tokens are automatically deduplicated.
### How it works[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#how-it-works "Direct link to How it works")
  * The **first token** in the list is the primary token, used for the Socket Mode connection (AsyncApp).
  * Each token is authenticated via `auth.test` on startup. The gateway maps each `team_id` to its own `WebClient` and `bot_user_id`.
  * When a message arrives, Hermes uses the correct workspace-specific client to respond.
  * The primary `bot_user_id` (from the first token) is used for backward compatibility with features that expect a single bot identity.

* * *
## Voice Messages[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#voice-messages "Direct link to Voice Messages")
Hermes supports voice on Slack:
  * **Incoming:** Voice/audio messages are automatically transcribed using the configured STT provider: local `faster-whisper`, Groq Whisper (`GROQ_API_KEY`), or OpenAI Whisper (`VOICE_TOOLS_OPENAI_KEY`)
  * **Outgoing:** TTS responses are sent as audio file attachments

* * *
## Per-Channel Prompts[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#per-channel-prompts "Direct link to Per-Channel Prompts")
Assign ephemeral system prompts to specific Slack channels. The prompt is injected at runtime on every turn — never persisted to transcript history — so changes take effect immediately.

```
slack:  
  channel_prompts:  
    "C01RESEARCH": |  
      You are a research assistant. Focus on academic sources,  
      citations, and concise synthesis.  
    "C02ENGINEERING": |  
      Code review mode. Be precise about edge cases and  
      performance implications.  

```

Keys are Slack channel IDs (find them via channel details → "About" → scroll to bottom). All messages in the matching channel get the prompt injected as an ephemeral system instruction.
## Per-Channel Skill Bindings[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#per-channel-skill-bindings "Direct link to Per-Channel Skill Bindings")
Auto-load a skill whenever a new session starts in a specific channel or DM. Unlike per-channel prompts (which are injected on every turn), skill bindings inject the skill content as a user message at **session start** — it becomes part of the conversation history and does not need to be reloaded on subsequent turns.
This is ideal for DMs or channels with a dedicated purpose (flashcards, a domain-specific Q&A bot, a support triage channel, etc.) where you don't want the model's own skill selector to decide whether to load on every short reply.

```
slack:  
  channel_skill_bindings:  
    # DM channel — always runs in "german-flashcards" mode  
    - id: "D0ATH9TQ0G6"  
      skills:  
        - german-flashcards  
    # Research channel — preload multiple skills in order  
    - id: "C01RESEARCH"  
      skills:  
        - arxiv  
        - writing-plans  
    # Short form: single skill as a string  
    - id: "C02SUPPORT"  
      skill: hubspot-on-demand  

```

Notes:
  * The binding matches by channel ID. For threaded messages in a bound channel, the thread inherits the parent channel's binding.
  * The skill is loaded only at session start (new session or after auto-reset). If you change the binding, run `/new` or wait for the session to auto-reset for it to take effect.
  * Combine with `channel_prompts` for per-channel tone/constraints on top of the skill's instructions.

## Troubleshooting[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#troubleshooting "Direct link to Troubleshooting")  
| Problem  | Solution  |  
| --- | --- |  
| Bot doesn't respond to DMs  | Verify `message.im` is in your event subscriptions and the app is reinstalled  |  
| Bot works in DMs but not in channels  |  **Most common issue.** Add `message.channels` and `message.groups` to event subscriptions, reinstall the app, and invite the bot to the channel with `/invite @Hermes Agent`  |  
| Bot doesn't respond to @mentions in channels  | 1) Check `message.channels` event is subscribed. 2) Bot must be invited to the channel. 3) Ensure `channels:history` scope is added. 4) Reinstall the app after scope/event changes  |  
| Bot ignores messages in private channels  | Add both the `message.groups` event subscription and `groups:history` scope, then reinstall the app and `/invite` the bot  |  
| Bot doesn't respond in group DMs (multi-person DMs)  | Add the `message.mpim` event subscription and the `mpim:history` scope (plus `mpim:read`), then **reinstall** the app. Without `message.mpim`, Slack never delivers group-DM messages to the bot — even though 1:1 DMs work.  |  
| "Sending messages to this app has been turned off" in DMs  | Enable the **Messages Tab** in App Home settings (see Step 5)  |  
| "not_authed" or "invalid_auth" errors  | Regenerate your Bot Token and App Token, update `.env`  |  
| Bot responds but can't post in a channel  | Invite the bot to the channel with `/invite @Hermes Agent`  |  
| Bot can chat but can't read uploaded images/files  | Add `files:read`, then **reinstall** the app. Hermes now surfaces attachment access diagnostics in-chat when Slack returns scope/auth/permission failures.  |  
|  `missing_scope` error  | Add the required scope in OAuth & Permissions, then **reinstall** the app  |  
| Socket disconnects frequently  | Check your network; Bolt auto-reconnects but unstable connections cause lag  |  
| Changed scopes/events but nothing changed  | You **must reinstall** the app to your workspace after any scope or event subscription change  |  
### Quick Checklist[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#quick-checklist "Direct link to Quick Checklist")
If the bot isn't working in channels, verify **all** of the following:
  1. ✅ `message.channels` event is subscribed (for public channels)
  2. ✅ `message.groups` event is subscribed (for private channels)
  3. ✅ `app_mention` event is subscribed
  4. ✅ `channels:history` scope is added (for public channels)
  5. ✅ `groups:history` scope is added (for private channels)
  6. ✅ App was **reinstalled** after adding scopes/events
  7. ✅ Bot was **invited** to the channel (`/invite @Hermes Agent`)
  8. ✅ You are **@mentioning** the bot in your message

* * *
## Security[​](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack#security "Direct link to Security")
warning
**Always set`SLACK_ALLOWED_USERS`** with the Member IDs of authorized users. Without this setting, the gateway will **deny all messages** by default as a safety measure. Never share your bot tokens — treat them like passwords.
  * Tokens should be stored in `~/.hermes/.env` (file permissions `600`)
  * Rotate tokens periodically via the Slack app settings
  * Audit who has access to your Hermes config directory
  * Socket Mode means no public endpoint is exposed — one less attack surface
