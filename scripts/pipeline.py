#!/usr/bin/env python3
"""
Research Newsletter — Full Pipeline
Fetches papers for all active subscriber topics, generates digests, and sends emails.
"""
import sys
import os
import json
import argparse
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.openalex import OpenAlexClient
from src.core.classifier import TopicClassifier
from src.core.db import init_db, get_active_subscribers, add_subscriber
from src.email.generator import generate_digest_html

def main():
    parser = argparse.ArgumentParser(description="Research Newsletter Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and score only, don't send")
    parser.add_argument("--topics", type=str, default=None, help="Comma-separated topics to process (default: all)")
    parser.add_argument("--limit", type=int, default=5, help="Max papers per topic")
    parser.add_argument("--from-date", type=str, default=None, help="Start date (default: 7 days ago)")
    parser.add_argument("--debug", action="store_true", help="Print debug info")
    args = parser.parse_args()

    if not args.from_date:
        from datetime import timedelta
        args.from_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    init_db()
    subs = get_active_subscribers()

    # Collect topics across all subscribers
    if args.topics:
        topic_list = [t.strip() for t in args.topics.split(",")]
    else:
        topic_list = set()
        for sub in subs:
            topic_list.update(sub['topics'])
        topic_list = list(topic_list)

    if not topic_list:
        print("No topics to process.")
        return

    print(f"Processing {len(topic_list)} topics for {len(subs)} subscribers...")
    print(f"Fetching papers from {args.from_date}")

    client = OpenAlexClient()
    classifier = TopicClassifier()
    classifier.load_categories()

    results = {}

    for topic in topic_list:
        if args.debug:
            print(f"\n--- Topic: {topic} ---")

        # Get keywords
        keywords = " OR ".join(classifier.categories.get(topic, [topic]))
        
        try:
            raw_papers = client.search_works(keywords, from_date=args.from_date, limit=args.limit * 3)
        except Exception as e:
            print(f"Error fetching {topic}: {e}")
            continue

        # Score and filter
        scored = []
        for paper in raw_papers:
            score = classifier.score_paper(paper, [topic])
            if score > 0.05:  # Minimum relevance threshold
                scored.append((score, paper))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_papers = [p for _, p in scored[:args.limit]]

        results[topic] = {
            "papers": top_papers,
            "count": len(top_papers),
            "subscribers": [s['email'] for s in subs if topic in s['topics']]
        }

        if args.debug:
            print(f"  Found {len(raw_papers)} papers, {len(scored)} scored > 0.05, top {len(top_papers)}")
            for p in top_papers[:3]:
                print(f"    - {p.get('title', 'N/A')[:80]}")

    # Generate and send
    if not args.dry_run:
        from src.email.sender import send_email
        sent_count = 0
        for sub in subs:
            sub_topics = sub['topics']
            all_papers = []
            for topic in sub_topics:
                if topic in results and results[topic]['papers']:
                    all_papers.extend(results[topic]['papers'])
            
            if not all_papers:
                continue

            # Deduplicate by DOI
            seen = set()
            unique = []
            for p in all_papers:
                doi = p.get('doi', '')
                if doi not in seen:
                    seen.add(doi)
                    unique.append(p)

            if not unique:
                continue

            # Group by topic for digest
            topic_groups = defaultdict(list)
            for p in unique:
                for topic in sub_topics:
                    if topic in results and p in results[topic]['papers']:
                        topic_groups[topic].append(p)

            # Generate multi-topic digest
            html = generate_multi_topic_digest(topic_groups, args.from_date)
            
            try:
                send_email(sub['email'], f"ResearchPulse Weekly: {', '.join(sub_topics)}", html)
                sent_count += 1
                print(f"Sent to {sub['email']} ({len(unique)} papers across {len(topic_groups)} topics)")
            except Exception as e:
                print(f"Failed to send to {sub['email']}: {e}")

        print(f"\nDone. Sent {sent_count} digests.")
    else:
        print(f"\nDry run. Would send to {sum(len(v['subscribers']) for v in results.values())} subscribers.")
        for topic, data in results.items():
            print(f"  {topic}: {data['count']} papers for {len(data['subscribers'])} subscribers")

if __name__ == "__main__":
    main()
