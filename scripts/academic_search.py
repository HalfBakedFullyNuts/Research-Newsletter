#!/usr/bin/env python3
"""
Academic paper search via OpenAlex API — standalone, no external dependencies.

Ranking model (Option B: relevance-gated quality tiers)
-------------------------------------------------------
1. RELEVANCE decides the bucket (HIGH / MEDIUM / LOW). A lower-relevance paper
   can NEVER outrank a higher-relevance one, no matter how prestigious.
   Relevance blends three signals:
     - literal keyword match on title/abstract   (precise, your original logic)
     - semantic keyword match on OpenAlex keywords/topic names
       (multilingual embedding-derived -> catches rephrasing & non-English)
     - topical match against anchor topics/subfields resolved from OpenAlex
       (catches ADJACENT concepts a keyword string would miss)
2. QUALITY orders papers WITHIN a bucket (journal impact, age-adjusted
   citations, author authority, OA nudge, fresh-paper credit).
3. CONFIDENCE (0..1) reflects how much data was actually resolved vs missing/
   fallback. It modulates the quality-within-bucket only -- it never moves a
   paper across bucket boundaries, so Option B's guarantee holds.

final_score = bucket_floor + quality_adjusted
    where quality_adjusted = quality(0..100) * (0.7 + 0.3 * confidence), capped
    just under the next floor so buckets never cross.

Usage:
    python3 academic_search.py --topic "attention deficit" --limit 15
    python3 academic_search.py --topic "servant leadership OR authentic leadership" --limit 10
    python3 academic_search.py --topic "machine learning" --from-date 2026-01-01 --json
"""
import argparse
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# ── Tunables ──────────────────────────────────────────────────────────────
# Relevance weights (must sum to 1.0). Feed into the 0..100 relevance score.
W_LITERAL = 0.40
W_SEMANTIC = 0.25
W_TOPICAL = 0.35

# Relevance -> bucket thresholds (on the 0..100 relevance scale).
# Tuned so an exact-topic paper with *no* literal keyword hit still reaches
# MEDIUM, and a same-subfield ("adjacent concept") paper just reaches MEDIUM.
BUCKET_HIGH = 50.0
BUCKET_MEDIUM = 20.0
BUCKET_FLOORS = {"HIGH": 200.0, "MEDIUM": 100.0, "LOW": 0.0}

# Topical match strength by hierarchy level of the match.
TOPICAL_EXACT = 1.0     # paper carries one of the anchor topics
TOPICAL_SUBFIELD = 0.6  # same subfield as an anchor topic (adjacent concept)
TOPICAL_FIELD = 0.3     # same broad field only (loosely related)

# Quality component caps (points; sum capped at 100).
Q_JOURNAL_MAX = 40
Q_CITATION_MAX = 35
Q_AUTHOR_MAX = 15
Q_OA_BONUS = 10

# Journal "quartile" PROXY thresholds on OpenAlex summary_stats.2yr_mean_citedness.
# NOTE: OpenAlex does NOT provide real JCR/Scimago quartiles (those are
# field-normalized and proprietary). 2yr_mean_citedness is OpenAlex's raw
# impact-factor equivalent and is NOT field-normalized -- a "Q1" oncology
# journal sits far higher than a "Q1" humanities journal. Treat these as a
# crude cross-field proxy and TUNE THEM to your newsletter's domain. Override
# at runtime with --q1-threshold / --q2-threshold.
DEFAULT_Q1_THRESHOLD = 8.0
DEFAULT_Q2_THRESHOLD = 4.0
Q3_THRESHOLD = 1.5  # below this -> Q4

# Fresh-paper credit (points) substituted for the citation component while a
# paper is too new to have accrued citations -- only granted to Q1/Q2 journals,
# on the logic that a reputable venue applied pre-publication quality control.
FRESH_CREDIT_Q1 = 35
FRESH_CREDIT_Q2 = 20

# Confidence signal weights (must sum to 1.0).
CONF_WEIGHTS = {
    "doi": 0.10,
    "abstract": 0.20,
    "topics": 0.20,
    "keywords": 0.15,
    "journal_metrics": 0.15,
    "retraction_authoritative": 0.10,
    "author_metrics": 0.10,
}

