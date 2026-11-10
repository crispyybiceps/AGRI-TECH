"""
RAG Retrieval Service for AGRI-TECH Chatbot.
Performs keyword & BM25-style relevance search over verified /knowledge documents.
Always returns source document names for transparency.
"""

import os
import re
import math
from typing import List, Dict, Any

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge")

# In-memory document chunk store
_CHUNKS: List[Dict[str, Any]] = []


def _tokenize(text: str) -> List[str]:
    """Simple lowercase alphanumeric tokenizer with stopword filtering."""
    stopwords = {
        "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
        "is", "are", "was", "were", "it", "this", "that", "from", "by", "as", "be",
        "का", "की", "के", "में", "से", "को", "पर", "है", "हैं", "था", "थे", "और",
        "चा", "ची", "चे", "मध्ये", "आणि", "किंवा", "आहे", "आहेत", "होते", "वर"
    }
    words = re.findall(r"\b[\w\u0900-\u097F]{2,}\b", text.lower())
    return [w for w in words if w not in stopwords]


def load_knowledge_base():
    """Load and index all markdown documents in /knowledge folder."""
    global _CHUNKS
    _CHUNKS = []

    if not os.path.exists(KNOWLEDGE_DIR):
        return

    for fname in sorted(os.listdir(KNOWLEDGE_DIR)):
        if fname.endswith(".md"):
            fpath = os.path.join(KNOWLEDGE_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Split by markdown headers
            sections = re.split(r"\n(?=#{1,3}\s)", content)
            for sec in sections:
                clean_sec = sec.strip()
                if len(clean_sec) > 30:
                    tokens = _tokenize(clean_sec)
                    _CHUNKS.append({
                        "source": fname,
                        "text": clean_sec,
                        "tokens": tokens,
                        "token_set": set(tokens)
                    })


def retrieve_relevant_chunks(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve top_k most relevant chunks using BM25-like scoring.
    """
    if not _CHUNKS:
        load_knowledge_base()

    query_tokens = _tokenize(query)
    if not query_tokens:
        return _CHUNKS[:top_k] if _CHUNKS else []

    scored_chunks = []
    total_docs = len(_CHUNKS)

    for chunk in _CHUNKS:
        score = 0.0
        chunk_tokens = chunk["tokens"]
        doc_len = len(chunk_tokens)
        avg_doc_len = 100.0

        for q in query_tokens:
            tf = chunk_tokens.count(q)
            if tf > 0:
                # IDF estimation
                docs_with_q = sum(1 for c in _CHUNKS if q in c["token_set"])
                idf = math.log((total_docs - docs_with_q + 0.5) / (docs_with_q + 0.5) + 1.0)
                # BM25 term frequency formula
                k1 = 1.2
                b = 0.75
                term_score = idf * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_doc_len))))
                score += term_score

        if score > 0.1:
            scored_chunks.append({
                "source": chunk["source"],
                "text": chunk["text"],
                "score": score
            })

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]

