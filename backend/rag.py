import faiss
import numpy as np
import torch
from transformers import RagTokenizer, RagSequenceForGeneration, RagRetriever

# Initialize tokenizer and model
tokenizer = RagTokenizer.from_pretrained("facebook/rag-sequence-nq")
model = RagSequenceForGeneration.from_pretrained("facebook/rag-sequence-nq")

# Create a FAISS index for vector storage (using float32 and L2 distance)
dimension = model.config.hidden_size  # Dimension of embeddings
faiss_index = faiss.IndexFlatL2(dimension)


def batch_encode_documents(documents, max_length=512, stride=128):
    """Encode documents into overlapping chunks for large documents."""
    all_embeddings = []
    for doc in documents:
        # Tokenize the document with overlap
        tokenized = tokenizer(doc, truncation=False, padding=False, return_tensors="pt")
        input_ids = tokenized['input_ids'][0]
        for i in range(0, input_ids.size(0), max_length - stride):
            chunk_ids = input_ids[i:i + max_length]  # Get a chunk of tokens
            chunk_tensor = torch.tensor([chunk_ids])  # Make it a batch
            inputs = {'input_ids': chunk_tensor, 'attention_mask': (chunk_tensor > 0).int()}
            outputs = model.rag.retriever(**inputs, return_tensors="pt")
            all_embeddings.append(outputs.cpu().detach().numpy())
    return np.vstack(all_embeddings)


def add_documents(documents):
    embeddings = batch_encode_documents(documents)
    faiss_index.add(embeddings)  # Add embeddings to the index


def search_documents(query, k=5):
    inputs = tokenizer(query, return_tensors="pt", padding=True, truncation=True, max_length=512)
    outputs = model.rag.retriever(inputs["input_ids"], inputs["attention_mask"], return_tensors="pt")
    query_vec = outputs.cpu().detach().numpy()
    distances, indices = faiss_index.search(query_vec, k)
    return indices


# Example usage
documents = [
    "This is a long fact about Earth that continues with more information to ensure we exceed the typical limit of a "
    "model's input size.",
    "Mars is very red"]
add_documents(documents)

# Querying the FAISS index
query = "Tell me more about Earth."
doc_indices = search_documents(query)
print("Retrieved document indices:", doc_indices)
