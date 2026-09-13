# Start Here — the one prompt that kicks off the build

Open the `openreel/` folder in Antigravity and paste the prompt below into a fresh chat.
It makes the agent **read every project file, confirm the plan, and wait** — then, once you
reply `go`, it builds **Phase 0**. After that, drive the build one phase at a time using the
phase prompts in `ANTIGRAVITY_GUIDE.md` (section 3).

If a session ever ends early (model/usage limit), use the **Resume prompt** in
`ANTIGRAVITY_GUIDE.md` (section 2) instead — it reads `PROGRESS.md` + git and continues.

Keep this file in `dev/` — it's local build scaffolding and is gitignored.

---

```
You are helping build OpenReel: a free, open-source, fully-local desktop app that turns a
script into a finished, edited video. This folder is the entire project. Work carefully and
step by step, and never guess when a decision is already written down in the docs.

── STEP 1 — READ EVERYTHING FIRST (do not write or change any file yet) ──
Read these files in full before doing anything else:
  • dev/BLUEPRINT.md          — the complete technical plan, architecture, and phases
  • dev/ANTIGRAVITY_GUIDE.md  — the build guide, per-phase prompts, and project rules
  • dev/PROGRESS.md           — build state / resume tracker
  • README.md, CONTRIBUTING.md, CHANGELOG.md, LICENSE
  • requirements.txt, .env.example, .gitignore, .github/pull_request_template.md

── NON-NEGOTIABLE RULES (apply to every step of the whole build) ──
  1. This folder is the whole project root. Everything — code, the virtual environment,
     models, caches, downloads, and renders — must stay INSIDE it. Never write to the home
     drive, C:\, or any global/default location.
  2. Use a project-local virtual environment at ./.venv. Never install Python packages
     globally; activate .venv before any install.
  3. Add backend/app/core/paths.py that, BEFORE importing any ML library, points HF_HOME,
     TORCH_HOME, and XDG_CACHE_HOME at ./data and creates
     ./data/{models,cache,downloads,renders,tmp}.
  4. Cross-platform: behave identically on Windows and macOS. Use pathlib; no OS-specific or
     hard-coded paths.
  5. Keep the repo clean and public-ready: NO AI attribution anywhere — no "generated with",
     no "Co-Authored-By", no assistant names — in code, comments, or commit messages. Use
     Conventional Commits (feat:, fix:, docs:, chore:, refactor:, test:).
  6. The copyright/author name everywhere is "Farhaal".
  7. The dev/ folder is gitignored (it is build scaffolding). Never commit it.
  8. Build ONE phase at a time. At the end of each phase, update dev/PROGRESS.md (tick the
     box, set the new Current phase + Next action, add a dated Log line) and commit — so the
     build can resume cleanly if a session ever stops early.

── STEP 2 — REPORT BACK, THEN WAIT ──
After reading, and WITHOUT creating or changing any files yet, reply to me with:
  a. One paragraph: what OpenReel is and how the pipeline works (voice OR text →
     words + timings → scenes → matched free footage → synced timeline → render → export).
  b. The exact folder/monorepo structure you will create (from BLUEPRINT §2).
  c. Confirmation that you understand and will follow all 8 rules above.
  d. Your P0 plan and its "Done when", plus which free API keys I need to obtain.
  e. Anything unclear, conflicting, or risky in the docs.
Then STOP and wait for me to reply "go". Do not write any code until I do.

── STEP 3 — ON "go", EXECUTE P0 (Foundation) ──
When I reply "go", carry out the P0 tasks exactly as specified in dev/ANTIGRAVITY_GUIDE.md
(section 3): create the monorepo (backend/, renderer/, frontend/, shared/, docs/, scripts/,
samples/); set up ./.venv and install requirements.txt + `python -m spacy download
en_core_web_sm`; add tooling (ruff, black, mypy, pytest, pre-commit) and CI
(.github/workflows/ci.yml running ruff + pytest); generate a clean, public-facing
docs/ARCHITECTURE.md derived from the blueprint with NO mention of AI tools or the build
process; add scripts/check_env.py; verify the public files (LICENSE shows "Farhaal"); then
initialize git with one clean commit "chore: initialize repository" on main, confirm dev/ is
NOT tracked, and update dev/PROGRESS.md.
Then stop and show me: the folder tree, the output of check_env.py, and git log --oneline.
Do not continue to P1 until I confirm.
```
