#!/usr/bin/env python3
"""Compile-smoke the composer output with tiny Arduino/M5/FreeRTOS host stubs.

This is not a substitute for an ESP32 toolchain build. It catches C++ syntax,
missing-symbol and injection-order mistakes in the generated runtime, including
the portMUX guarded control mailbox, in both USB-control modes.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from compose_swarm_firmware import compose  # noqa: E402

BASE = r'''#include <Arduino.h>
#include <M5EchoPyramid.h>
#define EP_SAMPLE_RATE 44100
#define JANUS_AUDIO_CHUNK_FRAMES 256
M5EchoPyramid ep;

struct Chunk { uint16_t frames; int16_t mono[256]; } chunk;

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

ARDUINO_STUB = r'''#pragma once
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

struct SerialClass {
  template <typename... Args> void printf(const char*, Args...) {}
  void println(const char*) {}
  int available() { return 0; }
  int read() { return -1; }
};
extern SerialClass Serial;

struct ESPClass {
  unsigned long getFreeHeap() const { return 65536UL; }
};
extern ESPClass ESP;

uint32_t micros();
uint32_t millis();

typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(mux) do { (void)(mux); } while (0)
#define portEXIT_CRITICAL(mux) do { (void)(mux); } while (0)
'''

M5_STUB = r'''#pragma once
#include <stdint.h>
class M5EchoPyramid {
 public:
  void write(int16_t*, int) {}
};
'''

RUNTIME_DEFS = r'''
SerialClass Serial;
ESPClass ESP;
static uint32_t fake_clock = 0;
uint32_t micros() { fake_clock += 100; return fake_clock; }
uint32_t millis() { return fake_clock / 1000U; }
'''


def compile_one(compiler: str, *, usb_control: bool) -> None:
    source = compose(BASE, usb_control=usb_control) + RUNTIME_DEFS
    with tempfile.TemporaryDirectory(prefix="echo_pyramid_compile_") as tmp:
        tmp_path = Path(tmp)
        include = tmp_path / "include"
        include.mkdir()
        (include / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
        (include / "M5EchoPyramid.h").write_text(M5_STUB, encoding="utf-8")
        src = tmp_path / "composed.cpp"
        obj = tmp_path / "composed.o"
        src.write_text(source, encoding="utf-8")

        warning_flags = ["-Wall", "-Wextra", "-Werror", "-pedantic"]
        if not usb_control:
            # The no-USB composition intentionally keeps the queue helper as part
            # of the shared block-boundary mailbox API even though the USB producer
            # is absent. Preserve every other warning as an error, but do not turn
            # that one intentional unused static helper into a false syntax failure.
            warning_flags.append("-Wno-error=unused-function")

        subprocess.run(
            [
                compiler,
                "-std=c++11",
                *warning_flags,
                "-I",
                str(include),
                "-I",
                str(ROOT / "firmware"),
                "-c",
                str(src),
                "-o",
                str(obj),
            ],
            check=True,
        )
        if not obj.is_file() or obj.stat().st_size == 0:
            raise AssertionError("compiler did not emit an object file")
    print(f"COMPOSED C++11 COMPILE PASS usb_control={usb_control}")


def main() -> int:
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("g++ is required for composed runtime compile smoke test")
    compile_one(compiler, usb_control=True)
    compile_one(compiler, usb_control=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
