#!/usr/bin/env python3
"""
Research Newsletter — CLI: Add/manage subscribers
"""
import sys
import os
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.db import init_db, add_subscriber, get_active_subscribers
from src.core.classifier import TopicClassifier

def main():
    parser = argparse.ArgumentParser(description="Manage subscribers")
    sub = parser.add_subparsers(dest="command")

    # Add
    add_p = sub.add_parser("add", help="Add a subscriber")
    add_p.add_argument("--email", required=True)
    add_p.add_argument("--topics", required=True, help="Comma-separated topic keys")
    add_p.add_argument("--list-topics", action="store_true", help="Show available topics")

    # List
    sub.add_parser("list", help="List active subscribers")

    # Remove
    rm_p = sub.add_parser("remove", help="Remove a subscriber")
    rm_p.add_argument("--email", required=True)

    args = parser.parse_args()
    init_db()

    if args.command == "add":
        if args.list_topics:
            classifier = TopicClassifier()
            classifier.load_categories()
            print("Available topics:")
            for domain, topics in classifier.categories.items():
                print(f"\n  {domain}:")
                for topic in topics:
                    print(f"    - {topic}")
            return

        topics = [t.strip() for t in args.topics.split(",")]
        add_subscriber(args.email, topics)
        print(f"Added {args.email} with topics: {', '.join(topics)}")

    elif args.command == "list":
        subs = get_active_subscribers()
        print(f"\nActive subscribers ({len(subs)}):")
        for s in subs:
            print(f"  {s['email']}: {', '.join(s['topics'])}")

    elif args.command == "remove":
        from src.core.db import get_db
        conn = get_db()
        conn.execute("DELETE FROM subscribers WHERE email=?", (args.email,))
        conn.commit()
        conn.close()
        print(f"Removed {args.email}")

if __name__ == "__main__":
    main()
