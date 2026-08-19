#pragma once

#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "JanusPyramid117121Profile.h"

class JanusPyramid117121DSP {
 public:
  JanusPyramid117121DSP()
      : ready_(false), enabled_(true), room_phase_(0), room_hold_(0.0f),
        amount_(1.0f), target_amount_(1.0f),
        eq_x1_(0.0f), eq_x2_(0.0f), eq_y1_(0.0f), eq_y2_(0.0f) {
    reset();
  }

  bool begin(uint32_t sample_rate_hz = janus_pyramid_117121::kSampleRateHz) {
    using namespace janus_pyramid_117121;
    // The physical Atom Matrix swarm path is fixed at 44.1 kHz. Keeping this
    // explicit makes the pre-sized embedded room delays provenance-safe.
    if (sample_rate_hz != kSampleRateHz) return false;

    // RBJ peaking EQ, identical coefficient construction to Pyramid117121Filter.
    const float amplitude = powf(10.0f, kAnchorGainDb / 40.0f);
    const float omega = 2.0f * kPi * kAnchorCenterHz / static_cast<float>(sample_rate_hz);
    const float alpha = sinf(omega) / (2.0f * kAnchorQ);
    const float cosine = cosf(omega);

    const float b0 = 1.0f + alpha * amplitude;
    const float b1 = -2.0f * cosine;
    const float b2 = 1.0f - alpha * amplitude;
    const float a0 = 1.0f + alpha / amplitude;
    const float a1 = -2.0f * cosine;
    const float a2 = 1.0f - alpha / amplitude;

    eq_b0_ = b0 / a0;
    eq_b1_ = b1 / a0;
    eq_b2_ = b2 / a0;
    eq_a1_ = a1 / a0;
    eq_a2_ = a2 / a0;

    const float frequencies[3] = {kAnchorLowHz, kAnchorCenterHz, kAnchorHighHz};
    const float radius = expf(-1.0f / (kAnchorDecaySeconds * static_cast<float>(sample_rate_hz)));
    const float radius2 = radius * radius;
    const float scale = maxFloat(1.0f - radius, 1.0e-7f);
    for (size_t i = 0; i < 3; ++i) {
      resonators_[i].coefficient =
          2.0f * radius * cosf(2.0f * kPi * frequencies[i] / static_cast<float>(sample_rate_hz));
      resonators_[i].radius_squared = radius2;
      resonators_[i].scale = scale;
    }

    reset();
    ready_ = true;
    return true;
  }

  void setEnabled(bool enabled) {
    if (enabled_ != enabled) reset();
    enabled_ = enabled;
  }

  bool enabled() const { return enabled_; }
  bool ready() const { return ready_; }
  uint32_t sampleRateHz() const { return janus_pyramid_117121::kSampleRateHz; }
  size_t roomDelayBytes() const { return janus_pyramid_117121::kDelayTotalSamples * sizeof(int16_t); }

  // Runtime spatial depth. 100 = canonical Pyramid Language v0.3.
  // 0 = original source audio. Changes are linearly ramped across the next
  // processed block to avoid an abrupt discontinuity/click.
  void setAmountPercent(uint8_t percent) {
    if (percent > 100U) percent = 100U;
    target_amount_ = static_cast<float>(percent) * 0.01f;
  }

  uint8_t targetAmountPercent() const {
    return static_cast<uint8_t>(target_amount_ * 100.0f + 0.5f);
  }

  uint8_t currentAmountPercent() const {
    return static_cast<uint8_t>(amount_ * 100.0f + 0.5f);
  }

  void reset() {
    eq_x1_ = eq_x2_ = eq_y1_ = eq_y2_ = 0.0f;
    for (size_t i = 0; i < 3; ++i) {
      resonators_[i].z1 = 0.0f;
      resonators_[i].z2 = 0.0f;
    }
    clearDelay(delay_lx_, janus_pyramid_117121::kDelayLxSamples, delay_lx_state_);
    clearDelay(delay_ly_, janus_pyramid_117121::kDelayLySamples, delay_ly_state_);
    clearDelay(delay_lz_, janus_pyramid_117121::kDelayLzSamples, delay_lz_state_);
    clearDelay(delay_mixed_, janus_pyramid_117121::kDelayMixedSamples, delay_mixed_state_);
    room_phase_ = 0;
    room_hold_ = 0.0f;
  }

