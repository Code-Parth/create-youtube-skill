---
name: create-youtube-skill
description: Turn any YouTube video into a ready-to-use Claude Code skill by extracting its transcript and drafting a new skill from what it teaches. Use whenever the user gives a YouTube URL or bare video ID and asks to "make a skill from this video", "turn this tutorial into a skill", "create a skill from this YouTube link", or similar — even if they just paste a youtube.com/youtu.be link alongside "can you make this into a skill".
---

# Create YouTube Skill

Turns a YouTube video's transcript into a new, fully-formed Claude Code skill, written directly into the current project at `.claude/skills/<name>/` and ready to use immediately.

This skill only extracts transcripts and captures intent. It does not draft, test, or write the resulting skill itself — that work is delegated to the **`skill-creator`** skill/plugin, which defines the canonical skill anatomy and the draft → test → eval → iterate loop. If `skill-creator` isn't available in this session, fall back per step 4 below.

## Step 1 — Fetch the transcript

Normalize whatever the user gave you (full URL or bare 11-character video ID — `scripts/fetch_transcript.py` handles both) and run:

```bash
python3 <skill-dir>/scripts/fetch_transcript.py "<url-or-id>"
```

If `yt-dlp` isn't installed, install it first: `pip install -r <skill-dir>/scripts/requirements.txt`.

The script prints transcript JSON to stdout on success, or an error JSON to stderr on failure. **Read `references/transcript-format.md` for the exact output shape and the full error-code table before handling failures** — do not guess at what an error means or invent transcript content when extraction fails. If the video has no captions, is unavailable, or yt-dlp gets blocked, tell the user plainly what happened and stop; don't proceed to drafting a skill from nothing.

## Step 2 — Skim the transcript, form a hypothesis

Read the transcript segments plus the video's title/channel. Before asking the user anything, work out candidate scopes for what this video could become a skill for:

- Is it teaching one focused tool/workflow, or does it cover several distinct techniques that could be separate skills?
- What's the concrete "doing" verb — is Claude meant to *generate* something (code, a document, a diagram), *follow a procedure* (a checklist, a review process), or *acquire domain knowledge* (explain concepts, answer questions in this area)?
- What phrases would a real user type that should trigger this skill later?

This is prep work for the interview in Step 3 — don't skip straight to drafting. A skill drafted from a silent guess is exactly what this workflow exists to avoid.

## Step 3 — Interview the user, grounded in the video

This is `skill-creator`'s "Capture Intent" step, but instead of generic questions, ask questions that reference what you actually found in the transcript so the user can answer quickly rather than re-explaining the video to you:

1. **Scope** — What should this skill enable Claude to do? If the video covers more than one distinct thing (from Step 2), name them and ask whether the user wants one combined skill or separate skills per topic.
2. **Triggers** — When should this skill fire? Propose 2-3 trigger phrases drawn from how the video itself frames the task, and let the user adjust or add their own.
3. **Output format** — What should the skill actually produce? Infer a sensible default from the video's nature (code tutorial → generated code; process/checklist video → a procedure; conceptual video → explanations/guidance) and confirm it rather than assuming it's correct.
4. **Test depth** — Confirm whether to run `skill-creator`'s full test-case + eval + benchmark loop (the default) or skip straight to a direct draft. Only skip if the user explicitly asks for a fast/lightweight pass.

Wait for the user's answers before writing anything. Use `AskUserQuestion` where the options are concrete and few (e.g. "one skill or split into two?"); use plain conversation where the answer is open-ended (e.g. trigger phrasing).

## Step 4 — Hand off to skill-creator

With the transcript content and the user's answers from Step 3 in hand, this is equivalent to having already completed `skill-creator`'s own "Capture Intent" interview — do not re-run that interview from scratch, just feed it these answers directly.

- **If the `skill-creator` skill is available in this session**, follow it: draft the `SKILL.md`, write test prompts, run the with-skill/without-skill eval loop, grade, launch the benchmark viewer, and iterate based on feedback, exactly as `skill-creator`'s own instructions describe. Treat the video transcript as reference material the drafted skill can pull from (e.g. as a `references/` file in the new skill) when the video contains specifics — code snippets, exact steps, terminology — worth preserving verbatim.
- **If `skill-creator` is not available**, fall back to drafting directly: write a `SKILL.md` with `name` + `description` frontmatter (the description must state both what the skill does and when to trigger it, per the answers from Step 3), keep the body under ~500 lines, and add `scripts/`/`references/`/`assets/` only if the video's content warrants bundled code or lookup docs. Tell the user that installing the `skill-creator` plugin would enable the full test/eval loop next time.

## Step 5 — Write the finished skill

Write the finished skill into the **current project root** at `.claude/skills/<skill-name>/` (create the directory if needed). This is the point of the whole workflow — the skill must be immediately usable in this project, not left in a temp location or requiring a separate install step.

## Step 6 — Report back

Tell the user: the skill's name, its location (`.claude/skills/<skill-name>/`), a one-line summary of what it does, and an example phrase that would trigger it.
