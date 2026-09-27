with open('frontend/src/SettingsView.tsx', 'r', encoding='utf-8') as f:
    s_content = f.read()

s_content = s_content.replace('export function SettingsView', 'export default function SettingsView')
s_content = s_content.replace('@/components/ui/card', './ui')
s_content = s_content.replace('@/components/ui/input', './ui')
s_content = s_content.replace('@/components/ui/button', './ui')
s_content = s_content.replace('@/components/ui/badge', './ui')
s_content = s_content.replace('@/hooks/use-toast', './ui')

# Fix implicitly any 'e'
s_content = s_content.replace('(e) =>', '(e: any) =>')

# Fix line 292
import re
s_content = re.sub(r'<span className="text-red-500">.*?</span>', '<span className="text-red-500">? {testStatus[p.provider].status ? "HTTP " + testStatus[p.provider].status : "Error"}: {testStatus[p.provider].msg}</span>', s_content)

with open('frontend/src/SettingsView.tsx', 'w', encoding='utf-8') as f:
    f.write(s_content)
