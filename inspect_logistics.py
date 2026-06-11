from pathlib import Path
import re
path = Path(r'c:\Users\Admin\AppData\Local\sins2\mods\RRR-updated\entities\vasari_rebel_rrr.player')
text = path.read_text(encoding='utf-8')
pattern = re.compile(r'"logistics"\s*:\s*\[', re.MULTILINE)
indices = [m.start() for m in pattern.finditer(text)]
print('logistics blocks:', len(indices))
for i, idx in enumerate(indices):
    start = idx
    level = 0
    in_string = False
    escape = False
    for j, ch in enumerate(text[start:], start):
        if ch == '"' and not escape:
            in_string = not in_string
        if ch == '\\' and not escape:
            escape = True
            continue
        escape = False
        if in_string:
            continue
        if ch == '[':
            level += 1
        elif ch == ']':
            level -= 1
            if level == 0:
                end = j + 1
                break
    block = text[start:end]
    values = re.findall(r'"max_planet_component_slots"\s*:\s*(\d+)', block)
    print(i+1, len(values), values)
    if i < 10:
        print(block[:500])
        print('---')
