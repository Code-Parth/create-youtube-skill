# Create YouTube Skill

[skills.sh](https://skills.sh/Code-Parth/create-youtube-skill)

A skill that turns a YouTube video into a ready-to-use Claude Code skill: it extracts the video's transcript with `yt-dlp`, interviews you about scope and triggers using what the video actually covers, then drafts and writes a brand-new skill straight into your project.

```bash
npx skills add Code-Parth/create-youtube-skill
```

The skill lives at the repo root and includes:

- `SKILL.md`: workflow and trigger instructions.
- `scripts/fetch_transcript.py`: `yt-dlp`-based transcript extraction, cleanup, and merge pipeline.
- `references/transcript-format.md`: transcript JSON schema and the error-code table for failure handling.



## What It Does

- Accepts a full YouTube URL (`youtube.com/watch?v=...`, `youtu.be/...`, `/shorts/...`) or a bare 11-character video ID.
- Downloads manual or auto-generated captions via `yt-dlp` and cleans, merges, and normalizes them into readable, timestamped segments.
- Reads the transcript to identify what the video is actually teaching, then interviews you about scope, trigger phrases, and output format — grounded in the video's content, not a blank questionnaire.
- Hands off to the `[skill-creator](https://github.com/anthropics/claude-code)` plugin (when installed) to draft, test, and evaluate the new skill through its full loop; falls back to a direct draft if `skill-creator` isn't available.
- Writes the finished skill into the current project's `.claude/skills/<name>/`, ready to invoke immediately — no separate install step.
- Distinguishes real failure modes (`no_captions`, `unavailable`, `blocked`) instead of failing silently or inventing transcript content.



## Requirements

The transcript extractor requires Python 3 and `yt-dlp`.

Check support:

```bash
python3 -c "import yt_dlp" 2>/dev/null && echo "yt-dlp is installed" || echo "yt-dlp is missing"
```

If `yt-dlp` is missing, the script stops with a clear message rather than failing halfway through. In any harness, the agent should explain the dependency and ask before running any package manager command.

Install it directly:

```bash
pip install -r scripts/requirements.txt
```

Once installed, invoke it naturally, for example:

```text
Make a skill from this video: https://youtu.be/dQw4w9WgXcQ
```

```text
Turn this tutorial into a skill for my project: dQw4w9WgXcQ
```

Claude will fetch the transcript, ask a couple of clarifying questions grounded in the video, then write the new skill into `.claude/skills/` in your current project.

## Script Usage

Run the bundled script directly:

```bash
python3 scripts/fetch_transcript.py <youtube-url-or-video-id> [--lang en]
```

Examples:

```bash
# Full URL
python3 scripts/fetch_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Bare video ID
python3 scripts/fetch_transcript.py dQw4w9WgXcQ

# Non-English captions
python3 scripts/fetch_transcript.py dQw4w9WgXcQ --lang es
```

Important options:

- `<youtube-url-or-video-id>`: full YouTube URL or bare 11-character video ID.
- `--lang CODE`: caption language to request; default `en`. No multi-language fallback — a video with only Spanish captions requires `--lang es`.

On success, the script prints a single JSON object to stdout: `{"video": {...}, "segments": [...]}`. On failure, it prints a JSON error object to stderr and exits non-zero. See `[references/transcript-format.md](references/transcript-format.md)` for the exact schema and the full error-code table (`no_captions`, `unavailable`, `blocked`, `unknown`).

## Transcript Output

Each transcript segment includes:

- 1-based `id`, ordered and non-overlapping
- `start`, `end`, and `dur` in seconds, rounded to 3 decimal places
- Cleaned, merged `text` — raw caption fragments are merged into readable chunks, splitting only on sentence-ending punctuation or once a chunk exceeds ~12 seconds

Video metadata (`id`, `title`, `channel_name`, `channel_id`) is included alongside the segments so the generated skill can reference its source.

## Design Notes

- Each run downloads captions into a fresh temporary directory that's always cleaned up, even on failure — concurrent invocations against different videos are safe, unlike a naive current-working-directory approach.
- Extraction relies entirely on YouTube's own caption tracks; there's no audio transcription fallback if a video has no captions at all.
- This skill does not draft, test, or write the resulting skill itself — that's delegated to `skill-creator` so generated skills follow the same anatomy and eval loop as any other Claude Code skill.



## Source Inspiration

The transcript pipeline is adapted from an internal `yt-dlp`-based transcript extractor, hardened here for concurrency-safe temp handling and typed error codes instead of generic exceptions.

## License

[MIT](LICENSE)