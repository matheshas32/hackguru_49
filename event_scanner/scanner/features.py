"""
Feature extraction + interpretable "verification signals" for event posts.

Each event post is turned into a numeric feature vector for the ML model AND
into a list of human-readable signals (red flags / green flags) so the scanner
can explain *why* it thinks a post is fake or real.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Vocabularies / patterns for hand-crafted signals
# ---------------------------------------------------------------------------

URGENCY_WORDS = [
    "urgent", "hurry", "limited", "only today", "act now", "last chance",
    "don't miss", "dont miss", "book now", "register fast", "limited seats",
    "few slots", "expires", "deadline", "immediately", "right away",
    "grab it", "before it's gone", "before it is gone",
]

TOO_GOOD_WORDS = [
    "100% free", "no cost", "no fees", "guaranteed", "100% guaranteed",
    "win free", "jackpot", "prize", "lucky", "giveaway", "gift", "reward",
    "free iphone", "free trip", "free gold", "free insurance", "cash prize",
    "cash prize", "lottery", "refund", "double your", "earn money",
    "work from home", "earn from home", "get paid", "profit",
]

PAYMENT_WORDS = [
    "booking fee", "registration fee", "deposit", "advance payment",
    "pay now", "pay a small", "send money", "transfer money", "send rs",
    "bank account", "scan and pay", "qr code",
]

CONTACT_ONLY_WORDS = [
    "whatsapp", "whatsapp us", "telegram", "dm us", "inbox us", "message us",
    "ping us", "whatsapp only", "call us", "sms", "direct message",
]

VAGUE_WORDS = [
    "somewhere", "near the city", "near the mall", "some location",
    "venue will be shared", "address shared later", "secret venue",
    "will reveal", "location hidden", "top secret", "surprise location",
    "details on telegram", "details on whatsapp",
]

EARN_MONEY = ["earn money", "make money", "earn daily", "easy money", "get rich"]

SHARE_BAIT = ["share", "forward", "tag your friends", "tag friends", "spread the word",
              "share this", "share to", "repost", "retweet"]

SUSPICIOUS_DOMAINS = [
    "bit.ly", "tinyurl", "t.co", "goo.gl", "ow.ly", "is.gd", "cutt.ly",
    "tiny.cc", "s.id", "rb.gy", "rebrand.ly", "free-tickets.xyz",
    "event-tickets-now.com", "claimnow.xyz", "prize-winner.info",
]

EXCESS_PUNCT = re.compile(r"[!]{2,}|\?{2,}|[{}$]{1,}|[.@#]{2,}")
ALL_CAPS_RUN = re.compile(r"\b[A-Z]{4,}\b")


@dataclass
class EventPost:
    """Normalized representation of an event post to be scored."""
    title: str
    description: str
    platform: str = "unknown"          # facebook, instagram, twitter, eventbrite, ...
    account_verified: bool = False
    account_followers: int = 0
    account_age_days: int = 0
    has_official_ticketing_link: bool = False
    event_date: str = ""               # optional ISO date, used for recency checks
    posted_at: str = ""                # optional ISO datetime
    has_venue_address: bool = False
    links: List[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return f"{self.title}. {self.description}"


@dataclass
class Signal:
    name: str
    category: str          # "content" | "source" | "link" | "payment" | "contact"
    weight: float          # magnitude of the signal
    direction: int         # +1 = pushes toward FAKE, -1 = pushes toward REAL
    note: str              # human-readable explanation

    @property
    def label(self) -> str:
        return "FAKE" if self.direction > 0 else "REAL"


def _count_any(text: str, words) -> int:
    low = text.lower()
    return sum(1 for w in words if w in low)


def extract_signals(post: EventPost) -> List[Signal]:
    """Produce interpretable verification signals from the raw post."""
    text = post.full_text
    low = text.lower()
    sig: List[Signal] = []

    def add(name, category, weight, direction, note):
        sig.append(Signal(name, category, weight, direction, note))

    # ---- Content: urgency -------------------------------------------------
    u = _count_any(text, URGENCY_WORDS)
    if u:
        add("urgency_language", "content", min(u * 0.6, 2.0), +1,
            f"Uses urgency/limited-offer language ({u} instances) common in scams that pressure you to act fast.")

    # ---- Content: too-good-to-be-true ------------------------------------
    tg = _count_any(text, TOO_GOOD_WORDS)
    if tg:
        add("too_good_to_be_true", "content", min(tg * 0.5, 2.0), +1,
            f"Offers something 'free'/guaranteed/lucrative ({tg} phrases) — high-value bait is a classic fake-signal.")

    # ---- Content: earn money ---------------------------------------------
    em = _count_any(text, EARN_MONEY)
    if em:
        add("earn_money_bait", "content", min(em * 1.2, 2.5), +1,
            "Promises easy income/money-making, a strong scam indicator.")

    # ---- Payment / deposit -----------------------------------------------
    p = _count_any(text, PAYMENT_WORDS)
    if p:
        add("upfront_payment_request", "payment", min(p * 1.0, 2.5), +1,
            f"Asks for an upfront fee/deposit ({p} payment words) — legitimate events usually don't require off-platform payment.")

    # ---- Contact only / no official channels -------------------------------
    c = _count_any(text, CONTACT_ONLY_WORDS)
    if c:
        add("contact_only_via_private_channel", "contact", min(c * 0.7, 2.0), +1,
            f"Directs you only to private messaging ({c} channels) rather than an official site — hard to verify & trace.")

    # ---- Share/forward bait -----------------------------------------------
    s = _count_any(text, SHARE_BAIT)
    if s:
        add("share_bait", "content", min(s * 0.6, 2.0), +1,
            f"Insists you 'share/forward' the post ({s} times) to spread content, typical of virality-driven fakery.")

    # ---- Vague location / hidden venue ------------------------------------
    v = _count_any(text, VAGUE_WORDS)
    if v:
        add("vague_or_hidden_venue", "content", min(v * 1.0, 2.0), +1,
            "Venue/location is vague, secret, or 'shared later' — real events have concrete details.")

    # ---- Excessive punctuation / CAPS -------------------------------------
    if EXCESS_PUNCT.search(text):
        add("excessive_punctuation", "content", 0.8, +1,
            "Heavy punctuation (!!, ???, $$$) is emotional manipulation, common in low-credibility spam.")
    caps = ALL_CAPS_RUN.findall(text)
    if len(caps) >= 3:
        add("aggressive_caps", "content", 0.7, +1,
            f"Aggressive ALL-CAPS emphasis ({len(caps)} words) signals hype/panic rather than factual detail.")

    # ---- Suspicious / shortened links -------------------------------------
    link_txt = " ".join(post.links) + " " + low
    for d in SUSPICIOUS_DOMAINS:
        if d in link_txt:
            add("suspicious_shortened_link", "link", 2.0, +1,
                f"Contains shortened/obscure link domain '{d}' that hides the real destination — unverifiable.")
            break

    # ---- Missing official ticketing link ------------------------------------
    if not post.has_official_ticketing_link and post.platform.lower() not in ("eventbrite", "meetup", "bookmyshow"):
        add("no_official_ticketing", "link", 1.0, +1,
            "No official ticketing/signup link provided — real organized events link to a trusted booking site.")
    else:
        add("official_ticketing_present", "link", 1.0, -1,
            "Has an official / trusted ticketing link.")

    # ---- Venue address -----------------------------------------------------
    if post.has_venue_address:
        add("venue_address_provided", "content", 1.0, -1,
            "Gives a concrete venue address — a credibility green flag.")
    else:
        add("venue_address_missing", "content", 0.6, +1,
            "No concrete venue address, making the event harder to verify.")

    # ---- Source credibility ------------------------------------------------
    if post.account_verified:
        add("verified_account", "source", 2.0, -1,
            "Post comes from a verified account — strong authenticity signal.")
    else:
        add("unverified_account", "source", 1.0, +1,
            "Post comes from an unverified account — easier to impersonate & harder to trust.")

    if post.account_followers >= 10_000:
        add("large_follower_base", "source", 1.0, -1,
            "Account has a substantial follower base (10k+) — more likely legitimate, established reach.")
    elif 0 < post.account_followers and post.account_followers < 100:
        add("small_follower_base", "source", 0.8, +1,
            "Very small follower base (<100) — a brand-new/one-off account, common for scam posts.")

    if post.account_age_days and post.account_age_days < 30:
        add("new_account", "source", 0.9, +1,
            f"Account is only {post.account_age_days} days old — scammers often spin up fresh accounts.")

    if not post.event_date and not post.posted_at:
        add("missing_dates", "content", 0.5, +1,
            "No event date or posting timestamp — hard to cross-check with calendars.")

    return sig


def weighted_signal_score(signals: List[Signal]) -> float:
    """Sum of weighted signals; >0 leans fake, <0 leans real."""
    return sum(s.weight * s.direction for s in signals)


# ---------------------------------------------------------------------------
# Numeric feature vector for the ML model
# ---------------------------------------------------------------------------
def extract_features(post: EventPost) -> List[float]:
    """Hand-crafted numeric features (independent of the TF-IDF text block)."""
    text = post.full_text
    low = text.lower()

    feats = [
        float(len(text) < 80),                                  # very short post
        float(_count_any(text, URGENCY_WORDS) > 0),
        float(_count_any(text, URGENCY_WORDS) >= 2),
        float(_count_any(text, TOO_GOOD_WORDS) > 0),
        float(_count_any(text, TOO_GOOD_WORDS) >= 2),
        float(_count_any(text, PAYMENT_WORDS) > 0),
        float(_count_any(text, CONTACT_ONLY_WORDS) > 0),
        float(_count_any(text, SHARE_BAIT) > 0),
        float(_count_any(text, EARN_MONEY) > 0),
        float(_count_any(text, VAGUE_WORDS) > 0),
        float(len(re.findall(r"[!?]{2,}", text))),              # excess punct count
        float(len(ALL_CAPS_RUN.findall(text)) >= 3),
        float(text.count("http") > 0),                          # has a link
        float(text.count("http") == 0),                         # no link
        float(any(d in low for d in SUSPICIOUS_DOMAINS)),
        float(post.has_official_ticketing_link),
        float(post.has_venue_address),
        float(post.account_verified),
        min(float(post.account_followers) / 100000.0, 1.0),
        float(post.account_age_days < 30),
        float(post.account_age_days >= 365),
        float(min(len(post.links), 3) / 3.0),
    ]
    return feats


FEATURE_NAMES = [
    "short_text", "urgency_1", "urgency_2", "freebie_1", "freebie_2",
    "payment", "private_contact", "share_bait", "earn_money", "vague_venue",
    "excess_punct", "aggressive_caps", "has_link", "no_link", "suspicious_domain",
    "official_ticketing", "venue_address", "verified_account", "follower_ratio",
    "new_account", "old_account", "link_count",
]
