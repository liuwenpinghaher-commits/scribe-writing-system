---
title: "Learning Path"
url: "https://hermes-agent.nousresearch.com/docs/getting-started/learning-path"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/getting-started/learning-path

# Learning Path
Hermes Agent can do a lot — CLI assistant, Telegram/Discord bot, task automation, RL training, and more. This page helps you figure out where to start and what to read based on your experience level and what you're trying to accomplish.
Start Here
If you haven't installed Hermes Agent yet, begin with the [Installation guide](https://hermes-agent.nousresearch.com/docs/getting-started/installation) and then run through the [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart). Everything below assumes you have a working installation.
First-time provider setup
First-time users almost always want `hermes setup --portal` — one OAuth covers a model plus the four Tool Gateway tools (search/image/TTS/browser). See [Nous Portal](https://hermes-agent.nousresearch.com/docs/integrations/nous-portal).
## How to Use This Page[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#how-to-use-this-page "Direct link to How to Use This Page")
  * **Know your level?** Jump to the [experience-level table](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#by-experience-level) and follow the reading order for your tier.
  * **Have a specific goal?** Skip to [By Use Case](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#by-use-case) and find the scenario that matches.
  * **Just browsing?** Check the [Key Features](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#key-features-at-a-glance) table for a quick overview of everything Hermes Agent can do.

## By Experience Level[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#by-experience-level "Direct link to By Experience Level")  
| Level  | Goal  | Recommended Reading  | Time Estimate  |  
| --- | --- | --- | --- |  
| **Beginner**  | Get up and running, have basic conversations, use built-in tools  |  [Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation) → [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) → [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli) → [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)  | ~1 hour  |  
| **Intermediate**  | Set up messaging bots, use advanced features like memory, cron jobs, and skills  |  [Sessions](https://hermes-agent.nousresearch.com/docs/user-guide/sessions) → [Messaging](https://hermes-agent.nousresearch.com/docs/user-guide/messaging) → [Tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools) → [Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) → [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) → [Cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)  | ~2–3 hours  |  
| **Advanced**  | Build custom tools, create skills, train models with RL, contribute to the project  |  [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture) → [Adding Tools](https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools) → [Creating Skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills) → [Contributing](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)  | ~4–6 hours  |  
## By Use Case[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#by-use-case "Direct link to By Use Case")
Pick the scenario that matches what you want to do. Each one links you to the relevant docs in the order you should read them.
### "I want a CLI coding assistant"[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#i-want-a-cli-coding-assistant "Direct link to "I want a CLI coding assistant"")
Use Hermes Agent as an interactive terminal assistant for writing, reviewing, and running code.
  1. [Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
  2. [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
  3. [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli)
  4. [Code Execution](https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution)
  5. [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)
  6. [Tips & Tricks](https://hermes-agent.nousresearch.com/docs/guides/tips)

tip
Pass files directly into your conversation with context files. Hermes Agent can read, edit, and run code in your projects.
### "I want a Telegram/Discord bot"[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#i-want-a-telegramdiscord-bot "Direct link to "I want a Telegram/Discord bot"")
Deploy Hermes Agent as a bot on your favorite messaging platform.
  1. [Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
  2. [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
  3. [Messaging Overview](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)
  4. [Telegram Setup](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)
  5. [Discord Setup](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord)
  6. [Voice Mode](https://hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode)
  7. [Use Voice Mode with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes)
  8. [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)

For full project examples, see:
  * [Daily Briefing Bot](https://hermes-agent.nousresearch.com/docs/guides/daily-briefing-bot)
  * [Team Telegram Assistant](https://hermes-agent.nousresearch.com/docs/guides/team-telegram-assistant)

### "I want to automate tasks"[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#i-want-to-automate-tasks "Direct link to "I want to automate tasks"")
Schedule recurring tasks, run batch jobs, or chain agent actions together.
  1. [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
  2. [Cron Scheduling](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
  3. [Batch Processing](https://hermes-agent.nousresearch.com/docs/user-guide/features/batch-processing)
  4. [Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation)
  5. [Hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks)

tip
Cron jobs let Hermes Agent run tasks on a schedule — daily summaries, periodic checks, automated reports — without you being present.
### "I want to build custom tools/skills"[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#i-want-to-build-custom-toolsskills "Direct link to "I want to build custom tools/skills"")
Extend Hermes Agent with your own tools and reusable skill packages.
  1. [Plugins](https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins)
  2. [Build a Hermes Plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
  3. [Tools Overview](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)
  4. [Skills Overview](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
  5. [MCP (Model Context Protocol)](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
  6. [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
  7. [Adding Tools](https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools)
  8. [Creating Skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills)

tip
For most custom tool creation, start with plugins. The [Adding Tools](https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools) page is for built-in Hermes core development, not the usual user/custom-tool path.
### "I want to train models"[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#i-want-to-train-models "Direct link to "I want to train models"")
Use reinforcement learning to fine-tune model behavior with Hermes Agent's RL training pipeline (powered by [Atropos](https://github.com/NousResearch/atropos)).
  1. [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
  2. [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
  3. [Atropos RL Environments](https://github.com/NousResearch/atropos) (external)
  4. [Provider Routing](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing)
  5. [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)

tip
RL training works best when you already understand the basics of how Hermes Agent handles conversations and tool calls. Run through the Beginner path first if you're new.
### "I want to use it as a Python library"[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#i-want-to-use-it-as-a-python-library "Direct link to "I want to use it as a Python library"")
Integrate Hermes Agent into your own Python applications programmatically.
  1. [Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
  2. [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
  3. [Python Library Guide](https://hermes-agent.nousresearch.com/docs/guides/python-library)
  4. [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
  5. [Tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)
  6. [Sessions](https://hermes-agent.nousresearch.com/docs/user-guide/sessions)

## Key Features at a Glance[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#key-features-at-a-glance "Direct link to Key Features at a Glance")
Not sure what's available? Here's a quick directory of major features:  
| Feature  | What It Does  | Link  |  
| --- | --- | --- |  
| **Tools**  | Built-in tools the agent can call (file I/O, search, shell, etc.)  | [Tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)  |  
| **Skills**  | Installable plugin packages that add new capabilities  | [Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)  |  
| **Memory**  | Persistent memory across sessions  | [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)  |  
| **Context Files**  | Feed files and directories into conversations  | [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)  |  
| **MCP**  | Connect to external tool servers via Model Context Protocol  | [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)  |  
| **Cron**  | Schedule recurring agent tasks  | [Cron](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)  |  
| **Delegation**  | Spawn sub-agents for parallel work  | [Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation)  |  
| **Code Execution**  | Run Python scripts that call Hermes tools programmatically  | [Code Execution](https://hermes-agent.nousresearch.com/docs/user-guide/features/code-execution)  |  
| **Browser**  | Web browsing and scraping  | [Browser](https://hermes-agent.nousresearch.com/docs/user-guide/features/browser)  |  
| **Hooks**  | Event-driven callbacks and middleware  | [Hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks)  |  
| **Batch Processing**  | Process multiple inputs in bulk  | [Batch Processing](https://hermes-agent.nousresearch.com/docs/user-guide/features/batch-processing)  |  
| **Provider Routing**  | Route requests across multiple LLM providers  | [Provider Routing](https://hermes-agent.nousresearch.com/docs/user-guide/features/provider-routing)  |  
## What to Read Next[​](https://hermes-agent.nousresearch.com/docs/getting-started/learning-path#what-to-read-next "Direct link to What to Read Next")
Based on where you are right now:
  * **Just finished installing?** → Head to the [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart) to run your first conversation.
  * **Completed the Quickstart?** → Read [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli) and [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) to customize your setup.
  * **Comfortable with the basics?** → Explore [Tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools), [Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), and [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) to unlock the full power of the agent.
  * **Setting up for a team?** → Read [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security) and [Sessions](https://hermes-agent.nousresearch.com/docs/user-guide/sessions) to understand access control and conversation management.
  * **Ready to build?** → Jump into the [Developer Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture) to understand the internals and start contributing.
  * **Want practical examples?** → Check out the [Guides](https://hermes-agent.nousresearch.com/docs/guides/tips) section for real-world projects and tips.

tip
You don't need to read everything. Pick the path that matches your goal, follow the links in order, and you'll be productive quickly. You can always come back to this page to find your next step.
