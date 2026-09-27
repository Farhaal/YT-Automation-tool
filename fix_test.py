with open('backend/tests/test_hook.py', 'r') as f:
    content = f.read()

content = content.replace('''    # Word preservation
    words_out_hook = []
    for s in scenes_hook:
        words_out_hook.extend(s["_words"])
        # Min duration check:
        if s["id"] != scenes_hook[-1]["id"]: # not last scene
            dur = s["end"] - s["start"]
            assert dur >= 1.0, f"Min duration violated in hook logic: {dur}"
            
    assert len(words_out_hook) == len(words), "Not all words were preserved"
    for i in range(len(words)):
        assert words_out_hook[i]["word"] == words[i]["word"], "Word order violated"''', '''    # Word preservation
    words_out_text = []
    for s in scenes_hook:
        words_out_text.append(s["text"])
        # Min duration check:
        if s["id"] != scenes_hook[-1]["id"]: # not last scene
            dur = s["end"] - s["start"]
            assert dur >= 1.0, f"Min duration violated in hook logic: {dur}"
            
    assert " ".join(words_out_text) == " ".join(w["word"] for w in words), "Word order violated"''')

with open('backend/tests/test_hook.py', 'w') as f:
    f.write(content)
