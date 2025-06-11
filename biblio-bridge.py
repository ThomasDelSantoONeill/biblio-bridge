import requests
import json
from tqdm import tqdm
import time

def fetch_openalex_data(identifier, email=None):
    """Fetch metadata from OpenAlex API for a given DOI or OpenAlex ID.
    
    Args:
        identifier (str): The Digital Object Identifier (e.g., "10.1111/faf.12817") 
                         or OpenAlex ID (e.g., "https://openalex.org/W2033142198").
        email (str, optional): Email for API's polite pool to improve request priority.
    
    Returns:
        dict: Metadata like title, abstract, authors, or an error message.
    """
    # Determine the base URL and ID based on the identifier format
    if identifier.startswith("https://openalex.org/"):
        # Extract the work ID (e.g., W1183577688) from any OpenAlex URL format
        work_id = identifier.split("/")[-1]  # Extract the last part (W-number)
        base_url = f"https://api.openalex.org/works/{work_id}"
    else:
        # Assume it's a DOI, use the search endpoint
        base_url = "https://api.openalex.org/works"
        params = {"filter": f"doi:{identifier}"}
    
    # Add email for polite pool if provided
    params = params if "params" in locals() else {}
    if email:
        params["mailto"] = email
    
    try:
        response = requests.get(base_url, params=params if "params" in locals() else None, timeout=10)
        response.raise_for_status()
        response.encoding = "utf-8"
        data = response.json()
        
        if data.get("results") or (isinstance(data, dict) and "id" in data):  # Handle both search and direct access
            work = data if "id" in data else data["results"][0]
            abstract_index = work.get("abstract_inverted_index", {})
            words_with_positions = []
            if abstract_index is not None:  # Check if abstract_index is not None
                for word, positions in abstract_index.items():
                    for pos in positions:
                        words_with_positions.append((pos, word))
                words_with_positions.sort()
                words = [word for pos, word in words_with_positions]
                abstract_text = " ".join(words) if words else "No abstract available"
            else:
                abstract_text = "No abstract available"  # Set to placeholder if None
            
            result = {
                "id": work.get("id"),
                "title": work.get("title", "No title available"),
                "abstract": abstract_text,
                "authors": [{"name": author.get("author", {}).get("display_name", "Unknown")} 
                           for author in work.get("authorships", [])],
                "publication_year": work.get("publication_year"),
                "cited_by_count": work.get("cited_by_count", 0),
                "referenced_works": work.get("referenced_works", [])  # Include referenced works
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

# Fetch and save data for each referenced work with a clean progress bar
referenced_ids = initial_data.get("referenced_works", [])
if not referenced_ids:
    print("No referenced works found.")
else:
    # Use tqdm with a single-line progress bar
    with tqdm(total=len(referenced_ids), desc="Fetching referenced works", unit="item", 
                 bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]") as pbar:
        for ref_id in referenced_ids:
            ref_data = fetch_openalex_data(ref_id, email)
            if "error" not in ref_data:
                file_name = f"resulting_metadata/{ref_id.split('/')[-1]}.json"
                with open(file_name, "w", encoding="utf-8") as f:
                    json.dump(ref_data, f, ensure_ascii=False, indent=2)
            else:
                pbar.set_postfix({"last_error": ref_data["error"].split(":")[0]})  # Show brief error summary
            time.sleep(1)  # Add delay to respect API rate limits
            pbar.update(1)

print("All referenced works data saved to resulting_metadata folder.")
