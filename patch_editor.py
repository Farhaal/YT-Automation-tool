import re

with open('frontend/src/EditorView.tsx', 'r') as f:
    content = f.read()

replacement = '''  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 pt-2">
      {job.llm_warning && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-4 rounded-lg flex items-start justify-between">
          <div className="flex gap-3 text-yellow-800 dark:text-yellow-400">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-sm">AI Provider Failover</h4>
              <p className="text-xs mt-1 leading-relaxed opacity-90">
                {job.llm_warning.used_provider 
                  ? \AI queries used \ (others failed).\ 
                  : \All AI providers failed &mdash; used basic keyword extraction.\}
                {' '}Check your keys/models in Settings and regenerate if needed.
              </p>
              {job.llm_warning.failed?.length > 0 && (
                <div className="mt-2 text-[10px] space-y-1 opacity-80 font-mono">
                  {job.llm_warning.failed.map((f: any, i: number) => (
                    <div key={i}>? {f.provider}/{f.model}: {f.status ? \HTTP \\ : f.message}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => {
            const t = {...job}; delete t.llm_warning; setJob(t);
          }} className="text-yellow-800 dark:text-yellow-400 hover:bg-yellow-100 dark:hover:bg-yellow-800/40 px-2 h-7">
            Dismiss
          </Button>
        </div>
      )}

      <div className="grid lg:grid-cols-12 gap-8 items-start">'''

target_str = '  return (\n    <div className="grid lg:grid-cols-12 gap-8 items-start animate-in fade-in slide-in-from-bottom-4 pt-2">'
new_content = content.replace(target_str, replacement)

# We also need to add a closing div tag before the final parenthesis of the return statement
# Wait, let's just find the closing parenthesis of the return.

# Find the end of EditorView
if '    </div>\n  );\n}\n' in new_content:
    new_content = new_content.replace('    </div>\n  );\n}\n', '    </div>\n    </div>\n  );\n}\n')
elif '    </div>\n  );\n}' in new_content:
    new_content = new_content.replace('    </div>\n  );\n}', '    </div>\n    </div>\n  );\n}')
else:
    # Append if not found easily
    new_content = new_content.replace('  );\n}', '    </div>\n  );\n}')

with open('frontend/src/EditorView.tsx', 'w') as f:
    f.write(new_content)
