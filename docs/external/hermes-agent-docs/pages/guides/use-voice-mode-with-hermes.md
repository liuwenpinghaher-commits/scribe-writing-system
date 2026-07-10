---
title: "Use Voice Mode with Hermes"
url: "https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes

# Use Voice Mode with Hermes
This guide is the practical companion to the [Voice Mode feature reference](https://hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode).
If the feature page explains what voice mode can do, this guide shows how to actually use it well.
tip
[Nous Portal](https://hermes-agent.nousresearch.com/docs/integrations/nous-portal) bundles both the LLM and TTS through one OAuth — voice mode works end-to-end with no extra credentials.
## What voice mode is good for[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#what-voice-mode-is-good-for "Direct link to What voice mode is good for")
Voice mode is especially useful when:
  * you want a hands-free CLI workflow
  * you want spoken responses in Telegram or Discord
  * you want Hermes sitting in a Discord voice channel for live conversation
  * you want quick idea capture, debugging, or back-and-forth while walking around instead of typing

## Choose your voice mode setup[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#choose-your-voice-mode-setup "Direct link to Choose your voice mode setup")
There are really three different voice experiences in Hermes.  
| Mode  | Best for  | Platform  |  
| --- | --- | --- |  
| Interactive microphone loop  | Personal hands-free use while coding or researching  | CLI  |  
| Voice replies in chat  | Spoken responses alongside normal messaging  | Telegram, Discord  |  
| Live voice channel bot  | Group or personal live conversation in a VC  | Discord voice channels  |  
A good path is:
  1. get text working first
  2. enable voice replies second
  3. move to Discord voice channels last if you want the full experience

## Step 1: make sure normal Hermes works first[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#step-1-make-sure-normal-hermes-works-first "Direct link to Step 1: make sure normal Hermes works first")
Before touching voice mode, verify that:
  * Hermes starts
  * your provider is configured
  * the agent can answer text prompts normally

```
hermes  

```

Ask something simple:

```
What tools do you have available?  

```

If that is not solid yet, fix text mode first.
## Step 2: install the right extras[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#step-2-install-the-right-extras "Direct link to Step 2: install the right extras")
### CLI microphone + playback[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#cli-microphone--playback "Direct link to CLI microphone + playback")

```
cd ~/.hermes/hermes-agent && uv pip install -e ".[voice]"  

```

### Messaging platforms[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#messaging-platforms "Direct link to Messaging platforms")

```
cd ~/.hermes/hermes-agent && uv pip install -e ".[messaging]"  

```

### Premium ElevenLabs TTS[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#premium-elevenlabs-tts "Direct link to Premium ElevenLabs TTS")

```
cd ~/.hermes/hermes-agent && uv pip install -e ".[tts-premium]"  

```

### Local NeuTTS (optional)[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#local-neutts-optional "Direct link to Local NeuTTS \(optional\)")

```
python -m pip install -U neutts[all]  

```

### Everything[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#everything "Direct link to Everything")

```
cd ~/.hermes/hermes-agent && uv pip install -e ".[all]"  

```

## Step 3: install system dependencies[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#step-3-install-system-dependencies "Direct link to Step 3: install system dependencies")
### macOS[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#macos "Direct link to macOS")

```
brew install portaudio ffmpeg opus  
brew install espeak-ng  

```

### Ubuntu / Debian[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#ubuntu--debian "Direct link to Ubuntu / Debian")

```
sudo apt install portaudio19-dev ffmpeg libopus0  
sudo apt install espeak-ng  

```

Why these matter:
  * `portaudio` → microphone input / playback for CLI voice mode
  * `ffmpeg` → audio conversion for TTS and messaging delivery
  * `opus` → Discord voice codec support
  * `espeak-ng` → phonemizer backend for NeuTTS

## Step 4: choose STT and TTS providers[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#step-4-choose-stt-and-tts-providers "Direct link to Step 4: choose STT and TTS providers")
Hermes supports both local and cloud speech stacks.
### Easiest / cheapest setup[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#easiest--cheapest-setup "Direct link to Easiest / cheapest setup")
Use local STT and free Edge TTS:
  * STT provider: `local`
  * TTS provider: `edge`

This is usually the best place to start.
### Environment file example[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#environment-file-example "Direct link to Environment file example")
Add to `~/.hermes/.env`:

```
# Cloud STT options (local needs no key)  
GROQ_API_KEY=***  
VOICE_TOOLS_OPENAI_KEY=***  
  
# Premium TTS (optional)  
ELEVENLABS_API_KEY=***  

```

### Provider recommendations[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#provider-recommendations "Direct link to Provider recommendations")
#### Speech-to-text[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#speech-to-text "Direct link to Speech-to-text")
  * `local` → best default for privacy and zero-cost use
  * `groq` → very fast cloud transcription
  * `openai` → good paid fallback

#### Text-to-speech[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#text-to-speech "Direct link to Text-to-speech")
  * `edge` → free and good enough for most users
  * `neutts` → free local/on-device TTS
  * `elevenlabs` → best quality
  * `openai` → good middle ground
  * `mistral` → multilingual, native Opus

### If you use `hermes setup`[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#if-you-use-hermes-setup "Direct link to if-you-use-hermes-setup")
If you choose NeuTTS in the setup wizard, Hermes checks whether `neutts` is already installed. If it is missing, the wizard tells you NeuTTS needs the Python package `neutts` and the system package `espeak-ng`, offers to install them for you, installs `espeak-ng` with your platform package manager, and then runs:

```
python -m pip install -U neutts[all]  

```

If you skip that install or it fails, the wizard falls back to Edge TTS.
## Step 5: recommended config[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#step-5-recommended-config "Direct link to Step 5: recommended config")

```
voice:  
  record_key: "ctrl+b"  
  max_recording_seconds: 120  
  auto_tts: false  
  beep_enabled: true  
  silence_threshold: 200  
  silence_duration: 3.0  
  
stt:  
  provider: "local"  
  local:  
    model: "base"  
  
tts:  
  provider: "edge"  
  edge:  
    voice: "en-US-AriaNeural"  

```

This is a good conservative default for most people.
If you want local TTS instead, switch the `tts` block to:

```
tts:  
  provider: "neutts"  
  neutts:  
    ref_audio: ''  
    ref_text: ''  
    model: neuphonic/neutts-air-q4-gguf  
    device: cpu  

```

## Use case 1: CLI voice mode[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#use-case-1-cli-voice-mode "Direct link to Use case 1: CLI voice mode")
## Turn it on[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#turn-it-on "Direct link to Turn it on")
Start Hermes:

```
hermes  

```

Inside the CLI:

```
/voice on  

```

### Recording flow[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#recording-flow "Direct link to Recording flow")
Default key:
  * `Ctrl+B`

Workflow:
  1. press `Ctrl+B`
  2. speak
  3. wait for silence detection to stop recording automatically
  4. Hermes transcribes and responds
  5. if TTS is on, it speaks the answer
  6. the loop can automatically restart for continuous use

### Useful commands[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#useful-commands "Direct link to Useful commands")

```
/voice  
/voice on  
/voice off  
/voice tts  
/voice status  

```

### Good CLI workflows[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#good-cli-workflows "Direct link to Good CLI workflows")
#### Walk-up debugging[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#walk-up-debugging "Direct link to Walk-up debugging")
Say:

```
I keep getting a docker permission error. Help me debug it.  

```

Then continue hands-free:
  * "Read the last error again"
  * "Explain the root cause in simpler terms"
  * "Now give me the exact fix"

#### Research / brainstorming[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#research--brainstorming "Direct link to Research / brainstorming")
Great for:
  * walking around while thinking
  * dictating half-formed ideas
  * asking Hermes to structure your thoughts in real time

#### Accessibility / low-typing sessions[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#accessibility--low-typing-sessions "Direct link to Accessibility / low-typing sessions")
If typing is inconvenient, voice mode is one of the fastest ways to stay in the full Hermes loop.
## Tuning CLI behavior[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#tuning-cli-behavior "Direct link to Tuning CLI behavior")
### Silence threshold[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#silence-threshold "Direct link to Silence threshold")
If Hermes starts/stops too aggressively, tune:

```
voice:  
  silence_threshold: 250  

```

Higher threshold = less sensitive.
### Silence duration[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#silence-duration "Direct link to Silence duration")
If you pause a lot between sentences, increase:

```
voice:  
  silence_duration: 4.0  

```

### Record key[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#record-key "Direct link to Record key")
If `Ctrl+B` conflicts with your terminal or tmux habits:

```
voice:  
  record_key: "ctrl+space"  

```

## Use case 2: voice replies in Telegram or Discord[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#use-case-2-voice-replies-in-telegram-or-discord "Direct link to Use case 2: voice replies in Telegram or Discord")
This mode is simpler than full voice channels.
Hermes stays a normal chat bot, but can speak replies.
### Start the gateway[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#start-the-gateway "Direct link to Start the gateway")

```
hermes gateway  

```

### Turn on voice replies[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#turn-on-voice-replies "Direct link to Turn on voice replies")
Inside Telegram or Discord:

```
/voice on  

```

or

```
/voice tts  

```

### Modes[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#modes "Direct link to Modes")  
| Mode  | Meaning  |  
| --- | --- |  
| `off`  | text only  |  
| `voice_only`  | speak only when the user sent voice  |  
| `all`  | speak every reply  |  
### When to use which mode[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#when-to-use-which-mode "Direct link to When to use which mode")
  * `/voice on` if you want spoken replies only for voice-originating messages
  * `/voice tts` if you want a full spoken assistant all the time

### Good messaging workflows[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#good-messaging-workflows "Direct link to Good messaging workflows")
#### Telegram assistant on your phone[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#telegram-assistant-on-your-phone "Direct link to Telegram assistant on your phone")
Use when:
  * you are away from your machine
  * you want to send voice notes and get quick spoken replies
  * you want Hermes to function like a portable research or ops assistant

#### Discord DMs with spoken output[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#discord-dms-with-spoken-output "Direct link to Discord DMs with spoken output")
Useful when you want private interaction without server-channel mention behavior.
## Use case 3: Discord voice channels[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#use-case-3-discord-voice-channels "Direct link to Use case 3: Discord voice channels")
This is the most advanced mode.
Hermes joins a Discord VC, listens to user speech, transcribes it, runs the normal agent pipeline, and speaks replies back into the channel.
## Required Discord permissions[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#required-discord-permissions "Direct link to Required Discord permissions")
In addition to the normal text-bot setup, make sure the bot has:
  * Connect
  * Speak
  * preferably Use Voice Activity

Also enable privileged intents in the Developer Portal:
  * Presence Intent
  * Server Members Intent
  * Message Content Intent

## Join and leave[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#join-and-leave "Direct link to Join and leave")
In a Discord text channel where the bot is present:

```
/voice join  
/voice leave  
/voice status  

```

### What happens when joined[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#what-happens-when-joined "Direct link to What happens when joined")
  * users speak in the VC
  * Hermes detects speech boundaries
  * transcripts are posted in the associated text channel
  * Hermes responds in text and audio
  * the text channel is the one where `/voice join` was issued

### Best practices for Discord VC use[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#best-practices-for-discord-vc-use "Direct link to Best practices for Discord VC use")
  * keep `DISCORD_ALLOWED_USERS` tight
  * use a dedicated bot/testing channel at first
  * verify STT and TTS work in ordinary text-chat voice mode before trying VC mode

## Voice quality recommendations[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#voice-quality-recommendations "Direct link to Voice quality recommendations")
### Best quality setup[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#best-quality-setup "Direct link to Best quality setup")
  * STT: local `large-v3` or Groq `whisper-large-v3`
  * TTS: ElevenLabs

### Best speed / convenience setup[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#best-speed--convenience-setup "Direct link to Best speed / convenience setup")
  * STT: local `base` or Groq
  * TTS: Edge

### Best zero-cost setup[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#best-zero-cost-setup "Direct link to Best zero-cost setup")
  * STT: local
  * TTS: Edge

## Common failure modes[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#common-failure-modes "Direct link to Common failure modes")
### "No audio device found"[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#no-audio-device-found "Direct link to "No audio device found"")
Install `portaudio`.
### "Bot joins but hears nothing"[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#bot-joins-but-hears-nothing "Direct link to "Bot joins but hears nothing"")
Check:
  * your Discord user ID is in `DISCORD_ALLOWED_USERS`
  * you are not muted
  * privileged intents are enabled
  * the bot has Connect/Speak permissions

### "It transcribes but does not speak"[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#it-transcribes-but-does-not-speak "Direct link to "It transcribes but does not speak"")
Check:
  * TTS provider config
  * API key / quota for ElevenLabs or OpenAI
  * `ffmpeg` install for Edge conversion paths

### "Whisper outputs garbage"[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#whisper-outputs-garbage "Direct link to "Whisper outputs garbage"")
Try:
  * quieter environment
  * higher `silence_threshold`
  * different STT provider/model
  * shorter, clearer utterances

### "It works in DMs but not in server channels"[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#it-works-in-dms-but-not-in-server-channels "Direct link to "It works in DMs but not in server channels"")
That is often mention policy.
By default, the bot needs an `@mention` in Discord server text channels unless configured otherwise.
## Suggested first-week setup[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#suggested-first-week-setup "Direct link to Suggested first-week setup")
If you want the shortest path to success:
  1. get text Hermes working
  2. install `hermes-agent[voice]`
  3. use CLI voice mode with local STT + Edge TTS
  4. then enable `/voice on` in Telegram or Discord
  5. only after that, try Discord VC mode

That progression keeps the debugging surface small.
## Where to read next[​](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes#where-to-read-next "Direct link to Where to read next")
  * [Voice Mode feature reference](https://hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode)
  * [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)
  * [Discord setup](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/discord)
  * [Telegram setup](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)
  * [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
