#!/usr/bin/env python3
"""Compose canonical JANUS Pyramid swarm firmware with Pyramid Language v0.3.

The default physical voice operator is the current The-Voice-of-Janus
117-121 Hz anchored space. This tool is fail-closed: source drift, console
ownership conflicts, and real-time audio budget overruns are handled explicitly.
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
SERIAL_INPUT_TOKENS = ("Serial.available(", "Serial.read(", "Serial.readString", "Serial.parseInt(")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_exactly_once(text: str, anchor: str, label: str) -> None:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}: {anchor!r}")


def serial_input_owners(source: str) -> list[str]:
    return [token for token in SERIAL_INPUT_TOKENS if token in source]


def runtime_block(*, usb_control: bool) -> str:
    common = r'''M5EchoPyramid ep;

#ifndef JANUS_PYRAMID_LANGUAGE_AMOUNT
#define JANUS_PYRAMID_LANGUAGE_AMOUNT 100
#endif

#ifndef JANUS_PYRAMID_DSP_FAILSAFE
#define JANUS_PYRAMID_DSP_FAILSAFE 1
#endif

#ifndef JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP
#define JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP 3
#endif

JanusPyramid117121DSP janusVoiceDsp;
volatile uint32_t janusVoiceBlocks = 0;
volatile uint32_t janusVoiceFramesL32 = 0;
volatile uint32_t janusVoiceProcessUsEma = 0;
volatile uint32_t janusVoiceProcessUsPeakWindow = 0;
volatile bool janusVoiceBudgetTrip = false;
volatile uint8_t janusVoiceOverBudgetStreak = 0;
volatile uint32_t janusVoiceFailsafeTrips = 0;

static void janusVoiceProcessChunk(int16_t* pcm, uint16_t frames) {
  janusVoiceBlocks++;
  janusVoiceFramesL32 += frames;

  // Once the real-time guard trips, leave the queued source PCM untouched.
  // The main loop performs the one-time state reset outside this audio task.
  if (janusVoiceBudgetTrip || !janusVoiceDsp.enabled() || !pcm || frames == 0) return;

  const uint32_t budgetUs =
      ((uint32_t)frames * 1000000UL) / (uint32_t)EP_SAMPLE_RATE;
  const uint32_t started = micros();
  janusVoiceDsp.processInPlace(pcm, frames);
  const uint32_t elapsed = micros() - started;

  if (janusVoiceProcessUsEma == 0) janusVoiceProcessUsEma = elapsed;
  else janusVoiceProcessUsEma = (janusVoiceProcessUsEma * 7U + elapsed) / 8U;
  if (elapsed > janusVoiceProcessUsPeakWindow) janusVoiceProcessUsPeakWindow = elapsed;

#if JANUS_PYRAMID_DSP_FAILSAFE
  if (budgetUs > 0 && elapsed >= budgetUs) {
    if (janusVoiceOverBudgetStreak < 255U) janusVoiceOverBudgetStreak++;
    if (janusVoiceOverBudgetStreak >= JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP) {
      janusVoiceBudgetTrip = true;
      janusVoiceFailsafeTrips++;
      janusVoiceOverBudgetStreak = 0;
    }
  } else {
    janusVoiceOverBudgetStreak = 0;
  }
#endif
}

static void janusVoiceSafetyTick() {
#if JANUS_PYRAMID_DSP_FAILSAFE
  if (janusVoiceBudgetTrip && janusVoiceDsp.enabled()) {
    // Reset resonator/delay state outside the audio playback task. Future chunks
    // remain dry until an explicit local PYR=ON or a reboot clears the trip.
    janusVoiceDsp.setEnabled(false);
    Serial.printf("PYRAMID_LANGUAGE_FAILSAFE | DRY_BYPASS reason=DSP_OVER_BUDGET trips=%lu peak_us=%lu\n",
                  (unsigned long)janusVoiceFailsafeTrips,
                  (unsigned long)janusVoiceProcessUsPeakWindow);
  }
#endif
}
'''

    usb = r'''
char janusVoiceSerialBuf[24] = {0};
uint8_t janusVoiceSerialLen = 0;

static void janusVoicePrintControlState(const char* reason) {
  Serial.printf("PYRAMID_LANGUAGE_CONTROL | %s enabled=%d depth=%u%% failsafe=%d trips=%lu profile=%s\n",
                reason ? reason : "STATE",
                janusVoiceDsp.enabled() ? 1 : 0,
                (unsigned)janusVoiceDsp.targetAmountPercent(),
                janusVoiceBudgetTrip ? 1 : 0,
                (unsigned long)janusVoiceFailsafeTrips,
                janus_pyramid_117121::kProfileId);
}

static void janusVoiceApplySerialCommand(const char* cmd) {
  if (!cmd || !cmd[0]) return;

  if (strcmp(cmd, "PYR?") == 0) {
    janusVoicePrintControlState("QUERY");
    return;
  }
  if (strcmp(cmd, "PYR=OFF") == 0) {
    janusVoiceDsp.setEnabled(false);
    janusVoicePrintControlState("HARD_BYPASS");
    return;
  }
  if (strcmp(cmd, "PYR=ON") == 0) {
    janusVoiceBudgetTrip = false;
    janusVoiceOverBudgetStreak = 0;
    janusVoiceProcessUsEma = 0;
    janusVoiceProcessUsPeakWindow = 0;
    janusVoiceDsp.setEnabled(true);
    janusVoicePrintControlState("ENABLED_FAILSAFE_CLEARED");
    return;
  }
  if (strncmp(cmd, "PYR=", 4) == 0) {
    char* end = nullptr;
    long value = strtol(cmd + 4, &end, 10);
    if (end && *end == '\0' && value >= 0 && value <= 100) {
      janusVoiceDsp.setAmountPercent((uint8_t)value);
      janusVoicePrintControlState("DEPTH_SET");
      return;
    }
  }

  Serial.printf("PYRAMID_LANGUAGE_CONTROL | INVALID command=%s expected=PYR? | PYR=0..100 | PYR=ON | PYR=OFF\n", cmd);
}

static void janusVoiceSerialControlTick() {
  while (Serial.available() > 0) {
    const char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      if (janusVoiceSerialLen > 0) {
        janusVoiceSerialBuf[janusVoiceSerialLen] = '\0';
        janusVoiceApplySerialCommand(janusVoiceSerialBuf);
        janusVoiceSerialLen = 0;
      }
      continue;
    }

    if (c >= 32 && c <= 126) {
      if (janusVoiceSerialLen + 1U < sizeof(janusVoiceSerialBuf)) {
        janusVoiceSerialBuf[janusVoiceSerialLen++] = c;
      } else {
        janusVoiceSerialLen = 0;
        Serial.println("PYRAMID_LANGUAGE_CONTROL | INPUT_OVERFLOW");
      }
    }
  }
}
'''

    status = r'''
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

  Serial.printf("PYRAMID_LANGUAGE | enabled=%d depth=%u%% failsafe=%d trips=%lu anchor=117/119/121Hz blocks=%lu frames_l32=%lu dsp_ema_us=%lu dsp_peak_us=%lu budget_us=%lu dsp_load=%lu%% delay_bytes=%u heap=%lu\n",
                janusVoiceDsp.enabled() ? 1 : 0,
                (unsigned)janusVoiceDsp.targetAmountPercent(),
                janusVoiceBudgetTrip ? 1 : 0,
                (unsigned long)janusVoiceFailsafeTrips,
                (unsigned long)janusVoiceBlocks,
                (unsigned long)janusVoiceFramesL32,
                (unsigned long)emaUs,
                (unsigned long)peakUs,
                (unsigned long)budgetUs,
                (unsigned long)loadPct,
                (unsigned)janusVoiceDsp.roomDelayBytes(),
                (unsigned long)ESP.getFreeHeap());
}'''
    return common + (usb if usb_control else "") + status


def compose(source: str, *, usb_control: bool = True) -> str:
    if '#include "JanusPyramid117121DSP.h"' in source:
        raise RuntimeError("source already contains Pyramid Language v0.3 integration")

    require_exactly_once(source, INCLUDE_ANCHOR, "include")
    require_exactly_once(source, GLOBAL_ANCHOR, "global")
    require_exactly_once(source, INIT_ANCHOR, "init")
    require_exactly_once(source, WRITE_ANCHOR, "audio write")
    require_exactly_once(source, LOOP_STATUS_ANCHOR, "loop status")

    if usb_control:
        owners = serial_input_owners(source)
        if owners:
            raise RuntimeError(
                "USB Serial input ownership conflict: base firmware already consumes Serial input "
                f"via {owners!r}; review ownership or compose with --no-usb-control"
            )

    extra_includes = '\n#include "JanusPyramid117121DSP.h"'
    if usb_control:
        extra_includes += "\n#include <stdlib.h>\n#include <string.h>"
    source = source.replace(INCLUDE_ANCHOR, INCLUDE_ANCHOR + extra_includes, 1)
    source = source.replace(GLOBAL_ANCHOR, runtime_block(usb_control=usb_control), 1)

    init_text = (
        INIT_ANCHOR
        + "\n  const bool janusVoiceOk = janusVoiceDsp.begin(EP_SAMPLE_RATE);"
        + "\n  janusVoiceDsp.setAmountPercent(JANUS_PYRAMID_LANGUAGE_AMOUNT);"
        + "\n  Serial.printf(\"JANUS PYRAMID LANGUAGE | ok=%d profile=%s evidence=%s sr=%lu depth=%u%% failsafe=%d trip_blocks=%u delay_bytes=%u object_bytes=%u\\n\","
        + "\n                janusVoiceOk ? 1 : 0, janus_pyramid_117121::kProfileId,"
        + "\n                janus_pyramid_117121::kEvidenceStatus,"
        + "\n                (unsigned long)janusVoiceDsp.sampleRateHz(),"
        + "\n                (unsigned)janusVoiceDsp.targetAmountPercent(),"
        + "\n                (unsigned)JANUS_PYRAMID_DSP_FAILSAFE,"
        + "\n                (unsigned)JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP,"
        + "\n                (unsigned)janusVoiceDsp.roomDelayBytes(),"
        + "\n                (unsigned)sizeof(janusVoiceDsp));"
    )
    if usb_control:
        init_text += "\n  Serial.println(\"Pyramid Language USB control: PYR? | PYR=0..100 | PYR=ON | PYR=OFF\");"
    else:
        init_text += "\n  Serial.println(\"Pyramid Language USB control: DISABLED_BY_COMPOSER\");"
    source = source.replace(INIT_ANCHOR, init_text, 1)

    source = source.replace(
        WRITE_ANCHOR,
        "        janusVoiceProcessChunk(chunk.mono, chunk.frames);\n" + WRITE_ANCHOR,
        1,
    )

    loop_prefix = "  janusVoiceSafetyTick();\n  janusVoiceStatusTick();\n"
    if usb_control:
        loop_prefix = "  janusVoiceSafetyTick();\n  janusVoiceSerialControlTick();\n  janusVoiceStatusTick();\n"
    source = source.replace(LOOP_STATUS_ANCHOR, loop_prefix + LOOP_STATUS_ANCHOR, 1)

    banner = (
        "// JANUS PYRAMID LANGUAGE COMPOSED LAYER\n"
        "// Profile: " + PROFILE_ID + "\n"
        "// Ordinary source PCM is preserved and acoustically colored in real time.\n"
        "// Audio priority: 3 consecutive over-budget DSP blocks -> dry failsafe bypass.\n"
        + ("// USB tuning: PYR? | PYR=0..100 | PYR=ON | PYR=OFF\n" if usb_control
           else "// USB tuning: disabled by composer option\n")
        + "// 117-121 Hz is a project anchor band, not the only frequency.\n"
        "// MODEL_BASED_EFFECT != MEASURED_CHAMBER_IR\n\n"
    )
    return banner + source


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inject current Voice-of-Janus Pyramid Language into canonical Pyramid swarm firmware"
    )
    parser.add_argument("base", type=Path, help="canonical ATOM_MATRIX_Pyramid.ino")
    parser.add_argument("output", type=Path, help="output composed .ino")
    parser.add_argument(
        "--no-usb-control",
        action="store_true",
        help="do not consume Serial input; use when the base firmware owns the USB console",
    )
    args = parser.parse_args()

    base = args.base.resolve()
    output = args.output.resolve()
    if base == output:
        raise RuntimeError("refusing to overwrite canonical swarm source; choose a separate output path")

    raw = base.read_bytes()
    text = raw.decode("utf-8-sig")
    usb_control = not args.no_usb_control
    composed = compose(text, usb_control=usb_control)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(composed, encoding="utf-8", newline="\n")

    repo_root = Path(__file__).resolve().parents[1]
    firmware_dir = repo_root / "firmware"
    for header in ("JanusPyramid117121DSP.h", "JanusPyramid117121Profile.h"):
        shutil.copy2(firmware_dir / header, output.parent / header)

    out_raw = output.read_bytes()
    receipt = {
        "schema": "janus.echo_pyramid.compose_receipt.v2.5",
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
            "audio-budget dry-bypass failsafe",
            "EP_SAMPLE_RATE DSP init",
            "timed processInPlace immediately before ep.write(chunk.mono, chunk.frames)",
            "10-second DSP real-time budget telemetry",
        ] + (["USB Serial local tuning control"] if usb_control else []),
        "usb_control": {
            "enabled": usb_control,
            "network_io": false,
            "ownership_guard": "FAIL_CLOSED_IF_BASE_CONSUMES_SERIAL_INPUT",
            "commands": ["PYR?", "PYR=0..100", "PYR=ON", "PYR=OFF"] if usb_control else [],
            "purpose": "Local A/B acoustic tuning without reflashing the device",
        },
        "real_time_budget": {
            "chunk_frames": 256,
            "sample_rate_hz": 44100,
            "chunk_budget_us_floor": 5804,
            "telemetry": ["dsp_ema_us", "dsp_peak_us", "dsp_load_percent"],
            "failsafe": {
                "enabled_by_default": true,
                "trip_condition": "DSP_PROCESS_TIME >= PCM_BLOCK_BUDGET",
                "consecutive_blocks": 3,
                "action": "DRY_BYPASS_UNTIL_EXPLICIT_PYR_ON_OR_REBOOT"
            }
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
            "AUDIO_CONTINUITY_HAS_PRIORITY_OVER_EFFECT",
            "117_121_HZ_IS_AN_ANCHOR_BAND_NOT_THE_ONLY_FREQUENCY",
            "SERIAL_INPUT_HAS_ONE_OWNER",
            "MODEL_BASED_EFFECT != MEASURED_CHAMBER_IR",
        ],
    }
    receipt_path = output.with_suffix(output.suffix + ".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("JANUS Echo-Pyramid composition PASS")
    print(f"Profile:         {PROFILE_ID}")
    print(f"USB control:     {'ON' if usb_control else 'OFF'}")
    print("DSP failsafe:    ON (3 consecutive over-budget blocks -> dry bypass)")
    print(f"Base SHA-256:   {receipt['base_sha256']}")
    print(f"Output SHA-256: {receipt['output_sha256']}")
    print(f"Firmware:       {output}")
    print(f"Receipt:        {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
