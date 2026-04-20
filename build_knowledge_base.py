"""
Vector store: ChromaDB-backed semantic search over insurance policy chunks.

Usage:
  1. Call index_policy(raw_text) when a new policy is uploaded.
  2. Call retrieve_policy_clauses(rejection_reasons) to get relevant chunks
     before the policy checker Claude call.

Embedding model: claude's built-in or sentence-transformers (local, no API cost).
"""

import logging
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from shared.config import CHROMA_DIR

logger = logging.getLogger(__name__)

COLLECTION_NAME = "policy_clauses"
CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 50
TOP_K = 5               # how many chunks to retrieve per query


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=DefaultEmbeddingFunction(),
    )


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def index_policy(raw_text: str, policy_id: str = "current_policy") -> int:
    """
    Chunk and embed a policy document into ChromaDB.
    Call this once per uploaded policy. Returns number of chunks indexed.
    """
    collection = _get_collection()

    # Clear previous policy
    try:
        existing = collection.get(where={"policy_id": policy_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    chunks = _chunk_text(raw_text)
    ids = [f"{policy_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"policy_id": policy_id, "chunk_index": i} for i in range(len(chunks))]

    collection.add(documents=chunks, ids=ids, metadatas=metadatas)
    logger.info(f"Indexed {len(chunks)} policy chunks into ChromaDB")
    return len(chunks)


def retrieve_policy_clauses(queries: list[str], top_k: int = TOP_K) -> list[str]:
    """
    Retrieve the most semantically relevant policy chunks for a list of queries.
    Returns deduplicated list of clause strings.
    """
    if not queries:
        return []

    collection = _get_collection()

    # Check if anything is indexed
    if collection.count() == 0:
        logger.warning("Policy not indexed — call index_policy() first")
        return []

    all_chunks: list[str] = []
    seen: set[str] = set()

    for query in queries:
        try:
            results = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))
            for doc in results["documents"][0]:
                if doc not in seen:
                    all_chunks.append(doc)
                    seen.add(doc)
        except Exception as e:
            logger.error(f"Vector search failed for query '{query}': {e}")

    return all_chunks
