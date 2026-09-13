# Contributing to OpenReel

Thanks for helping make free video creation available to everyone. Contributions of
all sizes are welcome — bug reports, docs, new asset providers, effects, and fixes.

## Ways to contribute

- Report bugs or request features via Issues (include your OS and steps to reproduce).
- Improve documentation.
- Add a new free asset provider, transition/effect, caption style, or language.
- Tackle an item from the roadmap in `BLUEPRINT.md`.

Please open an issue to discuss substantial changes before starting, so we can agree on
the approach.

## Development setup

Works the same on Windows and macOS. From the repo root:

```bash
# Backend (Python 3.11+)
# Windows (PowerShell):
python  -m venv .venv;  .venv\Scripts\Activate.ps1
# macOS / Linux:
python3 -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Frontend (Node 20+, added in the frontend phase)
cd frontend && npm install
```

Copy `.env.example` to `.env` and add your free Pexels / Pixabay keys.

Keep everything project-local: the virtual environment lives in `.venv/`, and models and
caches are written under the project folder (see `BLUEPRINT.md`). Nothing should be
installed globally or written outside the repo.

## Coding standards

- Python: format with `black`, lint with `ruff`, type-check with `mypy`. Add `pytest` tests
  for new logic.
- Frontend: `prettier` + `eslint`; add `vitest` tests where practical.
- Keep functions small and typed. Comments explain *why*, not *what*.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
  `docs:`, `refactor:`, `test:`, `chore:`. Imperative mood, no emojis.
- One focused change per pull request; describe what and why.
- Do not include AI-assistant attribution or generated boilerplate in code or commit
  messages — keep the history clean and human-readable.
- Ensure linters and tests pass before opening the PR.

## Licensing of contributions

By contributing, you agree that your contributions are licensed under the project's
[MIT License](LICENSE). If you add a dependency or asset source, note its license in the
PR and prefer permissive (MIT/BSD/Apache/CC0) options.
