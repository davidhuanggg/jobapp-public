import hashlib

def hash_resume(text: str) -> str:
    """
    Create a deterministic hash for resume content.
    Minor formatting changes won't break it.
    """
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