  // In-place mono PCM16 processing. No heap allocation, no additional I2S,
  // no network access. Intended for the existing janus_audio playback task.
  void processInPlace(int16_t* samples, size_t frames) {
    using namespace janus_pyramid_117121;
    if (!enabled_ || samples == nullptr || frames == 0) return;
    if (!ready_ && !begin()) return;

    const float amount_step = (target_amount_ - amount_) / static_cast<float>(frames);

    for (size_t frame = 0; frame < frames; ++frame) {
      amount_ += amount_step;

      const float dry_input = static_cast<float>(samples[frame]) / 32768.0f;
      const float colored = processEq(dry_input);

      float anchor_sum = 0.0f;
      for (size_t i = 0; i < 3; ++i) anchor_sum += processResonator(resonators_[i], colored);
      const float anchor = anchor_sum / 3.0f;

      if (room_phase_ == 0) {
        const float room_input = colored + kRoomAnchorInjection * anchor;
        const float room_sum =
            processDelay(delay_lx_, kDelayLxSamples, delay_lx_state_, room_input, kFeedbackLx) +
            processDelay(delay_ly_, kDelayLySamples, delay_ly_state_, room_input, kFeedbackLy) +
            processDelay(delay_lz_, kDelayLzSamples, delay_lz_state_, room_input, kFeedbackLz) +
            processDelay(delay_mixed_, kDelayMixedSamples, delay_mixed_state_, room_input, kFeedbackMixed);
        room_hold_ = room_sum * 0.25f;
      }
      room_phase_ = static_cast<uint8_t>((room_phase_ + 1U) % kRoomDecimation);

      const float wet_signal =
          kWetColoredWeight * colored + kWetAnchorWeight * anchor + kWetRoomWeight * room_hold_;
      const float effect_mixed = kDry * dry_input + kWet * wet_signal;
      const float effect_limited = fastTanh(effect_mixed);

      // Crossfade the entire acoustic-space operator against the untouched source.
      // This makes "amount" a true spatial-depth control rather than a second gain knob.
      const float output = dry_input + amount_ * (effect_limited - dry_input);
      samples[frame] = floatToPcm16(output);
    }

    // Eliminate tiny accumulated float error at the end of the ramp.
    amount_ = target_amount_;
  }

 private:
  static constexpr float kPi = 3.14159265358979323846f;

  struct ResonatorState {
    float coefficient = 0.0f;
    float radius_squared = 0.0f;
    float scale = 0.0f;
    float z1 = 0.0f;
    float z2 = 0.0f;
  };

  struct DelayState {
    size_t index = 0;
    float low_pass_state = 0.0f;
  };

  static float maxFloat(float a, float b) { return a > b ? a : b; }

  static float clampUnit(float x) {
    if (x > 1.0f) return 1.0f;
    if (x < -1.0f) return -1.0f;
    return x;
  }

  static int16_t floatToPcm16(float x) {
    const float clamped = clampUnit(x);
    int32_t value = static_cast<int32_t>(clamped * 32767.0f);
    if (value > 32767) value = 32767;
    if (value < -32768) value = -32768;
    return static_cast<int16_t>(value);
  }

  static float pcm16ToFloat(int16_t x) { return static_cast<float>(x) / 32768.0f; }

  static float fastTanh(float x) {
    if (x >= 3.0f) return 1.0f;
    if (x <= -3.0f) return -1.0f;
    const float x2 = x * x;
    return x * (27.0f + x2) / (27.0f + 9.0f * x2);
  }

  static void clearDelay(int16_t* buffer, size_t size, DelayState& state) {
    memset(buffer, 0, size * sizeof(int16_t));
    state.index = 0;
    state.low_pass_state = 0.0f;
  }

  float processEq(float sample) {
    const float output = eq_b0_ * sample + eq_b1_ * eq_x1_ + eq_b2_ * eq_x2_ -
                         eq_a1_ * eq_y1_ - eq_a2_ * eq_y2_;
    eq_x2_ = eq_x1_;
    eq_x1_ = sample;
    eq_y2_ = eq_y1_;
    eq_y1_ = output;
    return output;
  }

  static float processResonator(ResonatorState& r, float sample) {
    const float output = sample + r.coefficient * r.z1 - r.radius_squared * r.z2;
    r.z2 = r.z1;
    r.z1 = output;
    return output * r.scale;
  }

  static float processDelay(int16_t* buffer, size_t size, DelayState& state,
                            float sample, float feedback) {
    using namespace janus_pyramid_117121;
    const float delayed = pcm16ToFloat(buffer[state.index]);
    state.low_pass_state =
        (1.0f - kDelayDamping) * delayed + kDelayDamping * state.low_pass_state;
    const float stored = sample + state.low_pass_state * feedback;
    buffer[state.index] = floatToPcm16(stored);
    state.index++;
    if (state.index >= size) state.index = 0;
    return delayed;
  }

  bool ready_;
  bool enabled_;
  uint8_t room_phase_;
  float room_hold_;
  float amount_;
  float target_amount_;

  float eq_b0_ = 0.0f;
  float eq_b1_ = 0.0f;
  float eq_b2_ = 0.0f;
  float eq_a1_ = 0.0f;
  float eq_a2_ = 0.0f;
  float eq_x1_;
  float eq_x2_;
  float eq_y1_;
  float eq_y2_;

  ResonatorState resonators_[3];

  int16_t delay_lx_[janus_pyramid_117121::kDelayLxSamples];
  int16_t delay_ly_[janus_pyramid_117121::kDelayLySamples];
  int16_t delay_lz_[janus_pyramid_117121::kDelayLzSamples];
  int16_t delay_mixed_[janus_pyramid_117121::kDelayMixedSamples];
  DelayState delay_lx_state_;
  DelayState delay_ly_state_;
  DelayState delay_lz_state_;
  DelayState delay_mixed_state_;
};
