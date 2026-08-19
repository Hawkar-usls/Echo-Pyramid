/*
  Echo_Pyramid_Janus_Demo.ino

  Minimal hardware smoke test for M5Stack Atom Matrix + Echo Pyramid.
  Hold the Atom button to route microphone PCM through the current JANUS
  Pyramid Language v0.3 (117-121 Hz anchored space) and then to the speaker.

  WARNING: acoustic loopback can feed back. Keep volume low and keep the
  speaker away from your ears while testing.
*/

#include <Arduino.h>

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

M5EchoPyramid ep;
JanusPyramid117121DSP janusVoiceDsp;

int16_t micBuffer[FRAMES];
int16_t refBuffer[FRAMES];
int16_t silenceBuffer[FRAMES] = {0};

void setup() {
  Serial.begin(115200);
  delay(100);

  auto cfg = M5.config();
  M5.begin(cfg);

  Serial.println("JANUS Echo-Pyramid Language v0.3 smoke test");
  Serial.printf("profile=%s\nevidence=%s\n",
                janus_pyramid_117121::kProfileId,
                janus_pyramid_117121::kEvidenceStatus);

  const bool pyramidOk = ep.begin(&Wire, EP_I2C_SDA, EP_I2C_SCL,
                                  EP_I2S_BCLK, EP_I2S_WS, EP_I2S_DOUT, EP_I2S_DIN,
                                  EP_SAMPLE_RATE);
  const bool dspOk = janusVoiceDsp.begin(EP_SAMPLE_RATE);

  Serial.printf("pyramid=%d dsp=%d sample_rate=%lu room_delay_bytes=%u\n",
                pyramidOk ? 1 : 0, dspOk ? 1 : 0,
                (unsigned long)EP_SAMPLE_RATE,
                (unsigned)janusVoiceDsp.roomDelayBytes());

  // Deliberately quiet for loopback safety.
  ep.codec().setVolume(25);
  ep.codec().mute(false);
}

void loop() {
  M5.update();

  if (!M5.BtnA.isPressed()) {
    ep.write(silenceBuffer, FRAMES);
    delay(2);
    return;
  }

  ep.read(micBuffer, refBuffer, FRAMES);
  janusVoiceDsp.processInPlace(micBuffer, FRAMES);
  ep.write(micBuffer, FRAMES);
}
