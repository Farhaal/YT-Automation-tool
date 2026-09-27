with open('README.md', 'r') as f:
    content = f.read()

content = content.replace('- **GPU (optional):** an NVIDIA RTX with recent drivers/CUDA speeds up transcription and encoding.', '- **GPU (optional):** an NVIDIA RTX with recent drivers speeds up transcription and encoding. (The required CUDA runtime libraries for Windows are automatically fetched when you install requirements.txt).')

with open('README.md', 'w') as f:
    f.write(content)
