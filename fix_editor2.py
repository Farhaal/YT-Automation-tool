with open('frontend/src/EditorView.tsx', 'r', encoding='utf-8') as f:
    e_content = f.read()

e_content = e_content.replace('{f.status ? "HTTP " : f.message}', '{f.status ? "HTTP " + f.status : f.message}')

with open('frontend/src/EditorView.tsx', 'w', encoding='utf-8') as f:
    f.write(e_content)
