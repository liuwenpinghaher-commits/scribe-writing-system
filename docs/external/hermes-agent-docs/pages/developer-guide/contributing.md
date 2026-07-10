---
title: "Contributing"
url: "https://hermes-agent.nousresearch.com/docs/developer-guide/contributing"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/developer-guide/contributing

# Contributing
Thank you for contributing to Hermes Agent! This guide covers setting up your dev environment, understanding the codebase, and getting your PR merged.
## Contribution Priorities[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#contribution-priorities "Direct link to Contribution Priorities")
We value contributions in this order:
  1. **Bug fixes** — crashes, incorrect behavior, data loss
  2. **Cross-platform compatibility** — macOS, different Linux distros, WSL2
  3. **Security hardening** — shell injection, prompt injection, path traversal
  4. **Performance and robustness** — retry logic, error handling, graceful degradation
  5. **New skills** — broadly useful ones (see [Creating Skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills))
  6. **New tools** — rarely needed; most capabilities should be skills
  7. **Documentation** — fixes, clarifications, new examples

## Common contribution paths[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#common-contribution-paths "Direct link to Common contribution paths")
  * Building a custom/local tool without modifying Hermes core? Start with [Build a Hermes Plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
  * Building a new built-in core tool for Hermes itself? Start with [Adding Tools](https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools)
  * Building a new skill? Start with [Creating Skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills)
  * Building a new inference provider? Start with [Adding Providers](https://hermes-agent.nousresearch.com/docs/developer-guide/adding-providers)

## Development Setup[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#development-setup "Direct link to Development Setup")
### Prerequisites[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#prerequisites "Direct link to Prerequisites")  
| Requirement  | Notes  |  
| --- | --- |  
| **Git**  | With the `git-lfs` extension installed  |  
| **Python 3.11–3.13**  | uv will install it if missing  |  
| **uv**  | Fast Python package manager ([install](https://docs.astral.sh/uv/))  |  
| **Node.js 20+**  | Optional — needed for browser tools and WhatsApp bridge (matches root `package.json` engines)  |  
### Install with the standard installer[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#install-with-the-standard-installer "Direct link to Install with the standard installer")
For most contributors, the best development bootstrap is the same path users take: run the standard installer, then work inside the repository it cloned. The installer creates the Hermes venv, wires the `hermes` command, stamps the install method for `hermes update`, and clones the full git project into `$HERMES_HOME/hermes-agent` (usually `~/.hermes/hermes-agent`). That keeps your development environment on the same layout the CLI, updater, lazy dependency installer, gateway, and docs assume.

```
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash  
cd "${HERMES_HOME:-$HOME/.hermes}/hermes-agent"  
  
# Add dev/test extras on top of the standard install.  
uv pip install -e ".[all,dev]"  
  
# Optional: browser tools / docs site dependencies.  
npm install  

```

After that, create branches and run tests from that checkout:

```
git checkout -b fix/description  
scripts/run_tests.sh  

```

### Manual clone fallback[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#manual-clone-fallback "Direct link to Manual clone fallback")
Use this only if you intentionally do not want Hermes' managed install layout (for example, a throwaway clone inside a container or CI job). If you install this way, make sure you run the `hermes` entrypoint from this venv; running the system `python3 -m hermes_cli.main` can pick up unrelated system Python packages.
Create the venv **outside** the cloned source tree. A venv that lives inside the directory the agent operates from can be wiped by a relative-path command the agent runs against its own checkout (`rm -rf venv`, `uv venv venv`, etc.), which silently destroys the running runtime mid-session. Keeping it outside the tree means no relative path from the workspace resolves to it.

```
git clone https://github.com/NousResearch/hermes-agent.git  
cd hermes-agent  
  
# Create venv with Python 3.11, OUTSIDE the source tree  
uv venv ~/.hermes/venvs/hermes-dev --python 3.11  
export VIRTUAL_ENV="$HOME/.hermes/venvs/hermes-dev"  
export PATH="$VIRTUAL_ENV/bin:$PATH"  
  
# Install with all extras (messaging, cron, CLI menus, dev tools)  
uv pip install -e ".[all,dev]"  
  
# Optional: browser tools  
npm install  

```

### Configure for Development[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#configure-for-development "Direct link to Configure for Development")

```
mkdir -p ~/.hermes/{cron,sessions,logs,memories,skills}  
cp cli-config.yaml.example ~/.hermes/config.yaml  
touch ~/.hermes/.env  
  
# Add at minimum an LLM provider key:  
echo 'OPENROUTER_API_KEY=sk-or-v1-your-key' >> ~/.hermes/.env  

```

### Run[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#run "Direct link to Run")

```
# The standard installer already put `hermes` on PATH.  
hermes doctor  
hermes chat -q "Hello"  

```

If you used the manual clone fallback, run `./hermes` from the checkout or symlink this clone's venv explicitly:

```
mkdir -p ~/.local/bin  
ln -sf "$(pwd)/venv/bin/hermes" ~/.local/bin/hermes  

```

### Run Tests[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#run-tests "Direct link to Run Tests")

```
scripts/run_tests.sh  

```

## Code Style[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#code-style "Direct link to Code Style")
  * **PEP 8** with practical exceptions (no strict line length enforcement)
  * **Comments** : Only when explaining non-obvious intent, trade-offs, or API quirks
  * **Error handling** : Catch specific exceptions. Use `logger.warning()`/`logger.error()` with `exc_info=True` for unexpected errors
  * **Cross-platform** : Never assume Unix (see below)
  * **Profile-safe paths** : Never hardcode `~/.hermes` — use `get_hermes_home()` from `hermes_constants` for code paths and `display_hermes_home()` for user-facing messages. See [AGENTS.md](https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md#profiles-multi-instance-support) for full rules.

## Cross-Platform Compatibility[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#cross-platform-compatibility "Direct link to Cross-Platform Compatibility")
See **[Platform Support](https://hermes-agent.nousresearch.com/docs/getting-started/platform-support)**. Native Windows uses Git Bash (from [Git for Windows](https://git-scm.com/download/win)) for shell commands. A few features require POSIX kernel primitives and are gated: the dashboard's embedded PTY terminal pane (`/chat` tab) needs a POSIX PTY (Linux, macOS, or WSL2). If you're doing Windows-heavy dev, run the Windows-footgun lint (`scripts/check-windows-footguns.py`) before pushing.
When contributing code, keep these rules in mind:
  * **Don't add unguarded`signal.SIGKILL` references.** It's not defined on Windows. Either route through `gateway.status.terminate_pid(pid, force=True)` (the centralized primitive that does `taskkill /T /F` on Windows and SIGKILL on POSIX), or fall back with `getattr(signal, "SIGKILL", signal.SIGTERM)`.
  * **Catch`OSError` alongside `ProcessLookupError` on `os.kill(pid, 0)` probes.** Windows raises `OSError` (WinError 87, "parameter is incorrect") for an already-gone PID instead of `ProcessLookupError`.
  * **Don't force the terminal to POSIX semantics.** `os.setsid`, `os.killpg`, `os.getpgid`, `os.fork` all raise on Windows — gate them with `if sys.platform != "win32":` or `if os.name != "nt":`.
  * **Open files with an explicit`encoding="utf-8"`.** The Python default on Windows is the system locale (often cp1252), which mojibakes or crashes on non-Latin text.
  * **Use`pathlib.Path` / `os.path.join` — never manually concat with `/`.** This matters less for strings the OS gives us back and more for strings we construct to hand to subprocesses.

Key patterns:
### 1. `termios` and `fcntl` are Unix-only[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#1-termios-and-fcntl-are-unix-only "Direct link to 1-termios-and-fcntl-are-unix-only")
Always catch both `ImportError` and `NotImplementedError`:

```
try:  
    from simple_term_menu import TerminalMenu  
    menu = TerminalMenu(options)  
    idx = menu.show()  
except (ImportError, NotImplementedError):  
    # Fallback: numbered menu  
    for i, opt in enumerate(options):  
        print(f"  {i+1}. {opt}")  
    idx = int(input("Choice: ")) - 1  

```

### 2. File encoding[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#2-file-encoding "Direct link to 2. File encoding")
Some environments may save `.env` files in non-UTF-8 encodings:

```
try:  
    load_dotenv(env_path)  
except UnicodeDecodeError:  
    load_dotenv(env_path, encoding="latin-1")  

```

### 3. Process management[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#3-process-management "Direct link to 3. Process management")
`os.setsid()`, `os.killpg()`, and signal handling differ across platforms:

```
import platform  
if platform.system() != "Windows":  
    kwargs["preexec_fn"] = os.setsid  

```

### 4. Path separators[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#4-path-separators "Direct link to 4. Path separators")
Use `pathlib.Path` instead of string concatenation with `/`.
## Security Considerations[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#security-considerations "Direct link to Security Considerations")
Hermes has terminal access. Security matters.
### Existing Protections[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#existing-protections "Direct link to Existing Protections")  
| Layer  | Implementation  |  
| --- | --- |  
| **Sudo password piping**  | Uses `shlex.quote()` to prevent shell injection  |  
| **Dangerous command detection**  | Regex patterns in `tools/approval.py` with user approval flow  |  
| **Cron prompt injection**  | Scanner blocks instruction-override patterns  |  
| **Write deny list**  | Protected paths resolved via `os.path.realpath()` to prevent symlink bypass  |  
| **Skills guard**  | Security scanner for hub-installed skills  |  
| **Code execution sandbox**  | Child process runs with API keys stripped  |  
| **Container hardening**  | Docker: all capabilities dropped, no privilege escalation, PID limits  |  
### Contributing Security-Sensitive Code[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#contributing-security-sensitive-code "Direct link to Contributing Security-Sensitive Code")
  * Always use `shlex.quote()` when interpolating user input into shell commands
  * Resolve symlinks with `os.path.realpath()` before access control checks
  * Don't log secrets
  * Catch broad exceptions around tool execution
  * Test on all platforms if your change touches file paths or processes

## Pull Request Process[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#pull-request-process "Direct link to Pull Request Process")
### Branch Naming[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#branch-naming "Direct link to Branch Naming")

```
fix/description        # Bug fixes  
feat/description       # New features  
docs/description       # Documentation  
test/description       # Tests  
refactor/description   # Code restructuring  

```

### Before Submitting[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#before-submitting "Direct link to Before Submitting")
  1. **Run tests** : `scripts/run_tests.sh` for CI-parity. Use direct `python -m pytest ...` only when the wrapper is unavailable or you are intentionally debugging outside the wrapper.
  2. **Test manually** : Run `hermes` and exercise the code path you changed
  3. **Check cross-platform impact** : Consider macOS, Linux, WSL2, and native Windows. If you touch file I/O, process management, terminal handling, subprocesses, or signals, run `scripts/check-windows-footguns.py`.
  4. **Keep PRs focused** : One logical change per PR

### PR Description[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#pr-description "Direct link to PR Description")
Include:
  * **What** changed and **why**
  * **How to test** it
  * **What platforms** you tested on
  * Reference any related issues

### Commit Messages[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#commit-messages "Direct link to Commit Messages")
We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>  

```
  
| Type  | Use for  |  
| --- | --- |  
| `fix`  | Bug fixes  |  
| `feat`  | New features  |  
| `docs`  | Documentation  |  
| `test`  | Tests  |  
| `refactor`  | Code restructuring  |  
| `chore`  | Build, CI, dependency updates  |  
Scopes: `cli`, `gateway`, `tools`, `skills`, `agent`, `install`, `whatsapp`, `security`
Examples:

```
fix(cli): prevent crash in save_config_value when model is a string  
feat(gateway): add WhatsApp multi-user session isolation  
fix(security): prevent shell injection in sudo password piping  

```

## Reporting Issues[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#reporting-issues "Direct link to Reporting Issues")
  * Use [GitHub Issues](https://github.com/NousResearch/hermes-agent/issues)
  * Include: OS, Python version, Hermes version (`hermes version`), full error traceback
  * Include steps to reproduce
  * Check existing issues before creating duplicates
  * For security vulnerabilities, please report privately

## Community[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#community "Direct link to Community")
  * **Discord** : [discord.gg/NousResearch](https://discord.gg/NousResearch)
  * **GitHub Discussions** : For design proposals and architecture discussions
  * **Skills Hub** : Upload specialized skills and share with the community

## License[​](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing#license "Direct link to License")
By contributing, you agree that your contributions will be licensed under the [MIT License](https://github.com/NousResearch/hermes-agent/blob/main/LICENSE).
