"""
rag_service.py — Mocked RAG pipeline for hackathon pitch.
(No ChromaDB or sentence-transformers dependencies required)
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from loguru import logger

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
    """Mock ingest"""
    path = Path(file_path).resolve()
    logger.info("Mock Ingesting '{}' → subject='{}' topic='{}'", path.name, subject, topic)

    return IngestResult(
        subject=subject,
        topic=topic,
        file_name=path.name,
        chunks_added=1,
        chunks_skipped=0,
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
    """Mock retrieval"""
    logger.debug("Mock Retrieved chunks for '{}' / '{}'", subject, topic)
    return [
        RetrievedChunk(
            text=f"Ushbu dars {subject} fanining {topic} mavzusiga bag'ishlangan muhim materiallardan iborat.",
            subject=subject,
            topic=topic,
            source_file="mock_material.pdf",
            score=0.99,
            chunk_index=0,
        )
    ]


# ─── Collection management helpers ───────────────────────────────────────────

def list_collections() -> list[str]:
    return ["mock_collection"]

def delete_collection(subject: str) -> bool:
    return True

def collection_stats(subject: str) -> dict:
    return {
        "collection": subject,
        "subject":    subject,
        "count":      1,
    }
