/*
  Echo_Pyramid_Janus_Demo.ino

  Standalone hardware smoke test for M5Stack Atom Matrix + Echo Pyramid.
  Hold the Atom button to route microphone PCM through the current JANUS
  Pyramid Language v0.3 / ESP32-r2 and then to the speaker.

  USB Serial @115200:
    PYR?        status
    PYR=0..100  Pyramid-space depth
    PYR=ON      enable DSP
    PYR=OFF     hard bypass DSP

  WARNING: acoustic loopback can feed back. Keep volume low and keep the
  speaker away from your ears while testing.
*/

#include <Arduino.h>
#include <stdlib.h>
#include <string.h>

#if !defined(CONFIG_IDF_TARGET_ESP32)
#error "Echo_Pyramid_Janus_Demo targets Atom Matrix / classic ESP32."
#endif

#include <M5Unified.h>
#include <M5EchoPyramid.h>
#include "JanusPyramid117121DSP.h"

static const int EP_I2C_SDA = 25;
static const int EP_I2C_SCL = 21;
static const int EP_I2S_BCLK = 19;
static const int EP_I2S_WS = 33;
static const int EP_I2S_DOUT = 22;
static const int EP_I2S_DIN = 23;
static const uint32_t EP_SAMPLE_RATE = 44100;
static const size_t FRAMES = 256;
static const uint32_t BLOCK_BUDGET_US = (FRAMES * 1000000UL) / EP_SAMPLE_RATE;

M5EchoPyramid ep;
JanusPyramid117121DSP janusVoiceDsp;

int16_t micBuffer[FRAMES];
int16_t refBuffer[FRAMES];
int16_t silenceBuffer[FRAMES] = {0};

char serialBuf[24] = {0};
uint8_t serialLen = 0;
uint32_t dspBlocks = 0;
uint32_t dspUsEma = 0;
uint32_t dspUsPeak = 0;
uint32_t lastStatusMs = 0;

void printStatus(const char* reason) {
  const uint32_t loadPct = BLOCK_BUDGET_US ? (dspUsEma * 100UL) / BLOCK_BUDGET_US : 0;
  Serial.printf(
      "PYRAMID_DEMO | %s enabled=%d depth=%u%% button=%d blocks=%lu "
      "dsp_ema_us=%lu dsp_peak_us=%lu budget_us=%lu load=%lu%% delay_bytes=%u profile=%s\n",
      reason ? reason : "STATUS",
      janusVoiceDsp.enabled() ? 1 : 0,
      (unsigned)janusVoiceDsp.targetAmountPercent(),
      M5.BtnA.isPressed() ? 1 : 0,
      (unsigned long)dspBlocks,
      (unsigned long)dspUsEma,
      (unsigned long)dspUsPeak,
      (unsigned long)BLOCK_BUDGET_US,
      (unsigned long)loadPct,
      (unsigned)janusVoiceDsp.roomDelayBytes(),
      janus_pyramid_117121::kProfileId);
}

void applyCommand(const char* cmd) {
  if (!cmd || !cmd[0]) return;

  if (strcmp(cmd, "PYR?") == 0) {
    printStatus("QUERY");
    return;
  }
  if (strcmp(cmd, "PYR=OFF") == 0) {
    janusVoiceDsp.setEnabled(false);
    printStatus("HARD_BYPASS");
    return;
  }
  if (strcmp(cmd, "PYR=ON") == 0) {
    janusVoiceDsp.setEnabled(true);
    dspUsEma = 0;
    dspUsPeak = 0;
    printStatus("ENABLED");
    return;
  }
  if (strncmp(cmd, "PYR=", 4) == 0) {
    char* end = nullptr;
    long value = strtol(cmd + 4, &end, 10);
    if (end && *end == '\0' && value >= 0 && value <= 100) {
      janusVoiceDsp.setAmountPercent((uint8_t)value);
      printStatus("DEPTH_SET");
      return;
    }
  }

  Serial.printf("PYRAMID_DEMO | INVALID command=%s expected=PYR? | PYR=0..100 | PYR=ON | PYR=OFF\n", cmd);
}

void serialTick() {
  while (Serial.available() > 0) {
    const char c = (char)Serial.read();
    if (c == '\r' || c == '\n') {
      if (serialLen > 0) {
        serialBuf[serialLen] = '\0';
        applyCommand(serialBuf);
        serialLen = 0;
      }
      continue;
    }
    if (c >= 32 && c <= 126) {
      if (serialLen + 1U < sizeof(serialBuf)) {
        serialBuf[serialLen++] = c;
      } else {
        serialLen = 0;
        Serial.println("PYRAMID_DEMO | INPUT_OVERFLOW");
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);

  auto cfg = M5.config();
  M5.begin(cfg);

  Serial.println("JANUS Echo-Pyramid Language v0.3 / ESP32-r2 smoke test");
  Serial.printf("profile=%s\nevidence=%s\n",
                janus_pyramid_117121::kProfileId,
                janus_pyramid_117121::kEvidenceStatus);

  const bool pyramidOk = ep.begin(&Wire, EP_I2C_SDA, EP_I2C_SCL,
                                  EP_I2S_BCLK, EP_I2S_WS, EP_I2S_DOUT, EP_I2S_DIN,
                                  EP_SAMPLE_RATE);
  const bool dspOk = janusVoiceDsp.begin(EP_SAMPLE_RATE);
  janusVoiceDsp.setAmountPercent(100);

  Serial.printf("pyramid=%d dsp=%d sample_rate=%lu block_budget_us=%lu room_delay_bytes=%u object_bytes=%u\n",
                pyramidOk ? 1 : 0, dspOk ? 1 : 0,
                (unsigned long)EP_SAMPLE_RATE,
                (unsigned long)BLOCK_BUDGET_US,
                (unsigned)janusVoiceDsp.roomDelayBytes(),
                (unsigned)sizeof(janusVoiceDsp));
  Serial.println("Hold Atom button for mic loopback. USB: PYR? | PYR=0..100 | PYR=ON | PYR=OFF");

  // Deliberately quiet for loopback safety.
  ep.codec().setVolume(20);
  ep.codec().mute(false);
}

void loop() {
  M5.update();
  serialTick();

  if (!M5.BtnA.isPressed()) {
    ep.write(silenceBuffer, FRAMES);
    delay(2);
  } else {
    ep.read(micBuffer, refBuffer, FRAMES);

    const uint32_t started = micros();
    janusVoiceDsp.processInPlace(micBuffer, FRAMES);
    const uint32_t elapsed = micros() - started;
    dspBlocks++;
    if (dspUsEma == 0) dspUsEma = elapsed;
    else dspUsEma = (dspUsEma * 7U + elapsed) / 8U;
    if (elapsed > dspUsPeak) dspUsPeak = elapsed;

    ep.write(micBuffer, FRAMES);
  }

  const uint32_t now = millis();
  if (now - lastStatusMs >= 2000UL) {
    lastStatusMs = now;
    printStatus("PERIODIC");
    dspUsPeak = 0;
  }
}
