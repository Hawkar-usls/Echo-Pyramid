#pragma once

#include <stddef.h>
#include <stdint.h>

namespace janus_voice {

struct AcousticMode {
  float physical_hz;
  float render_hz;
  uint8_t octave_multiplier;
  uint8_t p;
  uint8_t q;
  uint8_t r;
};

// Embedded contract copied from The-Voice-of-Janus:
// configs/pyramid_language.activation.json +
// presets/great_pyramid_kings_chamber.example.json
//
// IMPORTANT: this is an ILLUSTRATIVE_MODEL_BASED room-mode profile.
// It is not a claim that the Great Pyramid was intentionally tuned to these
// frequencies, and it is not a measured impulse response.
static const char kProfileId[] = "GREAT-PYRAMID-KINGS-CHAMBER-EXAMPLE-v0.1/ESP32-LIVE-6";
static const char kEvidenceStatus[] = "ILLUSTRATIVE_MODEL_BASED";
static const char kClaimBoundary[] = "MODEL_BASED_RECONSTRUCTION != MEASURED_HISTORICAL_SOUND";

static const uint32_t kSampleRateHz = 44100;
static const float kDecaySeconds = 0.32f;
static const float kWet = 0.72f;
static const float kDry = 0.62f;
static const float kOutputGain = 0.85f;
static const size_t kModeCount = 6;

// Same mode derivation used by The-Voice-of-Janus/pyramid_dsp.py:
// rectangular chamber eigenmodes, sorted by physical frequency, then frequencies
// below 35 Hz are octave-translated upward by powers of two for the render bank.
static const AcousticMode kModes[kModeCount] = {
    {16.411483f, 65.645933f, 4, 1, 0, 0},
    {29.568966f, 59.137931f, 2, 0, 0, 1},
    {32.980769f, 65.961538f, 2, 0, 1, 0},
    {33.818050f, 67.636100f, 2, 1, 0, 1},
    {36.838403f, 36.838403f, 1, 1, 1, 0},
    {44.177719f, 44.177719f, 1, 2, 0, 1},
};

}  // namespace janus_voice
