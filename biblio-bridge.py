import requests
import json
from tqdm import tqdm

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

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Handle both single work and results list
        work = data if "id" in data else data.get("results", [{}])[0]
        if not work:
            return {"error": f"No results found for {identifier}"}

        # Process abstract (remove "abstract" and handle inverted index)
        abstract_index = work.get("abstract_inverted_index", {})
        if abstract_index:
            words_with_positions = [(pos, word) for word, positions in abstract_index.items() for pos in positions]
            words_with_positions.sort()
            words = [word for pos, word in words_with_positions if word.lower() != "abstract"]
            abstract_text = " ".join(words) if words else "No abstract available"
        else:
            abstract_text = "No abstract available"

        # Extract authors
        authors = [{"name": author.get("author", {}).get("display_name", "Unknown")} 
                   for author in work.get("authorships", [])]
        if not authors:
            return {"error": f"No authors available for {identifier}"}

        # Build result with safe dictionary access
        primary_topic = work.get("primary_topic", {}) or {}
        return {
            "id": work.get("id", ""),
            "title": work.get("title", "No title available"),
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

    except requests.Timeout:
        return {"error": f"Request timed out for {identifier}"}
    except (requests.RequestException, ValueError) as e:
        return {"error": f"Failed to fetch data for {identifier}: {str(e)}"}
      
# Example usage
doi = "10.1111/faf.12817"
email = "delsantooneillthomas@gmail.com"

# Fetch initial data
initial_data = fetch_openalex_data(doi, email)
if "error" in initial_data:
    print(f"Error: {initial_data['error']}")
    exit()

# Save initial data to a separate file in the existing resulting_metadata folder
with open(f"resulting_metadata/initial_data_{doi.replace('/', '_')}.json", "w", encoding="utf-8") as f:
    json.dump(initial_data, f, ensure_ascii=False, indent=2)
print(f"Initial data saved to resulting_metadata/initial_data_{doi.replace('/', '_')}.json")

# Fetch and save data for first-level referenced works with a clean progress bar
referenced_ids = initial_data.get("referenced_works", [])
if not referenced_ids:
    print("No referenced works found.")
else:
    # Initialize processed_ids as a set
    processed_ids = set(referenced_ids)  # Start with first-level references
    second_level_refs = []
    with tqdm(total=len(referenced_ids), desc="Fetching first-level referenced works", unit="item", 
              bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]") as pbar:
        for ref_id in referenced_ids:
            ref_data = fetch_openalex_data(ref_id, email)
            if "error" not in ref_data:
                file_name = f"resulting_metadata/dl0/{ref_id.split('/')[-1]}.json"
                with open(file_name, "w", encoding="utf-8") as f:
                    json.dump(ref_data, f, ensure_ascii=False, indent=2)
                second_level_refs.extend(ref_data.get("referenced_works", []))
            else:
                pbar.set_postfix({"last_error": ref_data["error"].split(":")[0]})
            pbar.update(1)

    print("All first-level referenced works data saved to resulting_metadata folder.")

    # Fetch and save data for second-level referenced works
    if second_level_refs:
        unique_second_level_refs = list(set(second_level_refs) - processed_ids)  # Remove duplicates and already processed IDs
        if unique_second_level_refs:
            with tqdm(total=len(unique_second_level_refs), desc="Fetching second-level referenced works", unit="item",
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]") as pbar:
                for ref_id in unique_second_level_refs:
                    ref_data = fetch_openalex_data(ref_id, email)
                    if "error" not in ref_data:
                        file_name = f"resulting_metadata/dl1/{ref_id.split('/')[-1]}.json"
                        with open(file_name, "w", encoding="utf-8") as f:
                            json.dump(ref_data, f, ensure_ascii=False, indent=2)
                        processed_ids.add(ref_id)  # Update processed_ids
                    else:
                        pbar.set_postfix({"last_error": ref_data["error"].split(":")[0]})
                    pbar.update(1)
            print("All second-level referenced works data saved to resulting_metadata folder.")
        else:
            print("No unique second-level referenced works found.")
    else:
        print("No second-level referenced works found.")

print("All data processing complete.")