MAILTO = os.environ.get("OPENALEX_MAILTO", "")  # set for OpenAlex "polite pool"
_UA = f"academic-search/2.0 (mailto:{MAILTO})" if MAILTO else "academic-search/2.0"


def _short_id(v):
    """Normalize an OpenAlex id/url to its bare id, e.g. .../T10017 -> T10017."""
    if not v:
        return ""
    if isinstance(v, dict):
        v = v.get("id", "")
    return str(v).rstrip("/").split("/")[-1]


def _get_json(url, timeout=30, retries=3):
    """GET JSON with simple backoff on 429/5xx (OpenAlex rate-limits the
    common pool). Set OPENALEX_MAILTO to join the faster 'polite pool'."""
    import time
    delay = 1.0
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except Exception as e:  # transient network errors
            last_err = e
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise last_err


# ── OpenAlex client ─────────────────────────────────────────────────────────

def search_openalex(query, from_date=None, to_date=None, limit=60):
    """Search OpenAlex works API. Returns list of paper dicts."""
    filters = ["type:article"]
    if from_date:
        filters.append(f"from_publication_date:{from_date}")
    if to_date:
        filters.append(f"to_publication_date:{to_date}")

    if MAILTO:
        filters_str = ",".join(filters)
        tail = f"&mailto={urllib.parse.quote(MAILTO)}"
    else:
        filters_str = ",".join(filters)
        tail = ""

    url = (
        "https://api.openalex.org/works?"
        f"search={urllib.parse.quote(query)}&"
        f"filter={filters_str}&"
        f"sort=relevance_score:desc&"
        f"per_page={limit}&"
        # topics + keywords added for the semantic/topical relevance layer;
        # locations + open_access added so the OA signal actually resolves.
        f"select=id,doi,title,abstract_inverted_index,publication_date,"
        f"cited_by_count,authorships,primary_location,locations,open_access,"
        f"topics,keywords"
        f"{tail}"
    )
    return _get_json(url).get("results", [])


def resolve_anchor_topics(topic_string, keywords):
    """Resolve the search topic to OpenAlex anchor topic/subfield/field ids.

    One extra API call. Returns dict with sets of short ids, or None on failure
    (relevance then falls back to literal + semantic only).
    """
    query = topic_string.replace(" OR ", " ")
    try:
        url = (
            "https://api.openalex.org/topics?"
            f"search={urllib.parse.quote(query)}&per_page=8&"
            f"select=id,display_name,description,subfield,field,domain,keywords"
        )
        results = _get_json(url, timeout=20).get("results", [])
    except Exception:
        return None
    if not results:
        return None

    anchor = {"topics": set(), "subfields": set(), "fields": set(), "names": []}
    for t in results:
        anchor["topics"].add(_short_id(t.get("id")))
        anchor["subfields"].add(_short_id(t.get("subfield")))
        anchor["fields"].add(_short_id(t.get("field")))
        if t.get("display_name"):
            anchor["names"].append(t["display_name"].lower())
    anchor["topics"].discard("")
    anchor["subfields"].discard("")
    anchor["fields"].discard("")
    return anchor


def _batch_fetch(entity, ids, select):
    """Fetch a batch of entities by OpenAlex id (chunked, OR-filtered)."""
    out = {}
    ids = [i for i in ids if i]
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        try:
            url = (
                f"https://api.openalex.org/{entity}?"
                f"filter=ids.openalex:{'|'.join(chunk)}&per_page=50&"
                f"select={select}"
            )
            for obj in _get_json(url, timeout=25).get("results", []):
                out[_short_id(obj.get("id"))] = obj
        except Exception:
            continue  # degrade gracefully; missing data lowers confidence
    return out


