#!/usr/bin/env python3
"""Verify a checked-out canonical swarm sketch before composition.

The source lock stores Git blob SHA-1 values, so this check catches a branch-head
change that silently mutates the Pyramid sketch even when the path stays the same.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "config" / "sources.lock.json"


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify pinned JANUS swarm Pyramid source")
    parser.add_argument("sketch", type=Path)
    args = parser.parse_args()

    sketch = args.sketch.resolve()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    swarm = lock["swarm"]
    relative = "firmware/pyramid/ATOM_MATRIX_Pyramid.ino"
    expected = swarm["files"][relative]
    actual = git_blob_sha(sketch)
    if actual != expected:
        raise AssertionError(
            f"swarm source drift: expected Git blob {expected}, actual {actual}; "
            "review upstream and refresh config/sources.lock.json deliberately"
        )

    text = sketch.read_text(encoding="utf-8-sig")
    for anchor in swarm["integration_anchors"]:
        count = text.count(anchor)
        if count != 1:
            raise AssertionError(f"integration anchor count {count}, expected 1: {anchor!r}")

    serial_tokens = ("Serial.available(", "Serial.read(", "Serial.readString", "Serial.parseInt(")
    owners = [token for token in serial_tokens if token in text]
    expected_owner = bool(swarm.get("observed_serial_input_owner", False))
    if bool(owners) != expected_owner:
        raise AssertionError(
            f"Serial input ownership observation changed: expected_owner={expected_owner}, tokens={owners}"
        )

    print("JANUS swarm source lock PASS")
    print(f"Sketch:   {sketch}")
    print(f"Git blob: {actual}")
    print(f"Serial input owner: {bool(owners)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
