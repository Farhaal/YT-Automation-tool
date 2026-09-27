import re

with open('backend/app/services/transcription.py', 'r') as f:
    content = f.read()

# Add the dll_directory injection before imports
imports_target = "import ctranslate2\nfrom faster_whisper import WhisperModel"
injection = '''import os
import sys

if sys.platform == "win32":
    try:
        import site
        sp_dirs = []
        if hasattr(site, 'getsitepackages'):
            sp_dirs.extend(site.getsitepackages())
        sp_dirs.append(os.path.join(sys.prefix, 'Lib', 'site-packages'))
        
        for sp in set(sp_dirs):
            for lib in ["cublas", "cudnn"]:
                bin_dir = os.path.join(sp, "nvidia", lib, "bin")
                if os.path.exists(bin_dir):
                    os.add_dll_directory(bin_dir)
    except Exception:
        pass

import ctranslate2
from faster_whisper import WhisperModel'''

content = content.replace(imports_target, injection)

# Update the log messages
content = content.replace('logger.info("Whisper model loaded successfully.")', 'logger.info(f"Whisper model loaded successfully. Using {device} {compute_type}.")')
content = content.replace('logger.info("Whisper model loaded successfully on CPU fallback.")', 'logger.info(f"Whisper model loaded successfully on CPU fallback. Using {device} {compute_type}.")')

with open('backend/app/services/transcription.py', 'w') as f:
    f.write(content)
