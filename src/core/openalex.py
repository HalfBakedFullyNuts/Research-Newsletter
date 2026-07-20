import json
import urllib.parse
import urllib.request
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import OPENALEX_DELAY

class OpenAlexClient:
    def __init__(self):
        self.base_url = "https://api.openalex.org"
        self.delay = OPENALEX_DELAY

    def search_works(self, query, from_date=None, to_date=None, limit=20):
        filters = ["type:article"]
        if from_date:
            filters.append(f"from_publication_date:{from_date}")
        if to_date:
            filters.append(f"to_publication_date:{to_date}")
        
        url = (
            f"{self.base_url}/works?"
            f"search={urllib.parse.quote(query)}&"
            f"filter={','.join(filters)}&"
            f"sort=relevance_score:desc&"
            f"per_page={limit}&"
            f"select=doi,title,abstract_inverted_index,publication_date,cited_by_count,authorships,primary_location"
        )
        
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
        
        return data.get("results", [])

if __name__ == "__main__":
    client = OpenAlexClient()
    results = client.search_works("ADHD attention deficit", from_date="2026-07-01", limit=3)
    for r in results:
        print(f"Title: {r['title']}\nDate: {r['publication_date']}\nCitations: {r['cited_by_count']}\n---")
