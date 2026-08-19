#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include "JanusPyramidDSP.h"

int main() {
  JanusPyramidDSP dsp;
  assert(dsp.begin(44100));
  assert(dsp.ready());
  assert(dsp.sampleRateHz() == 44100);

  int16_t silence[256] = {0};
  dsp.processInPlace(silence, 256);
  for (size_t i = 0; i < 256; ++i) assert(silence[i] == 0);

  dsp.reset();
  int16_t tone[1024];
  int16_t original[1024];
  const float pi2 = 6.28318530717958647692f;
  for (size_t i = 0; i < 1024; ++i) {
    const float s = sinf(pi2 * 120.0f * static_cast<float>(i) / 44100.0f);
    tone[i] = static_cast<int16_t>(s * 12000.0f);
    original[i] = tone[i];
  }

  dsp.processInPlace(tone, 1024);
  bool changed = false;
  for (size_t i = 0; i < 1024; ++i) {
    if (tone[i] != original[i]) changed = true;
    assert(tone[i] >= -32768 && tone[i] <= 32767);
  }
  assert(changed);

  dsp.setEnabled(false);
  int16_t bypass[8] = {-20000, -10000, -1, 0, 1, 10000, 20000, 32767};
  int16_t expected[8];
  for (size_t i = 0; i < 8; ++i) expected[i] = bypass[i];
  dsp.processInPlace(bypass, 8);
  for (size_t i = 0; i < 8; ++i) assert(bypass[i] == expected[i]);

  printf("JANUS Pyramid DSP tests PASS | profile=%s\n", janus_voice::kProfileId);
  return 0;
}
