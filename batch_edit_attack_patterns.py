#!/usr/bin/env python3
"""
Batch-edit .unit JSON files using settings defined at the top of this file.

Edit the SETTINGS section below, then run:

    python fixed_unit_attack_pattern_mapper.py
"""

from __future__ import annotations

import codecs
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Iterable


# =============================================================================
# SETTINGS — EDIT THESE VALUES
# =============================================================================

# Folder containing the .unit files.
UNIT_DIRECTORY = Path(r"./entities")

# Search folders inside UNIT_DIRECTORY too.
SEARCH_SUBDIRECTORIES = True

# Preview changes without editing any files.
DRY_RUN = False

# Create a .bak copy before editing each file.
CREATE_BACKUPS = False


# =============================================================================
# FIXED ATTACK-PATTERN MAPPINGS
# =============================================================================

# Mapping order determines precedence if a unit has multiple matching tags.
TAG_TO_ATTACK_PATTERN: dict[str, dict] = {
    "frigate": {
        "type": "circle_strafe",
        "angle_range_off_gravity_well_plane": [-45.0, 45.0],
    },
    "cruiser": {
        "type": "circle_strafe",
        "angle_range_off_gravity_well_plane": [-45.0, 45.0],
    },
    "capital_ship": {
        "type": "circle_strafe",
        "angle_range_off_gravity_well_plane": [-45.0, 45.0],
    },
    "super_capital_ship": {
        "type": "circle_strafe",
        "angle_range_off_gravity_well_plane": [-45.0, 45.0],
    },
    "titan": {
        "type": "circle_strafe",
        "angle_range_off_gravity_well_plane": [-45.0, 45.0],
    },
}


# =============================================================================
# SCRIPT
# =============================================================================

def find_unit_files(directory: Path) -> Iterable[Path]:
    """Yield .unit files in a stable order."""
    iterator = directory.rglob("*.unit") if SEARCH_SUBDIRECTORIES else directory.glob("*.unit")
    yield from sorted((path for path in iterator if path.is_file()), key=str)


def read_utf8_json(path: Path) -> tuple[bytes, str, dict]:
    """Read a UTF-8 JSON file, allowing an optional UTF-8 BOM."""
    raw = path.read_bytes()

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"not valid UTF-8: {exc}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")

    return raw, text, data


def choose_attack_pattern(tags: object) -> tuple[str, dict, list[str]] | None:
    """
    Return the selected tag, its attack pattern, and all matching mapped tags.

    Tag matching is case-insensitive.
    """
    if not isinstance(tags, list):
        return None

    normalized_tags = {
        tag.casefold()
        for tag in tags
        if isinstance(tag, str)
    }

    matches = [
        (tag, attack_pattern)
        for tag, attack_pattern in TAG_TO_ATTACK_PATTERN.items()
        if tag.casefold() in normalized_tags
    ]

    if not matches:
        return None

    selected_tag, selected_pattern = matches[0]
    return selected_tag, selected_pattern, [tag for tag, _ in matches]


def detect_indentation(text: str) -> int:
    """Estimate the JSON indentation width used by the file."""
    for line in text.splitlines():
        stripped = line.lstrip(" ")
        if stripped and stripped != line:
            return len(line) - len(stripped)

    return 4


def detect_newline(text: str) -> str:
    """Return the newline convention used by the file."""
    return "\r\n" if "\r\n" in text else "\n"


def serialize_json_preserving_style(data: dict, original_text: str) -> str:
    """
    Serialize JSON using the source file's indentation and newline convention.

    This rewrites the whole JSON document, but preserves key order because
    Python dictionaries retain JSON insertion order.
    """
    indent = detect_indentation(original_text)
    newline = detect_newline(original_text)

    output = json.dumps(
        data,
        ensure_ascii=False,
        indent=indent,
    )

    if newline != "\n":
        output = output.replace("\n", newline)

    # Preserve whether the original file ended with a newline.
    if original_text.endswith(("\n", "\r")):
        output += newline

    return output


