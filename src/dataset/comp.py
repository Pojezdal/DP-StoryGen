import json
import numpy as np
from sentence_transformers import SentenceTransformer
from embed import split_text_into_chunks
import torch
from torch import tensor, empty, cat
from scipy import stats


with open("datasets/wikidata/literary/embedding_config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)

model_name = config.get("model_name", "all-MiniLM-L6-v2")
max_chunk_size = config.get("max_chunk_size", 512)
stories_info = config.get("stories", [])
print(f"Using model: {model_name} with max chunk size: {max_chunk_size} and stories count: {len(stories_info)}")

with open("datasets/wikidata/literary/embeddings_mean.npy", "rb") as stories_file:
    embeddings_mean = np.load(stories_file)
    
with open("datasets/wikidata/literary/embeddings_all.npy", "rb") as stories_file:
    embeddings_all = np.load(stories_file)

model = SentenceTransformer(model_name)


intra_dataset_similarity = model.similarity(embeddings_mean, embeddings_mean).fill_diagonal_(0)

positions = torch.where(intra_dataset_similarity == 1)
print(f"Positions where similarity is 1: {list(zip(positions[0].tolist(), positions[1].tolist()))}")

intra_dataset_similarity_max = intra_dataset_similarity.max(dim=1).values
intra_dataset_similarity_top_5 = intra_dataset_similarity.topk(k=5, dim=1).values.mean(dim=1)
intra_dataset_similarity_top_10 = intra_dataset_similarity.topk(k=10, dim=1).values.mean(dim=1)
intra_dataset_similarity_mean = intra_dataset_similarity.mean(dim=1)
intra_dataset_similarity = intra_dataset_similarity[torch.triu_indices(intra_dataset_similarity.shape[0], intra_dataset_similarity.shape[1], offset=1).unbind()]

def plot_similarity_distribution(similarity_data, title, xlabel, ylabel, filename):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 6))
    plt.hist(similarity_data, bins=50, edgecolor='black', alpha=0.7, density=True)

    # Fit and plot normal distribution curve
    mu, sigma = stats.norm.fit(similarity_data)
    x = np.linspace(similarity_data.min(), similarity_data.max(), 100)
    plt.plot(x, stats.norm.pdf(x, mu, sigma), 'r-', linewidth=2, label='Normal Distribution')

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title + "\n" + f"Mean: {mu:.4f}, Std Dev: {sigma:.4f}")
    plt.grid(axis='y', alpha=0.3)
    plt.legend()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()

# plot_similarity_distribution(
#     intra_dataset_similarity.numpy(),
#     title="Intra-dataset Similarity Distribution (Mean Embeddings)",
#     xlabel="Similarity Score",
#     ylabel="Density",
#     filename="src/dataset/files/intra_dataset_similarity_distribution_mean_embeddings.png"
# )

# plot_similarity_distribution(
#     intra_dataset_similarity_max.numpy(),
#     title="Max Intra-dataset Similarity Distribution (Mean Embeddings)",
#     xlabel="Max Similarity Score",
#     ylabel="Density",
#     filename="src/dataset/files/intra_dataset_max_similarity_distribution_mean_embeddings.png"
# )

# plot_similarity_distribution(
#     intra_dataset_similarity_top_5.numpy(),
#     title="Top 5 Intra-dataset Similarity Distribution (Mean Embeddings)",
#     xlabel="Top 5 Mean Similarity Score",
#     ylabel="Density",
#     filename="src/dataset/files/intra_dataset_top_5_similarity_distribution_mean_embeddings.png"
# )

# plot_similarity_distribution(
#     intra_dataset_similarity_top_10.numpy(),
#     title="Top 10 Intra-dataset Similarity Distribution (Mean Embeddings)",
#     xlabel="Top 10 Mean Similarity Score",
#     ylabel="Density",
#     filename="src/dataset/files/intra_dataset_top_10_similarity_distribution_mean_embeddings.png"
# )

# plot_similarity_distribution(
#     intra_dataset_similarity_mean.numpy(),
#     title="Mean Intra-dataset Similarity Distribution (Mean Embeddings)",
#     xlabel="Mean Similarity Score",
#     ylabel="Density",
#     filename="src/dataset/files/intra_dataset_mean_similarity_distribution_mean_embeddings.png"
# )

# exit()

print(f"Intra-dataset similarity (mean embeddings) shape: {intra_dataset_similarity.shape}")


stories_to_compare = [
    "the_raven's_peak_inheritance_2025-12-08_125252",
    "The_Oakhaven_Requiem_2025-11-30_205622",
    "The_Cartographer's_Shadow_2025-11-19_175908",
    "The_Architect_of_Silence_2025-11-27_174658",
]

print(f"Mean embedding shape: {embeddings_mean.shape}")
print(f"All embeddings shape: {embeddings_all.shape}")


instruction = "Given a detective story, retrieve other stories with similar plot structure, events, and character roles."

mean_similarity = empty((embeddings_mean.shape[0], 0))
mean_indices = empty((embeddings_mean.shape[0], 0))
all_similarity = empty((embeddings_mean.shape[0], 0))
all_indices = empty((embeddings_mean.shape[0], 0))

