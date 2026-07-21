---
name: academic-topic-search
description: >
  Search OpenAlex for academic papers on any topic with QC gates (retraction,
  predatory, age, citations), relevance scoring, Journal Impact (Publisher Tier
  + Avg Citations), Author Impact (citations + institutions), and ranked output.
  Reusable for one-off searches on any research topic.
---

# Academic Topic Search

Search OpenAlex for academic research papers on any topic, apply quality control
gates, score by relevance, and return ranked results.

## When to Use

- User asks for "academic papers on X" or "research about Y"
- User wants literature review on a specific topic
- User needs evidence-based sources for a topic
- Any ad-hoc academic search task

## Quick Start

### Option A: Run the standalone script (fastest)

```bash
cd /opt/data && python3 scripts/academic_search.py --topic "your topic here" --limit 15
```

### Option B: Use web_search + OpenAlex API directly

If the script isn't available, use the workflow below.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--topic` | **required** | Topic name (e.g. "ADHD", "cancer immunotherapy") |
| `--limit` | 10 | Max papers to return |
| `--from-date` | 365d ago | Start date YYYY-MM-DD |
| `--to-date` | today | End date YYYY-MM-DD |
| `--max-age-days` | 365 | QC: max paper age |
| `--min-citations` | 0 | QC: min citation count (circuit breaker: <30d papers bypass) |
| `--language-filter` | off | QC: English-only |
| `--open-access` | off | QC: OA-only |
| `--no-retraction` | off | Disable retraction check |
| `--no-predatory` | off | Disable predatory check |
| `--no-impact` | off | Skip journal/author impact lookups |
| `--json` | off | JSON output |
| `--debug` | off | Show pipeline stats (fetched/scored/QC passed/rejected) |

## Built-in Topic Mapping

The script includes 20 pre-configured topics with academic keywords:

- `adhd` / `adhs`, `psychotherapy`, `trauma`, `depression`, `anxiety`
- `healthcare_ai`, `cancer`, `cardiovascular`, `diabetes`
- `neuroscience`, `immunology`, `epidemiology`, `public_health`
- `climate`, `education`, `psychology`, `sociology`
- `physics`, `chemistry`, `biology`, `computer_science`

Use `--topic adhd` to trigger the built-in keyword expansion.

## Quality Control Gates

All results pass through these filters:

1. **Retraction check** — Crossref `updated-by` field (authoritative)
2. **Predatory journal filter** — Cappellato et al. 2020 list
3. **Age filter** — Max 365 days (configurable)
4. **Citation filter** — Default: 0 (off); set `MIN_CITATIONS` in script
5. **Deduplication** — By DOI

Circuit breaker: Papers < 30 days old bypass the citation gate.

## Pipeline & Sort-After-QC

The script uses a **2-phase relevance scoring** pipeline — papers are ranked by quality *before* and *after* QC gates:

### Phase 1: Pre-QC Scoring (fetch & prune)
1. Fetch **3× requested limit** from OpenAlex (e.g., `--limit 10` → fetch 30)
2. Score every paper 0.0–1.0 (see Scoring Weights below)
3. Discard papers scoring **< 0.05**
4. Keep **top 2× limit** candidates for QC

### Phase 2: QC Gates
5. Run quality gates (retraction, predatory, age, citations, dedup)
6. Separate into passed / rejected lists

### Phase 3: Re-Score & Final Sort
7. **Re-score** all QC-passed papers (they lost their original scores)
8. **Sort descending** by relevance score — highest quality first
9. Return top `--limit` papers

### Scoring Weights
- Keyword match in **title**: +5 points per match
- Keyword match in **abstract**: +2 points per match
- Unique keyword bonus: +0.5 × (unique matched / total keywords)
- Normalized to 0.0–1.0 range

**Output is always sorted by relevance score (highest first).** Use `--json` to see exact `score` values.

## Examples

```bash
# Simple topic search
python3 scripts/academic_search.py --topic "machine learning in healthcare" --limit 10

# Multi-keyword search (OR in topic string)
python3 scripts/academic_search.py --topic "adhd OR attention deficit OR hyperactivity" --limit 20

# Date range
python3 scripts/academic_search.py --topic "climate change" --from-date 2025-01-01 --limit 15

# JSON output
python3 scripts/academic_search.py --topic cancer --json

# Debug mode (shows fetched/scored/QC passed/rejected)
python3 scripts/academic_search.py --topic "trauma therapy" --debug

# Relaxed filters (older papers, English-only)
python3 scripts/academic_search.py --topic depression --max-age-days 730 --language-filter
```

