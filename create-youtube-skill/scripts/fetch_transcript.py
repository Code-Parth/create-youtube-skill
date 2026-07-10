#!/usr/bin/env python3
"""Fetch and normalize a YouTube video's transcript via yt-dlp.

Usage:
    python3 fetch_transcript.py <youtube-url-or-video-id> [--lang en]

Prints a JSON object to stdout:
    {"video": {"id", "title", "channel_name", "channel_id"}, "segments": [...]}

On failure, prints a JSON object {"error": "<code>", "message": "<detail>"}
to stderr and exits non-zero. Error codes:
    no_captions        - video has no captions in the requested language
    unavailable         - video is private, deleted, or otherwise unavailable
    blocked             - network/download failure (rate limiting, bot detection, etc.)
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from typing import List, Optional

import yt_dlp


# -----------------------------
# URL / ID normalization
# -----------------------------

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def normalize_url(value: str) -> str:
    value = value.strip()
    if "://" not in value and _VIDEO_ID_RE.match(value):
        return f"https://www.youtube.com/watch?v={value}"
    return value


# -----------------------------
# Models
# -----------------------------

class Seg:
    def __init__(self, utf8: str):
        self.utf8 = utf8


class Event:
    def __init__(self, t_start_ms: int, d_duration_ms: int, segs: Optional[List[Seg]] = None):
        self.t_start_ms = t_start_ms
        self.d_duration_ms = d_duration_ms
        self.segs = segs or []

    def get_text(self) -> str:
        return "".join(seg.utf8 for seg in self.segs).strip()

    def to_clean(self):
        text = clean_text(self.get_text())
        if not text:
            return None

        return {
            "start": self.t_start_ms / 1000,
            "end": (self.t_start_ms + self.d_duration_ms) / 1000,
            "text": text,
        }


class TranscriptData:
    def __init__(self, events: List[Event]):
        self.events = events


class TranscriptError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class _SilentLogger:
    """Swallows yt-dlp's own stderr logging so stdout/stderr only ever carry our JSON."""

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


# -----------------------------
# yt-dlp Extraction (WITH META)
# -----------------------------

def fetch_video_data(url: str, lang: str = "en"):
    workdir = tempfile.mkdtemp(prefix="yt-transcript-")
    try:
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [lang],
            "subtitlesformat": "json3",
            "outtmpl": os.path.join(workdir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "logger": _SilentLogger(),
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            msg = str(e)
            if any(s in msg for s in ("Private video", "Video unavailable", "This video is unavailable")):
                raise TranscriptError("unavailable", msg) from e
            raise TranscriptError("blocked", msg) from e

        video_id = info["id"]
        title = info.get("title", "")
        channel = info.get("uploader", "")
        channel_id = info.get("channel_id") or info.get("uploader_id")

        subtitle_data = None
        for fname in os.listdir(workdir):
            if fname.startswith(video_id) and fname.endswith(".json3"):
                with open(os.path.join(workdir, fname), "r", encoding="utf-8") as f:
                    subtitle_data = json.load(f)
                break

        if not subtitle_data:
            raise TranscriptError(
                "no_captions",
                f"No '{lang}' captions (manual or auto-generated) are available for this video.",
            )

        return {
            "video_id": video_id,
            "title": title,
            "channel_name": channel,
            "channel_id": channel_id,
            "subtitles": subtitle_data,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# -----------------------------
# Parsing
# -----------------------------

def parse_events(data: dict) -> TranscriptData:
    events = []

    for e in data.get("events", []):
        segs = [Seg(seg.get("utf8", "")) for seg in e.get("segs", [])]

        events.append(
            Event(
                t_start_ms=e.get("tStartMs", 0),
                d_duration_ms=e.get("dDurationMs", 0),
                segs=segs,
            )
        )

    return TranscriptData(events)


# -----------------------------
# Cleaning
# -----------------------------

def clean_text(text: str) -> str:
    return text.replace("\n", " ").replace("  ", " ").strip()


# -----------------------------
# Build Transcript
# -----------------------------

def build_transcript(data: TranscriptData):
    return [e.to_clean() for e in data.events if e.to_clean()]


# -----------------------------
# Smart Merge
# -----------------------------

def smart_merge_segments(segments, max_duration=12):
    merged = []
    current = None

    for seg in segments:
        if not current:
            current = seg.copy()
            continue

        duration = current["end"] - current["start"]

        should_split = (
            duration > max_duration or
            current["text"].endswith((".", "?", "!"))
        )

        if should_split:
            merged.append(current)
            current = seg.copy()
        else:
            current["text"] += " " + seg["text"]
            current["end"] = seg["end"]

    if current:
        merged.append(current)

    return merged


# -----------------------------
# Normalize
# -----------------------------

def normalize_segments(segments):
    normalized = []

    for i, seg in enumerate(segments):
        start = seg["start"]
        end = seg["end"]

        if i > 0:
            prev = normalized[-1]
            if start < prev["end"]:
                start = prev["end"]

        normalized.append({
            "id": i + 1,
            "start": round(start, 3),
            "end": round(end, 3),
            "dur": round(end - start, 3),
            "text": seg["text"],
        })

    return normalized


# -----------------------------
# FINAL PIPELINE
# -----------------------------

def process_video(url: str, lang: str = "en"):
    data = fetch_video_data(url, lang=lang)

    parsed = parse_events(data["subtitles"])
    transcript = build_transcript(parsed)
    transcript = smart_merge_segments(transcript)
    transcript = normalize_segments(transcript)

    return {
        "video": {
            "id": data["video_id"],
            "title": data["title"],
            "channel_name": data["channel_name"],
            "channel_id": data["channel_id"],
        },
        "segments": transcript,
    }


# -----------------------------
# CLI
# -----------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch a YouTube video's transcript as JSON.")
    parser.add_argument("url", help="Full YouTube URL or bare video ID.")
    parser.add_argument("--lang", default="en", help="Caption language code (default: en).")
    args = parser.parse_args()

    url = normalize_url(args.url)

    try:
        result = process_video(url, lang=args.lang)
    except TranscriptError as e:
        print(json.dumps({"error": e.code, "message": e.message}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": "unknown", "message": str(e)}), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
