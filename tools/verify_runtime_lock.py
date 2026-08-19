#!/usr/bin/env python3
"""Verify that the pinned Voice-of-Janus runtime lock matches local firmware blobs.

This intentionally verifies Git *blob* SHA-1, not a plain file SHA-1, so values can
be compared directly with GitHub contents API blob SHAs.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "config" / "the_voice_of_janus.runtime_lock.json"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def require_hex40(value: object, label: str) -> str:
    text = str(value)
    if re.fullmatch(r"[0-9a-f]{40}", text) is None:
        raise AssertionError(f"{label} must be a 40-character lowercase hex SHA: {text!r}")
    return text


def verify_local_blob(lock_section: dict[str, object], path_key: str, sha_key: str) -> None:
    relative = Path(str(lock_section[path_key]))
    expected = require_hex40(lock_section[sha_key], sha_key)
    actual = git_blob_sha(ROOT / relative)
    if actual != expected:
        raise AssertionError(
            f"runtime lock drift for {relative}: expected Git blob {expected}, actual {actual}"
        )
    print(f"LOCK OK {relative} {actual}")


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if lock.get("status") != "ACTIVE_PINNED_LANGUAGE_RUNTIME":
        raise AssertionError("runtime lock must be ACTIVE_PINNED_LANGUAGE_RUNTIME")

    canonical = lock["canonical_language"]
    require_hex40(canonical["activation_blob_sha"], "activation_blob_sha")
    require_hex40(
        canonical["reference_implementation_blob_sha"],
        "reference_implementation_blob_sha",
    )
    if canonical["profile_id"] != "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3":
        raise AssertionError("unexpected canonical Pyramid Language profile id")

    embedded = lock["embedded_implementation"]
    if embedded.get("revision") != "ESP32-r2":
        raise AssertionError("embedded revision must be ESP32-r2")

    verify_local_blob(embedded, "voice_contract", "voice_contract_blob_sha")
    verify_local_blob(embedded, "profile_header", "profile_header_blob_sha")
    verify_local_blob(embedded, "dsp_header", "dsp_header_blob_sha")
    verify_local_blob(embedded, "composer", "composer_blob_sha")

    profile_text = (ROOT / str(embedded["profile_header"])).read_text(encoding="utf-8")
    if "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2" not in profile_text:
        raise AssertionError("profile header does not identify ESP32-r2")
    if "kAnchorCenterHz = 119.0f" not in profile_text:
        raise AssertionError("119 Hz anchor center missing from embedded profile")

    contract = json.loads((ROOT / str(embedded["voice_contract"])).read_text(encoding="utf-8"))
    dsp = contract["primary_dsp"]
    if dsp.get("language_version") != canonical["profile_id"]:
        raise AssertionError("voice contract language version disagrees with runtime lock")
    if dsp.get("embedded_revision") != embedded["revision"]:
        raise AssertionError("voice contract embedded revision disagrees with runtime lock")
    if dsp.get("anchor_band_hz") != [117.0, 121.0]:
        raise AssertionError("voice contract anchor band drifted")

    print("JANUS Echo-Pyramid runtime lock PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
