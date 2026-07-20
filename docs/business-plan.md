# ResearchPulse — 1-Page Business Plan

## Mission

Inspire people and organizations to trust science and narrow the gap between theory and practice by delivering AI-curated, domain-specific research updates directly to professional inboxes.

---

## 1. Problem Statement

Publications exceed 2.5 million per year across PubMed, arXiv, IEEE, ACM, Web of Science, and more. Researchers, clinicians, and industry professionals spend an estimated **4–6 hours per week** manually tracking relevant new papers. Free aggregators (Google Scholar alerts, arXiv RSS) deliver undifferentiated firehoses — no curation, no context, no signal-to-noise filtering. The result: key advances are missed, and the theory-practice gap widens.

---

## 2. Solution

**ResearchPulse** is a subscription newsletter service where users select the topics, journals, and fields they care about and receive a weekly digest of the most impactful recent publications — curated, summarized, and annotated by AI, with human editorial oversight on paid tiers.

- **Topic picker**: Browse a taxonomy spanning 40+ domains (e.g., oncology, NLP, climate science, materials, behavioral economics).
- **Smart filtering**: Citation impact, recency, novelty, and relevance scoring powered by Semantic Scholar + arXiv APIs.
- **Readable digests**: 3–5 sentence plain-language summaries, key findings callouts, and links to open-access full text.
- **No vendor lock-in**: Export, forward, integrate — users own their feed.

---

## 3. Target Audiences

| Segment | Pain Point | Size (est.) | Willingness to Pay |
|---|---|---|---|
| **Academia** (faculty, postdocs, PhD students) | Can't keep up with their own subfield | ~7 M globally | Low–Medium ($5–15/mo) |
| **Healthcare / Clinical** (physicians, nurses, pharmacists) | Evidence-based practice requires current literature | ~14 M US, ~42 M globally | Medium–High ($15–30/mo) |
| **Corporate R&D** (pharma, biotech, tech, engineering) | Competitive intelligence; scanning for patents/tech | ~2 M R&D professionals | High ($50–150/user/mo) |
| **Consultants & Policy Advisors** | Need credible, timely science for client deliverables | ~3 M globally | Medium–High ($20–50/mo) |
| **Graduate Students** | Literature review, thesis monitoring | ~4 M globally | Low (freemium primary) |

**Primary beachhead:** Healthcare professionals and corporate R&D — highest willingness to pay, clearest ROI (time saved, decisions improved).

---

## 4. Competitive Landscape

| Competitor | Model | Strengths | Weaknesses vs. ResearchPulse |
|---|---|---|---|
| **ScienceDaily** | Free (ad-supported) | Huge traffic, broad topics | No customization, press-release quality, no deep-dive |
| **arXiv email alerts** | Free | Covers CS/physics/math exhaustively | No curation, no summaries, single-domain focus |
| **Google Scholar Alerts** | Free | Massive index | Keyword-only, no ranking, no summaries |
| **PubPeer** | Free + institutional | Post-publication peer review, 260K+ papers | Community-driven comments, not a digest; niche audience |
| **Retraction Watch** | Free (donations) | Science integrity journalism | Narrow scope (retractions), editorial-driven, not automated |
| **Semantic Scholar** | Free (nonprofit) | AI-powered discovery, API access | Search/retrieval tool, not a newsletter; no personalization |
| **Research.com** | Freemium + premium | Paper metrics, recommendations | Heavy paywall, limited newsletter-style delivery |
| **Alpha / AlphaSignal** | N/A (parked domain) | — | Not active in this space |

**Key gap:** No existing service combines **user-defined topic selection + AI curation + plain-language summaries + multi-domain coverage + a subscription newsletter format**. ResearchPulse fills this white space.

---

## 5. Monetization (Three-Tier Freemium)

| Tier | Price | Features |
|---|---|---|
| **Free** | $0 | 1 topic area, weekly digest (5 papers), basic summaries, ad-supported |
| **Pro** | $12/mo or $99/yr | Up to 10 topics, daily digest, citation context, open-access full-text links, export to Zotero/Notion, no ads |
| **Enterprise** | $79/user/mo (min. 10 seats) | Unlimited topics, API access, custom taxonomies, team management, SSO, compliance reporting, dedicated support |

**Additional revenue streams (Phase 2):**
- Sponsored placements (pharma, instrumentation vendors) — clearly labeled
- Institutional site licenses (universities, hospital networks)
- Custom one-off literature review reports

---

## 6. Core Value Propositions

