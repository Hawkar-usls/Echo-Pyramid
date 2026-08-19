#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from compose_swarm_firmware import PROFILE_ID, compose  # noqa: E402


BASE = r'''#include <Arduino.h>
#include <M5EchoPyramid.h>
#define EP_SAMPLE_RATE 44100
#define JANUS_AUDIO_CHUNK_FRAMES 256
M5EchoPyramid ep;

struct Chunk { unsigned short frames; short mono[256]; } chunk;

void audio_task() {
  if (true) {
        ep.write(chunk.mono, chunk.frames);
  }
}

void initPyramid() {}
void serialStatus() {}

void setup() {
  initPyramid();
}

void loop() {
  serialStatus();
}
'''


def expect_fail(source: str, needle: str) -> None:
    try:
        compose(source)
    except RuntimeError as exc:
        if needle not in str(exc):
            raise AssertionError(f"expected {needle!r} in error, got {exc!r}") from exc
        return
    raise AssertionError("composer unexpectedly accepted invalid source")


def main() -> int:
    out = compose(BASE)
    assert PROFILE_ID.endswith("/ESP32-r2")
    assert '#include "JanusPyramid117121DSP.h"' in out
    assert "JanusPyramid117121DSP janusVoiceDsp;" in out
    assert "JANUS_PYRAMID_LANGUAGE_AMOUNT" in out
    assert "janusVoiceDsp.begin(EP_SAMPLE_RATE)" in out
    assert "janusVoiceDsp.setAmountPercent(JANUS_PYRAMID_LANGUAGE_AMOUNT)" in out
    assert "janusVoiceProcessChunk(chunk.mono, chunk.frames);" in out
    assert "janusVoiceStatusTick();" in out
    assert "dsp_ema_us" in out
    assert out.index("janusVoiceProcessChunk(chunk.mono, chunk.frames);") < out.index(
        "ep.write(chunk.mono, chunk.frames);"
    )

    expect_fail(BASE.replace("#include <M5EchoPyramid.h>\n", ""), "include")
    expect_fail(BASE.replace("M5EchoPyramid ep;", "M5EchoPyramid other;"), "global")
    expect_fail(BASE.replace("  initPyramid();\n", ""), "init")
    expect_fail(BASE.replace("        ep.write(chunk.mono, chunk.frames);\n", ""), "audio write")
    expect_fail(BASE.replace("  serialStatus();\n", ""), "loop status")
    expect_fail(BASE + "\n#include <M5EchoPyramid.h>\n", "include")
    expect_fail(out, "already contains")

    print("JANUS Echo-Pyramid composer tests PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
