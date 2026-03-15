"""
Beat Map module — tracks and analyzes the emotional arc of a scene.
Scores: tension (conflict/pressure), longing (desire/yearning), resolve (closure/determination).
"""

from dataclasses import dataclass, asdict


@dataclass
class BeatMap:
    tension: int   # 0-100 — conflict, dread, suspense
    longing: int   # 0-100 — desire, yearning, absence
    resolve: int   # 0-100 — determination, closure, catharsis

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BeatMap":
        def _clamp(val, default: int = 50) -> int:
            """Convert to int and clamp to [0, 100]. Accepts int, float, or numeric string."""
            return max(0, min(100, int(float(val))))

        return cls(
            tension=_clamp(data.get("tension", 50)),
            longing=_clamp(data.get("longing", 50)),
            resolve=_clamp(data.get("resolve", 50)),
        )

    def dominant_emotion(self) -> str:
        scores = {"tension": self.tension, "longing": self.longing, "resolve": self.resolve}
        return max(scores, key=scores.get)

    def arc_description(self) -> str:
        dom = self.dominant_emotion()
        if dom == "tension":
            return "High-stakes confrontation arc"
        elif dom == "longing":
            return "Aching desire arc"
        else:
            return "Redemptive resolve arc"

    def apply_revision(self, directive: str) -> "BeatMap":
        """
        Nudge scores based on plain-language revision directives.
        The agent will regenerate a proper beat map via LLM, but this
        provides an immediate preview delta for the UI.
        """
        directive = directive.lower()
        t, lo, r = self.tension, self.longing, self.resolve

        if any(w in directive for w in ["darker", "grim", "bleak", "brutal"]):
            t = min(100, t + 25)
            r = max(0, r - 20)
        elif any(w in directive for w in ["hopeful", "lighter", "uplifting"]):
            r = min(100, r + 25)
            t = max(0, t - 15)
        elif any(w in directive for w in ["romantic", "tender", "intimate"]):
            lo = min(100, lo + 25)
            t = max(0, t - 15)
        elif any(w in directive for w in ["tense", "urgent", "frantic"]):
            t = min(100, t + 30)
        elif any(w in directive for w in ["melancholy", "sad", "mournful"]):
            lo = min(100, lo + 20)
            r = max(0, r - 10)
        elif any(w in directive for w in ["slow", "meditative", "quiet"]):
            t = max(0, t - 20)
            lo = min(100, lo + 10)

        return BeatMap(tension=t, longing=lo, resolve=r)
