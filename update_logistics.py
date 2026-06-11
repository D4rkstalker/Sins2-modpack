from pathlib import Path
import re
path = Path(r'c:\Users\Admin\AppData\Local\sins2\mods\RRR-updated\entities\vasari_rebel_rrr.player')
text = path.read_text(encoding='utf-8')

block_pattern = re.compile(r'("logistics"\s*:\s*\[)(.*?)(\])', re.DOTALL)
slot_pattern = re.compile(r'("max_planet_component_slots"\s*:\s*)(\d+)')

changed = 0

def replace_block(match):
    global changed
    prefix, body, suffix = match.groups()
    values = slot_pattern.findall(body)
    if not values:
        return match.group(0)
    base = int(values[0][1])
    new_values = [min(base + i, 6) for i in range(len(values))]
    if [int(v[1]) for v in values] == new_values:
        return match.group(0)
    idx = 0
    def repl(m):
        nonlocal idx
        replacement = f'{m.group(1)}{new_values[idx]}'
        idx += 1
        return replacement
    new_body = slot_pattern.sub(repl, body)
    changed += 1
    return prefix + new_body + suffix

new_text = block_pattern.sub(replace_block, text)
if changed == 0:
    print('No logistics blocks changed.')
else:
    path.write_text(new_text, encoding='utf-8')
    print(f'Updated {changed} logistics blocks.')
