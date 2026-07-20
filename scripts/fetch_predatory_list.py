#!/usr/bin/env python3
"""
Fetch the latest Beall's predatory publisher list from Cappellato et al. (2020) GitHub repo.
Outputs a cleaned JSON file of publisher names for the QC gate.

Source: https://github.com/cappellato/beall-predatory (Cappellato NM et al., 2020)
License: CC BY 4.0
"""
import csv
import json
import urllib.request
import sys
import os
from datetime import datetime, timezone

# Cappellato 2020 Beall's list update — raw CSV
SOURCE_URL = (
    "https://raw.githubusercontent.com/cappellato/beall-predatory/"
    "master/compiled_list.csv"
)

def fetch_predatory_list():
    """Download and parse the Beall's list CSV."""
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "ResearchPulse/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    
    reader = csv.DictReader(raw.strip().splitlines())
    publishers = set()
    
    for row in reader:
        # Extract publisher name — field varies by row
        name = (row.get("Publisher name") or row.get("Publisher") or "").strip()
        if name and len(name) > 2:
            publishers.add(name.lower())
    
    return publishers

def main():
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src/core/predatory_publishers.json"
    )
    
    print(f"Fetching from: {SOURCE_URL}")
    publishers = fetch_predatory_list()
    sorted_list = sorted(publishers)
    
    payload = {
        "source": "Cappellato et al. 2020 (Beall's list update)",
        "url": SOURCE_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(sorted_list),
        "publishers": sorted_list
    }
    
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    
    print(f"Saved {len(sorted_list)} publishers to {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
