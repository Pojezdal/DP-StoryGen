import json
import nltk
from sentence_transformers import SentenceTransformer
import numpy as np
from nltk.tokenize import sent_tokenize

nltk.download('punkt_tab')

# model_name = "Qwen/Qwen3-Embedding-4B"
model_name = "intfloat/multilingual-e5-large-instruct"

# Load the model
model = SentenceTransformer(model_name)


def split_text_into_chunks(text, max_chunk_size, model):
    sentences = sent_tokenize(text)
    sentence_tokens = [model.tokenize([sentence]) for sentence in sentences]
    sentence_token_sizes = [tokens['input_ids'].shape[1] for tokens in sentence_tokens]
    current_chunk = []
    chunks = []
    current_size = 0
    for sentence, size in zip(sentences, sentence_token_sizes):
        if current_size + size <= max_chunk_size:
            current_chunk.append(sentence)
            current_size += size
        else:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            if size > max_chunk_size:
                print("Warning: single sentence exceeds max size, truncating.")
            current_chunk = [sentence]
            current_size = size
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

if __name__ == "__main__":

    with open("datasets/wikidata/literary/data.jsonl", "r", encoding="utf-8") as f:
        lines = f.readlines()
        qids = [json.loads(line)["qid"] for line in lines]
        texts = [json.loads(line)["plot"] for line in lines]
        embeddings = []
        max_chunk_size = model.max_seq_length
        for text in texts:
            chunks = split_text_into_chunks(text, max_chunk_size, model)
            chunk_embeddings = model.encode(chunks, normalize_embeddings=True)
            embeddings.append(chunk_embeddings)
        # Save configuration
        with open("datasets/wikidata/literary/embedding_config.json", "w", encoding="utf-8") as config_file:
            config = {
                "model_name": model_name,
                "max_seq_length": max_chunk_size,
                "embedding_dimension": model.get_sentence_embedding_dimension(),
                "stories": {}
                }
            offset = 0
            for idx, (qid, emb) in enumerate(zip(qids, embeddings)):
                config["stories"][qid] = {
                    "index": idx,
                    "chunk_offset": offset,
                    "chunk_count": emb.shape[0],
                }
                offset += emb.shape[0]
            config_file.write(json.dumps(config, indent=2))
            
        # Save the mean embeddings
        mean_embeddings = [np.mean(emb, axis=0) for emb in embeddings]
        mean_embeddings = np.vstack(mean_embeddings)
        np.save("datasets/wikidata/literary/embeddings_mean.npy", mean_embeddings)
        print("Saved mean embeddings shape:", mean_embeddings.shape)
        
        # Save all chunk embeddings
        all_embeddings = np.vstack(embeddings)
        np.save("datasets/wikidata/literary/embeddings_all.npy", all_embeddings)
        print("Saved all chunk embeddings shape:", all_embeddings.shape)
        

    # with open("datasets/wikidata/literary/embedding_config.json", "r", encoding="utf-8") as config_file:
    #     config = json.load(config_file)
    #     model_name = config["model_name"]
    #     max_chunk_size = config["max_seq_length"]
    #     embedding_dimension = config["embedding_dimension"]
    #     stories_info = config["stories"]
    #     print(f"Loaded embedding config for model {model_name} with {len(stories_info)} stories.")
        
    #     with open("datasets/wikidata/literary/embeddings_mean.npy", "rb") as mean_file:
    #         mean_embeddings = np.load(mean_file)
    #         print("Loaded mean embeddings shape:", mean_embeddings.shape)
            
    #     with open("datasets/wikidata/literary/embeddings_all.npy", "rb") as all_file:
    #         all_embeddings = np.load(all_file)
    #         print("Loaded all chunk embeddings shape:", all_embeddings.shape)



        
    # embeddings = model.encode(lines[0:1])
    # similarity_scores = model.similarity(embeddings, embeddings)
    # print(similarity_scores)
