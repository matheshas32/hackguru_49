"""
CLI to scan one or more event posts using a trained model.

Examples:
    python scan_cli.py --train
    python scan_cli.py --model models/event_scanner_model.joblib --file posts.json
    python scan_cli.py --model models/event_scanner_model.joblib \
        --title "FREE iPhone Giveaway WIN NOW" \
        --desc "URGENT limited slots, pay Rs99 to win, DM us" \
        --platform facebook --followers 5
    cat post.json | python scan_cli.py --model models/event_scanner_model.joblib --stdin
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scanner.features import EventPost                    # noqa: E402
from scanner.model import train, EventScannerModel        # noqa: E402
from scanner.verify import scan_post, print_report        # noqa: E402
from data.generate_data import generate                   # noqa: E402


def build_post(a) -> EventPost:
    return EventPost(
        title=a.title, description=a.desc, platform=a.platform,
        account_verified=a.verified, account_followers=a.followers,
        account_age_days=a.account_age, has_official_ticketing_link=a.official_link,
        has_venue_address=a.venue_address, event_date=a.event_date or "",
        links=a.links or [],
    )


def main():
    p = argparse.ArgumentParser(description="AI Event Quality & Verification Scanner")
    p.add_argument("--model", default=str(Path(__file__).parent / "models" / "event_scanner_model.joblib"))
    p.add_argument("--train", action="store_true", help="retrain + save the model")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--stdin", dest="stdin", action="store_true",
                   help="read JSON posts from stdin (list of post objects)")
    p.add_argument("--file", help="path to a JSON file containing a list of posts")
    p.add_argument("--title")
    p.add_argument("--desc")
    p.add_argument("--platform", default="facebook")
    p.add_argument("--verified", action="store_true")
    p.add_argument("--followers", type=int, default=0)
    p.add_argument("--account-age", dest="account_age", type=int, default=0)
    p.add_argument("--official-link", dest="official_link", action="store_true")
    p.add_argument("--venue-address", dest="venue_address", action="store_true")
    p.add_argument("--event-date", dest="event_date", default="")
    p.add_argument("--link", dest="links", action="append", default=[])

    a = p.parse_args()

    if a.train:
        print("Retraining model ...")
        data = generate(seed=a.seed)
        posts = [x for x, _ in data]
        labels = [l for _, l in data]
        model = train(posts, labels)
        path = model.save(a.model)
        print(f"Saved -> {path}")
        return

    if not Path(a.model).exists():
        print("Model not found. Run with --train first, e.g.:")
        print("  python scan_cli.py --train")
        return

    model = EventScannerModel.load(a.model)

    # Gather input posts
    posts: list = []
    if a.stdin:
        posts = json.load(sys.stdin)
    elif a.file:
        posts = json.load(Path(a.file).open())
    elif a.title or a.desc:
        posts = [build_post(a)]

    if not posts:
        print("Provide posts via --stdin, --file, or --title/--desc.")
        return

    for obj in posts:
        post = obj if isinstance(obj, EventPost) else EventPost(**obj)
        print_report(scan_post(post, model))
        print()


if __name__ == "__main__":
    main()
