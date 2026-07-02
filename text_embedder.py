"""
VibeSeek - Week 2
Text Embedder: Encodes transcript chunks and search queries into a shared
semantic text space using a sentence-transformer (all-MiniLM-L6-v2).

This is separate from CLIP: CLIP understands *images* + short visual phrases,
while MiniLM understands *spoken language*. Searching both spaces and fusing the
results is what lets VibeSeek match a query against what was seen AND what was said.
"""

import numpy as np
from sentence_transformers import SentenceTransformer


class TextEmbedder:
    """
    Wraps a sentence-transformer. Lazy-loaded on first use.

    Usage:
        embedder = TextEmbedder()
        vecs = embedder.embed_chunks(["hello there", "the beat drops"])
        q = embedder.embed_query("greeting")
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name      # 384-dim, fast on CPU
        self.model = None                 # loaded on first use

    def _ensure_model(self):
        if self.model is None:
            print(f"[TextEmbedder] Loading {self.model_name}...")
            self.model = SentenceTransformer(self.model_name)
            print("[TextEmbedder] Ready.")

    def embed_chunks(self, texts: list[str]) -> np.ndarray:
        """
        Encodes a list of texts into L2-normalised embeddings, shape (N, 384).
        Returns an empty (0, 0) array when given no texts.
        """
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        self._ensure_model()
        # normalize_embeddings=True → cosine similarity == dot product downstream
        vecs = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vecs, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Encodes a single query string. Returns shape (384,) float32."""
        return self.embed_chunks([query])[0]
