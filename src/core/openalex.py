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

    def search_works(self, query, from_date=None, to_date=None, select=None, limit=20):
        params = {
            "search": query,
            "filter": f"type:article",
            "sort": "cited_by_count:desc",
            "per_page": limit,
            "select": "doi,title,abstract_inverted_index,publication_date,cited_by_count,referenced_works,locations,authorships,primary_location"
        }
        if from_date:
            params["filter"] += f",from_publication_date:{from_date}"
        if to_date:
            params["filter"] += f",to_publication_date:{to_date}"

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self.base_url}/works?{query_string}"

        import urllib.parse
        url = f"{self.base_url}/works?search={urllib.parse.quote(query)}&filter=type:article&sort=cited_by_count:desc&per_page={limit}&select=doi,title,abstract_inverted_index,publication_date,cited_by_count,authorships,primary_location"
        if from_date:
            url += f"&filter=from_publication_date:{from_date}"

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        return data.get("results", [])

if __name__ == "__main__":
    client = OpenAlexClient()
    results = client.search_works("ADHS psychotherapie", limit=3)
    for r in results:
        print(f"Title: {r['title']}\nDate: {r['publication_date']}\nCitations: {r['cited_by_count']}\n---")
