---
title: "Youtube Content"
url: "https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content

# Youtube Content
YouTube transcripts to summaries, threads, blogs.
## Skill metadata[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#skill-metadata "Direct link to Skill metadata")  
|   |   |  
| --- | --- |  
| Source  | Bundled (installed by default)  |  
| Path  | `skills/media/youtube-content`  |  
| Platforms  | linux, macos, windows  |  
## Reference: full SKILL.md[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#reference-full-skillmd "Direct link to Reference: full SKILL.md")
info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
# YouTube Content Tool
## When to use[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#when-to-use "Direct link to When to use")
Use when the user shares a YouTube URL or video link, asks to summarize a video, requests a transcript, or wants to extract and reformat content from any YouTube video. Transforms transcripts into structured content (chapters, summaries, threads, blog posts).
Extract transcripts from YouTube videos and convert them into useful formats.
## Setup[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#setup "Direct link to Setup")
Use `uv` so the dependency is installed into the same Hermes-managed environment that runs the helper script:

```
uv pip install youtube-transcript-api  

```

## Helper Script[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#helper-script "Direct link to Helper Script")
`SKILL_DIR` is the directory containing this SKILL.md file. The script accepts any standard YouTube URL format, short links (youtu.be), shorts, embeds, live links, or a raw 11-character video ID.

```
# JSON output with metadata  
uv run python3 SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"  
  
# Plain text (good for piping into further processing)  
uv run python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only  
  
# With timestamps  
uv run python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps  
  
# Specific language with fallback chain  
uv run python3 SKILL_DIR/scripts/fetch_transcript.py "URL" --language tr,en  

```

## Output Formats[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#output-formats "Direct link to Output Formats")
After fetching the transcript, format it based on what the user asks for:
  * **Chapters** : Group by topic shifts, output timestamped chapter list
  * **Summary** : Concise 5-10 sentence overview of the entire video
  * **Chapter summaries** : Chapters with a short paragraph summary for each
  * **Thread** : Twitter/X thread format — numbered posts, each under 280 chars
  * **Blog post** : Full article with title, sections, and key takeaways
  * **Quotes** : Notable quotes with timestamps

### Example — Chapters Output[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#example--chapters-output "Direct link to Example — Chapters Output")

```
00:00 Introduction — host opens with the problem statement  
03:45 Background — prior work and why existing solutions fall short  
12:20 Core method — walkthrough of the proposed approach  
24:10 Results — benchmark comparisons and key takeaways  
31:55 Q&A — audience questions on scalability and next steps  

```

## Workflow[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#workflow "Direct link to Workflow")
  1. **Fetch** the transcript using the helper script with `--text-only --timestamps` via `uv run python3`.
  2. **Validate** : confirm the output is non-empty and in the expected language. If empty, retry without `--language` to get any available transcript. If still empty, tell the user the video likely has transcripts disabled.
  3. **Chunk if needed** : if the transcript exceeds ~50K characters, split into overlapping chunks (~40K with 2K overlap) and summarize each chunk before merging.
  4. **Transform** into the requested output format. If the user did not specify a format, default to a summary.
  5. **Verify** : re-read the transformed output to check for coherence, correct timestamps, and completeness before presenting.

## Error Handling[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/media/media-youtube-content#error-handling "Direct link to Error Handling")
  * **Transcript disabled** : tell the user; suggest they check if subtitles are available on the video page.
  * **Private/unavailable video** : relay the error and ask the user to verify the URL.
  * **No matching language** : retry without `--language` to fetch any available transcript, then note the actual language to the user.
  * **Dependency missing** : run `uv pip install youtube-transcript-api` and retry.
