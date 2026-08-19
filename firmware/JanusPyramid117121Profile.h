#pragma once

#include <stddef.h>
#include <stdint.h>

namespace janus_pyramid_117121 {

// Canonical source:
// Hawkar-usls/The-Voice-of-Janus
// configs/pyramid_117_121_space.activation.json
// src/pyramid_anchor_filter.py::Pyramid117121Filter
//
// Language version stays v0.3. ESP32-r2 identifies only this bounded physical
// implementation (runtime depth + corrected 4x-decimated room damping).
static const char kProfileId[] = "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2";
static const char kLanguageVersion[] = "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3";
static const char kEmbeddedRevision[] = "ESP32-r2";
static const char kEvidenceStatus[] = "MODEL_BASED_117_121_HZ_ANCHORED_EFFECT";
static const char kClaimBoundary[] = "117_121_HZ_IS_AN_ANCHOR_BAND_NOT_THE_ONLY_FREQUENCY";

static const uint32_t kSampleRateHz = 44100;

static const float kAnchorLowHz = 117.0f;
static const float kAnchorCenterHz = 119.0f;
static const float kAnchorHighHz = 121.0f;
static const float kAnchorQ = 29.75f;
static const float kAnchorGainDb = 11.5f;
static const float kAnchorDecaySeconds = 1.65f;

static const float kRoomDecay = 0.78f;
static const float kWet = 0.72f;
static const float kDry = 0.62f;
static const float kSpeedOfSoundMps = 343.0f;
static const float kGeometryLxM = 10.45f;
static const float kGeometryLyM = 5.20f;
static const float kGeometryLzM = 5.80f;

// Python reference FeedbackDelay damping at full 44.1 kHz.
static const float kSourceDelayDamping = 0.22f;

// Embedded room-tail optimization: the anchor path remains full-rate 44.1 kHz.
// Only the low-bandwidth feedback room tail is evaluated every four samples.
// Delay lengths preserve the same delay times used by the Python v0.3 operator.
static const uint8_t kRoomDecimation = 4;
static const uint32_t kRoomSampleRateHz = kSampleRateHz / kRoomDecimation;  // 11025 Hz

// One embedded room update spans four reference-rate samples. For the recurrence
// state[n] = (1-d)*x[n] + d*state[n-1], use d_embedded = d_source^4 so the
// persistence pole has approximately the same wall-clock decay under 4x decimation.
static const float kEmbeddedDelayDamping = 0.00234256f;  // 0.22^4

static const size_t kDelayLxSamples = 672;     // round((2*10.45/343)*11025)
static const size_t kDelayLySamples = 334;     // round((2*5.20/343)*11025)
static const size_t kDelayLzSamples = 373;     // round((2*5.80/343)*11025)
static const size_t kDelayMixedSamples = 354;  // round(((5.20+5.80)/343)*11025)
static const size_t kDelayTotalSamples =
    kDelayLxSamples + kDelayLySamples + kDelayLzSamples + kDelayMixedSamples;

static const float kFeedbackLx = kRoomDecay;
static const float kFeedbackLy = kRoomDecay * 0.94f;
static const float kFeedbackLz = kRoomDecay * 0.91f;
static const float kFeedbackMixed = kRoomDecay * 0.88f;

// Matches Pyramid117121Filter.process_sample().
static const float kWetColoredWeight = 0.58f;
static const float kWetAnchorWeight = 1.55f;
static const float kWetRoomWeight = 0.82f;
static const float kRoomAnchorInjection = 1.8f;

}  // namespace janus_pyramid_117121
