with open('frontend/src/SettingsView.tsx', 'r', encoding='utf-8') as f:
    s = f.read()

s = s.replace('size="icon"', 'size="sm"')
s = s.replace('variant="outline"', 'variant="secondary"')

with open('frontend/src/SettingsView.tsx', 'w', encoding='utf-8') as f:
    f.write(s)
