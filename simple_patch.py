with open('backend/app/services/verification.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line == '        "representing video/image candidates.\n':
        new_lines.append('        "representing video/image candidates.\\n\\n"\n')
    elif line == '\n' and new_lines and new_lines[-1] == '        "representing video/image candidates.\\n\\n"\n':
        pass
    elif line == '        "Return STRICTLY a JSON object with this exact schema (no markdown, no quotes around the json):\n':
        new_lines.append('        "Return STRICTLY a JSON object with this exact schema (no markdown, no quotes around the json):\\n"\n')
    elif line == '        "{\n':
        new_lines.append('        "{\\n"\n')
    elif line == '        \'  "best_index": <int>,\n':
        new_lines.append('        \'  "best_index": <int>,\\n\'\n')
    elif line == '        \'  "score": <float between 0.0 and 1.0, where 1.0 is perfect match>,\n':
        new_lines.append('        \'  "score": <float between 0.0 and 1.0, where 1.0 is perfect match>,\\n\'\n')
    elif line == '        \'  "reason": "<str: brief 1-sentence explanation of why it fits>"\n':
        new_lines.append('        \'  "reason": "<str: brief 1-sentence explanation of why it fits>"\\n\'\n')
    elif line == '        {"type": "text", "text": f"Video Topic: {topic}\n':
        new_lines.append('        {"type": "text", "text": f"Video Topic: {topic}\\nScene Text: {scene_text}\\n\\nCandidates:"}\n')
    elif line == 'Scene Text: {scene_text}\n':
        pass
    elif line == '\nCandidates:"}\n':
        pass
    else:
        new_lines.append(line)

with open('backend/app/services/verification.py', 'w') as f:
    f.writelines(new_lines)
