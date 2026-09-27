with open('CHANGELOG.md', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('### Added\n', '### Added\n- Added multi-provider AI failover with drag-and-drop prioritization and robust retry/fallback mechanics.\n- Added \"Punchy Hook\" pacing option to automatically condense scene durations in the first 30 seconds for higher viewer retention.\n')
content = content.replace('## [Unreleased]\n\n### Added\n', '## [Unreleased]\n\n### Fixed\n- Fixed GPU acceleration for Whisper transcription on Windows by correctly discovering and injecting nvidia-cublas-cu12 runtime paths.\n\n### Added\n')

with open('CHANGELOG.md', 'w', encoding='utf-8') as f:
    f.write(content)