## Output Format

### Text (default)
```
======================================================================
📚 Academic Search Results: artificial intelligence
======================================================================
Keywords: machine learning, deep learning, artificial intelligence
Fetched: 45 | QC Filtered: 12 | Results: 15
======================================================================

[1] Deep Learning for Medical Image Analysis: A Comprehensive Review
    Authors: Smith J, Johnson A, Williams R
    Year: 2026 | Journal: Nature Medicine
    Citations: 45 | Relevance: 0.892
    Publisher Tier: Elite (Nature Portfolio)
    Journal Impact: avg 154.5 citations/paper (16616 works)
    Corresponding Author: Jane Smith (168911 citations, 895 works, Johns Hopkins University)
    DOI: https://doi.org/10.xxxx/xxxx
    Abstract: This paper reviews the application of deep learning...
```

### JSON
```json
{
  "topic": "artificial intelligence",
  "keywords": ["machine learning", "deep learning"],
  "total_fetched": 45,
  "qc_filtered": 12,
  "results_count": 15,
  "results": [
    {
      "rank": 1,
      "title": "...",
      "authors": "...",
      "year": "2026",
      "journal": "...",
      "doi": "...",
      "citations": 45,
      "relevance_score": 0.892,
      "publisher_tier": "Elite",
      "publisher_name": "Nature Portfolio",
      "journal_avg_citations": 154.5,
      "journal_total_citations": 2568000,
      "journal_works_count": 16616,
      "corresponding_author": "Jane Smith",
      "author_citations": 168911,
      "author_works_count": 895,
      "author_institutions": ["Johns Hopkins University"],
      "abstract": "..."
    }
  ]
}
```

## Pitfalls

- **OpenAlex rate limiting**: The API allows ~5 requests/second. The script fetches in batches. For very large searches, add delays.
- **No DOI = no retraction check**: Papers without DOIs are assumed OK. Most journal articles have DOIs.
- **Predatory list is a subset**: The built-in list covers ~10 known publishers. For comprehensive filtering, update the list or use a larger source.
- **Keyword matching is basic**: Uses word boundaries (`\b`). Doesn't handle stemming or synonyms well.
- **Abstract truncation**: Abstracts are truncated to 300 chars in output. Use `--format json` for full abstracts.
- **h-index not available**: OpenAlex returns `None` for both journal and author h-index — always. Use `cited_by_count / works_count` as proxy.
- **Batch lookup syntax**: OpenAlex doesn't support `id:ID1,id:ID2` or multi-value filters. Must fetch each source/author individually via `ThreadPoolExecutor`.
- **Impact lookups add latency**: ~3-5s extra per search. Use `--no-impact` to skip if speed is critical.

See also:
- `references/openalex_api_quirks.md` — field availability, batch patterns, error handling
- `references/impact_data_sources.md` — journal/author impact metrics & proxies
- `references/publisher_tier_classification.md` — embedded tier list & implementation

## Extending Topics

To add a new topic, either:

1. Use `--keywords` flag for one-off searches
2. Add to `DEFAULT_TOPICS` in the script (dict at line ~50)
3. Create a `topics.json` file and load it (see classifier.py in Research-Newsletter for reference)

## Integration

This script is a standalone extract of the Research-Newsletter pipeline
(`/opt/data/Research-Newsletter/src/core/`). It reuses:

- OpenAlex client (search + relevance scoring)
- Quality gates (retraction, predatory, age, citations, dedup)
- Topic classification (keyword matching)
- Journal Impact (Publisher Tier list + batch source lookups)
- Author Impact (batch author lookups — corresponding author prioritized)

For the full newsletter pipeline with subscriber management, email delivery,
and cron automation, see the Research-Newsletter project.

## Impact Data Sources

All impact metrics come from **OpenAlex** — no commercial APIs required:

| Metric | Source | Method |
|--------|--------|--------|
| Publisher Tier | Embedded list (4 tiers) | No API call |
| Journal avg citations | `sources/{id}` — parallel batch | `cited_by_count / works_count` |
| Author citations | `authors/{id}` — parallel batch | Lifetime `cited_by_count` |
| Author institutions | `authors/{id}` — parallel batch | `last_known_institutions` |
| h-index | ❌ Not available in OpenAlex | — |

Impact lookups are skipped with `--no-impact` for faster results.

See also: `references/openalex_api_quirks.md` for field availability, batch lookup patterns, and error handling.