1. **"Never miss what matters"** — Personalized, impact-scored digests replace hours of manual searching.
2. **"Science made readable"** — AI-generated summaries distill dense methodology into actionable insights for non-specialists.
3. **"Built for your domain"** — 40+ topic categories across health, tech, environment, social science, and engineering.
4. **"Trust, not hype"** — Citation-aware curation, retraction checks (via Retraction Watch DB), and bias-flagging.
5. **"Integrates into your workflow"** — Email, web reader, Zotero/Notion export, API.

---

## 7. Go-to-Market Strategy

### Phase 1 — Launch (Months 1–3)
- Build MVP: topic picker + weekly email digest for 5 seed domains (AI/ML, oncology, climate science, neuroscience, materials engineering).
- Acquire first 500 users via academic subreddits, ResearchGate groups, LinkedIn science communities, and direct outreach to PhD student ambassadors.
- Offer free lifetime access to founding 500 subscribers (viral referral: each refers 2 friends = 1 month free).

### Phase 2 — Growth (Months 4–9)
- Expand to 40+ topics. Launch Pro tier ($12/mo).
- Content marketing: publish "State of [Domain] in 2026" reports (gated behind email signup).
- Partner with 3–5 academic departments for departmental pilot programs.
- SEO: rank for "latest research in [topic]" long-tail queries via weekly blog posts.

### Phase 3 — Scale (Months 10–18)
- Enterprise tier + API launch. Target R&D teams at pharma/biotech/top-500 tech.
- Integrate Stripe for self-serve payments.
- Referral program: 20% recurring commission for Pro referrers.
- Conference presence: ASH, NeurIPS, AAAS — sponsor "Latest Research" session.

### Acquisition channels (ranked by expected ROI)
1. **Organic/SEO** — "latest [topic] research" queries (high volume, low CPC).
2. **Academic ambassadors** — PhD students who share with their lab groups.
3. **LinkedIn** — targeted ads to job titles: researcher, scientist, clinical director, R&D manager.
4. **Partnerships** — co-branded digests with professional societies (e.g., ASCO, ACM SIGCHI).
5. **Content engine** — quarterly research trend reports distributed via PR.

---

## 8. Technology Stack (High-Level)

- **Data ingestion:** arXiv API, Semantic Scholar API, PubMed API, Crossref API, journal RSS feeds.
- **AI layer:** LLM-powered summarization + relevance scoring + novelty detection.
- **Backend:** Python/FastAPI, PostgreSQL, Redis (queue), Celery (scheduled jobs).
- **Frontend:** React/Next.js for topic picker, reader, and dashboard.
- **Email:** Resend / SendGrid for transactional + digest delivery.
- **Payments:** Stripe (Phase 2+).
- **Hosting:** Cloud (AWS/GCP), containerized.

---

## 9. Financial Projections (Year 1–3)

| Metric | Year 1 | Year 2 | Year 3 |
|---|---|---|---|
| Paid subscribers (Pro) | 500 | 3,500 | 12,000 |
| Enterprise seats | 50 | 400 | 1,500 |
| ARR | ~$65K | ~$560K | ~$2.1M |
| CAC | ~$15 | ~$22 | ~$30 |
| LTV | ~$180 | ~$240 | ~$350 |
| Burn (annual) | ~$120K | ~$350K | ~$800K |

*Assumptions: blended MRR of $20/user across tiers, 5% monthly churn, enterprise deals averaging $79/user/mo at 25-seat ACV.*

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| **AI summary accuracy** | Human review on Pro/Enterprise tiers; user feedback loop (upvote/downvote summaries); cite sources inline |
| **Competition from incumbents** (Google, Semantic Scholar adding newsletters) | Focus on curation quality, personalization depth, and community features — harder to replicate quickly |
| **API rate limits / data access** | Multi-source ingestion (arXiv + Semantic Scholar + Crossref + PubMed); cache aggressively |
| **Low conversion from free to paid** | Strong free tier drives habit; paywall on advanced features (daily digest, export, citation context) creates upgrade triggers |
| **Regulatory/compliance** (healthcare data) | Never process PHI; summaries are public-literature-based; GDPR-compliant data handling |

---

## 11. Key Milestones

- **Q3 2026:** MVP launch, 500 free users
- **Q4 2026:** Pro tier live, first 200 paying subscribers
- **Q2 2027:** 40+ topics, SEO traction, 1,000 Pro subscribers
- **Q3 2027:** Enterprise pilot with 3 organizations
- **Q1 2028:** $500K+ ARR, Series Seed round

---

*ResearchPulse — Making every breakthrough findable.*