def fetch_journal_metrics(papers):
    """Attach ._journal {impact, works_count, cited_by_count, type, resolved}."""
    source_ids = []
    for p in papers:
        src = (p.get("primary_location") or {}).get("source") or {}
        sid = _short_id(src.get("id"))
        if sid:
            source_ids.append(sid)
    fetched = _batch_fetch(
        "sources", set(source_ids),
        "id,display_name,summary_stats,works_count,cited_by_count,type,is_oa,is_in_doaj",
    )
    for p in papers:
        src = (p.get("primary_location") or {}).get("source") or {}
        sid = _short_id(src.get("id"))
        obj = fetched.get(sid)
        if obj:
            stats = obj.get("summary_stats") or {}
            p["_journal"] = {
                "name": obj.get("display_name") or src.get("display_name") or "",
                "impact": stats.get("2yr_mean_citedness"),
                "h_index": stats.get("h_index"),
                "works_count": obj.get("works_count"),
                "cited_by_count": obj.get("cited_by_count"),
                "type": obj.get("type"),
                "resolved": stats.get("2yr_mean_citedness") is not None,
            }
        else:
            p["_journal"] = {
                "name": src.get("display_name") or "",
                "impact": None, "resolved": False,
            }


def fetch_author_metrics(papers):
    """Attach ._author {name, cited_by_count, works_count, institution, resolved}.

    Uses the corresponding author when flagged, else the first author.
    """
    def pick_author(p):
        authorships = p.get("authorships") or []
        for a in authorships:
            if a.get("is_corresponding"):
                return a
        return authorships[0] if authorships else None

    author_ids = []
    for p in papers:
        a = pick_author(p)
        p["_picked_author"] = a
        if a:
            author_ids.append(_short_id((a.get("author") or {}).get("id")))
    fetched = _batch_fetch(
        "authors", set(author_ids),
        "id,display_name,cited_by_count,works_count,last_known_institutions",
    )
    for p in papers:
        a = p.pop("_picked_author", None)
        aid = _short_id((a.get("author") or {}).get("id")) if a else ""
        obj = fetched.get(aid)
        if obj:
            insts = obj.get("last_known_institutions") or []
            inst_name = insts[0].get("display_name") if insts else ""
            p["_author"] = {
                "name": obj.get("display_name") or "",
                "cited_by_count": obj.get("cited_by_count") or 0,
                "works_count": obj.get("works_count") or 0,
                "institution": inst_name,
                "corresponding": bool(a and a.get("is_corresponding")),
                "resolved": True,
            }
        else:
            p["_author"] = {"name": "", "cited_by_count": 0, "resolved": False}


# ── Relevance scoring (literal + semantic + topical) ─────────────────────────

def _extract_text(paper):
    """Reconstruct searchable text from title + abstract (inverted index)."""
    title = paper.get("title") or ""
    abstract = paper.get("abstract_inverted_index") or {}
    if isinstance(abstract, dict):
        abstract_text = " ".join(abstract.keys())
    elif isinstance(abstract, list):
        abstract_text = " ".join(str(x) for x in abstract)
    else:
        abstract_text = str(abstract)
    return (title + " " + abstract_text).lower()


def _extract_abstract_words(paper, max_words=200):
    """Extract abstract from inverted index, reconstructing by position."""
    abstract = paper.get("abstract_inverted_index") or {}
    if isinstance(abstract, dict):
        word_pos = []
        for word, positions in abstract.items():
            if isinstance(positions, list) and positions:
                first_pos = positions[0]
                if isinstance(first_pos, int):
                    word_pos.append((first_pos, word))
        word_pos.sort()
        return " ".join(w for _, w in word_pos[:max_words])
    return ""


def _literal_score(paper, keywords):
    """Original literal matcher, normalized to 0..1."""
    full_text = _extract_text(paper)
    title_lower = (paper.get("title") or "").lower()
    if not full_text.split():
        return 0.0
    total = 0.0
    matched = 0
    for kw in keywords:
        pattern = rf"\b{re.escape(kw.lower())}\b"
        count = len(re.findall(pattern, full_text))
        if count > 0:
            matched += 1
        total += count * 2
    for kw in keywords:
        if kw.lower() in title_lower:
            total += 5
    unique_factor = matched / max(1, len(keywords))
    return min(1.0, (total + unique_factor) / max(1, len(keywords) * 2))


def _paper_semantic_surface(paper):
    """Lowercased text of OpenAlex keywords + topic names for this paper.

    These are assigned by OpenAlex's multilingual, embedding-based pipeline, so
    a German paper about 'Herzinfarkt' can still carry the English keyword
    'myocardial infarction' -- which is how we catch rephrasing / other langs.
    """
    parts = []
    for kw in paper.get("keywords") or []:
        parts.append((kw.get("display_name") or kw.get("keyword") or "").lower())
    for t in paper.get("topics") or []:
        parts.append((t.get("display_name") or "").lower())
    return " ; ".join(p for p in parts if p)


