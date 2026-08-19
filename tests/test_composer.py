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


def expect_fail(source: str, needle: str, *, usb_control: bool = True) -> None:
    try:
        compose(source, usb_control=usb_control)
    except RuntimeError as exc:
        if needle not in str(exc):
            raise AssertionError(f"expected {needle!r} in error, got {exc!r}") from exc
        return
    raise AssertionError("composer unexpectedly accepted invalid source")


def main() -> int:
    out = compose(BASE)
    assert PROFILE_ID.endswith("/ESP32-r2")
    assert '#include "JanusPyramid117121DSP.h"' in out
    assert "#include <stdlib.h>" in out
    assert "#include <string.h>" in out
    assert "JanusPyramid117121DSP janusVoiceDsp;" in out
    assert "JANUS_PYRAMID_LANGUAGE_AMOUNT" in out
    assert "JANUS_PYRAMID_DSP_FAILSAFE" in out
    assert "JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP" in out
    assert "janusVoiceDsp.begin(EP_SAMPLE_RATE)" in out
    assert "janusVoiceDsp.setAmountPercent(JANUS_PYRAMID_LANGUAGE_AMOUNT)" in out
    assert "janusVoiceProcessChunk(chunk.mono, chunk.frames);" in out
    assert "janusVoiceSafetyTick();" in out
    assert "janusVoiceSerialControlTick();" in out
    assert "janusVoiceStatusTick();" in out
    assert "janusVoiceBudgetTrip" in out
    assert "janusVoiceOverBudgetStreak" in out
    assert "DSP_OVER_BUDGET" in out
    assert "DRY_BYPASS" in out
    assert "PYR=0..100" in out
    assert "PYR=OFF" in out
    assert "PYR=ON" in out
    assert "PYR?" in out
    assert "ENABLED_FAILSAFE_CLEARED" in out
    assert "dsp_ema_us" in out
    assert out.index("janusVoiceProcessChunk(chunk.mono, chunk.frames);") < out.index(
        "ep.write(chunk.mono, chunk.frames);"
    )
    assert out.index("janusVoiceSafetyTick();") < out.index("serialStatus();")
    assert out.index("janusVoiceSerialControlTick();") < out.index("serialStatus();")

    # Future base firmware may legitimately own the console. Default compose must
    # then stop instead of stealing bytes. Explicit no-USB mode keeps DSP,
    # telemetry, and the autonomous audio-budget failsafe.
    serial_owner = BASE.replace(
        "void serialStatus() {}",
        "void serialStatus() { if (Serial.available() > 0) { (void)Serial.read(); } }",
    )
    expect_fail(serial_owner, "USB Serial input ownership conflict")
    no_usb = compose(serial_owner, usb_control=False)
    assert "janusVoiceSerialControlTick" not in no_usb
    assert "PYR=0..100" not in no_usb
    assert "#include <stdlib.h>" not in no_usb
    assert "#include <string.h>" not in no_usb
    assert "janusVoiceProcessChunk(chunk.mono, chunk.frames);" in no_usb
    assert "janusVoiceSafetyTick();" in no_usb
    assert "janusVoiceStatusTick();" in no_usb
    assert "JANUS_PYRAMID_DSP_FAILSAFE" in no_usb
    assert "DSP_OVER_BUDGET" in no_usb
    assert "DISABLED_BY_COMPOSER" in no_usb

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
