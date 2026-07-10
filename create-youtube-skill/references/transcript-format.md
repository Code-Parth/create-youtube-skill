# Transcript output format

`scripts/fetch_transcript.py` prints a single JSON object to stdout on success.

## Success shape

```json
{
  "video": {
    "id": "dQw4w9WgXcQ",
    "title": "Video title",
    "channel_name": "Channel display name",
    "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx"
  },
  "segments": [
    {
      "id": 1,
      "start": 0.0,
      "end": 4.32,
      "dur": 4.32,
      "text": "Cleaned, merged caption text for this segment."
    }
  ]
}
```

- `segments` are ordered, 1-indexed, non-overlapping (each segment's `start` is clamped to the previous segment's `end`), and merged into readable chunks (a raw caption fragment is only split into a new segment once it ends in `.`, `?`, or `!`, or would otherwise exceed ~12 seconds).
- Timestamps are in seconds, rounded to 3 decimal places.

## Error shape

On failure, the script prints a JSON object to **stderr** and exits with a non-zero status:

```json
{"error": "no_captions", "message": "No 'en' captions (manual or auto-generated) are available for this video."}
```

`error` is one of:

| code | meaning | what to tell the user |
|---|---|---|
| `no_captions` | The video has no captions (manual or auto-generated) in the requested language. | This video can't be used as a skill source — no transcript to work from. Suggest trying a different video, or re-running with `--lang <code>` if the video has captions in another language. |
| `unavailable` | The video is private, deleted, age-restricted, or otherwise inaccessible. | Ask the user to double check the link, or confirm the video is public. |
| `blocked` | A network/download failure — commonly YouTube rate-limiting or bot-detection against yt-dlp. | This is often transient; suggest retrying. `yt-dlp` may need updating (`pip install -U yt-dlp`) if YouTube has changed its API recently — this project does not bundle cookie/proxy support, so persistent blocking may require the user to configure `yt-dlp` cookies themselves outside this skill. |
| `unknown` | Anything else (e.g. a crash inside yt-dlp not covered above). | Show the raw `message` to the user rather than guessing. |

## Other gotchas

- Only one caption language is fetched per run (`--lang`, default `en`). There's no multi-language fallback — if a video only has, say, Spanish captions, you must pass `--lang es`.
- Each invocation downloads into a fresh temp directory that is always cleaned up (even on failure), so concurrent invocations against different videos are safe.
- This relies entirely on YouTube's caption tracks (manual or auto-generated) via `yt-dlp` — it does not perform its own audio transcription. If YouTube has no captions at all, there's no fallback.
