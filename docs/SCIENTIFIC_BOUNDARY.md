# Scientific boundary

`Echo-Pyramid` may be imaginative in presentation while remaining strict about what the acoustics establish.

## Current default profile

The physical default is `PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32`, ported from the current `The-Voice-of-Janus` `Pyramid117121Filter`.

It colours ordinary source audio with:

- a dominant **117–121 Hz project anchor band** centered at 119 Hz;
- three damped resonators at 117 / 119 / 121 Hz;
- a model-based room tail derived from geometry `10.45 x 5.20 x 5.80 m` and `c = 343 m/s`;
- an intelligible dry path.

The 117–121 Hz range is therefore an **operator parameter / project anchor**, not a statement that all pyramids possess one special universal frequency.

## What it is not

The current profile is not evidence that:

- the Great Pyramid was intentionally tuned to 117–121 Hz;
- 117–121 Hz is the only meaningful acoustic band of a pyramid or chamber;
- the current room tail is a measured impulse response;
- a predicted/modelled acoustic effect reproduces an exact historical sound;
- air-acoustic resonance is identical to stone/structural vibration.

The upstream activation explicitly marks the effect model-based and keeps measured-IR and ancient-intent claims false.

## Earlier modal reference

The repository also preserves the earlier rectangular-room modal model. For dimensions `Lx`, `Ly`, `Lz` and speed of sound `c` it uses:

```text
f_pqr = (c / 2) * sqrt((p/Lx)^2 + (q/Ly)^2 + (r/Lz)^2)
```

That profile is useful for comparison but is no longer the physical composer default.

## Evidence ladder

Keep these labels distinct:

1. `ILLUSTRATIVE_MODEL_BASED`
2. `SOURCE_VERIFIED_GEOMETRY_MODEL`
3. `MODEL_BASED_117_121_HZ_ANCHORED_EFFECT`
4. `MEASURED_ROOM_RESPONSE`
5. `MEASURED_DEVICE_RESPONSE`

A later measurement does not retroactively convert an earlier model into measured evidence; keep both artifacts and their provenance.

## Hard rules

```text
DO_NOT_REPLACE_SOURCE_AUDIO_WITH_SYNTHETIC_TONES
117_121_HZ_IS_AN_ANCHOR_BAND_NOT_THE_ONLY_FREQUENCY
KEEP_DRY_PATH_FOR_INTELLIGIBILITY
MODEL_BASED_EFFECT != MEASURED_CHAMBER_IR
PREDICTED_ACOUSTIC_MODEL != PROOF_OF_ANCIENT_INTENT
AIR_ACOUSTIC_MODE != STRUCTURAL_VIBRATION_MODE
METAPHOR != PHYSICS
```

These rules are mirrored by `config/voice_contract.json` and should travel with every future firmware profile and receipt.
