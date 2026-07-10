---
title: "Huggingface Hub"
url: "https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub

# Huggingface Hub
HuggingFace hf CLI: search/download/upload models, datasets.
## Skill metadata[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#skill-metadata "Direct link to Skill metadata")  
|   |   |  
| --- | --- |  
| Source  | Bundled (installed by default)  |  
| Path  | `skills/mlops/huggingface-hub`  |  
| Version  | `1.0.0`  |  
| Author  | Hugging Face  |  
| License  | MIT  |  
| Platforms  | linux, macos, windows  |  
## Reference: full SKILL.md[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#reference-full-skillmd "Direct link to Reference: full SKILL.md")
info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
# Hugging Face CLI (`hf`) Reference Guide
The `hf` command is the modern command-line interface for interacting with the Hugging Face Hub, providing tools to manage repositories, models, datasets, and Spaces.
> **IMPORTANT:** The `hf` command replaces the now deprecated `huggingface-cli` command.
## Quick Start[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#quick-start "Direct link to Quick Start")
  * **Installation:** `curl -LsSf https://hf.co/cli/install.sh | bash -s`
  * **Help:** Use `hf --help` to view all available functions and real-world examples.
  * **Authentication:** Recommended via `HF_TOKEN` environment variable or the `--token` flag.

* * *
## Core Commands[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#core-commands "Direct link to Core Commands")
### General Operations[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#general-operations "Direct link to General Operations")
  * `hf download REPO_ID`: Download files from the Hub.
  * `hf upload REPO_ID`: Upload files/folders (recommended for single-commit).
  * `hf upload-large-folder REPO_ID LOCAL_PATH`: Recommended for resumable uploads of large directories.
  * `hf sync`: Sync files between a local directory and a bucket.
  * `hf env` / `hf version`: View environment and version details.

### Authentication (`hf auth`)[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#authentication-hf-auth "Direct link to authentication-hf-auth")
  * `login` / `logout`: Manage sessions using tokens from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
  * `list` / `switch`: Manage and toggle between multiple stored access tokens.
  * `whoami`: Identify the currently logged-in account.

### Repository Management (`hf repos`)[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#repository-management-hf-repos "Direct link to repository-management-hf-repos")
  * `create` / `delete`: Create or permanently remove repositories.
  * `duplicate`: Clone a model, dataset, or Space to a new ID.
  * `move`: Transfer a repository between namespaces.
  * `branch` / `tag`: Manage Git-like references.
  * `delete-files`: Remove specific files using patterns.

* * *
## Specialized Hub Interactions[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#specialized-hub-interactions "Direct link to Specialized Hub Interactions")
### Datasets & Models[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#datasets--models "Direct link to Datasets & Models")
  * **Datasets:** `hf datasets list`, `info`, and `parquet` (list parquet URLs).
  * **SQL Queries:** `hf datasets sql SQL` — Execute raw SQL via DuckDB against dataset parquet URLs.
  * **Models:** `hf models list` and `info`.
  * **Papers:** `hf papers list` — View daily papers.

### Discussions & Pull Requests (`hf discussions`)[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#discussions--pull-requests-hf-discussions "Direct link to discussions--pull-requests-hf-discussions")
  * Manage the lifecycle of Hub contributions: `list`, `create`, `info`, `comment`, `close`, `reopen`, and `rename`.
  * `diff`: View changes in a PR.
  * `merge`: Finalize pull requests.

### Infrastructure & Compute[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#infrastructure--compute "Direct link to Infrastructure & Compute")
  * **Endpoints:** Deploy and manage Inference Endpoints (`deploy`, `pause`, `resume`, `scale-to-zero`, `catalog`).
  * **Jobs:** Run compute tasks on HF infrastructure. Includes `hf jobs uv` for running Python scripts with inline dependencies and `stats` for resource monitoring.
  * **Spaces:** Manage interactive apps. Includes `dev-mode` and `hot-reload` for Python files without full restarts.

### Storage & Automation[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#storage--automation "Direct link to Storage & Automation")
  * **Buckets:** Full S3-like bucket management (`create`, `cp`, `mv`, `rm`, `sync`).
  * **Cache:** Manage local storage with `list`, `prune` (remove detached revisions), and `verify` (checksum checks).
  * **Webhooks:** Automate workflows by managing Hub webhooks (`create`, `watch`, `enable`/`disable`).
  * **Collections:** Organize Hub items into collections (`add-item`, `update`, `list`).

* * *
## Advanced Usage & Tips[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#advanced-usage--tips "Direct link to Advanced Usage & Tips")
### Global Flags[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#global-flags "Direct link to Global Flags")
  * `--format json`: Produces machine-readable output for automation.
  * `-q` / `--quiet`: Limits output to IDs only.

### Extensions & Skills[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/mlops/mlops-huggingface-hub#extensions--skills "Direct link to Extensions & Skills")
  * **Extensions:** Extend CLI functionality via GitHub repositories using `hf extensions install REPO_ID`.
  * **Skills:** Manage AI assistant skills with `hf skills add`.
