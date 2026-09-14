# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added "Export for Editor" feature to download an editable project zip (containing raw numbered clips, audio, properly formatted SRT subtitles, and an FCPXML project file) for native import into CapCut, DaVinci Resolve, and Premiere Pro.
- Added full 1080p final render functionality, exposed via the Editor UI, allowing users to switch between fast preview drafts and high-quality final outputs.
- Vastly accelerated asset search speeds by capping queries per scene (max 2), processing fast-tier providers (Pexels, Pixabay) first and skipping slow-tier providers upon success, and issuing searches concurrently.
- Added intelligent subtitle grouping (line-level captions) which chunks words into natural, readable phrases synced to the audio, significantly improving visual quality.
- Added gap-free visual layout rendering so that background clips remain contiguous and eliminate flashing black frames during audio pauses.
- Added two-stage topic-aware LLM query generation. When an LLM key is configured, the system first summarizes the global video context and injects it into per-scene queries, producing highly accurate, globally consistent search terms.

### Fixed
- Fixed 502 Bad Gateway errors on asset downloads (like Flickr-hosted Openverse images) and strict provider API rejections (Wikimedia) by passing a standard browser `User-Agent` header in all requests.
- Fixed API endpoint for Openverse provider to correctly follow redirects on `api.openverse.org`, and increased search timeout to 20.0s for improved reliability.
- Fixed robust fallback for Wikimedia provider to also safely follow HTTP redirects.
- Fixed test suites to strictly isolate `SETTINGS_PATH` inside `tmp_path`, guaranteeing local user data is untouched by test runs.
- Fixed crash in scene segmentation for users without an LLM key (removed stale `settings.USE_OLLAMA` reference that no longer exists in config).
- Fixed timing issue where LLM API keys saved in settings were not applied before scene segmentation, causing NLP to fall back to YAKE on a fresh backend process.
- Fixed GitHub Actions CI by correctly provisioning FFmpeg and spaCy models in the test runner.
- Fixed codebase linting errors and added strict, non-pedantic Ruff formatting configuration.

### Changed
- Improved asset search: Assets are now strictly prioritized by keyword relevance (token overlap with search query), ensuring highly accurate media selection. This relies on dynamically parsed descriptive tags from Pixabay and alt-text from Pexels.
- Wikimedia Commons is now treated exclusively as a fallback provider for unfilled gaps to improve quality and speed, and its search queries now utilize relevance sorting.

### Added
- Added optional user-provided LLM API key support (OpenAI-compatible) in Settings for smarter visual query extraction, with automatic fallback to local NLP.
- Support for selecting video aspect ratio (16:9 Landscape, 9:16 Portrait, 1:1 Square) in the frontend.
- Added UI toggle to disable Ken Burns motion for faster video generation.
- Optimized default FFmpeg encoder presets (`-preset p4` for NVENC, `-preset veryfast` for libx264).
- `WHISPER_MODEL` defaults to `small` for much faster transcription (configurable back to `large-v3` for accuracy).
- Backend timeline assembler now correctly defaults to 16:9 Landscape if not specified.
- Initial project scaffolding, documentation, and development tooling.

<!--
When you cut a release, move items from [Unreleased] into a new version section, e.g.:

## [0.2.0] - 2026-10-01
### Added
- Word-level transcription and alignment (sync core).
-->
