import json
import os
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

# Load spaCy model from specified path
nlp = spacy.load("./models/en_core_web_lg/en_core_web_lg/en_core_web_lg-3.8.0/")

def preprocess_text(text):
    doc = nlp(text)
    terms = [token.lemma_.lower() for token in doc if token.pos_ in ["NOUN", "PROPN", "ADJ"] and not token.is_stop]
    return " ".join(terms)

def extract_key_terms(text, n=10):
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

def compute_similarity_matrix(texts):
    if len(texts) < 2:
        return np.array([])
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(texts)
    similarity_matrix = cosine_similarity(tfidf_matrix)
    return similarity_matrix

def process_json_files(doi_safe, depth_level):
    # Paths based on dynamic DOI
    base_dir = "metadata"
    focal_file = os.path.join(base_dir, f"initial_data_{doi_safe}.json")
    # Adjust reference directory to match R code's saving logic (dl{depth_level-1})
    ref_dir = os.path.join(base_dir, f"dl{depth_level-1}") if depth_level > 0 else base_dir
    results_dir = "results"
    output_file = f"network_results_depth_{depth_level}.json"
    output_path = os.path.join(results_dir, output_file)

    # Ensure results directory exists
    os.makedirs(results_dir, exist_ok=True)

    # Load focal data
    if not os.path.exists(focal_file):
        return {"status": f"Error: Focal file {focal_file} not found"}
    with open(focal_file, "r") as f:
        focal_data = json.load(f)

    focal_id = focal_data.get("id", os.path.basename(focal_file).replace(".json", ""))
    focal_title = focal_data.get("title", "No title available")
    focal_abstract = focal_data.get("abstract", "No abstract available")
    focal_text = f"{focal_title} {focal_abstract}"
    focal_key_terms = extract_key_terms(focal_text)

    # Collect all reference files in the specified depth level
    all_files = [os.path.join(ref_dir, f) for f in os.listdir(ref_dir) if f.endswith(".json") and f != os.path.basename(focal_file)] if os.path.exists(ref_dir) else []
    all_files.insert(0, focal_file)

    # Log the files being processed
    status_info = f"Processing {len(all_files)} files: {', '.join([os.path.basename(f) for f in all_files])}"

    # Extract data from relevant files
    works = {}
    texts = []
    for file_path in all_files:
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r") as f:
            data = json.load(f)
        work_id = data.get("id", os.path.basename(file_path).replace(".json", ""))
        title = data.get("title", "No title available")
        abstract = data.get("abstract", "No abstract available")
        text = f"{title} {abstract}"
        key_terms = extract_key_terms(text)
        works[work_id] = {"title": title, "key_terms": key_terms}
        texts.append(text)

    # Compute similarity matrix
    similarity_matrix = compute_similarity_matrix(texts)
    edges = []
    if similarity_matrix.size > 0:
        file_ids = [os.path.basename(f).replace(".json", "") for f in all_files]
        for i in range(len(all_files)):
            for j in range(i + 1, len(all_files)):
                similarity = similarity_matrix[i, j]
                if similarity > 0:
                    edges.append({
                        "source": file_ids[i],
                        "target": file_ids[j],
                        "weight": similarity
                    })

    # Prepare network output
    network = {
        "nodes": [{"id": work_id, "title": data["title"], "key_terms": data["key_terms"]} for work_id, data in works.items()],
        "edges": edges,
        "debug": status_info
    }

    # Save results
    with open(output_path, "w") as f:
        json.dump(network, f, indent=2)

    return {"status":"Context of referenced works analysed"}
