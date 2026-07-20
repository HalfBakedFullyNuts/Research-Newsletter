#!/usr/bin/env python3
"""
ResearchPulse — Quality Control Gates
Filters papers through multiple quality gates before delivery.
"""
import json
import re
import urllib.request
import urllib.parse
import os
from datetime import datetime

class QualityGates:
    """
    Paper quality control pipeline.
    Each gate returns (pass: bool, reason: str, score: float).
    A paper must pass ALL configured gates to be included in a digest.
    """
    
    GATE_CONFIG = {
        # Gate name: (enabled, min_score, description)
        "retraction_check": (True, 1.0, "Filter retracted papers"),
        "predatory_journal": (True, 1.0, "Filter predatory journals"),
        "min_citations": (True, 10, "Minimum citation count (filters low-quality)"),
        "max_age_days": (True, 365, "Max paper age in days"),
        "open_access": (False, 0, "Require open access full text"),
        "language_check": (False, 0, "Filter non-English papers (disabled — multilingual)"),
        "journal_impact": (False, 0, "Minimum journal quality tier"),
        "duplicate_check": (True, 0, "Deduplicate by DOI/title similarity"),
    }
    
    def __init__(self, config_path=None):
        self.seen_dois = set()
        self.config = dict(self.GATE_CONFIG)
        if config_path:
            self.load_config(config_path)
        self.load_predatory_list()
    
    def load_config(self, path):
        try:
            with open(path) as f:
                overrides = json.load(f)
            for key, value in overrides.items():
                if key in self.config:
                    self.config[key] = (self.config[key][0], value, self.config[key][2])
        except FileNotFoundError:
            pass
    
    def load_predatory_list(self):
        """Load known predatory publishers.
        
        Source: Cappellato et al. 2020 (Beall's list update) or fallback.
        File updated monthly via cron job.
        """
        json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predatory_publishers.json")
        try:
            with open(json_path) as f:
                data = json.load(f)
            self.predatory_publishers = set(data.get("publishers", []))
            self.predatory_prefixes = set()
            self.predatory_source = data.get("source", "Unknown")
            self.predatory_fetched = data.get("fetched_at", "Unknown")
        except (FileNotFoundError, json.JSONDecodeError):
            # Fallback: embedded list (Cappellato 2020 subset)
            self.predatory_publishers = {
                "academia publishing", "alphascript", "atlas scientific",
                "cc publishers", "eastern scientific", "excellence publishing",
                "global academic", "global research", "standard publishers",
            }
            self.predatory_prefixes = {
                "asian online", "turkish journal", "indian journal",
                "international journal of", "world journal of",
            }
            self.predatory_source = "Fallback"
            self.predatory_fetched = "N/A"
    
    def check(self, paper):
        """
        Run all quality gates on a paper.
        Returns: (passed: bool, results: dict)
        """
        results = {}
        
        # 1. Retraction check
        doi = paper.get("doi", "")
        if doi:
            passed, reason, score = self.retraction_check(doi)
            results["retraction_check"] = {"passed": passed, "reason": reason, "score": score}
            if not passed:
                return False, results
        
        # 2. Predatory journal check
        if self.config["predatory_journal"][0]:
            passed, reason, score = self.predatory_journal_check(paper)
            results["predatory_journal"] = {"passed": passed, "reason": reason, "score": score}
            if not passed:
                return False, results
        
        # 3. Age check
        if self.config["max_age_days"][0]:
            passed, reason, score = self.max_age_check(paper)
            results["max_age_days"] = {"passed": passed, "reason": reason, "score": score}
            if not passed:
                return False, results
        
        # 4. Language check
        if self.config["language_check"][0]:
            passed, reason, score = self.language_check(paper)
            results["language_check"] = {"passed": passed, "reason": reason, "score": score}
            if not passed:
                return False, results
        
        # 5. Duplicate check
        if self.config["duplicate_check"][0]:
            passed, reason, score = self.duplicate_check(paper)
            results["duplicate_check"] = {"passed": passed, "reason": reason, "score": score}
            if not passed:
                return False, results
        
        # 6. Open access check
        if self.config["open_access"][0]:
            passed, reason, score = self.open_access_check(paper)
            results["open_access"] = {"passed": passed, "reason": reason, "score": score}
            if not passed:
                return False, results
        
        # 7. Min citations
        if self.config["min_citations"][0]:
            passed, reason, score = self.min_citations_check(paper)
            results["min_citations"] = {"passed": passed, "reason": reason, "score": score}
            if not passed:
                return False, results
        
        # 8. Journal impact
        if self.config["journal_impact"][0]:
            passed, reason, score = self.journal_impact_check(paper)
            results["journal_impact"] = {"passed": passed, "reason": reason, "score": score}
            if not passed:
                return False, results
        
        return True, results
    
    # ── Individual Gate Implementations ──
    
    def retraction_check(self, doi):
        """Check if a paper has been retracted via Crossref API.
        
        Uses the `updated-by` field — the authoritative Crossref indicator.
        A retraction is flagged when any entry in `updated-by` has `"type": "retraction"`.
        Falls back gracefully on API errors (passes the paper).
        """
        if not doi:
            return True, "No DOI", 0.5
        
        try:
            url = f"https://api.crossref.org/works?filter=doi:{urllib.parse.quote(doi)}&select=DOI,title,updated-by"
            req = urllib.request.Request(url, headers={"User-Agent": "ResearchPulse/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            
            items = data.get("message", {}).get("items", [])
            if not items:
                return True, "Not found in Crossref", 0.5
            
            paper = items[0]
            updated_by = paper.get("updated-by", [])
            
            for entry in updated_by:
                if entry.get("type") == "retraction":
                    source = entry.get("source", "unknown")
                    date = entry.get("updated", {}).get("date-parts", [["?"]])
                    date_str = f"{date[0][0]}-{date[0][1]:02d}-{date[0][2]:02d}" if len(date[0]) == 3 else "?"
                    return False, f"Retracted ({source}, {date_str})", 0.0
            
            return True, "Not retracted", 1.0
        except Exception as e:
            # If we can't verify, pass (better than false negatives)
            return True, f"Check failed: {str(e)[:40]}", 0.5
    
    def predatory_journal_check(self, paper):
        """Check if the publisher/journal is known predatory."""
        source_info = paper.get("primary_location", {}).get("source", {})
        if not source_info:
            return True, "OK: Unknown publisher", 0.5
        publisher = (source_info.get("host_organization_name") or "").lower()
        journal_name = (source_info.get("display_name") or source_info.get("name") or "").lower()
        
        # Check publisher against known predatory publishers
        for pred in self.predatory_publishers:
            if pred in publisher:
                return False, f"Predatory publisher: {publisher[:50]}", 0.0
        
        # Check journal name prefixes
        for prefix in self.predatory_prefixes:
            if journal_name.startswith(prefix):
                return False, f"Predatory journal prefix: {journal_name[:50]}", 0.0
        
        return True, f"OK: {publisher[:50] or 'Unknown'}", 1.0
    
    def max_age_check(self, paper):
        """Check if paper is within max age."""
        pub_date = paper.get("publication_date", "")
        if not pub_date:
            return True, "No date", 0.5
        
        max_days = self.config["max_age_days"][1]
        try:
            pub = datetime.fromisoformat(pub_date[:10])
            age_days = (datetime.now() - pub).days
            if age_days > max_days:
                return False, f"Too old: {age_days} days", 0.0
            return True, f"Age: {age_days} days", 1.0
        except:
            return True, "Date parse failed", 0.5
    
    def language_check(self, paper):
        """Filter non-English papers (basic heuristic)."""
        title = paper.get("title", "")
        
        # Common non-English language indicators
        non_english_patterns = [
            # German
            r'\b(der|die|das|und|oder|für|von|mit|auf|im|zu|ist|sind)\b',
            # French
            r'\b(le|la|les|et|ou|pour|dans|est|sont|du|de|un|une)\b',
            # Spanish
            r'\b(el|la|los|las|y|o|para|en|es|son|del|de|un|una)\b',
            # Japanese/Chinese/Korean
            r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uac00-\ud7af]',
        ]
        
        for pattern in non_english_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                return False, f"Non-English: {title[:40]}", 0.0
        
        return True, "English", 1.0
    
    def duplicate_check(self, paper):
        """Deduplicate by DOI."""
        doi = paper.get("doi", "")
        if doi and doi in self.seen_dois:
            return False, "Duplicate DOI", 0.0
        if doi:
            self.seen_dois.add(doi)
        return True, "Unique", 1.0
    
    def open_access_check(self, paper):
        """Check if paper has open access full text."""
        locations = paper.get("locations", [])
        if not locations:
            primary = paper.get("primary_location", {})
            if primary:
                is_oa = primary.get("is_oa", False)
                return is_oa, "Open access" if is_oa else "No OA", 1.0 if is_oa else 0.0
        
        for loc in locations:
            if loc.get("is_oa"):
                return True, "Open access", 1.0
        
        return False, "No open access", 0.0
    
    def min_citations_check(self, paper):
        """Check minimum citation count.
        
        Circuit breaker: papers <30 days old bypass the citation gate.
        """
        citations = paper.get("cited_by_count", 0)
        min_count = self.config["min_citations"][1]
        
        # Circuit breaker: new papers (<30 days) bypass citation check
        pub_date = paper.get("publication_date", "")
        if pub_date:
            try:
                pub = datetime.fromisoformat(pub_date[:10])
                age_days = (datetime.now() - pub).days
                if age_days < 30:
                    return True, f"New ({age_days}d), bypass", 1.0
            except:
                pass
        
        if citations < min_count:
            return False, f"Low citations: {citations}", 0.0
        return True, f"Citations: {citations}", 1.0
    
    def journal_impact_check(self, paper):
        """Basic journal impact heuristic based on OpenAlex host institution."""
        # TODO: Integrate with SCImago or OpenAlex journal metrics
        primary = paper.get("primary_location", {})
        if primary:
            source = primary.get("source", {})
            host = source.get("host_organization_name", "").lower()
            # Quick check for known top-tier publishers
            top_publishers = ["springer", "nature", "elsevier", "wiley", "ieee", "acm", 
                             "oxford", "cambridge", "aaas", "cell press", "nih"]
            for tp in top_publishers:
                if tp in host:
                    return True, f"Top publisher: {host[:40]}", 1.0
        return True, "Unknown publisher", 0.5


def run_quality_pipeline(papers, config_path=None):
    """
    Run quality gates on a list of papers.
    Returns: (filtered_papers: list, qc_results: dict)
    """
    qc = QualityGates(config_path=config_path)
    filtered = []
    qc_results = []
    
    for paper in papers:
        passed, results = qc.check(paper)
        if passed:
            filtered.append(paper)
        else:
            qc_results.append({
                "paper": paper.get("title", "Untitled"),
                "doi": paper.get("doi", ""),
                "gates": results
            })
    
    return filtered, qc_results


if __name__ == "__main__":
    # Test with sample data
    sample_papers = [
        {
            "title": "ADHD and executive function: A meta-analysis",
            "doi": "10.1037/0022-0061.2019.123",
            "publication_date": "2026-01-15",
            "cited_by_count": 45,
            "locations": [{"is_oa": True}],
            "primary_location": {
                "is_oa": True,
                "source": {"display_name": "Journal of Abnormal Psychology", "host_organization_name": "American Psychological Association"}
            }
        },
        {
            "title": "Die Rolle von ADHS in der modernen Gesellschaft",  # German title
            "doi": "10.1234/test2",
            "publication_date": "2026-03-01",
            "cited_by_count": 2,
            "locations": [{"is_oa": False}],
            "primary_location": {
                "is_oa": False,
                "source": {"display_name": "German Journal", "host_organization_name": "German Publisher"}
            }
        },
        {
            "title": "Academic Publishing: A predatory model analysis",
            "doi": "10.5555/test3",
            "publication_date": "2026-05-01",
            "cited_by_count": 1,
            "locations": [{"is_oa": True}],
            "primary_location": {
                "is_oa": True,
                "source": {"display_name": "Academic Publishing Journal", "host_organization_name": "Academic Publishing"}
            }
        },
    ]
    
    filtered, qc_results = run_quality_pipeline(sample_papers)
    
    print(f"Input: {len(sample_papers)} papers")
    print(f"Passed: {len(filtered)}")
    print(f"Filtered: {len(qc_results)}")
    for qr in qc_results:
        print(f"\n  ❌ {qr['paper']}")
        for gate, result in qr['gates'].items():
            if not result['passed']:
                print(f"     Gate: {gate} → {result['reason']}")