def _semantic_score(paper, keywords):
    """Fraction of user keywords found in the paper's OpenAlex keyword/topic tags."""
    surface = _paper_semantic_surface(paper)
    if not surface or not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw.lower() in surface)
    return hits / len(keywords)


def _topical_score(paper, anchor):
    """Strongest hierarchy-level match of the paper's topics to the anchor set."""
    if not anchor:
        return 0.0, None
    best = 0.0
    best_name = None
    for t in paper.get("topics") or []:
        name = t.get("display_name")
        if _short_id(t.get("id")) in anchor["topics"]:
            return TOPICAL_EXACT, name  # can't beat an exact topic match
        if _short_id(t.get("subfield")) in anchor["subfields"]:
            if TOPICAL_SUBFIELD > best:
                best, best_name = TOPICAL_SUBFIELD, name
        elif _short_id(t.get("field")) in anchor["fields"]:
            if TOPICAL_FIELD > best:
                best, best_name = TOPICAL_FIELD, name
    return best, best_name


def compute_relevance(paper, keywords, anchor):
    """Blended 0..100 relevance plus components (for bucketing + display)."""
    literal = _literal_score(paper, keywords)
    semantic = _semantic_score(paper, keywords)
    topical, topical_name = _topical_score(paper, anchor)
    relevance = 100.0 * (W_LITERAL * literal
                         + W_SEMANTIC * semantic
                         + W_TOPICAL * topical)
    return {
        "relevance": relevance,
        "literal": literal,
        "semantic": semantic,
        "topical": topical,
        "topical_name": topical_name,
    }


def bucket_for(relevance):
    if relevance >= BUCKET_HIGH:
        return "HIGH"
    if relevance >= BUCKET_MEDIUM:
        return "MEDIUM"
    return "LOW"


# ── Quality scoring ──────────────────────────────────────────────────────────

def _age_days(paper):
    pub_date = paper.get("publication_date", "")
    if not pub_date:
        return None
    try:
        pub = datetime.fromisoformat(pub_date[:10]).replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - pub).days
    except Exception:
        return None


def journal_quartile(impact, q1_threshold, q2_threshold):
    """Map OpenAlex 2yr_mean_citedness to a quartile PROXY (see module note)."""
    if impact is None:
        return None
    if impact >= q1_threshold:
        return "Q1"
    if impact >= q2_threshold:
        return "Q2"
    if impact >= Q3_THRESHOLD:
        return "Q3"
    return "Q4"


def _log_norm(x, cap):
    """Log-normalize a heavy-tailed count to 0..1 (citations are log-distributed)."""
    if x is None or x <= 0:
        return 0.0
    return min(1.0, math.log1p(x) / math.log1p(cap))


def compute_quality(paper, opts):
    """0..100 quality score + components. Fresh Q1/Q2 papers get a citation
    substitute so they can compete despite having no citations yet."""
    age = _age_days(paper)
    fresh = age is not None and age < opts.fresh_window_days

    journal = paper.get("_journal") or {}
    impact = journal.get("impact")
    quartile = journal_quartile(impact, opts.q1_threshold, opts.q2_threshold)

    # Journal impact component (log-normalized 2yr_mean_citedness).
    journal_pts = Q_JOURNAL_MAX * _log_norm(impact, cap=50)

    # Citation component: age-adjusted (citations per month), log-normalized.
    cites = paper.get("cited_by_count") or 0
    if age and age > 0:
        cpm = cites / max(age / 30.0, 1.0)
    else:
        cpm = float(cites)
    citation_pts = Q_CITATION_MAX * _log_norm(cpm, cap=20)

    # Freshness circuit breaker (quality side): a brand-new paper cannot have
    # citations, so for Q1/Q2 venues substitute a pre-publication-QC credit.
    fresh_credit = 0
    if fresh and quartile in ("Q1", "Q2"):
        fresh_credit = FRESH_CREDIT_Q1 if quartile == "Q1" else FRESH_CREDIT_Q2
        citation_pts = max(citation_pts, float(fresh_credit))

    # Author authority component.
    author = paper.get("_author") or {}
    author_pts = Q_AUTHOR_MAX * _log_norm(author.get("cited_by_count"), cap=50000)

    # Open-access nudge (readers can actually click through).
    oa = bool((paper.get("open_access") or {}).get("is_oa")
              or (paper.get("primary_location") or {}).get("is_oa"))
    oa_pts = Q_OA_BONUS if oa else 0

    quality = min(100.0, journal_pts + citation_pts + author_pts + oa_pts)
    return {
        "quality": quality,
        "journal_pts": journal_pts,
        "citation_pts": citation_pts,
        "author_pts": author_pts,
        "oa_pts": oa_pts,
        "fresh_credit": fresh_credit,
        "fresh": fresh,
        "quartile": quartile,
        "impact": impact,
        "oa": oa,
        "age_days": age,
    }


