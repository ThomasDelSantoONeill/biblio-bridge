import requests
import json

def fetch_openalex_data(doi, email=None):
    """Fetch metadata from OpenAlex API for a given DOI.
    
    Args:
        doi (str): The Digital Object Identifier for the work.
        email (str, optional): Email for API's polite pool to improve request priority.
    
    Returns:
        dict: Metadata like title, abstract, authors, or an error message.
    """
    # Base URL for the OpenAlex API
    base_url = "https://api.openalex.org/works"
    
    # Set up parameters for API request via DOI filter.
    params = {"filter": f"doi:{doi}"}
    
    # If provided, add email to parameters for better API access
    if email:
        params["mailto"] = email
    
    try:
        # Send a GET request to the API with parameters and a 10-second timeout
        response = requests.get(base_url, params=params, timeout=10)
        
        # Check if the request was successful, raise error if not
        response.raise_for_status()
        response.encoding = "utf-8"
        
        # Parse the response into JSON format
        data = response.json()
        
        # Check if any results were returned
        if data.get("results"):
            # Get the first result (work) from the response
            work = data["results"][0]
            
            # Process the abstract, which is stored as an inverted index (words mapped to positions)
            abstract_index = work.get("abstract_inverted_index", {})
            words_with_positions = []
            
            # Loop through each word and its positions in the abstract
            for word, positions in abstract_index.items():
                for pos in positions:
                    words_with_positions.append((pos, word))
            
            # Sort words by their position, extract them in order and join into a single string
            words_with_positions.sort()
            words = [word for pos, word in words_with_positions]
            abstract_text = " ".join(words) if words else "No abstract available"
            
            # Build the result dictionary with key metadata
            result = {
                "id": work.get("id"),
                "title": work.get("title", "No title available"),
                "abstract": abstract_text,
                "authors": [
                    # Extract author names, default to "Unknown" if missing
                    {"name": author.get("author", {}).get("display_name", "Unknown")}
                    for author in work.get("authorships", [])
                ],
                "publication_year": work.get("publication_year"),
                "cited_by_count": work.get("cited_by_count", 0)
            }
            return result
        else:
            # Return error if no results found for the DOI
            return {"error": "No results found for DOI"}
            
    except requests.Timeout:
        # Handle case where the request takes too long (exceeds 10 seconds)
        return {"error": "Request timed out after 10 seconds"}
    except requests.RequestException as e:
        # Handle other network or API request errors
        return {"error": f"API request failed: {str(e)}"}
    except ValueError as e:
        # Handle errors in parsing JSON response
        return {"error": f"Invalid JSON response: {str(e)}"}

# Example usage
doi = "10.1111/faf.12817"
openalex_data = fetch_openalex_data(doi, email="delsantooneillthomas@gmail.com")
print("OpenAlex Data:")
print(json.dumps(openalex_data, indent=2, ensure_ascii=False))
