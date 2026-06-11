import json
from pathlib import Path

path = Path(r'c:\Users\Admin\AppData\Local\sins2\mods\RRR-updated\entities\vasari_rebel_rrr.player')
with path.open('r', encoding='utf-8') as f:
    data = json.load(f)

changed = 0

def update_logistics(obj):
    global changed
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'logistics' and isinstance(value, list):
                slots = [entry.get('max_planet_component_slots') for entry in value if isinstance(entry, dict) and 'max_planet_component_slots' in entry]
                if slots:
                    # if there's an ascending progression, update based on first slot and index
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
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f'Updated {changed} max_planet_component_slots entries.')
else:
    print('No changes made.')
