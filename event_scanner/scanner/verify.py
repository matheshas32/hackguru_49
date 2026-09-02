"""
Verification scanner: score a single event post (or a batch) and explain WHY.

Combines the machine-learning probability with the interpretable rule-based
signals into a transparent decision + a readable report.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List

from .features import EventPost, extract_signals, weighted_signal_score
from .model import EventScannerModel


@dataclass
class Verdict:
    event_title: str
    fake_probability: float          # model P(FAKE)
    rule_score: float                # weighted signal score
    final: str                       # REAL / FAKE / UNCERTAIN
    confidence: float
    signals: List[dict]

    def to_dict(self):
        return asdict(self)


def decide(probability: float, rule_score: float) -> tuple:
    """Combine model probability + rule score -> final label + confidence."""
    # Anchor on the model, nudge with rule score
    score = 0.7 * probability + 0.3 * (1 / (1 + 2.718 ** (-rule_score)))
    if score >= 0.6:
        label = "FAKE"
        conf = min(0.99, 0.5 + abs(score - 0.5) * 1.6)
    elif score <= 0.4:
        label = "REAL"
        conf = min(0.99, 0.5 + abs(score - 0.5) * 1.6)
    else:
        label = "UNCERTAIN"
        conf = 0.5 + (0.5 - abs(score - 0.5)) * 0.4
    return label, round(conf, 3)


def scan_post(post: EventPost, model: EventScannerModel) -> Verdict:
    """Run one post through the full scanner."""
    prob = float(model.predict_proba([post])[0])
    sigs = extract_signals(post)
    rule_score = weighted_signal_score(sigs)
    label, conf = decide(prob, rule_score)

    # Rank signals by |weight*direction|, most decisive first
    sigs_sorted = sorted(sigs, key=lambda s: abs(s.weight * s.direction), reverse=True)
    signals = [
        {"name": s.name, "category": s.category, "direction": s.direction,
         "weight": round(s.weight, 2), "lean": s.label, "note": s.note}
        for s in sigs_sorted
    ]
    return Verdict(post.title, round(prob, 3), round(rule_score, 3),
                   label, conf, signals)


def scan_batch(posts: List[EventPost], model: EventScannerModel) -> List[Verdict]:
    return [scan_post(p, model) for p in posts]


def print_report(verdict: Verdict):
    bar = "=" * 64
    flag = {"REAL": "🟢", "FAKE": "🔴", "UNCERTAIN": "🟡"}[verdict.final]
    print(bar)
    print(f"{flag}  VERDICT: {verdict.final}   "
          f"(confidence {verdict.confidence:.0%})")
    print(f"    Event: {verdict.event_title}")
    print(f"    Model P(fake): {verdict.fake_probability:.3f}")
    print(f"    Rule signal score: {verdict.rule_score:+.2f}  "
          f"(+ = leans fake, - = leans real)")
    print(bar)
    if not verdict.signals:
        print("    No notable verification signals detected.")
    for i, s in enumerate(verdict.signals, 1):
        mark = "+" if s["direction"] > 0 else "-"
        print(f"  {i:>2}. [{s['lean']:>4}] {s['name']:<28} weight {s['weight']:+.1f}")
        print(f"        -> {s['note']}")
    print(bar)
