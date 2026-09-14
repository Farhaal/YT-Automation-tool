# Build Progress & Resume State

**This file is the single source of truth for where the OpenReel build stands.** It exists
so the build can survive interruptions: if Antigravity hits a model/usage limit mid-build,
a fresh session reads this file plus the git history and continues exactly where it left
off — no lost context, no guessing.

Keep this file in the `dev/` folder. `dev/` is gitignored on purpose: it's build
scaffolding (plan, guide, progress), not part of the shipped product.

---

## How to resume after a limit or in a new session

When a session ends early (limit reached, app closed, next day), open a fresh Antigravity
session in the project folder and paste this **resume prompt**:

```
Read dev/PROGRESS.md, dev/BLUEPRINT.md, and dev/ANTIGRAVITY_GUIDE.md in full. Then run
`git log --oneline -n 15` and `git status` to see the real state of the code. Reconcile
what the code actually shows against dev/PROGRESS.md, then tell me:
  1. the current phase,
  2. what is already done,
  3. the exact "Next action".
Continue from that Next action, one phase at a time. Do NOT restart finished phases or
overwrite working files. When the phase's "Done when" (see BLUEPRINT) is met, update this
file — check the box, set the new Current phase + Next action, append a dated Log line —
then commit.
```

Git is the durable backup of the actual code; this file is the human-readable pointer to
"where we are." Together they make the build fully resumable.

---

## Rules for the agent (keep work recoverable)

- **Commit often.** Small, logical commits after every meaningful step, so an interruption
  mid-phase never loses more than a few minutes of work.
- **Update this file at the end of every phase** (and before stopping if you sense a limit
  approaching): tick the box, update **Current phase** + **Next action**, add a Log line,
  then commit with `docs: update build progress`.
- **Never mark a phase done** unless its "Done when" in `BLUEPRINT.md` is actually met and
  verified.
- **Never restart or overwrite** a completed phase's working files on resume — extend them.

---

## Snapshot  (update this block every phase)

- **Current phase:** P9 — Export and credits
- **Next action:** Implement full-resolution export, downloadable MP4, and credits.txt from timeline asset metadata.
- **Last commit:** (pending docs update)
- **Current branch:** fix/aspect-ratio (branching off phase-8-frontend)
- **Latest tag:** —
- **Last updated:** 2026-09-14

---

## Phase checklist

- [x] **P0** — Foundation, repo hygiene, professional structure
- [x] **P1** — Backend skeleton (FastAPI, config, health, stub routes)
- [x] **P2** — Transcription + word-level alignment — the sync core ⚡
- [x] **P3** — Text-to-speech path (text → narration → same word timings)
- [x] **P4** — Scenes + keyword/query extraction
- [x] **P5** — Asset providers (Pexels, Pixabay, Openverse, Wikimedia) + ranking
- [x] **P6** — Timeline assembly + schema validation
- [x] **P7** — Renderer (captions, transitions, effects, pop-ups, export)
- [x] **P8** — Frontend (upload/paste, progress, preview, clip swap, export)
- [ ] **P9** — Full-res export + auto-generated credits
- [ ] **P10** — Packaging & polish (Tauri shell, docs, v1.0)
- [ ] **P11** — Optional upgrades (LLM scripting, upscaling, music, themes)

---

## Log

_One line per work session or completed phase, newest at the bottom._

- 2026-09-13: Completed P0 (Foundation, project structure, virtual environment, CI, scripts)
- 2026-09-13: Completed P1 (Backend skeleton, FastAPI, health check, startup checks, stub routes)
- 2026-09-13: Completed P2 (Transcription service with faster-whisper and word-level alignment)
- 2026-09-13: Completed P3 (Text-to-speech path with pyttsx3 baseline and unified transcription output)
- 2026-09-13: Completed P4 (Scene segmentation and keyword/query extraction using spaCy and YAKE)
- 2026-09-13: Completed P5 (Asset providers integrated with ranking, caching, deduplication, and fallback policies)
- 2026-09-13: Completed P6 (Timeline assembly with JSON schema validation)
- 2026-09-13: Fixed P6 timeline schema strictness, fixed P5 test tempfile leakage, rewrote requirements.txt clean.
- 2026-09-13: Completed P7 (Draft renderer using MoviePy with NVENC/libx264 fallback).
- 2026-09-13: Completed P8 (Frontend React UI, orchestration pipeline, strict timeline validation, and UI controls).
- 2026-09-14: Updated aspect ratio defaults and user selection UI for 16:9, 9:16, 1:1 format choice. Handoff for P8 stabilization.
- 2026-09-14: Performance improvements: configured faster whisper default (small), optional Ken Burns motion in UI, and optimized encoder presets.
- 2026-09-14: Added optional user-provided LLM API key support (OpenAI-compatible) for smarter visual query extraction with secure local storage.
- 2026-09-14: Enhanced asset selection with relevance-aware ranking (token overlap) and optimized Wikimedia fallback strategy. Added tag parsing from Pixabay and alt-text parsing from Pexels to power ranking.
- 2026-09-14: Standardized CI pipeline by adding Ruff (E, F, I) formatting configuration, fixing remaining lint errors, and properly provisioning the GitHub Actions test runner with FFmpeg and spaCy dependencies.
- 2026-09-14: Fixed Openverse endpoint domain, increased timeout, added redirect handling to Openverse/Wikimedia, rigorously isolated settings file path across test suites, and added global User-Agent header to prevent 502/rejection errors on asset APIs and downloads.
- 2026-09-14: Introduced two-stage topic-aware LLM query extraction, summarizing global transcript context to guide highly accurate per-scene visual queries.
- 2026-09-14: Massively improved visual render quality: implemented contiguous gap-free scene backgrounds, grouped subtitle words into natural readable lines anchored safely at the screen bottom, and exposed a 1080p 'Final Render' button in the frontend Editor.
