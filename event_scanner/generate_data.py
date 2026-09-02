"""
Generate a labeled dataset of REAL vs FAKE event posts.

Each post is an EventPost plus a ground-truth label. The fake posts are seeded
with the same signal templates our scanner looks for, so the model learns to
recognise real patterns (we also add real-event phrasing so it isn't trivial).
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scanner.features import EventPost  # noqa: E402


# ---- Real event templates --------------------------------------------------
REAL_TITLES = [
    "Annual Tech Developers Conference 2026",
    "Chennai Food & Music Festival",
    "Marathon for Clean Rivers",
    "Indie Rock Night - Live",
    "Startup Pitch Demo Day",
    "International Yoga Day Celebration",
    "Art & Craft Workshop for Kids",
    "City Half Marathon & Fun Run",
    "Photography Masterclass Weekend",
    "Community Theatre Show",
    "Career Fair for Engineering Graduates",
    "Science Exhibition - Open to Public",
    "Standup Comedy Open Mic Night",
    "Classical Dance Recital",
]

REAL_DESC_OPENERS = [
    "We are excited to announce our annual celebration, now in its 8th year.",
    "Organised by the City Cultural Trust, this is an open admissions event.",
    "The event will be held at the Grand Convention Hall, MG Road.",
    "Ticketed via our official booking partner, BookMyShow.",
    "Venue: Riverside Amphitheatre, Gate 2. Address will be on your e-ticket.",
    "Fees are waived for students with a valid ID card.",
    "Gate opens at 6 PM; registration closes 30 minutes before entry.",
    "Confirmed with the local municipality for public entry.",
]

REAL_DESC_CLOSERS = [
    "For full schedule, visit our verified page and official website.",
    "Your e-ticket QR code will be emailed after confirmed booking.",
    "Free entry for children under 12 accompanied by an adult.",
    "For queries, contact our helpdesk between 9 AM and 6 PM.",
]

# ---- Fake event templates --------------------------------------------------
FAKE_TITLES = [
    "FREE iPhone 16 Giveaway - WIN TODAY!!!",
    "URGENT: Limited slots Earn Rs 5000 daily from home",
    "Jackpot Lottery WIN RS 10 LAKH cash prize",
    "FREE tickets to the sold out concert - click now",
    "100% GUARANTEED government job alert, pay Rs 99 registration",
    "Get a free trip to Dubai, share to claim!!!",
    "Secret star night - venue hidden, DM us for entry",
    "Work from home, earn money, no cost, apply urgently",
    "WIN FREE GOLD COINS - Hurry! only 10 left",
    "Free insurance cashback offer, WhatsApp us to claim",
]

FAKE_DESC_OPENERS = [
    "URGENT!!! Only today! This offer expires soon, act now!!!",
    "Congratulations!!! You have been selected to win free reward.",
    "Limited slots left, register now, you won't regret it!!",
    "100% free, no cost, guaranteed payout, hurry hurry!!",
    "To claim, pay a small booking fee of Rs 99 via UPI and confirm.",
    "Details and venue will be shared on WhatsApp after you message us.",
    "This is a top secret event, location hidden, share to unlock!!",
    "Click the link below to claim your prize before it's gone!!",
    "Tag your friends and forward this to 5 people to qualify!!!",
    "Easy money, work from home, get paid immediately, no experience needed.",
]

FAKE_DESC_CLOSERS = [
    "WhatsApp us now or lose your chance!!",
    "Don't wait, seats fill fast!!!",
    "Transfer the fee and your ticket is guaranteed.",
    "Share this post to enter the draw!!!",
    "Message us on Telegram for the hidden surprise location.",
]


def _make(post: EventPost, label: int) -> tuple:
    return (post, label)


def generate(n_real: int = 300, n_fake: int = 300, seed: int = 42) -> list:
    rng = random.Random(seed)
    data: list = []
    platforms = ["facebook", "instagram", "twitter", "eventbrite", "meetup", "bookmyshow"]

    # REAL posts
    for _ in range(n_real):
        title = rng.choice(REAL_TITLES)
        desc = " ".join([
            rng.choice(REAL_DESC_OPENERS),
            rng.choice(REAL_DESC_OPENERS),
            rng.choice(REAL_DESC_CLOSERS),
        ])
        p = EventPost(
            title=title,
            description=desc,
            platform=rng.choice(platforms),
            account_verified=rng.random() < 0.8,
            account_followers=rng.choice([200, 800, 3000, 12000, 45000, 120000]),
            account_age_days=rng.choice([60, 200, 800, 1500, 3000]),
            has_official_ticketing_link=rng.random() < 0.85,
            has_venue_address=rng.random() < 0.9,
            event_date="2026-10-15",
            posted_at="2026-09-01",
            links=["https://bookmyshow.com/event"] if rng.random() < 0.7 else [],
        )
        data.append(_make(p, 0))  # 0 = REAL

    # FAKE posts
    for _ in range(n_fake):
        title = rng.choice(FAKE_TITLES)
        desc = " ".join([
            rng.choice(FAKE_DESC_OPENERS),
            rng.choice(FAKE_DESC_OPENERS),
            rng.choice(FAKE_DESC_CLOSERS),
        ])
        p = EventPost(
            title=title,
            description=desc,
            platform=rng.choice(platforms),
            account_verified=rng.random() < 0.05,          # almost never verified
            account_followers=rng.choice([0, 5, 20, 60, 150, 400]),
            account_age_days=rng.choice([2, 5, 12, 20, 45]),
            has_official_ticketing_link=False,             # never official
            has_venue_address=rng.random() < 0.1,
            event_date="",                                   # often no date
            posted_at="",
            links=rng.choice([
                ["https://bit.ly/3xYz89"],
                ["https://free-tickets.xyz/claim"],
                ["https://tinyurl.com/win24"],
                [],
            ]),
        )
        data.append(_make(p, 1))  # 1 = FAKE

    rng.shuffle(data)
    return data


if __name__ == "__main__":
    import json
    d = generate()
    real = sum(1 for _, l in d if l == 0)
    fake = sum(1 for _, l in d if l == 1)
    print(f"Generated {len(d)} posts  →  {real} REAL, {fake} FAKE")
    for p, l in d[:3]:
        print(f"\n[{ 'FAKE' if l else 'REAL' }] {p.title}")
        print("  ", p.description[:120], "...")
