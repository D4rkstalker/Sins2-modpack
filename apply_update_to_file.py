import json
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Usage: python apply_update_to_file.py <path_to_player_file>')
    sys.exit(1)

p = Path(sys.argv[1])
if not p.exists():
    print('File not found:', p)
    sys.exit(1)

with p.open('r', encoding='utf-8') as f:
    data = json.load(f)

changed = 0

def update_logistics(obj):
    global changed
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'logistics' and isinstance(value, list):
                slots = [entry.get('max_planet_component_slots') for entry in value if isinstance(entry, dict) and 'max_planet_component_slots' in entry]
                if slots:
                    base = int(slots[0])
                    for idx, entry in enumerate(value):
                        if isinstance(entry, dict) and 'max_planet_component_slots' in entry:
                            new_val = min(base + idx, 6)
                            if entry['max_planet_component_slots'] != new_val:
                                entry['max_planet_component_slots'] = new_val
                                changed += 1
            else:
                update_logistics(value)
    elif isinstance(obj, list):
        for item in obj:
            update_logistics(item)

update_logistics(data)

if changed:
    with p.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f'Updated {changed} max_planet_component_slots entries in {p.name}.')
else:
    print(f'No changes made to {p.name}.')
