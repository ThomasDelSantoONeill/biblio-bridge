import requests
import json
from tqdm import tqdm

def fetch_openalex_data(identifier, email=None):
    """Fetch metadata from OpenAlex API for a given DOI or OpenAlex ID.
    
    Args:
        identifier (str): The Digital Object Identifier (e.g., "10.1111/faf.12817") 
                         or OpenAlex ID (e.g., "https://openalex.org/W2033142198").
        email (str, optional): Email for API's polite pool to improve request priority.
    
    Returns:
        dict: Metadata like title, abstract, authors, or an error message.
              Returns {"error": "No authors available for <identifier>"} if authors list is empty.
    """
    # Determine the base URL and ID based on the identifier format
    if identifier.startswith("https://openalex.org/"):
        work_id = identifier.split("/")[-1]
        base_url = f"https://api.openalex.org/works/{work_id}"
    else:
        base_url = "https://api.openalex.org/works"
        params = {"filter": f"doi:{identifier}"}
    
    params = params if "params" in locals() else {}
    if email:
        params["mailto"] = email
    
    try:
        response = requests.get(base_url, params=params if "params" in locals() else None, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        data = response.json()
        
        if data.get("results") or (isinstance(data, dict) and "id" in data):
            work = data if "id" in data else data["results"][0]
            abstract_index = work.get("abstract_inverted_index", {})
            words_with_positions = []
            if abstract_index is not None:
                for word, positions in abstract_index.items():
                    for pos in positions:
                        words_with_positions.append((pos, word))
                words_with_positions.sort()
                words = [word for pos, word in words_with_positions]
                abstract_text = " ".join(words) if words else "No abstract available"
            else:
                abstract_text = "No abstract available"
            
            authors = [{"name": author.get("author", {}).get("display_name", "Unknown")} 
                       for author in work.get("authorships", [])]
            
            if not authors:
                return {"error": f"No authors available for {identifier}"}
            
            # Ensure work_data is always a dictionary
            work_data = work if work is not None and isinstance(work, dict) else {}
            try:
                result = {
                    "id": work_data.get("id"),
                    "title": work_data.get("title", "No title available"),
                    "abstract": abstract_text,
                    "authors": authors,
                    "publication_year": work_data.get("publication_year"),
                    "cited_by_count": work_data.get("cited_by_count", 0),
                    "primary_topic": work_data.get("primary_topic", {"display_name": "Unknown topic"}).get("display_name", "Unknown topic"),
                    "subfield_topic": work_data.get("primary_topic", {"subfield": {"display_name": "Unknown subfield"}}).get("subfield", {}).get("display_name", "Unknown subfield"),
                    "field_topic": work_data.get("primary_topic", {"field": {"display_name": "Unknown field"}}).get("field", {}).get("display_name", "Unknown field"),
                    "domain_topic": work_data.get("primary_topic", {"domain": {"display_name": "Unknown domain"}}).get("domain", {}).get("display_name", "Unknown domain"),
                    "referenced_works": work_data.get("referenced_works", [])
                }
            except AttributeError as e:
                print(f"Failed item ID: {identifier}")
                result = {
                    "id": work_data.get("id"),
                    "title": work_data.get("title", "No title available"),
                    "abstract": abstract_text,
                    "authors": authors,
                    "publication_year": work_data.get("publication_year"),
                    "cited_by_count": work_data.get("cited_by_count", 0),
                    "primary_topic": "Unknown topic",
                    "subfield_topic": "Unknown subfield",
                    "field_topic": "Unknown field",
                    "domain_topic": "Unknown domain",
                    "referenced_works": work_data.get("referenced_works", [])
                }
            return result
        else:
            return {"error": f"No results found for {identifier}"}
            
    except requests.Timeout:
        return {"error": f"Request timed out after 10 seconds for {identifier}"}
    except requests.RequestException as e:
        return {"error": f"API request failed for {identifier}: {str(e)}"}
    except ValueError as e:
        return {"error": f"Invalid JSON response for {identifier}: {str(e)}"}
      
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
