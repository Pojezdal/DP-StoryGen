import json
from sentence_transformers import SentenceTransformer
import numpy as np

# Load the model
#model = SentenceTransformer("Qwen/Qwen3-Embedding-4B")
model = SentenceTransformer('intfloat/multilingual-e5-large-instruct')

with open("datasets/wikidata/literary/data.jsonl", "r", encoding="utf-8") as f:
    lines = f.readlines()
    qids = [json.loads(line)["qid"] for line in lines]
    texts = [json.loads(line)["plot"] for line in lines]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    
    np.savez_compressed("datasets/wikidata/literary/embeddings.npz", qids=qids, embeddings=embeddings)

# embeddings_data = np.load("datasets/wikidata/literary/embeddings.npz")
# qids = embeddings_data["qids"]
# embeddings = embeddings_data["embeddings"]
    
# embeddings = model.encode(lines[0:1])
# similarity_scores = model.similarity(embeddings, embeddings)
# print(similarity_scores)
