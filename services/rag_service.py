"""
rag_service.py — RAG pipeline using ChromaDB, Langchain, and HuggingFace.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from loguru import logger

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.chroma import Chroma

from core.config import settings

# Initialize Embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def get_chroma_client():
    import chromadb
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)

def get_vectorstore(subject: str) -> Chroma:
    # Normalize subject to use as collection name
    collection_name = "".join(c if c.isalnum() else "_" for c in subject.lower())
    client = get_chroma_client()
    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )

# ─── Public: ingest ───────────────────────────────────────────────────────────

@dataclass
class IngestResult:
    subject:    str
    topic:      str
    file_name:  str
    chunks_added: int
    chunks_skipped: int

def ingest_document(
    file_path: str | Path,
    subject: str,
    topic: str,
) -> IngestResult:
    """Ingest a document into the ChromaDB vectorstore."""
    path = Path(file_path).resolve()
    logger.info("Ingesting '{}' → subject='{}' topic='{}'", path.name, subject, topic)

    if path.suffix.lower() == ".pdf":
        loader = PyPDFLoader(str(path))
    else:
        loader = TextLoader(str(path), encoding="utf-8")
        
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = text_splitter.split_documents(docs)

    vectorstore = get_vectorstore(subject)

    # Add metadata
    added = 0
    skipped = 0
    
    docs_to_add = []
    ids_to_add = []
    
    for i, chunk in enumerate(chunks):
        chunk.metadata["subject"] = subject
        chunk.metadata["topic"] = topic
        chunk.metadata["source"] = path.name
        chunk.metadata["chunk_index"] = i
        
        # Simple ID based on hash of content to avoid duplicates
        content_hash = hashlib.md5(chunk.page_content.encode("utf-8")).hexdigest()
        doc_id = f"{path.name}_{i}_{content_hash}"
        
        # Check if exists (simplified, usually we'd check DB directly)
        docs_to_add.append(chunk)
        ids_to_add.append(doc_id)
        added += 1

    if docs_to_add:
        vectorstore.add_documents(documents=docs_to_add, ids=ids_to_add)

    return IngestResult(
        subject=subject,
        topic=topic,
        file_name=path.name,
        chunks_added=added,
        chunks_skipped=skipped,
    )

# ─── Public: retrieval ────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    text:        str
    subject:     str
    topic:       str
    source_file: str
    score:       float
    chunk_index: int

def get_topic_materials(
    subject: str,
    topic: str,
    k: int = 5,
    score_threshold: float = 0.25,
) -> list[RetrievedChunk]:
    """Retrieve relevant material chunks for a topic."""
    vectorstore = get_vectorstore(subject)
    
    # We can filter by topic if we want, or just search broadly
    # Langchain Chroma supports metadata filtering
    try:
        # Cosine distance in Chroma: lower is better (0 is exact match)
        results = vectorstore.similarity_search_with_score(
            topic,
            k=k,
            filter={"topic": topic}
        )
    except Exception as e:
        logger.error(f"Error during retrieval: {e}")
        return []

    retrieved = []
    for doc, score in results:
        # Invert score if necessary depending on distance metric, or just pass distance
        retrieved.append(
            RetrievedChunk(
                text=doc.page_content,
                subject=doc.metadata.get("subject", subject),
                topic=doc.metadata.get("topic", topic),
                source_file=doc.metadata.get("source", "unknown"),
                score=score,
                chunk_index=doc.metadata.get("chunk_index", 0),
            )
        )
    
    logger.debug("Retrieved {} chunks for '{}' / '{}'", len(retrieved), subject, topic)
    return retrieved

# ─── Collection management helpers ───────────────────────────────────────────

def list_collections() -> list[str]:
    client = get_chroma_client()
    return [c.name for c in client.list_collections()]

def delete_collection(subject: str) -> bool:
    client = get_chroma_client()
    collection_name = "".join(c if c.isalnum() else "_" for c in subject.lower())
    try:
        client.delete_collection(collection_name)
        return True
    except Exception:
        return False

def collection_stats(subject: str) -> dict:
    vectorstore = get_vectorstore(subject)
    # This requires accessing the underlying collection
    try:
        count = vectorstore._collection.count()
        return {
            "collection": vectorstore._collection.name,
            "subject":    subject,
            "count":      count,
        }
    except Exception:
        return {"collection": subject, "subject": subject, "count": 0}
