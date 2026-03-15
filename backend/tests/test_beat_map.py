"""
Zero-mock unit tests for beat_map.py.
No GCP, no network — pure Python logic only.
"""

import pytest
from beat_map import BeatMap


# ---------------------------------------------------------------------------
# BeatMap.from_dict — parsing + clamping
# ---------------------------------------------------------------------------

class TestBeatMapFromDict:
    def test_valid_integers(self):
        bm = BeatMap.from_dict({"tension": 70, "longing": 55, "resolve": 30})
        assert bm.tension == 70
        assert bm.longing == 55
        assert bm.resolve == 30

    def test_missing_keys_use_defaults(self):
        """All keys missing → all default to 50."""
        bm = BeatMap.from_dict({})
        assert bm.tension == 50
        assert bm.longing == 50
        assert bm.resolve == 50

    def test_partial_keys(self):
        bm = BeatMap.from_dict({"tension": 80})
        assert bm.tension == 80
        assert bm.longing == 50   # default
        assert bm.resolve == 50   # default

    def test_float_values_truncated_not_rounded(self):
        """Gemini may return floats like 75.9 — must truncate cleanly."""
        bm = BeatMap.from_dict({"tension": 75.9, "longing": 40.1, "resolve": 0.7})
        assert bm.tension == 75
        assert bm.longing == 40
        assert bm.resolve == 0

    def test_numeric_string_values(self):
        """Gemini may return strings like "75" — must parse."""
        bm = BeatMap.from_dict({"tension": "75", "longing": "40", "resolve": "20"})
        assert bm.tension == 75
        assert bm.longing == 40
        assert bm.resolve == 20

    def test_out_of_range_clamped_high(self):
        """Values above 100 must be clamped to 100."""
        bm = BeatMap.from_dict({"tension": 150, "longing": 200, "resolve": 101})
        assert bm.tension == 100
        assert bm.longing == 100
        assert bm.resolve == 100

    def test_out_of_range_clamped_low(self):
        """Negative values must be clamped to 0."""
        bm = BeatMap.from_dict({"tension": -10, "longing": -1, "resolve": -50})
        assert bm.tension == 0
        assert bm.longing == 0
        assert bm.resolve == 0

    def test_boundary_values(self):
        """0 and 100 must be accepted exactly."""
        bm = BeatMap.from_dict({"tension": 0, "longing": 100, "resolve": 0})
        assert bm.tension == 0
        assert bm.longing == 100
        assert bm.resolve == 0


# ---------------------------------------------------------------------------
# BeatMap.to_dict — round-trip fidelity
# ---------------------------------------------------------------------------

class TestBeatMapToDict:
    def test_round_trip(self):
        original = BeatMap(tension=60, longing=45, resolve=80)
        d = original.to_dict()
        reconstructed = BeatMap.from_dict(d)
        assert reconstructed.tension == 60
        assert reconstructed.longing == 45
        assert reconstructed.resolve == 80

    def test_dict_has_exact_keys(self):
        d = BeatMap(tension=1, longing=2, resolve=3).to_dict()
        assert set(d.keys()) == {"tension", "longing", "resolve"}

    def test_dict_values_are_ints(self):
        d = BeatMap(tension=70, longing=50, resolve=30).to_dict()
        for key in ("tension", "longing", "resolve"):
            assert isinstance(d[key], int), f"{key} should be int, got {type(d[key])}"


# ---------------------------------------------------------------------------
# BeatMap.dominant_emotion
# ---------------------------------------------------------------------------

class TestDominantEmotion:
    def test_tension_wins(self):
        assert BeatMap(tension=90, longing=40, resolve=20).dominant_emotion() == "tension"

    def test_longing_wins(self):
        assert BeatMap(tension=30, longing=80, resolve=20).dominant_emotion() == "longing"

    def test_resolve_wins(self):
        assert BeatMap(tension=20, longing=30, resolve=90).dominant_emotion() == "resolve"

    def test_all_equal_returns_tension(self):
        """Tie → Python dict ordering guarantees 'tension' is first."""
        assert BeatMap(tension=50, longing=50, resolve=50).dominant_emotion() == "tension"

    def test_all_zero_returns_tension(self):
        assert BeatMap(tension=0, longing=0, resolve=0).dominant_emotion() == "tension"


