#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include "JanusPyramid117121DSP.h"

static float rms(const int16_t* data, size_t n) {
  double sum = 0.0;
  for (size_t i = 0; i < n; ++i) {
    const double x = static_cast<double>(data[i]) / 32768.0;
    sum += x * x;
  }
  return static_cast<float>(sqrt(sum / static_cast<double>(n)));
}

static void fillTone(int16_t* dst, size_t n, float hz, float amplitude) {
  const float two_pi = 6.28318530717958647692f;
  for (size_t i = 0; i < n; ++i) {
    const float s = sinf(two_pi * hz * static_cast<float>(i) / 44100.0f);
    dst[i] = static_cast<int16_t>(s * amplitude);
  }
}

int main() {
  JanusPyramid117121DSP dsp;
  assert(dsp.begin(44100));
  assert(dsp.ready());
  assert(!dsp.begin(48000));  // fixed-size room-delay provenance is 44.1 kHz only
  assert(dsp.begin(44100));
  assert(dsp.roomDelayBytes() == 3466U);
  assert(sizeof(dsp) < 4096U);
  assert(dsp.targetAmountPercent() == 100U);
  assert(dsp.currentAmountPercent() == 100U);

  int16_t silence[256] = {0};
  dsp.processInPlace(silence, 256);
  for (size_t i = 0; i < 256; ++i) assert(silence[i] == 0);

  // A 119 Hz carrier should survive and be altered by the anchored operator.
  dsp.reset();
  const size_t n = 44100;
  static int16_t tone[n];
  static int16_t original[n];
  fillTone(tone, n, 119.0f, 6500.0f);
  for (size_t i = 0; i < n; ++i) original[i] = tone[i];

  const float input_rms = rms(original, n);
  dsp.processInPlace(tone, n);
  const float output_rms = rms(tone, n);
  bool changed = false;
  for (size_t i = 0; i < n; ++i) {
    if (tone[i] != original[i]) changed = true;
    assert(tone[i] >= -32768 && tone[i] <= 32767);
  }
  assert(changed);
  assert(output_rms > 0.0f);
  assert(input_rms > 0.0f);

  // Runtime spatial-depth control: after the one-block ramp reaches 0%, the
  // following block must be the original PCM (allowing one LSB from float roundtrip).
  dsp.setAmountPercent(0);
  int16_t ramp_block[256];
  fillTone(ramp_block, 256, 311.0f, 8000.0f);
  dsp.processInPlace(ramp_block, 256);
  assert(dsp.currentAmountPercent() == 0U);

  int16_t dry_block[256];
  int16_t dry_expected[256];
  fillTone(dry_block, 256, 311.0f, 8000.0f);
  for (size_t i = 0; i < 256; ++i) dry_expected[i] = dry_block[i];
  dsp.processInPlace(dry_block, 256);
  for (size_t i = 0; i < 256; ++i) {
    const int delta = static_cast<int>(dry_block[i]) - static_cast<int>(dry_expected[i]);
    assert(delta >= -1 && delta <= 1);
  }

  dsp.setAmountPercent(37);
  assert(dsp.targetAmountPercent() == 37U);
  int16_t depth_block[256];
  fillTone(depth_block, 256, 119.0f, 6500.0f);
  dsp.processInPlace(depth_block, 256);
  assert(dsp.currentAmountPercent() == 37U);

  // Hard bypass remains bit-transparent and resets acoustic state when toggled.
  dsp.setEnabled(false);
  int16_t bypass[8] = {-20000, -10000, -1, 0, 1, 10000, 20000, 32767};
  int16_t expected[8];
  for (size_t i = 0; i < 8; ++i) expected[i] = bypass[i];
  dsp.processInPlace(bypass, 8);
  for (size_t i = 0; i < 8; ++i) assert(bypass[i] == expected[i]);

  printf("JANUS 117-121 DSP PASS | profile=%s | delay_bytes=%u | object_bytes=%u | depth=%u%%\n",
         janus_pyramid_117121::kProfileId,
         static_cast<unsigned>(dsp.roomDelayBytes()),
         static_cast<unsigned>(sizeof(dsp)),
         static_cast<unsigned>(dsp.targetAmountPercent()));
  return 0;
}
