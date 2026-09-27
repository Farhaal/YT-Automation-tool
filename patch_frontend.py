import re

with open('frontend/src/CreatorView.tsx', 'r') as f:
    content = f.read()

# Add state
content = content.replace("const [pace, setPace] = useState('balanced');", "const [pace, setPace] = useState('balanced');\n  const [punchyHook, setPunchyHook] = useState('true');")

# Add to JSON payload
content = content.replace("pace\n        })", "pace,\n          punchy_hook: punchyHook === 'true'\n        })")

# Add to FormData
content = content.replace("fd.append('pace', pace);", "fd.append('pace', pace);\n    fd.append('punchy_hook', punchyHook);")

# Add to UI
ui_replacement = '''<div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Hook</label>
              <SegmentedControl 
                value={punchyHook}
                onChange={setPunchyHook}
                options={[
                  { label: 'Punchy (30s)', value: 'true' },
                  { label: 'Normal', value: 'false' }
                ]}
              />
            </div>
          </div>
        </div>
      </Card>'''

content = content.replace("</div>\n          </div>\n        </Card>", ui_replacement)

with open('frontend/src/CreatorView.tsx', 'w') as f:
    f.write(content)
