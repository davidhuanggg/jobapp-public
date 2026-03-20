"""
Skill identity for matching resume vs role/job skills.

1) **Structural normalize** — deterministic cleanup (Unicode, phrases like node.js→node,
   compact alnum, strip trailing js on known stems). No hand-maintained synonym table.

2) **Dynamic cluster map** — built from every skill string seen in *this* request; uses
   fuzzy string similarity (rapidfuzz/difflib) to merge close keys (e.g. postgres ↔ postgresql).

3) **Optional semantic merge** — if ``SKILL_USE_EMBEDDINGS=1`` and ``sentence-transformers``
   is installed, merge clusters whose **meanings** are close in embedding space
   (e.g. js ↔ javascript). See ``skill_semantic.py``.

Pass `cluster_map` into `normalize_skill_for_match` so all comparisons share
the same merged vocabulary for that batch.
"""

from __future__ import annotations

import difflib
import logging
import os
import re
import unicodedata
from collections.abc import Iterable

logger = logging.getLogger(__name__)


def _fuzzy_max_score(a: str, b: str) -> int:
    """0–100 similarity; prefers rapidfuzz, falls back to difflib."""
    try:
        from rapidfuzz import fuzz

        return max(fuzz.ratio(a, b), fuzz.token_set_ratio(a, b))
    except ImportError:
        r = int(round(100 * difflib.SequenceMatcher(None, a, b).ratio()))
        ta = "".join(sorted(re.findall(r"[a-z0-9]+", a)))
        tb = "".join(sorted(re.findall(r"[a-z0-9]+", b)))
        if ta and tb:
            r = max(r, int(round(100 * difflib.SequenceMatcher(None, ta, tb).ratio())))
        return r

# Longer phrases first (structural only — not a synonym table for arbitrary tech).
_PHRASE_SUBS: tuple[tuple[str, str], ...] = (
    ("asp.net", "aspnet"),
    ("objective-c", "objectivec"),
    ("node.js", "node"),
    ("react.js", "react"),
    ("vue.js", "vue"),
    ("angular.js", "angular"),
    ("next.js", "next"),
    ("nuxt.js", "nuxt"),
    ("three.js", "threejs"),
    ("d3.js", "d3"),
    (".net", "dotnet"),
    ("c++", "cpp"),
    ("c#", "csharp"),
)

_JS_STRIP_IF_STEM_KNOWN: frozenset[str] = frozenset(
    {"react", "node", "vue", "angular", "next", "nuxt", "express"}
)


def _compact_alnum(s: str) -> str:
    parts: list[str] = []
    for ch in s:
        if ch.isalnum() or ch in "+#":
            parts.append(ch)
    return "".join(parts)


def structural_normalize(skill: str | None) -> str:
    """
    Deterministic key: same input always maps to same string.
    Does not merge arbitrary synonyms unless they become identical here.
    """
    if skill is None:
        return ""
    s = unicodedata.normalize("NFKC", str(skill).strip().lower())
    if not s:
        return ""

    for old, new in _PHRASE_SUBS:
        if old in s:
            s = s.replace(old, new)

    s = re.sub(r"[\s\-_/]+", "", s)
    full = _compact_alnum(s)
    if not full:
        return ""

    if len(full) > 2 and full.endswith("js") and full[:-2] in _JS_STRIP_IF_STEM_KNOWN:
        full = full[:-2]

    return full


def _uf_find(parent: dict[str, str], x: str) -> str:
    if parent[x] != x:
        parent[x] = _uf_find(parent, parent[x])
    return parent[x]


def _uf_union(parent: dict[str, str], a: str, b: str) -> None:
    ra, rb = _uf_find(parent, a), _uf_find(parent, b)
    if ra != rb:
        parent[rb] = ra


def build_dynamic_cluster_map(
    strings: Iterable[str],
    *,
    threshold: int = 86,
    short_token_max_score: int = 95,
    use_semantic_merge: bool | None = None,
    semantic_cosine: float | None = None,
) -> dict[str, str]:
    """
    From all skill mentions in one batch, merge structurally different keys that are
    still likely the same skill (fuzzy ratio / token-set ratio).

    If ``use_semantic_merge`` is True, or env ``SKILL_USE_EMBEDDINGS`` is truthy,
    runs an extra merge pass using sentence embeddings (see ``skill_semantic``).

    Returns: structural_key -> canonical_key (shortest key in each cluster, stable).

    Empty or single-key input yields a map of each key to itself.
    """
    if use_semantic_merge is None:
        use_semantic_merge = os.getenv("SKILL_USE_EMBEDDINGS", "").lower() in (
            "1",
            "true",
            "yes",
        )
    keys: list[str] = []
    seen: set[str] = set()
    for s in strings:
        k = structural_normalize(s)
        if k and k not in seen:
            seen.add(k)
            keys.append(k)

    if len(keys) <= 1:
        return {k: k for k in keys}

    parent = {k: k for k in keys}

    n = len(keys)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = keys[i], keys[j]
            if _uf_find(parent, a) == _uf_find(parent, b):
                continue
            score = _fuzzy_max_score(a, b)
            la, lb = len(a), len(b)
            if la < 4 or lb < 4:
                if score < short_token_max_score:
                    continue
            elif score < threshold:
                continue
            _uf_union(parent, a, b)

    # group members by root
    groups: dict[str, list[str]] = {}
    for k in keys:
        r = _uf_find(parent, k)
        groups.setdefault(r, []).append(k)

    key_to_canon: dict[str, str] = {}
    for members in groups.values():
        canon = min(members, key=lambda x: (len(x), x))
        for k in members:
            key_to_canon[k] = canon

    if use_semantic_merge and len(key_to_canon) > 1:
        try:
            from app.services.skill_semantic import merge_cluster_map_semantically

            cos = semantic_cosine
            if cos is None:
                cos = float(os.getenv("SKILL_EMBED_COSINE", "0.82"))
            key_to_canon = merge_cluster_map_semantically(
                key_to_canon,
                cosine_threshold=cos,
            )
        except Exception as e:
            logger.debug("Semantic skill merge skipped: %s", e)

    return key_to_canon


def normalize_skill_for_match(
    skill: str | None,
    cluster_map: dict[str, str] | None = None,
) -> str:
    """
    Map a skill to its comparison key. With `cluster_map` from
    `build_dynamic_cluster_map` over the current batch, synonyms merge dynamically.
    Without a map, only structural normalization applies.
    """
    k = structural_normalize(skill)
    if not k:
        return ""
    if cluster_map is not None:
        return cluster_map.get(k, k)
    return k


def collect_strings_for_clustering(
    resume_skills: list[str] | None,
    role_skill_rows: list[tuple[str, list[str]]],
) -> list[str]:
    out: list[str] = []
    for s in resume_skills or []:
        out.append(s)
    for _, skills in role_skill_rows:
        for s in skills or []:
            out.append(s)
    return out