# ── Confidence scoring ───────────────────────────────────────────────────────

def compute_confidence(paper):
    """0..1 fraction of resolvable signals actually resolved (+ missing list)."""
    signals = {
        "doi": bool(paper.get("doi")),
        "abstract": bool(paper.get("abstract_inverted_index")),
        "topics": bool(paper.get("topics")),
        "keywords": bool(paper.get("keywords")),
        "journal_metrics": bool((paper.get("_journal") or {}).get("resolved")),
        "retraction_authoritative": bool(paper.get("_retraction_authoritative")),
        "author_metrics": bool((paper.get("_author") or {}).get("resolved")),
    }
    score = sum(CONF_WEIGHTS[k] for k, ok in signals.items() if ok)
    missing = [k for k, ok in signals.items() if not ok]
    return score, missing


def final_score(bucket, quality, confidence):
    """Option B: bucket floor dominates; confidence*quality orders within it."""
    floor = BUCKET_FLOORS[bucket]
    adjusted = quality * (0.7 + 0.3 * confidence)
    adjusted = min(adjusted, 99.9)  # never cross into the next bucket's band
    return floor + adjusted


# ── Quality control gates ────────────────────────────────────────────────────

_PREDATORY_PUBLISHERS = {
    "academia publishing", "alphascript", "atlas scientific",
    "cc publishers", "eastern scientific", "excellence publishing",
    "global academic", "global research", "standard publishers",
}
_PREDATORY_PREFIXES = {
    "asian online", "turkish journal", "indian journal",
    "international journal of", "world journal of",
}
_NON_ENGLISH_PATTERNS = [
    r'\b(der|die|das|und|oder|für|von|mit|auf|im|zu|ist|sind)\b',   # German
    r'\b(le|la|les|et|ou|pour|dans|est|sont|du|de|un|une)\b',       # French
    r'\b(el|la|los|las|y|o|para|en|es|son|del|de|un|una)\b',        # Spanish
    r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uac00-\ud7af]',  # CJK
]


def check_retraction(doi):
    """Check Crossref for retraction. Returns (passed, reason, authoritative)."""
    if not doi:
        return True, "No DOI", False
    try:
        doi_clean = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        url = (f"https://api.crossref.org/works?filter=doi:{urllib.parse.quote(doi_clean)}"
               f"&select=DOI,title,updated-by")
        data = _get_json(url, timeout=6)
        items = data.get("message", {}).get("items", [])
        if not items:
            return True, "Not in Crossref", False
        for entry in items[0].get("updated-by", []):
            if entry.get("type") == "retraction":
                return False, f"Retracted ({entry.get('source', 'unknown')})", True
        return True, "Not retracted", True
    except Exception:
        return True, "Check failed", False  # fail-open, but not authoritative


def check_predatory(paper):
    source = (paper.get("primary_location") or {}).get("source") or {}
    publisher = (source.get("host_organization_name") or "").lower()
    journal = (source.get("display_name") or source.get("name") or "").lower()
    for pred in _PREDATORY_PUBLISHERS:
        if pred in publisher:
            return False, f"Predatory: {publisher[:50]}"
    for prefix in _PREDATORY_PREFIXES:
        if journal.startswith(prefix):
            return False, f"Predatory prefix: {journal[:50]}"
    return True, "OK"


def check_age(paper, max_days):
    age = _age_days(paper)
    if age is None:
        return True, "No/unparsable date"
    if age > max_days:
        return False, f"Too old: {age} days"
    return True, f"{age} days old"


