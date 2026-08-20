# Janus-Echo-Кусто

Jacques-Yves Cousteau research branch for underwater acoustic inverse-search calibration.

Parent recipe: `config/underwater_resonator_recipe.v1.json`
Reverse recipe: `config/underwater_resonator_reverse_recipe.v1.json`

Historical anchor: J. Alinat & J.-Y. Cousteau (1962), “Accidents de terrain en mer de Ligurie”, CNRS, pp. 121–123. The branch adopts the same methodological spirit: acoustic/bathymetric observation first, geological interpretation second.

Calibration source of truth: `Hawkar-usls/Janus-Cosmos` branch `janus-echo-cousteau`, gate `BLIND_REFERENCE_LIBRARY_V1`.

Rules:
- preserve PASS, FAIL and AMBIGUOUS outcomes;
- synthetic calibration is not physical hydrophone evidence;
- do not use 119 Hz or ~520 Hz as a blind-search key;
- do not expose target scale or label to first-stage classification;
- forward-replay must reject wrong models before expedition admission;
- no target detected until field replication exists.
