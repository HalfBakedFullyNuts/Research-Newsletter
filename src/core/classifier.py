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
        text = (paper.get("title", "") + " " + 
                " ".join(paper.get("abstract_inverted_index", []))).lower()
        
        total_relevance = 0
        total_words = len(text.split())
        if total_words == 0:
            return 0.0
        
        for topic in selected_topics:
            keywords = self.categories.get(topic, [topic])
            for kw in keywords:
                count = len(re.findall(rf'\b{re.escape(kw)}\b', text))
                total_relevance += count
        
        # Normalize by number of selected topics and length
        return min(1.0, total_relevance / max(1, len(selected_topics) * 5))

if __name__ == "__main__":
    c = TopicClassifier()
    c.load_categories()
    score = c.score_paper({"title": "New treatments for ADHD in adults", "abstract_inverted_index": ["adhd", "psychotherapy", "cognitive", "behavioral"]}, ["adhs", "psychotherapy"])
    print(f"Score: {score}")
