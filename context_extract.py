import json
import os
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import logging
import argparse
from multiprocessing import Pool
from joblib import Memory

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise OSError("Please install the spaCy model: python -m spacy download en_core_web_sm")

def preprocess_text(text):
    """Preprocess text for better term extraction."""
    doc = nlp(text)
    terms = [token.lemma_.lower() for token in doc if token.pos_ in ["NOUN", "PROPN", "ADJ"] and not token.is_stop]
    return " ".join(terms)

def extract_key_terms(text, n=10):
    """Extract top n key terms from text using spaCy."""
    if not text or text == "No abstract available":
        return []
    processed_text = preprocess_text(text)
    doc = nlp(processed_text)
    terms = [token.text for token in doc]
    term_freq = defaultdict(int)
    for term in terms:
        term_freq[term] += 1
    sorted_terms = sorted(term_freq.items(), key=lambda x: x[1], reverse=True)
    return [term for term, _ in sorted_terms[:n]]

memory = Memory("cache_dir", verbose=0)

@memory.cache
def compute_similarity_matrix(texts):
    """Compute cosine similarity matrix for all pairs of texts using TF-IDF with caching."""
    if len(texts) < 2:
        return np.array([])
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(texts)
    similarity_matrix = cosine_similarity(tfidf_matrix)
    return similarity_matrix

def process_json_files(base_dir, output_file, include_deeper_levels=False):
    """Process all JSON files in dl0/ to extract a context-based network."""
    logger.info(f"Processing files in base directory: {base_dir}")
    
    # Define paths
    dl0_path = os.path.join(base_dir, "dl0")
    dl1_path = os.path.join(base_dir, "dl1") if include_deeper_levels and os.path.exists(os.path.join(base_dir, "dl1")) else None
    
    if not os.path.exists(dl0_path):
        logger.error(f"Directory {dl0_path} does not exist")
        return {"error": f"Directory {dl0_path} does not exist"}

    # Collect all JSON files
    all_files = [os.path.join(dl0_path, f) for f in os.listdir(dl0_path) if f.endswith(".json")]
    if dl1_path and os.path.exists(dl1_path):
        all_files.extend([os.path.join(dl1_path, f) for f in os.listdir(dl1_path) if f.endswith(".json")])

    if not all_files:
        logger.error(f"No JSON files found in {dl0_path} or {dl1_path}")
        return {"error": f"No JSON files found in {dl0_path} or {dl1_path}"}

    # Extract data from all files
    works = {}
    texts = []
    for file_path in all_files:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            work_id = data.get("id", os.path.basename(file_path))
            title = data.get("title", "No title available")
            abstract = data.get("abstract", "No abstract available")
            text = f"{title} {abstract}"
            key_terms = extract_key_terms(text)
            works[work_id] = {"title": title, "key_terms": key_terms}
            texts.append(text)
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            works[os.path.basename(file_path)] = {"title": "Error", "key_terms": [], "error": str(e)}

    # Compute similarity matrix
    similarity_matrix = compute_similarity_matrix(texts)
    if similarity_matrix.size == 0:
        logger.warning("Similarity matrix is empty due to insufficient texts")
        edges = []
    else:
        edges = []
        for i in range(len(all_files)):
            for j in range(i + 1, len(all_files)):
                similarity = similarity_matrix[i, j]
                if similarity > 0:  # Optional threshold can be added here
                    edges.append({
                        "source": os.path.basename(all_files[i]).replace(".json", ""),
                        "target": os.path.basename(all_files[j]).replace(".json", ""),
                        "weight": similarity
                    })

    # Prepare network output
    network = {
        "nodes": [{"id": work_id, "title": data["title"], "key_terms": data["key_terms"]} for work_id, data in works.items()],
        "edges": edges
    }

    # Save results
    try:
        with open(output_file, "w") as f:
            json.dump(network, f, indent=2)
        logger.info(f"Network results saved to {output_file}")
        return {"status": f"Network results saved to {output_file}"}
    except Exception as e:
        logger.error(f"Failed to save results: {str(e)}")
        return {"error": f"Failed to save results: {str(e)}"}

def test_module(base_dir=None, output_file=None, include_deeper_levels=False):
    """Test the context extraction module with sample JSON data."""
    if not base_dir or not output_file:
        os.makedirs("test_resulting_metadata/dl0", exist_ok=True)
        os.makedirs("test_resulting_metadata/dl1", exist_ok=True)
        focal_json = {
            "id": "https://openalex.org/W4393009312",
            "title": "An efficient tool to find multispecies MSY for interacting fish stocks",
            "abstract": "Natural ecological communities exhibit complex mixtures of interspecific biological interactions...",
            "referenced_works": ["https://openalex.org/W1183577688"]
        }
        ref_json = {
            "id": "https://openalex.org/W1183577688",
            "title": "Moving towards ecosystem-based fisheries management...",
            "abstract": "No abstract available",
            "referenced_works": []
        }
        with open("test_resulting_metadata/dl0/focal.json", "w") as f:
            json.dump(focal_json, f, indent=2)
        with open("test_resulting_metadata/dl1/ref1.json", "w") as f:
            json.dump(ref_json, f, indent=2)
        base_dir = "test_resulting_metadata"
        output_file = "test_resulting_metadata/network_results.json"

    result = process_json_files(base_dir, output_file, include_deeper_levels)
    print(json.dumps(result, indent=2))

    # Cleanup if using default test data
    if not base_dir or not output_file:
        import shutil
        shutil.rmtree("test_resulting_metadata", ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test context extraction module.")
    parser.add_argument("--base_dir", help="Path to base directory (e.g., resulting_metadata)")
    parser.add_argument("--output", help="Path to output JSON file")
    parser.add_argument("--include_deeper", action="store_true", help="Include deeper levels (e.g., dl1)")
    args = parser.parse_args()
    test_module(args.base_dir, args.output, args.include_deeper)
