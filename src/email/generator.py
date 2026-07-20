def generate_digest_html(papers, topic_name, date):
    """
    papers: list of dicts from OpenAlex
    topic_name: string
    date: string (YYYY-MM-DD)
    returns: HTML string
    """
    header = f"""
    <html>
    <body style="font-family: system-ui, -apple-system, sans-serif; max-width: 600px; margin: auto; padding: 20px; color: #333;">
        <h1 style="color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px;">
            🔬 Research Update: {topic_name}
        </h1>
        <p style="color: #666; font-size: 14px;">Curated for you on {date}</p>
    """
    
    articles = ""
    for i, p in enumerate(papers):
        title = p.get('title', 'Untitled')
        date_p = p.get('publication_date', 'Unknown')
        citations = p.get('cited_by_count', 0)
        doi_url = f"https://doi.org/{p['doi']}" if p.get('doi') else '#'
        
        # Extract first author
        authors = []
        if 'authorships' in p and p['authorships']:
            for a in p['authorships'][:3]:
                name = a.get('author', {}).get('display_name') or a.get('raw_affiliation_string', 'Unknown')
                authors.append(name)
        author_str = ", ".join(authors) if authors else "Various authors"
        
        articles += f"""
        <div style="margin-bottom: 25px; border-bottom: 1px solid #eee; padding-bottom: 15px;">
            <h2 style="margin: 0 0 5px 0; font-size: 18px;">
                <a href="{doi_url}" style="color: #2563eb; text-decoration: none;">{title}</a>
            </h2>
            <p style="color: #666; font-size: 14px; margin: 5px 0;">
                {author_str} • {date_p} • 📈 {citations} citations
            </p>
        </div>
        """
    
    footer = """
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #999;">
            Delivered by Research Newsletter. Narrowing the gap between theory and practice.
        </p>
    </body>
    </html>
    """
    
    return header + articles + footer

if __name__ == "__main__":
    sample = [{"title": "Testing", "doi": "10.1234/test", "publication_date": "2026-07-20", "cited_by_count": 5, "authorships": [{"author": {"display_name": "Dr. Test"}}]}]
    print(generate_digest_html(sample, "ADHD", "2026-07-20"))
