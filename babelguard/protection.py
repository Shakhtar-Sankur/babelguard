"""The protection gap: how well a detector protects people, language by language.

For each language (or any other grouping), two numbers matter to the people who get the messages:

- detection rate: of the scams they receive, how many the detector flags;
- false-alarm rate: of their genuine messages (bank alerts, OTPs, deliveries), how many it flags.

Both come with 95% Wilson score intervals, which stay honest for small samples, and groups with
too few messages are marked instead of ranked. The gap is each language's detection rate minus
English's.
"""
import math
from collections import defaultdict
from dataclasses import dataclass

MIN_N = 30


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes in n trials; (nan, nan) when n == 0."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


@dataclass
class Rates:
    scams: int
    caught: int
    genuine: int
    false_alarms: int

    @property
    def detection(self):
        return self.caught / self.scams if self.scams else float("nan")

    @property
    def false_alarm(self):
        return self.false_alarms / self.genuine if self.genuine else float("nan")

    def as_dict(self):
        lo, hi = wilson(self.caught, self.scams)
        flo, fhi = wilson(self.false_alarms, self.genuine)
        return {"scams": self.scams, "detection": _r(self.detection), "detection_ci": [_r(lo), _r(hi)],
                "genuine": self.genuine, "false_alarm": _r(self.false_alarm), "false_alarm_ci": [_r(flo), _r(fhi)],
                "enough_data": self.scams >= MIN_N}


def _r(x):
    return None if x != x else round(x, 4)


def rates(labels, flagged):
    """Rates over parallel lists: labels in {'scam', 'legit', ...}, flagged booleans. Other labels
    (spam, unknown) count in neither rate."""
    s = c = g = f = 0
    for lab, hit in zip(labels, flagged):
        if lab == "scam":
            s += 1
            c += bool(hit)
        elif lab == "legit":
            g += 1
            f += bool(hit)
    return Rates(s, c, g, f)


def by_group(records, flagged, key=lambda r: r.lang):
    """{group: Rates} for records and parallel flags, plus the gap to English where it exists."""
    labs, hits = defaultdict(list), defaultdict(list)
    for r, h in zip(records, flagged):
        labs[key(r)].append(r.label)
        hits[key(r)].append(h)
    table = {g: rates(labs[g], hits[g]) for g in labs}
    en = table.get("en")
    out = {}
    for g, rt in sorted(table.items(), key=lambda kv: -kv[1].scams):
        d = rt.as_dict()
        d["gap_vs_english"] = (_r(rt.detection - en.detection)
                               if en is not None and en.scams and rt.scams else None)
        out[g] = d
    return out
