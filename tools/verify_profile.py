#!/usr/bin/env python3
"""Recompute the embedded ESP32 live mode bank from the documented model."""

from __future__ import annotations

import math

LX = 10.45
LY = 5.20
LZ = 5.80
C = 343.0
MAX_INDEX = 5
FREQUENCY_LIMIT_HZ = 240.0
MINIMUM_RENDER_HZ = 35.0
MAXIMUM_RENDER_HZ = 900.0
MODE_COUNT = 6

EXPECTED = [
    (16.411483, 65.645933, 4, (1, 0, 0)),
    (29.568966, 59.137931, 2, (0, 0, 1)),
    (32.980769, 65.961538, 2, (0, 1, 0)),
    (33.818050, 67.636100, 2, (1, 0, 1)),
    (36.838403, 36.838403, 1, (1, 1, 0)),
    (44.177719, 44.177719, 1, (2, 0, 1)),
]


def calculate_modes() -> list[tuple[float, int, int, int]]:
    modes: list[tuple[float, int, int, int]] = []
    for p in range(MAX_INDEX + 1):
        for q in range(MAX_INDEX + 1):
            for r in range(MAX_INDEX + 1):
                if p == q == r == 0:
                    continue
                f = (C / 2.0) * math.sqrt((p / LX) ** 2 + (q / LY) ** 2 + (r / LZ) ** 2)
                if f <= FREQUENCY_LIMIT_HZ:
                    modes.append((f, p, q, r))
    modes.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return modes


def derive_live_bank() -> list[tuple[float, float, int, tuple[int, int, int]]]:
    derived = []
    seen: set[float] = set()
    for physical, p, q, r in calculate_modes():
        render = physical
        multiplier = 1
        while render < MINIMUM_RENDER_HZ:
            render *= 2.0
            multiplier *= 2
        while render > MAXIMUM_RENDER_HZ and multiplier > 1:
            render /= 2.0
            multiplier //= 2
        if not MINIMUM_RENDER_HZ <= render <= MAXIMUM_RENDER_HZ:
            continue
        key = round(render, 6)
        if key in seen:
            continue
        seen.add(key)
        derived.append((physical, render, multiplier, (p, q, r)))
        if len(derived) == MODE_COUNT:
            break
    return derived


def main() -> int:
    actual = derive_live_bank()
    assert len(actual) == len(EXPECTED)
    for index, (got, expected) in enumerate(zip(actual, EXPECTED)):
        gp, gr, gm, gi = got
        ep, er, em, ei = expected
        assert abs(gp - ep) < 1e-6, (index, "physical", gp, ep)
        assert abs(gr - er) < 1e-6, (index, "render", gr, er)
        assert gm == em, (index, "multiplier", gm, em)
        assert gi == ei, (index, "indices", gi, ei)
    print("JANUS Pyramid embedded profile verification PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
