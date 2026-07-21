# Hermes on Android with Termux
Tier 2 platform
Termux (Android) is a [Tier 2 platform](https://hermes-agent.nousresearch.com/docs/getting-started/platform-support#tier-2). The installer script and documentation here are maintained on a best-effort basis only. Commits to `main` may break these packages at any point in time.
Hermes Agent can run directly on an Android phone through [Termux](https://termux.dev/).
It gives you a working local CLI on the phone, plus the core extras that are currently known to install cleanly on Android.
## What is supported in the tested path?[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#what-is-supported-in-the-tested-path "Direct link to What is supported in the tested path?")
The tested Termux bundle installs:
  * the Hermes CLI
  * cron support
  * PTY/background terminal support
  * Telegram gateway support (manual / best-effort background runs)
  * MCP support
  * Honcho memory support
  * ACP support

Concretely, it maps to:

```
python -m pip install -e '.[termux]' -c constraints-termux.txt  

```

## What is not part of the tested path yet?[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#what-is-not-part-of-the-tested-path-yet "Direct link to What is not part of the tested path yet?")
A few features still need desktop/server-style dependencies that are not published for Android, or have not been validated on phones yet:
  * `.[all]` is not supported on Android today
  * the `voice` extra is blocked by `faster-whisper -> ctranslate2`, and `ctranslate2` does not publish Android wheels
  * automatic browser / Playwright bootstrap is skipped in the Termux installer
  * Docker-based terminal isolation is not available inside Termux
  * Android may still suspend Termux background jobs, so gateway persistence is best-effort rather than a normal managed service

That does not stop Hermes from working well as a phone-native CLI agent — it just means the recommended mobile install is intentionally narrower than the desktop/server install.
* * *
## Option 1: One-line installer[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#option-1-one-line-installer "Direct link to Option 1: One-line installer")
Hermes now ships a Termux-aware installer path:

```
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash  

```

On Termux, the installer automatically:
  * uses `pkg` for system packages
  * creates the venv with `python -m venv`
  * attempts the broad `.[termux-all]` extra first and falls back to the smaller `.[termux]` extra (then a base install) — the curl installer matches this order automatically
  * links `hermes` into `$PREFIX/bin` so it stays on your Termux PATH
  * skips the untested browser / WhatsApp bootstrap

If you want the explicit commands or need to debug a failed install, use the manual path below.
* * *
## Option 2: Manual install (fully explicit)[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#option-2-manual-install-fully-explicit "Direct link to Option 2: Manual install \(fully explicit\)")
### 1. Update Termux and install system packages[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#1-update-termux-and-install-system-packages "Direct link to 1. Update Termux and install system packages")

```
pkg update  
pkg install -y git python clang rust make pkg-config libffi openssl nodejs ripgrep ffmpeg  

```

Why these packages?
  * `python` — runtime + venv support
  * `git` — clone/update the repo
  * `clang`, `rust`, `make`, `pkg-config`, `libffi`, `openssl` — needed to build a few Python dependencies on Android
  * `nodejs` — optional Node runtime for experiments beyond the tested core path
  * `ripgrep` — fast file search
  * `ffmpeg` — media / TTS conversions

### 2. Clone Hermes[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#2-clone-hermes "Direct link to 2. Clone Hermes")

```
git clone https://github.com/NousResearch/hermes-agent.git  
cd hermes-agent  

```

### 3. Create a virtual environment[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#3-create-a-virtual-environment "Direct link to 3. Create a virtual environment")

```
python -m venv venv  
source venv/bin/activate  
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"  
python -m pip install --upgrade pip setuptools wheel  

```

`ANDROID_API_LEVEL` is important for Rust / maturin-based packages such as `jiter`.
### 4. Install the tested Termux bundle[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#4-install-the-tested-termux-bundle "Direct link to 4. Install the tested Termux bundle")

```
python -m pip install -e '.[termux]' -c constraints-termux.txt  

```

If you only want the minimal core agent, this also works:

```
python -m pip install -e '.' -c constraints-termux.txt  

```

### 5. Put `hermes` on your Termux PATH[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#5-put-hermes-on-your-termux-path "Direct link to 5-put-hermes-on-your-termux-path")

```
ln -sf "$PWD/venv/bin/hermes" "$PREFIX/bin/hermes"  

```

`$PREFIX/bin` is already on PATH in Termux, so this makes the `hermes` command persist across new shells without re-activating the venv every time.
### 6. Verify the install[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#6-verify-the-install "Direct link to 6. Verify the install")

```
hermes version  
hermes doctor  

```

### 7. Start Hermes[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#7-start-hermes "Direct link to 7. Start Hermes")

```
hermes  

```

* * *
## Recommended follow-up setup[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#recommended-follow-up-setup "Direct link to Recommended follow-up setup")
### Configure a model[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#configure-a-model "Direct link to Configure a model")

```
hermes model  

```

Or set keys directly in `~/.hermes/.env`.
### Re-run the full interactive setup wizard later[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#re-run-the-full-interactive-setup-wizard-later "Direct link to Re-run the full interactive setup wizard later")

```
hermes setup  

```

### Install optional Node dependencies manually[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#install-optional-node-dependencies-manually "Direct link to Install optional Node dependencies manually")
The tested Termux path skips Node/browser bootstrap on purpose. If you want to experiment with browser tooling later:

```
pkg install nodejs-lts  
npm install  

```

The browser tool automatically includes Termux directories (`/data/data/com.termux/files/usr/bin`) in its PATH search, so `agent-browser` and `npx` are discovered without any extra PATH configuration.
Treat browser / WhatsApp tooling on Android as experimental until documented otherwise.
* * *
## Troubleshooting[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#troubleshooting "Direct link to Troubleshooting")
###  `No solution found` when installing `.[all]`[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#no-solution-found-when-installing-all "Direct link to no-solution-found-when-installing-all")
Use the tested Termux bundle instead:

```
python -m pip install -e '.[termux]' -c constraints-termux.txt  

```

The blocker is currently the `voice` extra:
  * `voice` pulls `faster-whisper`
  * `faster-whisper` depends on `ctranslate2`
  * `ctranslate2` does not publish Android wheels

###  `uv pip install` fails on Android[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#uv-pip-install-fails-on-android "Direct link to uv-pip-install-fails-on-android")
Use the Termux path with the stdlib venv + `pip` instead:

```
python -m venv venv  
source venv/bin/activate  
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"  
python -m pip install --upgrade pip setuptools wheel  
python -m pip install -e '.[termux]' -c constraints-termux.txt  

```

###  `jiter` / `maturin` complains about `ANDROID_API_LEVEL`[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#jiter--maturin-complains-about-android_api_level "Direct link to jiter--maturin-complains-about-android_api_level")
Set the API level explicitly before installing:

```
export ANDROID_API_LEVEL="$(getprop ro.build.version.sdk)"  
python -m pip install -e '.[termux]' -c constraints-termux.txt  

```

###  `hermes doctor` says ripgrep or Node is missing[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#hermes-doctor-says-ripgrep-or-node-is-missing "Direct link to hermes-doctor-says-ripgrep-or-node-is-missing")
Install them with Termux packages:

```
pkg install ripgrep nodejs  

```

### Build failures while installing Python packages[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#build-failures-while-installing-python-packages "Direct link to Build failures while installing Python packages")
Make sure the build toolchain is installed:

```
pkg install clang rust make pkg-config libffi openssl  

```

Then retry:

```
python -m pip install -e '.[termux]' -c constraints-termux.txt  

```

* * *
## Known limitations on phones[​](https://hermes-agent.nousresearch.com/docs/getting-started/termux#known-limitations-on-phones "Direct link to Known limitations on phones")
  * Docker backend is unavailable
  * local voice transcription via `faster-whisper` is unavailable in the tested path
  * browser automation setup is intentionally skipped by the installer
  * some optional extras may work, but only `.[termux]` and `.[termux-all]` are currently documented as the tested Android bundles

If you hit a new Android-specific issue, please open a GitHub issue with:
  * your Android version
  * `termux-info`
  * `python --version`
  * `hermes doctor`
  * the exact install command and full error output
