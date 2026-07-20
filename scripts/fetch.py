#!/usr/bin/env python3
"""
CLI: Fetch latest papers for a topic and generate digest
"""
import sys
import os
import json
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.openalex import OpenAlexClient
from src.core.classifier import TopicClassifier
from src.core.db import init_db, get_active_subscribers
from src.email.generator import generate_digest_html

def main():
    parser = argparse.ArgumentParser(description="Fetch research papers")
    parser.add_argument("--topic", type=str, required=True, help="Topic key (e.g., adhs)")
    parser.add_argument("--limit", type=int, default=5, help="Max papers to return")
    parser.add_argument("--output", choices=["json", "html", "send"], default="json")
    parser.add_argument("--from-date", type=str, default="2026-07-01")
    args = parser.parse_args()

    client = OpenAlexClient()
    classifier = TopicClassifier()
    classifier.load_categories()

    # Get keywords for the topic
    keywords = " OR ".join(classifier.categories.get(args.topic, [args.topic]))
    
    results = client.search_works(keywords, from_date=args.from_date, limit=args.limit)
    
    # Score and filter
    scored = []
    for r in results:
        score = classifier.score_paper(r, [args.topic])
        if score > 0.1:
            scored.append((score, r))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    top_papers = [p for _, p in scored[:args.limit]]

    if args.output == "json":
        print(json.dumps(top_papers, indent=2))
    elif args.output == "html":
        html = generate_digest_html(top_papers, args.topic, "2026-07-20")
        print(html)
    elif args.output == "send":
        init_db()
        subs = get_active_subscribers()
        from src.email.sender import send_email
        for sub in subs:
            if args.topic in sub['topics']:
                html = generate_digest_html(top_papers, args.topic, "2026-07-20")
                send_email(sub['email'], f"Research Update: {args.topic}", html)
                print(f"Sent to {sub['email']}")

if __name__ == "__main__":
    main()
