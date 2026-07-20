import re

class TopicClassifier:
    """
    Scores research papers against a list of user-selected topics.
    """
    def __init__(self):
        self.categories = {} # Loaded from categories.json

    def load_categories(self, path="src/topics/categories.json"):
        import json
        try:
            with open(path) as f:
                data = json.load(f)
            # Handle both flat and nested category structures
            if any(isinstance(v, dict) for v in data.values()):
                # Nested: {domain: {topic: [keywords]}}
                flat = {}
                for domain, topics in data.items():
                    for topic, keywords in topics.items():
                        flat[topic] = keywords
                self.categories = flat
            else:
                self.categories = data
        except FileNotFoundError:
            print("Warning: categories.json not found, using defaults.")
            self.categories = self._get_defaults()

    def _get_defaults(self):
        return {
            "adhs": ["adhd", "attention deficit", "hyperactivity", "impulsivity"],
            "psychotherapy": ["cognitive behavioral", "schematherapy", "emdr", "trauma focused", "psychodynamic"],
            "trauma": ["ptsd", "complex trauma", "ace score", "childhood maltreatment"],
            "healthcare_ai": ["machine learning", "deep learning", "natural language processing", "clinical decision support"]
        }

    def score_paper(self, paper, selected_topics):
        """
        paper: dict from OpenAlex
        selected_topics: list of topic keys
        returns: float (0.0 to 1.0)
        """
        # Handle abstract: OpenAlex uses inverted_index (dict) or list
        abstract = paper.get("abstract_inverted_index", {})
        if isinstance(abstract, dict):
            text = " ".join(abstract.keys())
        elif isinstance(abstract, list):
            text = " ".join(str(x) for x in abstract)
        else:
            text = str(abstract)
        
        full_text = (paper.get("title", "") + " " + text).lower()
        
        total_relevance = 0
        total_words = len(full_text.split())
        if total_words == 0:
            return 0.0
        
        matched_keywords = 0
        for topic in selected_topics:
            keywords = self.categories.get(topic, [topic])
            for kw in keywords:
                import re
                count = len(re.findall(rf'\b{re.escape(kw)}\b', full_text))
                if count > 0:
                    matched_keywords += 1
                total_relevance += count * 2  # Each keyword match counts double
        
        # Bonus for keyword in title (strong signal)
        title_lower = paper.get("title", "").lower()
        for topic in selected_topics:
            for kw in self.categories.get(topic, []):
                if kw.lower() in title_lower:
                    total_relevance += 5
        
        # Score based on unique matched keywords and total word count
        unique_factor = matched_keywords / max(1, len(selected_topics))
        return min(1.0, (total_relevance + unique_factor) / max(1, len(selected_topics) * 2))

if __name__ == "__main__":
    c = TopicClassifier()
    c.load_categories()
    score = c.score_paper({"title": "New treatments for ADHD in adults", "abstract_inverted_index": ["adhd", "psychotherapy", "cognitive", "behavioral"]}, ["adhs", "psychotherapy"])
    print(f"Score: {score}")
