# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
