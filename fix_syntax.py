with open('frontend/src/SettingsView.tsx', 'r', encoding='utf-8') as f:
    s_content = f.read()

s_content = s_content.replace('await fetch(http://localhost:8000/settings/ + provider, { method: \'DELETE\' });', 'await fetch("http://localhost:8000/settings/" + provider, { method: \'DELETE\' });')
s_content = s_content.replace('toast(Cleared config, "success");', 'toast("Cleared config", "success");')

with open('frontend/src/SettingsView.tsx', 'w', encoding='utf-8') as f:
    f.write(s_content)


with open('frontend/src/EditorView.tsx', 'r', encoding='utf-8') as f:
    e_content = f.read()

e_content = e_content.replace('? \AI queries used \ (others failed).\ ', '? AI queries used  (others failed).')
e_content = e_content.replace(': \All AI providers failed &mdash; used basic keyword extraction.\}', ': "All AI providers failed - used basic keyword extraction."}')
e_content = e_content.replace('<div key={i}>? {f.provider}/{f.model}: {f.status ? \HTTP \ : f.message}</div>', '<div key={i}> {f.provider}/{f.model}: {f.status ? HTTP  : f.message}</div>')

with open('frontend/src/EditorView.tsx', 'w', encoding='utf-8') as f:
    f.write(e_content)
