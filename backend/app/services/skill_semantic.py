"""
Optional **semantic** skill clustering using sentence embeddings.

String fuzzy matching (rapidfuzz/difflib) catches typos and surface variants;
**embeddings** catch different words with the same meaning (e.g. ``js`` vs
``javascript``, ``NLP`` vs ``natural language processing``) when they appear
as separate normalized keys.

Enable with env:

- ``SKILL_USE_EMBEDDINGS=1`` — run semantic merge after string clustering
- ``SKILL_EMBED_MODEL=all-MiniLM-L6-v2`` — any SentenceTransformers model name
- ``SKILL_EMBED_COSINE=0.82`` — merge cluster roots when cosine similarity ≥ this

Install: ``pip install sentence-transformers`` (pulls PyTorch; first run may
download the model).

Alternative for production: call an embeddings API (OpenAI, Voyage, etc.) and
replace ``_encode`` with HTTP — same merge logic applies.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict

logger = logging.getLogger(__name__)

_encoder = None


def _uf_find(parent: dict[str, str], x: str) -> str:
    if parent[x] != x:
        parent[x] = _uf_find(parent, parent[x])
    return parent[x]


def _uf_union(parent: dict[str, str], a: str, b: str) -> None:
    ra, rb = _uf_find(parent, a), _uf_find(parent, b)
    if ra != rb:
        parent[rb] = ra


def _encode(texts: list[str]):
    """Return (n, d) float32 array, L2-normalized rows (cosine = dot product)."""
    global _encoder
    import numpy as np

    if _encoder is None:
        from sentence_transformers import SentenceTransformer

        name = os.getenv("SKILL_EMBED_MODEL", "all-MiniLM-L6-v2")
        logger.debug("Loading skill embedding model: %s", name)
        _encoder = SentenceTransformer(name)

    emb = _encoder.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return np.asarray(emb, dtype=np.float32)


def merge_cluster_map_semantically(
    key_to_canon: dict[str, str],
    *,
    cosine_threshold: float = 0.82,
) -> dict[str, str]:
    """
    ``key_to_canon``: structural_key -> canonical_key after string clustering.

    Merges **canonical roots** whose embedding cosine similarity is high, then
    recomputes one canonical (shortest structural key) per merged group.
    """
    if len(key_to_canon) <= 1:
        return key_to_canon

    canons = sorted(set(key_to_canon.values()))
    if len(canons) < 2:
        return key_to_canon

    try:
        emb = _encode(canons)
    except ImportError:
        logger.debug("sentence-transformers not installed; skipping semantic skill merge")
        return key_to_canon
    except Exception as e:
        logger.warning("Skill semantic merge skipped: %s", e)
        return key_to_canon

    import numpy as np

    parent = {c: c for c in canons}
    n = len(canons)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = canons[i], canons[j]
            if _uf_find(parent, a) == _uf_find(parent, b):
                continue
            sim = float(np.dot(emb[i], emb[j]))
            la, lb = len(a), len(b)
            # Short acronyms: require stronger evidence
            if min(la, lb) <= 2 and sim < 0.92:
                continue
            if min(la, lb) <= 4 and sim < max(cosine_threshold, 0.88):
                continue
            if sim >= cosine_threshold:
                _uf_union(parent, a, b)

    # Group every structural key by the UF root of its current canon
    root_to_structural: dict[str, list[str]] = defaultdict(list)
    for k_str, c in key_to_canon.items():
        r = _uf_find(parent, c)
        root_to_structural[r].append(k_str)

    new_map: dict[str, str] = {}
    for _r, structural_keys in root_to_structural.items():
        canon = min(structural_keys, key=lambda x: (len(x), x))
        for k_str in structural_keys:
            new_map[k_str] = canon

    return new_map
