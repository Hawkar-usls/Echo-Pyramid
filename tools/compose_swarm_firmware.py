#!/usr/bin/env python3
"""Compose the canonical JANUS Pyramid swarm firmware with Voice-of-Janus DSP.

This tool is intentionally fail-closed. It does not guess when integration anchors
move: source drift must be reviewed and the composer updated explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

PROFILE_ID = "GREAT-PYRAMID-KINGS-CHAMBER-EXAMPLE-v0.1/ESP32-LIVE-6"

INCLUDE_ANCHOR = "#include <M5EchoPyramid.h>"
GLOBAL_ANCHOR = "M5EchoPyramid ep;"
INIT_ANCHOR = "  initPyramid();"
WRITE_ANCHOR = "        ep.write(chunk.mono, chunk.frames);"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_exactly_once(text: str, anchor: str, label: str) -> None:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}: {anchor!r}")


def compose(source: str) -> str:
    if '#include "JanusPyramidDSP.h"' in source:
        raise RuntimeError("source already contains JanusPyramidDSP integration")

    require_exactly_once(source, INCLUDE_ANCHOR, "include")
    require_exactly_once(source, GLOBAL_ANCHOR, "global")
    require_exactly_once(source, INIT_ANCHOR, "init")
    require_exactly_once(source, WRITE_ANCHOR, "audio write")

    source = source.replace(
        INCLUDE_ANCHOR,
        INCLUDE_ANCHOR + '\n#include "JanusPyramidDSP.h"',
        1,
    )
    source = source.replace(
        GLOBAL_ANCHOR,
        GLOBAL_ANCHOR + "\nJanusPyramidDSP janusVoiceDsp;",
        1,
    )
    source = source.replace(
        INIT_ANCHOR,
        INIT_ANCHOR
        + "\n  const bool janusVoiceOk = janusVoiceDsp.begin(EP_SAMPLE_RATE);"
        + "\n  Serial.printf(\"JANUS VOICE DSP | ok=%d profile=%s evidence=%s sr=%lu\\n\","
        + "\n                janusVoiceOk ? 1 : 0, janus_voice::kProfileId, janus_voice::kEvidenceStatus,"
        + "\n                (unsigned long)janusVoiceDsp.sampleRateHz());",
        1,
    )
    source = source.replace(
        WRITE_ANCHOR,
        "        janusVoiceDsp.processInPlace(chunk.mono, chunk.frames);\n" + WRITE_ANCHOR,
        1,
    )

    banner = (
        "// JANUS VOICE COMPOSED LAYER\n"
        "// Profile: " + PROFILE_ID + "\n"
        "// MODEL_BASED_RECONSTRUCTION != MEASURED_HISTORICAL_SOUND\n\n"
    )
    return banner + source


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject Voice-of-Janus DSP into canonical Pyramid swarm firmware")
    parser.add_argument("base", type=Path, help="canonical ATOM_MATRIX_Pyramid.ino")
    parser.add_argument("output", type=Path, help="output composed .ino")
    args = parser.parse_args()

    base = args.base.resolve()
    output = args.output.resolve()
    if base == output:
        raise RuntimeError("refusing to overwrite canonical swarm source; choose a separate output path")

    raw = base.read_bytes()
    # Current swarm sketch carries an optional UTF-8 BOM; utf-8-sig handles both forms.
    text = raw.decode("utf-8-sig")
    composed = compose(text)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(composed, encoding="utf-8", newline="\n")

    repo_root = Path(__file__).resolve().parents[1]
    firmware_dir = repo_root / "firmware"
    for header in ("JanusPyramidDSP.h", "JanusPyramidVoiceProfile.h"):
        shutil.copy2(firmware_dir / header, output.parent / header)

    out_raw = output.read_bytes()
    receipt = {
        "schema": "janus.echo_pyramid.compose_receipt.v1",
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "base_path": str(base),
        "base_sha256": sha256_bytes(raw),
        "output_path": str(output),
        "output_sha256": sha256_bytes(out_raw),
        "injections": [
            "JanusPyramidDSP include",
            "JanusPyramidDSP global instance",
            "EP_SAMPLE_RATE DSP init",
            "processInPlace immediately before ep.write(chunk.mono, chunk.frames)",
        ],
        "hard_rule": "MODEL_BASED_RECONSTRUCTION != MEASURED_HISTORICAL_SOUND",
    }
    receipt_path = output.with_suffix(output.suffix + ".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("JANUS Echo-Pyramid composition PASS")
    print(f"Base SHA-256:   {receipt['base_sha256']}")
    print(f"Output SHA-256: {receipt['output_sha256']}")
    print(f"Firmware:       {output}")
    print(f"Receipt:        {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