for story_to_compare in stories_to_compare:
    print(f"\nComparing story: {story_to_compare}")
    
    def generate_story_embedding(story_path: str, model: SentenceTransformer, instruction: str, max_chunk_size: int):
        with open(story_path, "r", encoding="utf-8") as story_file:
            story_text = story_file.read()
        story_chunks = split_text_into_chunks(story_text, max_chunk_size, model)
        story_chunks = [f"Instruct: {instruction}\nQuery: {chunk}" for chunk in story_chunks]
        print(f"Story split into {len(story_chunks)} chunks.")
        story_embeddings = model.encode(story_chunks, normalize_embeddings=True)
        print(f"Generated {len(story_embeddings)} embeddings for the story chunks.")
        return story_embeddings
    
    story_directory = f"src/demo/Stories/{story_to_compare}/"
    story_embeddings_file = f"{story_directory}/full_story_embeddings.npy"
    story_embeddings = None
    try:
        with open(story_embeddings_file, "rb") as story_embedding_file:
            story_embeddings = np.load(story_embedding_file)
        print(f"Loaded existing embeddings for story: {story_to_compare}")
    except FileNotFoundError:
        print(f"Generating embeddings for story: {story_to_compare}")
        story_embeddings = generate_story_embedding(f"src/demo/Stories/{story_to_compare}/full_story.txt", model, instruction, max_chunk_size)
        with open(f"src/demo/Stories/{story_to_compare}/full_story_embeddings.npy", "wb") as story_embedding_file:
            np.save(story_embedding_file, story_embeddings)
        print(f"Saved embeddings for story: {story_to_compare}")


    def compare_mean_embeddings(story_embedding, embeddings_mean, model : SentenceTransformer):
        story_mean_embedding = np.mean(story_embedding, axis=0, keepdims=True)
        
        similarity = model.similarity(story_mean_embedding, embeddings_mean)
        print(f"Most similar story (mean embeddings) index: {np.argmax(similarity)}, similarity: {similarity.max()}")
        print(f"Least similar story (mean embeddings) index: {np.argmin(similarity)}, similarity: {similarity.min()}")
        print(f"Mean similarity across all stories (mean embeddings): {similarity.mean()}")
        print(f"Standard deviation of similarity (mean embeddings): {similarity.std()}")
        print(f"Sum of similarity (mean embeddings): {similarity.sum()}")
        print(f"Mean similarity acroess top 10 stories (mean embeddings): {similarity.topk(k=10).values.mean()}")
        print(f"Sum of similarity across top 10 stories (mean embeddings): {similarity.topk(k=10).values.sum()}")
        return (similarity, similarity.argsort(descending=True))
        
    def compare_all_embeddings(story_embedding, embeddings_all, model : SentenceTransformer):
        similarity_scores = empty((0, 1))
        for story in stories_info.values():
            index = story["index"]
            chunk_offset = story["chunk_offset"]
            chunk_count = story["chunk_count"]
            story_chunks_embeddings = embeddings_all[chunk_offset:chunk_offset + chunk_count]
            
            similarity = model.similarity(story_embedding, story_chunks_embeddings)
            similarity = similarity.max(dim=1).values

            top_k = similarity.topk(k=3).values
            top_k_mean = top_k.mean().item()
            similarity_scores = cat((similarity_scores, tensor([[top_k_mean]])), dim=0)
        
        print(f"Mean similarity across all stories (all embeddings): {similarity_scores.mean().item()}")
        print(f"Standard deviation of similarity (all embeddings): {similarity_scores.std().item()}")
        print(f"Sum of similarity (all embeddings): {similarity_scores.sum().item()}")
        print(f"Mean similarity across top 10 stories (all embeddings): {similarity_scores.topk(k=10, dim=0).values.mean().item()}")
        print(f"Sum of similarity across top 10 stories (all embeddings): {similarity_scores.topk(k=10, dim=0).values.sum().item()}")
        
        return (similarity_scores, similarity_scores.argsort(descending=True))
    
    def compare_chunk_coverage(story_embedding, embeddings_all, model : SentenceTransformer):
        similarity_chunks = model.similarity(story_embedding, embeddings_all)
        similarity_chunks_max = similarity_chunks.max(dim=1).values
        coverage = similarity_chunks_max.mean().item()
        print(f"Chunk coverage (all embeddings): {coverage}")
        
    
    def calculate_mean_percentile(story_embedding, embeddings_mean, intra_dataset_similarity, model : SentenceTransformer):
        story_mean_embedding = np.mean(story_embedding, axis=0, keepdims=True)
        
        similarity = model.similarity(story_mean_embedding, embeddings_mean)
        similarity = similarity.topk(k=10).values.mean().item()
        percentile = (intra_dataset_similarity <= similarity).float().mean().item()
        print(f"Mean embedding similarity: {similarity}, Percentile: {percentile * 100:.2f}%")
        return percentile

            
    new_mean, new_mean_indices = compare_mean_embeddings(story_embeddings, embeddings_mean, model)
    mean_similarity = cat((mean_similarity, new_mean.T), dim=1)
    mean_indices = cat((mean_indices, new_mean_indices.T), dim=1)
    print(f"Updated mean indices shape: {mean_indices.shape}")
    
    new_all, new_all_indices = compare_all_embeddings(story_embeddings, embeddings_all, model)
    all_similarity = cat((all_similarity, new_all), dim=1)
    all_indices = cat((all_indices, new_all_indices), dim=1)
    print(f"Updated all indices shape: {all_indices.shape}")
    
    compare_chunk_coverage(story_embeddings, embeddings_all, model)
    
    percentile = calculate_mean_percentile(story_embeddings, embeddings_mean, intra_dataset_similarity_top_10, model)
    


with open("src/dataset/files/comp_mean_indices.npy", "wb") as indices_file:
    np.save(indices_file, mean_indices.numpy())
with open("src/dataset/files/comp_mean_similarity.npy", "wb") as similarity_file:
    np.save(similarity_file, mean_similarity.numpy())
    
with open("src/dataset/files/comp_all_indices.npy", "wb") as indices_file:
    np.save(indices_file, all_indices.numpy())
with open("src/dataset/files/comp_all_similarity.npy", "wb") as similarity_file:
    np.save(similarity_file, all_similarity.numpy())