def check_citations(paper, min_count, fresh_window_days):
    """Citation gate. Fresh papers bypass (circuit breaker)."""
    citations = paper.get("cited_by_count") or 0
    if min_count <= 0:
        return True, f"{citations} citations"
    age = _age_days(paper)
    if age is not None and age < fresh_window_days:
        return True, f"Fresh ({age}d), citation gate bypassed"
    if citations < min_count:
        return False, f"Low citations: {citations}"
    return True, f"{citations} citations"


def check_language(paper):
    title = paper.get("title", "") or ""
    for pattern in _NON_ENGLISH_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            return False, f"Non-English: {title[:40]}"
    return True, "English"


def check_open_access(paper):
    if (paper.get("open_access") or {}).get("is_oa"):
        return True, "OA"
    if (paper.get("primary_location") or {}).get("is_oa"):
        return True, "OA"
    for loc in paper.get("locations", []) or []:
        if loc.get("is_oa"):
            return True, "OA"
    return False, "No OA"


def run_qc(papers, opts):
    """Run quality gates. Returns (passed_list, rejected_list)."""
    seen_dois = set()
    passed, rejected = [], []

    for paper in papers:
        doi = paper.get("doi", "")

        if doi and doi in seen_dois:
            rejected.append((paper, "Duplicate DOI"))
            continue
        if doi:
            seen_dois.add(doi)

        if not getattr(opts, "no_retraction", False):
            ok, reason, authoritative = check_retraction(doi)
            paper["_retraction_authoritative"] = authoritative
            if not ok:
                rejected.append((paper, reason))
                continue
        else:
            paper["_retraction_authoritative"] = False

        if not getattr(opts, "no_predatory", False):
            ok, reason = check_predatory(paper)
            if not ok:
                rejected.append((paper, reason))
                continue

        ok, reason = check_age(paper, opts.max_age_days)
        if not ok:
            rejected.append((paper, reason))
            continue

        ok, reason = check_citations(paper, opts.min_citations, opts.fresh_window_days)
        if not ok:
            rejected.append((paper, reason))
            continue

        if opts.language_filter:
            ok, reason = check_language(paper)
            if not ok:
                rejected.append((paper, reason))
                continue

        if opts.open_access:
            ok, reason = check_open_access(paper)
            if not ok:
                rejected.append((paper, reason))
                continue

        passed.append(paper)

    return passed, rejected


# ── Output formatting ────────────────────────────────────────────────────────

def _get_authors(paper, max_authors=3):
    authorships = paper.get("authorships") or []
    authors = []
    for a in authorships[:max_authors + 1]:
        name = (a.get("author") or {}).get("display_name", "")
        if name:
            authors.append(name)
    if len(authorships) > max_authors:
        authors = authors[:max_authors] + ["et al."]
    return ", ".join(authors)


def _get_year(paper):
    pub = paper.get("publication_date", "")
    return pub[:4] if pub else "?"


