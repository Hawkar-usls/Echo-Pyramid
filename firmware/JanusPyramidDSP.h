#pragma once

#include <math.h>
#include <stddef.h>
#include <stdint.h>

#include "JanusPyramidVoiceProfile.h"

class JanusPyramidDSP {
 public:
  JanusPyramidDSP() : sample_rate_hz_(0), r_(0.0f), r2_(0.0f), wet_scale_(0.0f), enabled_(true), ready_(false) {
    reset();
  }

  bool begin(uint32_t sample_rate_hz = janus_voice::kSampleRateHz) {
    if (sample_rate_hz < 8000U) return false;
    sample_rate_hz_ = sample_rate_hz;

    r_ = expf(-1.0f / (janus_voice::kDecaySeconds * static_cast<float>(sample_rate_hz_)));
    r2_ = r_ * r_;
    wet_scale_ = (1.0f - r_) / static_cast<float>(janus_voice::kModeCount);

    const float two_pi = 6.28318530717958647692f;
    for (size_t i = 0; i < janus_voice::kModeCount; ++i) {
      const float hz = janus_voice::kModes[i].render_hz;
      if (!(hz > 0.0f && hz < static_cast<float>(sample_rate_hz_) * 0.5f)) return false;
      coeff_[i] = 2.0f * r_ * cosf(two_pi * hz / static_cast<float>(sample_rate_hz_));
    }

    reset();
    ready_ = true;
    return true;
  }

  void reset() {
    for (size_t i = 0; i < janus_voice::kModeCount; ++i) {
      z1_[i] = 0.0f;
      z2_[i] = 0.0f;
      coeff_[i] = 0.0f;
    }
  }

  void setEnabled(bool enabled) {
    if (enabled_ != enabled) reset();
    enabled_ = enabled;
  }

  bool enabled() const { return enabled_; }
  bool ready() const { return ready_; }
  uint32_t sampleRateHz() const { return sample_rate_hz_; }

  // Processes mono signed PCM16 in-place. No heap allocation, no extra I2S channel,
  // no blocking I/O. Intended insertion point: immediately before ep.write().
  void processInPlace(int16_t* samples, size_t frames) {
    if (!enabled_ || samples == nullptr || frames == 0) return;
    if (!ready_ && !begin(janus_voice::kSampleRateHz)) return;

    for (size_t frame = 0; frame < frames; ++frame) {
      const float x = static_cast<float>(samples[frame]) / 32768.0f;
      float resonant_sum = 0.0f;

      for (size_t i = 0; i < janus_voice::kModeCount; ++i) {
        const float y = x + coeff_[i] * z1_[i] - r2_ * z2_[i];
        z2_[i] = z1_[i];
        z1_[i] = y;
        resonant_sum += y;
      }

      const float wet_sample = resonant_sum * wet_scale_;
      const float mixed = (janus_voice::kDry * x + janus_voice::kWet * wet_sample) * janus_voice::kOutputGain;
      const float limited = fastTanh(mixed);
      int32_t pcm = static_cast<int32_t>(limited * 32767.0f);
      if (pcm > 32767) pcm = 32767;
      if (pcm < -32768) pcm = -32768;
      samples[frame] = static_cast<int16_t>(pcm);
    }
  }

 private:
  static float fastTanh(float x) {
    if (x >= 3.0f) return 1.0f;
    if (x <= -3.0f) return -1.0f;
    const float x2 = x * x;
    return x * (27.0f + x2) / (27.0f + 9.0f * x2);
  }

  uint32_t sample_rate_hz_;
  float r_;
  float r2_;
  float wet_scale_;
  float coeff_[janus_voice::kModeCount];
  float z1_[janus_voice::kModeCount];
  float z2_[janus_voice::kModeCount];
  bool enabled_;
  bool ready_;
};
