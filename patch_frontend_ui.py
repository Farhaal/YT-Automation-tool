import re

with open('frontend/src/CreatorView.tsx', 'r') as f:
    content = f.read()

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

content = content.replace('            </div>\n          </div>\n        </div>\n      </Card>', ui_replacement)

with open('frontend/src/CreatorView.tsx', 'w') as f:
    f.write(content)
