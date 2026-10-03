# Contributing to OpenReel

Thanks for helping make free video creation available to everyone. Contributions of
all sizes are welcome — bug reports, docs, new asset providers, effects, and fixes.

## Ways to contribute

- Report bugs or request features via Issues (include your OS and steps to reproduce).
- Improve documentation.
- Add a new free asset provider, transition/effect, caption style, or language.
- Tackle an item from the Roadmap in `README.md`.

Please open an issue to discuss substantial changes before starting, so we can agree on
the approach.

## Development setup

Follow the setup steps in [README.md](README.md) (Python 3.11, Node.js 22 LTS, FFmpeg),
then install the dev tools:

```bash
pip install pytest ruff
```

Keep everything project-local: the virtual environment lives in `.venv/`, and models,
caches, jobs and settings are written under `data/` (git-ignored). Nothing should be
installed globally or written outside the repo.

## Checks to run before committing

```bash
ruff check .          # Python lint
pytest                # backend tests

cd frontend
npm run lint          # frontend lint (oxlint)
npm run test          # frontend tests (vitest)
npm run build         # type-check and build
```

The same checks run in CI on every push.

## Coding standards

- Python: lint with `ruff` (config in `pyproject.toml`). Add `pytest` tests for new logic;
  tests must not use real API keys, the network, or the real `data/` folder.
- Frontend: TypeScript + `oxlint`; add `vitest` tests where practical.
- Keep functions small and typed. Comments explain *why*, not *what*.
- Edit `requirements.txt` as plain UTF-8 in your editor — don't append to it with shell
  redirection (`>>` in Windows PowerShell writes UTF-16 and breaks `pip install`).
- Never commit throwaway helper scripts, API keys, `.env`, or anything under `data/`.
- Asset providers must make search requests through `AssetProvider._get_json()`, not
  `httpx.get` directly. That's what applies the request quotas, the 429 cooldown/failover and
  the search cache. Never log a URL that may contain a key; use `redact_url()` if you must.

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