# ---------------------------------------------------------------------------
# BeatMap.arc_description
# ---------------------------------------------------------------------------

class TestArcDescription:
    def test_tension_arc(self):
        desc = BeatMap(tension=80, longing=20, resolve=10).arc_description()
        assert desc == "High-stakes confrontation arc"

    def test_longing_arc(self):
        desc = BeatMap(tension=20, longing=80, resolve=10).arc_description()
        assert desc == "Aching desire arc"

    def test_resolve_arc(self):
        desc = BeatMap(tension=20, longing=10, resolve=80).arc_description()
        assert desc == "Redemptive resolve arc"


# ---------------------------------------------------------------------------
# BeatMap.apply_revision — keyword heuristics
# ---------------------------------------------------------------------------

class TestApplyRevision:
    def test_darker_raises_tension_lowers_resolve(self):
        bm = BeatMap(tension=50, longing=50, resolve=50)
        result = bm.apply_revision("make it darker")
        assert result.tension == 75   # +25
        assert result.resolve == 30   # -20

    def test_hopeful_raises_resolve_lowers_tension(self):
        bm = BeatMap(tension=50, longing=50, resolve=50)
        result = bm.apply_revision("add hope, make it hopeful")
        assert result.resolve == 75   # +25
        assert result.tension == 35   # -15

    def test_romantic_raises_longing_lowers_tension(self):
        bm = BeatMap(tension=50, longing=50, resolve=50)
        result = bm.apply_revision("make it romantic")
        assert result.longing == 75   # +25
        assert result.tension == 35   # -15

    def test_tense_raises_tension(self):
        bm = BeatMap(tension=50, longing=50, resolve=50)
        result = bm.apply_revision("raise tension, make it more tense")
        assert result.tension == 80   # +30

    def test_melancholy_raises_longing_lowers_resolve(self):
        bm = BeatMap(tension=50, longing=50, resolve=50)
        result = bm.apply_revision("make it melancholy")
        assert result.longing == 70   # +20
        assert result.resolve == 40   # -10

    def test_slow_lowers_tension_raises_longing(self):
        bm = BeatMap(tension=50, longing=50, resolve=50)
        result = bm.apply_revision("slow it down")
        assert result.tension == 30   # -20
        assert result.longing == 60   # +10

    def test_unrecognised_directive_unchanged(self):
        """Unknown directive must leave beat map untouched."""
        bm = BeatMap(tension=60, longing=40, resolve=20)
        result = bm.apply_revision("add a dog")
        assert result.tension == 60
        assert result.longing == 40
        assert result.resolve == 20

    def test_empty_directive_unchanged(self):
        bm = BeatMap(tension=60, longing=40, resolve=20)
        result = bm.apply_revision("")
        assert result.tension == 60
        assert result.longing == 40
        assert result.resolve == 20

    def test_case_insensitive(self):
        """Keyword matching must be case-insensitive."""
        bm = BeatMap(tension=50, longing=50, resolve=50)
        result = bm.apply_revision("DARKER")
        assert result.tension == 75

    def test_clamping_prevents_overflow(self):
        """Starting at 95, 'darker' adds 25 → must be clamped to 100."""
        bm = BeatMap(tension=95, longing=50, resolve=50)
        result = bm.apply_revision("darker")
        assert result.tension == 100

    def test_clamping_prevents_underflow(self):
        """Starting at 10, 'hopeful' subtracts 15 from tension → must be clamped to 0."""
        bm = BeatMap(tension=10, longing=50, resolve=50)
        result = bm.apply_revision("hopeful")
        assert result.tension == 0

    def test_returns_new_instance(self):
        """apply_revision must not mutate the original BeatMap."""
        bm = BeatMap(tension=50, longing=50, resolve=50)
        result = bm.apply_revision("darker")
        assert bm.tension == 50   # original unchanged
        assert result.tension == 75
