with open('frontend/src/EditorView.tsx', 'r', encoding='utf-8') as f:
    e_content = f.read()

e_content = e_content.replace('? AI queries used  (others failed).', '? "AI queries used (others failed)."')
e_content = e_content.replace('? HTTP  :', '? "HTTP " :')

with open('frontend/src/EditorView.tsx', 'w', encoding='utf-8') as f:
    f.write(e_content)

with open('frontend/src/SettingsView.tsx', 'r', encoding='utf-8') as f:
    s_content = f.read()
    
# Let's fix line 292 SettingsView
s_content = s_content.replace('className=\\"\\', 'className=\\"')
s_content = s_content.replace('w-4 h-4\ ', 'w-4 h-4"')

with open('frontend/src/SettingsView.tsx', 'w', encoding='utf-8') as f:
    f.write(s_content)

