import requests

def fetch_openalex_data(identifier, email=None):
    """Fetch metadata from OpenAlex API for a given DOI or OpenAlex ID.
    
    Args:
        identifier (str): DOI (e.g., "10.1111/faf.12817") or OpenAlex ID (e.g., "https://openalex.org/W2033142198").
        email (str, optional): Email for API's polite pool to improve request priority.
    
    Returns:
        dict: Metadata (title, abstract, authors, etc.) or an error message.
    """
    # Set up base URL and parameters
    if identifier.startswith("https://openalex.org/"):
        work_id = identifier.split("/")[-1]
        url = f"https://api.openalex.org/works/{work_id}"
        params = {"mailto": email} if email else {}
    else:
        url = "https://api.openalex.org/works"
        params = {"filter": f"doi:{identifier}", "mailto": email} if email else {"filter": f"doi:{identifier}"}

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Handle both single work and results list
    work = data if "id" in data else data.get("results", [{}])[0]
    if not work:
        return {"error": f"No results for {identifier}"}

    # Process abstract (remove "abstract" and handle inverted index)
    abstract_index = work.get("abstract_inverted_index", {})
    if abstract_index:
        words_with_positions = [(pos, word) for word, positions in abstract_index.items() for pos in positions]
        words_with_positions.sort()
        words = [word for pos, word in words_with_positions if word.lower() != "abstract"]
        abstract_text = " ".join(words) if words else "No abstract available"
    else:
        abstract_text = "No abstract available"

    # Replace Unicode escapes with standard dash
    abstract_text = abstract_text.replace("\u2010", "-").replace("\u2013", "-")
    title = work.get("title", "No title available").replace("\u2010", "-").replace("\u2013", "-")

    # Replace <scp>text</scp> with text by removing <scp> and </scp> tags
    import re
    abstract_text = re.sub(r'<scp>(.*?)</scp>', r'\1', abstract_text)
    title = re.sub(r'<scp>(.*?)</scp>', r'\1', title)

    # Extract authors
    authors = [{"name": author.get("author", {}).get("display_name", "Unknown")} 
               for author in work.get("authorships", [])]

    # Build result with safe dictionary access
    primary_topic = work.get("primary_topic", {}) or {}
    return {
        "id": work.get("id", ""),
        "title": title,
        "abstract": abstract_text,
        "authors": authors,
        "publication_year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count", 0),
        "primary_topic": primary_topic.get("display_name", "Unknown topic"),
        "subfield_topic": primary_topic.get("subfield", {}).get("display_name", "Unknown subfield"),
        "field_topic": primary_topic.get("field", {}).get("display_name", "Unknown field"),
        "domain_topic": primary_topic.get("domain", {}).get("display_name", "Unknown domain"),
        "referenced_works": work.get("referenced_works", [])
    }
