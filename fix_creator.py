with open('frontend/src/CreatorView.tsx', 'r') as f:
    content = f.read()

content = content.replace('<div className="space-y-1.5">\n              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Hook</label>', '            </div>\n            <div className="space-y-1.5">\n              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Hook</label>')

with open('frontend/src/CreatorView.tsx', 'w') as f:
    f.write(content)