def format_paper(rank, entry):
    """entry = dict assembled in main() with all scoring info."""
    paper = entry["paper"]
    rel = entry["rel"]
    qual = entry["qual"]
    title = paper.get("title", "Untitled")
    authors = _get_authors(paper)
    year = _get_year(paper)
    doi = paper.get("doi") or ""
    doi_clean = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    doi_url = f"https://doi.org/{doi_clean}" if doi_clean else ""
    citations = paper.get("cited_by_count") or 0
    abstract = _extract_abstract_words(paper)
    journal = paper.get("_journal") or {}
    author = paper.get("_author") or {}

    q_str = qual["quartile"] or "n/a"
    impact_str = f"{qual['impact']:.1f}" if qual["impact"] is not None else "n/a"
    fresh_tag = "  ⚡FRESH" if qual["fresh"] else ""

    lines = [
        f"\n{'─' * 64}",
        f"{rank}. {title}",
        f"   {authors}  ·  {year}  ·  {citations} cites{fresh_tag}",
        f"   [{entry['bucket']}]  final={entry['final']:.1f}  "
        f"relevance={rel['relevance']:.0f}  quality={qual['quality']:.0f}  "
        f"confidence={entry['confidence']:.2f}",
        f"   relevance: literal={rel['literal']:.2f} semantic={rel['semantic']:.2f} "
        f"topical={rel['topical']:.2f}"
        + (f" ({rel['topical_name']})" if rel.get("topical_name") else ""),
        f"   journal: {journal.get('name', '?')[:48]}  "
        f"impact={impact_str} quartile={q_str}"
        + (f"  fresh-credit={qual['fresh_credit']}" if qual["fresh_credit"] else ""),
    ]
    if author.get("resolved"):
        role = "corresp." if author.get("corresponding") else "first"
        lines.append(
            f"   author ({role}): {author.get('name', '?')}  "
            f"cites={author.get('cited_by_count', 0)}"
            + (f"  @ {author['institution']}" if author.get("institution") else "")
        )
    if entry["missing"]:
        lines.append(f"   low-confidence (missing: {', '.join(entry['missing'])})")
    if doi_url:
        lines.append(f"   DOI: {doi_url}")
    if abstract:
        lines.append(f"   {abstract[:300]}{'...' if len(abstract) > 300 else ''}")
    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Search academic papers via OpenAlex (Option B ranking)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--topic", required=True, help="Search topic/keywords")
    parser.add_argument("--limit", type=int, default=10, help="Papers to return (default: 10)")
    parser.add_argument("--from-date", default=None, help="Start date YYYY-MM-DD (default: 365 days ago)")
    parser.add_argument("--to-date", default=None, help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--max-age-days", type=int, default=365, help="QC: max paper age (default: 365)")
    parser.add_argument("--min-citations", type=int, default=0, help="QC: min citation count (default: 0)")
    parser.add_argument("--fresh-window-days", type=int, default=30,
                        help="Papers younger than this bypass the citation gate and "
                             "are eligible for Q1/Q2 fresh credit (default: 30)")
    parser.add_argument("--q1-threshold", type=float, default=DEFAULT_Q1_THRESHOLD,
                        help=f"Journal 2yr_mean_citedness for Q1 proxy (default: {DEFAULT_Q1_THRESHOLD})")
    parser.add_argument("--q2-threshold", type=float, default=DEFAULT_Q2_THRESHOLD,
                        help=f"Journal 2yr_mean_citedness for Q2 proxy (default: {DEFAULT_Q2_THRESHOLD})")
    parser.add_argument("--language-filter", action="store_true", help="QC: English-only")
    parser.add_argument("--open-access", action="store_true", help="QC: OA-only")
    parser.add_argument("--no-retraction", action="store_true", help="Disable retraction check")
    parser.add_argument("--no-predatory", action="store_true", help="Disable predatory check")
    parser.add_argument("--no-semantic", action="store_true",
                        help="Disable OpenAlex topic/keyword relevance layer (literal only)")
    parser.add_argument("--no-author-metrics", action="store_true",
                        help="Skip author enrichment API calls (faster, lower confidence)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--debug", action="store_true", help="Show pipeline stats")

    args = parser.parse_args()

    if not args.from_date:
        args.from_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    if not args.to_date:
        args.to_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    keywords = [kw.strip() for kw in args.topic.split(" OR ")]
    query = " OR ".join(keywords)

    fetch_limit = max(args.limit * 3, 20)
    if args.debug:
        print(f"Query: {query}")
        print(f"Keywords: {keywords}")
        print(f"Date range: {args.from_date} → {args.to_date}")
        print(f"Fetching up to {fetch_limit} papers…")

    papers = search_openalex(query, from_date=args.from_date, to_date=args.to_date, limit=fetch_limit)
    if args.debug:
        print(f"Fetched: {len(papers)} papers")

    # Resolve semantic anchor (adjacent-concept detection). 1 API call.
    anchor = None
    if not args.no_semantic:
        anchor = resolve_anchor_topics(args.topic, keywords)
        if args.debug:
            if anchor:
                print(f"Anchor topics: {len(anchor['topics'])} topics, "
                      f"{len(anchor['subfields'])} subfields "
                      f"({', '.join(anchor['names'][:3])}…)")
            else:
                print("Anchor topics: none resolved (literal + semantic only)")

    # Pre-QC relevance to pick candidates.
    scored = []
    for p in papers:
        rel = compute_relevance(p, keywords, anchor)
        if rel["relevance"] > 3.0:  # tiny floor to drop total non-matches
            scored.append((rel["relevance"], p))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [p for _, p in scored[:args.limit * 3]]
    if args.debug:
        print(f"Relevant candidates: {len(scored)}, taken forward: {len(top_candidates)}")

    # Journal metrics are needed for the freshness circuit breaker, so enrich
    # BEFORE quality scoring (the QC gate itself only needs age/citations).
    fetch_journal_metrics(top_candidates)

    passed, rejected = run_qc(top_candidates, args)
    if args.debug:
        print(f"QC passed: {len(passed)}, rejected: {len(rejected)}")
        for p, reason in rejected[:8]:
            print(f"  Rejected: {(p.get('title') or '?')[:60]} — {reason}")

    # Author metrics only for survivors (cheaper).
    if not args.no_author_metrics:
        fetch_author_metrics(passed)
    else:
        for p in passed:
            p["_author"] = {"name": "", "cited_by_count": 0, "resolved": False}

    # Assemble full scoring for each survivor.
    entries = []
    for p in passed:
        rel = compute_relevance(p, keywords, anchor)
        qual = compute_quality(p, args)
        confidence, missing = compute_confidence(p)
        bucket = bucket_for(rel["relevance"])
        final = final_score(bucket, qual["quality"], confidence)
        entries.append({
            "paper": p, "rel": rel, "qual": qual, "bucket": bucket,
            "confidence": confidence, "missing": missing, "final": final,
        })

    # Sort: bucket floor already encoded in final -> single descending sort.
    entries.sort(key=lambda e: e["final"], reverse=True)
    final_entries = entries[:args.limit]

    if args.debug:
        from collections import Counter
        dist = Counter(e["bucket"] for e in final_entries)
        print(f"Bucket distribution (shown): {dict(dist)}")

    # Output
    if args.json:
        output = []
        for rank, e in enumerate(final_entries, 1):
            p, rel, qual = e["paper"], e["rel"], e["qual"]
            author = p.get("_author") or {}
            journal = p.get("_journal") or {}
            output.append({
                "rank": rank,
                "title": p.get("title", ""),
                "authors": _get_authors(p, max_authors=10),
                "year": _get_year(p),
                "doi": p.get("doi", ""),
                "citations": p.get("cited_by_count", 0),
                "bucket": e["bucket"],
                "final_score": round(e["final"], 2),
                "relevance": {
                    "score": round(rel["relevance"], 1),
                    "literal": round(rel["literal"], 3),
                    "semantic": round(rel["semantic"], 3),
                    "topical": round(rel["topical"], 3),
                    "topical_match": rel.get("topical_name"),
                },
                "quality": {
                    "score": round(qual["quality"], 1),
                    "journal_pts": round(qual["journal_pts"], 1),
                    "citation_pts": round(qual["citation_pts"], 1),
                    "author_pts": round(qual["author_pts"], 1),
                    "oa_pts": qual["oa_pts"],
                    "fresh_credit": qual["fresh_credit"],
                },
                "confidence": round(e["confidence"], 2),
                "confidence_missing": e["missing"],
                "journal": {
                    "name": journal.get("name", ""),
                    "impact_2yr_mean_citedness": qual["impact"],
                    "quartile_proxy": qual["quartile"],
                },
                "author": {
                    "name": author.get("name", ""),
                    "cited_by_count": author.get("cited_by_count", 0),
                    "institution": author.get("institution", ""),
                    "corresponding": author.get("corresponding", False),
                },
                "fresh": qual["fresh"],
                "age_days": qual["age_days"],
                "open_access": qual["oa"],
                "abstract": _extract_abstract_words(p),
            })
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"\nAcademic search: \"{args.topic}\"")
        print(f"Found {len(final_entries)} papers "
              f"(from {len(papers)} fetched, {len(rejected)} rejected)")
        print(f"Period: {args.from_date} → {args.to_date}")
        print("Ranking: relevance bucket → confidence-weighted quality within bucket")
        for rank, e in enumerate(final_entries, 1):
            print(format_paper(rank, e))
        if not final_entries:
            print("\nNo papers matched your criteria. Try:")
            print("  - Widening the date window (--max-age-days 730)")
            print("  - Broadening keywords (use OR)")
            print("  - Keeping the semantic layer on (avoid --no-semantic)")


if __name__ == "__main__":
    main()
