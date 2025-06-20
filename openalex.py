import asyncio
import aiohttp
import re
from typing import List, Dict, Optional, Union

async def _fetch_openalex_data_batch(identifiers: List[str], email: Optional[str] = None) -> List[Dict]:
    """Internal async function to fetch metadata from OpenAlex API for a list of DOIs or OpenAlex IDs in batches of 5."""
    async def fetch_single(session: aiohttp.ClientSession, identifier: str) -> Dict:
        # Set up base URL and parameters
        if identifier.startswith("https://openalex.org/"):
            work_id = identifier.split("/")[-1]
            url = f"https://api.openalex.org/works/{work_id}"
            params = {"mailto": email} if email else {}
        else:
            url = "https://api.openalex.org/works"
            params = {"filter": f"doi:{identifier}", "mailto": email} if email else {"filter": f"doi:{identifier}"}

        try:
            async with session.get(url, params=params, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()

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

                # Replace <scp>text</scp> with text
                abstract_text = re.sub(r'<scp>(.*?)</scp>', r'\1', abstract_text)
                title = re.sub(r'<scp>(.*?)</scp>', r'\1', title)

                # Extract authors
                authors = [{"name": author.get("author", {}).get("display_name", "Unknown")} 
                           for author in work.get("authorships", [])]

                # Build result
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
        except Exception as e:
            return {"error": f"Failed to fetch {identifier}: {str(e)}"}

    async def fetch_batch(batch: List[str]) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_single(session, identifier) for identifier in batch]
            return await asyncio.gather(*tasks, return_exceptions=True)

    # Process identifiers in batches of 5
    results = []
    for i in range(0, len(identifiers), 5):
        batch = identifiers[i:i + 5]
        batch_results = await fetch_batch(batch)
        results.extend(batch_results)
    
    return results

def fetch_openalex_data_batch(identifier: Union[str, List[str]], email: Optional[str] = None) -> Union[Dict, List[Dict]]:
    """Synchronous wrapper to fetch metadata from OpenAlex API for a single DOI/OpenAlex ID or a list of them.
    
    Args:
        identifier: Single DOI/OpenAlex ID or list of DOIs/OpenAlex IDs.
        email: Email for API's polite pool.
    
    Returns:
        Dictionary for single identifier or list of dictionaries for multiple identifiers.
    """
    # Convert single identifier to list for uniform processing
    identifiers = [identifier] if isinstance(identifier, str) else identifier
    # Run the async function and wait for results
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(_fetch_openalex_data_batch(identifiers, email))
    # Return single result if single identifier was provided
    return results[0] if isinstance(identifier, str) else results

def fetch_openalex_data(identifier: str, email: Optional[str] = None) -> Dict:
    """Synchronous function for single identifier fetch (backward compatibility).
    
    Args:
        identifier: DOI or OpenAlex ID.
        email: Email for API's polite pool.
    
    Returns:
        Dictionary with metadata or error message.
    """
    return fetch_openalex_data_batch(identifier, email)