def write_atomic(path: Path, original_raw: bytes, new_text: str) -> None:
    """Safely replace a file while preserving a UTF-8 BOM if one existed."""
    had_bom = original_raw.startswith(codecs.BOM_UTF8)
    new_raw = (codecs.BOM_UTF8 if had_bom else b"") + new_text.encode("utf-8")

    file_mode = path.stat().st_mode
    temporary_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(new_raw)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.chmod(temporary_path, file_mode)
        os.replace(temporary_path, path)

    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def process_file(path: Path) -> str:
    """
    Process one .unit file.

    Returns:
        changed, unchanged, unmapped, or error
    """
    try:
        original_raw, original_text, data = read_utf8_json(path)

        selection = choose_attack_pattern(data.get("tags"))
        if selection is None:
            print(f"SKIP      {path} — no mapped tag")
            return "unmapped"

        selected_tag, new_pattern, all_matches = selection

        attack = data.get("attack")
        if not isinstance(attack, dict):
            raise ValueError('missing or invalid root "attack" object')

        old_pattern = attack.get("attack_pattern")
        if not isinstance(old_pattern, dict):
            raise ValueError('missing or invalid "attack.attack_pattern" object')

        if len(all_matches) > 1:
            print(
                f"WARNING   {path} — multiple mapped tags {all_matches}; "
                f"using {selected_tag!r}"
            )

        if old_pattern == new_pattern:
            print(
                f"UNCHANGED {path} — tag {selected_tag!r}, "
                f"pattern already {new_pattern['type']!r}"
            )
            return "unchanged"

        old_type = old_pattern.get("type", "<missing>")
        new_type = new_pattern["type"]

        # Replace the entire object so obsolete parameters are removed.
        attack["attack_pattern"] = new_pattern.copy()

        new_text = serialize_json_preserving_style(data, original_text)

        # Validate before writing.
        validated = json.loads(new_text)
        validated_pattern = (
            validated.get("attack", {})
            .get("attack_pattern")
        )

        if validated_pattern != new_pattern:
            raise ValueError("post-edit validation failed")

        if DRY_RUN:
            print(
                f"WOULD SET {path} — tag {selected_tag!r}: "
                f"{old_type!r} -> {new_type!r}"
            )
            return "changed"

        if CREATE_BACKUPS:
            backup_path = path.with_name(path.name + ".bak")

            if not backup_path.exists():
                shutil.copy2(path, backup_path)
                print(f"BACKUP    {backup_path}")
            else:
                print(f"BACKUP    {backup_path} already exists; keeping it")

        write_atomic(path, original_raw, new_text)

        print(
            f"UPDATED   {path} — tag {selected_tag!r}: "
            f"{old_type!r} -> {new_type!r}"
        )
        return "changed"

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR     {path} — {exc}", file=sys.stderr)
        return "error"


def main() -> int:
    directory = UNIT_DIRECTORY.expanduser()

    if not directory.is_absolute():
        directory = (Path(__file__).resolve().parent / directory).resolve()
    else:
        directory = directory.resolve()

    if not directory.exists():
        print(
            f"ERROR: UNIT_DIRECTORY does not exist:\n{directory}\n\n"
            "Edit UNIT_DIRECTORY near the top of this script.",
            file=sys.stderr,
        )
        return 2

    if not directory.is_dir():
        print(
            f"ERROR: UNIT_DIRECTORY is not a directory:\n{directory}",
            file=sys.stderr,
        )
        return 2

    files = list(find_unit_files(directory))

    if not files:
        print(f"No .unit files found in:\n{directory}")
        return 0

    print(f"Directory:             {directory}")
    print(f"Search subdirectories: {SEARCH_SUBDIRECTORIES}")
    print(f"Dry run:               {DRY_RUN}")
    print(f"Create backups:        {CREATE_BACKUPS}")
    print()
    print("Fixed mappings:")

    for tag, attack_pattern in TAG_TO_ATTACK_PATTERN.items():
        print(f"  {tag!r} -> {attack_pattern['type']!r}")

    print()

    counts = {
        "changed": 0,
        "unchanged": 0,
        "unmapped": 0,
        "error": 0,
    }

    for path in files:
        result = process_file(path)
        counts[result] += 1

    action = "would change" if DRY_RUN else "changed"

    print(
        "\nSummary: "
        f"{counts['changed']} {action}, "
        f"{counts['unchanged']} unchanged, "
        f"{counts['unmapped']} without mapped tags, "
        f"{counts['error']} errors."
    )

    return 1 if counts["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())