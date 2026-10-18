"""
Local Ollama embedding helper.

AI-search embeddings run against the on-prem Ollama server (nomic-embed-text),
so text never leaves the intranet. Replaces the previous sentence-transformers /
HuggingFace model (intfloat/multilingual-e5-small), which downloaded weights
from huggingface.co on first use.

Containers should set OLLAMA_EMBED_URL=http://host.docker.internal:11434/api/embed
(the host-side scripts default to 127.0.0.1, which matches Ollama's local listen).
"""
import os

import httpx

OLLAMA_EMBED_URL = os.environ.get(
    "OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed"
)
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "nomic-embed-text")
EMBEDDING_DIM = 768  # nomic-embed-text output dimension


class _Vectors(list):
    """List of vectors exposing .tolist() like a numpy array.

    Kept so existing call sites that do `embedding.tolist()` keep working
    without pulling in numpy.
    """

    def tolist(self):
        return [list(v) for v in self]


class OllamaEmbedder:
    """Drop-in replacement for SentenceTransformer.encode(), backed by local Ollama."""

    def __init__(self, model: str = EMBEDDING_MODEL, url: str = OLLAMA_EMBED_URL):
        self.model = model
        self.url = url

    def encode(
        self,
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
        **kwargs,
    ):
        """Embed one string or a list of strings. Returns a _Vectors (list-like) result."""
        if isinstance(texts, str):
            texts = [texts]

        vectors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {"model": self.model, "input": batch}
            resp = httpx.post(self.url, json=payload, timeout=180)
            resp.raise_for_status()
            for e in resp.json().get("embeddings", []):
                v = [float(x) for x in e]
                if normalize_embeddings:
                    norm = sum(x * x for x in v) ** 0.5
                    if norm:
                        v = [x / norm for x in v]
                vectors.append(v)

        return _Vectors(vectors)


def embed_texts(texts, batch_size=64, timeout_sec: int = 180) -> list:
    """Embed one or more strings, returning a list of flat float vectors."""
    if isinstance(texts, str):
        texts = [texts]
    return OllamaEmbedder().encode(texts, batch_size=batch_size).tolist()


def embed_one(text: str, timeout_sec: int = 180) -> list:
    """Embed a single string, returning a flat float vector."""
    return embed_texts([text])[0]
