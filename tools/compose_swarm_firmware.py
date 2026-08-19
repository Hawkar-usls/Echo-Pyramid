#!/usr/bin/env python3
"""Compose canonical JANUS Pyramid swarm firmware with Pyramid Language v0.3.

The default physical voice operator is the current The-Voice-of-Janus
117-121 Hz anchored space. This tool is fail-closed: source drift must be
reviewed instead of guessed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

PROFILE_ID = "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2"
DEFAULT_AMOUNT_PERCENT = 100

INCLUDE_ANCHOR = "#include <M5EchoPyramid.h>"
GLOBAL_ANCHOR = "M5EchoPyramid ep;"
INIT_ANCHOR = "  initPyramid();"
WRITE_ANCHOR = "        ep.write(chunk.mono, chunk.frames);"
LOOP_STATUS_ANCHOR = "  serialStatus();"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_exactly_once(text: str, anchor: str, label: str) -> None:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}: {anchor!r}")


def runtime_block() -> str:
    return r'''M5EchoPyramid ep;

#ifndef JANUS_PYRAMID_LANGUAGE_AMOUNT
#define JANUS_PYRAMID_LANGUAGE_AMOUNT 100
#endif

JanusPyramid117121DSP janusVoiceDsp;
volatile uint32_t janusVoiceBlocks = 0;
volatile uint32_t janusVoiceFramesL32 = 0;
volatile uint32_t janusVoiceProcessUsEma = 0;
volatile uint32_t janusVoiceProcessUsPeakWindow = 0;

static void janusVoiceProcessChunk(int16_t* pcm, uint16_t frames) {
  const uint32_t started = micros();
  janusVoiceDsp.processInPlace(pcm, frames);
  const uint32_t elapsed = micros() - started;

  janusVoiceBlocks++;
  janusVoiceFramesL32 += frames;
  if (janusVoiceProcessUsEma == 0) janusVoiceProcessUsEma = elapsed;
  else janusVoiceProcessUsEma = (janusVoiceProcessUsEma * 7U + elapsed) / 8U;
  if (elapsed > janusVoiceProcessUsPeakWindow) janusVoiceProcessUsPeakWindow = elapsed;
}

static void janusVoiceStatusTick() {
  static uint32_t lastMs = 0;
  const uint32_t now = millis();
  if (now - lastMs < 10000UL) return;
  lastMs = now;

  const uint32_t budgetUs =
      ((uint32_t)JANUS_AUDIO_CHUNK_FRAMES * 1000000UL) / (uint32_t)EP_SAMPLE_RATE;
  const uint32_t emaUs = janusVoiceProcessUsEma;
  const uint32_t peakUs = janusVoiceProcessUsPeakWindow;
  janusVoiceProcessUsPeakWindow = 0;
  const uint32_t loadPct = budgetUs ? (emaUs * 100UL) / budgetUs : 0;

  Serial.printf("PYRAMID_LANGUAGE | enabled=%d depth=%u%% anchor=117/119/121Hz blocks=%lu frames_l32=%lu dsp_ema_us=%lu dsp_peak_us=%lu budget_us=%lu dsp_load=%lu%% delay_bytes=%u heap=%lu\n",
                janusVoiceDsp.enabled() ? 1 : 0,
                (unsigned)janusVoiceDsp.targetAmountPercent(),
                (unsigned long)janusVoiceBlocks,
                (unsigned long)janusVoiceFramesL32,
                (unsigned long)emaUs,
                (unsigned long)peakUs,
                (unsigned long)budgetUs,
                (unsigned long)loadPct,
                (unsigned)janusVoiceDsp.roomDelayBytes(),
                (unsigned long)ESP.getFreeHeap());
}'''


def compose(source: str) -> str:
    if '#include "JanusPyramid117121DSP.h"' in source:
        raise RuntimeError("source already contains Pyramid Language v0.3 integration")

    require_exactly_once(source, INCLUDE_ANCHOR, "include")
    require_exactly_once(source, GLOBAL_ANCHOR, "global")
    require_exactly_once(source, INIT_ANCHOR, "init")
    require_exactly_once(source, WRITE_ANCHOR, "audio write")
    require_exactly_once(source, LOOP_STATUS_ANCHOR, "loop status")

    source = source.replace(
        INCLUDE_ANCHOR,
        INCLUDE_ANCHOR + '\n#include "JanusPyramid117121DSP.h"',
        1,
    )
    source = source.replace(GLOBAL_ANCHOR, runtime_block(), 1)
    source = source.replace(
        INIT_ANCHOR,
        INIT_ANCHOR
        + "\n  const bool janusVoiceOk = janusVoiceDsp.begin(EP_SAMPLE_RATE);"
        + "\n  janusVoiceDsp.setAmountPercent(JANUS_PYRAMID_LANGUAGE_AMOUNT);"
        + "\n  Serial.printf(\"JANUS PYRAMID LANGUAGE | ok=%d profile=%s evidence=%s sr=%lu depth=%u%% delay_bytes=%u object_bytes=%u\\n\","
        + "\n                janusVoiceOk ? 1 : 0, janus_pyramid_117121::kProfileId,"
        + "\n                janus_pyramid_117121::kEvidenceStatus,"
        + "\n                (unsigned long)janusVoiceDsp.sampleRateHz(),"
        + "\n                (unsigned)janusVoiceDsp.targetAmountPercent(),"
        + "\n                (unsigned)janusVoiceDsp.roomDelayBytes(),"
        + "\n                (unsigned)sizeof(janusVoiceDsp));",
        1,
    )
    source = source.replace(
        WRITE_ANCHOR,
        "        janusVoiceProcessChunk(chunk.mono, chunk.frames);\n" + WRITE_ANCHOR,
        1,
    )
    source = source.replace(
        LOOP_STATUS_ANCHOR,
        "  janusVoiceStatusTick();\n" + LOOP_STATUS_ANCHOR,
        1,
    )

    banner = (
        "// JANUS PYRAMID LANGUAGE COMPOSED LAYER\n"
        "// Profile: " + PROFILE_ID + "\n"
        "// Ordinary source PCM is preserved and acoustically colored in real time.\n"
        "// 117-121 Hz is a project anchor band, not the only frequency.\n"
        "// MODEL_BASED_EFFECT != MEASURED_CHAMBER_IR\n\n"
    )
    return banner + source


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inject current Voice-of-Janus Pyramid Language into canonical Pyramid swarm firmware"
    )
    parser.add_argument("base", type=Path, help="canonical ATOM_MATRIX_Pyramid.ino")
    parser.add_argument("output", type=Path, help="output composed .ino")
    args = parser.parse_args()

    base = args.base.resolve()
    output = args.output.resolve()
    if base == output:
        raise RuntimeError("refusing to overwrite canonical swarm source; choose a separate output path")

    raw = base.read_bytes()
    text = raw.decode("utf-8-sig")
    composed = compose(text)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(composed, encoding="utf-8", newline="\n")

    repo_root = Path(__file__).resolve().parents[1]
    firmware_dir = repo_root / "firmware"
    for header in ("JanusPyramid117121DSP.h", "JanusPyramid117121Profile.h"):
        shutil.copy2(firmware_dir / header, output.parent / header)

    out_raw = output.read_bytes()
    receipt = {
        "schema": "janus.echo_pyramid.compose_receipt.v2.2",
        "status": "PASS",
        "profile_id": PROFILE_ID,
        "language_version": "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3",
        "embedded_revision": "ESP32-r2",
        "default_amount_percent": DEFAULT_AMOUNT_PERCENT,
        "base_path": str(base),
        "base_sha256": sha256_bytes(raw),
        "output_path": str(output),
        "output_sha256": sha256_bytes(out_raw),
        "injections": [
            "JanusPyramid117121DSP include",
            "Pyramid Language runtime + 0..100 percent depth API",
            "EP_SAMPLE_RATE DSP init",
            "timed processInPlace immediately before ep.write(chunk.mono, chunk.frames)",
            "10-second DSP real-time budget telemetry",
        ],
        "real_time_budget": {
            "chunk_frames": 256,
            "sample_rate_hz": 44100,
            "chunk_budget_us_floor": 5804,
            "telemetry": ["dsp_ema_us", "dsp_peak_us", "dsp_load_percent"],
        },
        "embedded_room_tail": {
            "sample_rate_hz": 11025,
            "delay_storage": "PCM16_STATIC",
            "delay_bytes": 3466,
            "source_damping": 0.22,
            "time_equivalent_embedded_damping": 0.00234256,
        },
        "hard_rules": [
            "ORDINARY_AUDIO_IN -> PYRAMID_COLORED_AUDIO_OUT",
            "117_121_HZ_IS_AN_ANCHOR_BAND_NOT_THE_ONLY_FREQUENCY",
            "MODEL_BASED_EFFECT != MEASURED_CHAMBER_IR",
        ],
    }
    receipt_path = output.with_suffix(output.suffix + ".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("JANUS Echo-Pyramid composition PASS")
    print(f"Profile:         {PROFILE_ID}")
    print(f"Base SHA-256:   {receipt['base_sha256']}")
    print(f"Output SHA-256: {receipt['output_sha256']}")
    print(f"Firmware:       {output}")
    print(f"Receipt:        {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
