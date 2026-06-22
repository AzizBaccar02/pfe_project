#C:\Users\Lenovo\django_project\pfe_project2\pfe_project\ai_recommendations\services\embedding_service.py

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_TIMEOUT_SECONDS = 20
_executor = ThreadPoolExecutor(max_workers=1)


class EmbeddingTimeoutError(TimeoutError):
    """Raised when NLP embedding generation exceeds the allowed time budget."""


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(MODEL_NAME)


def _run_with_timeout(func, *, timeout_seconds=EMBEDDING_TIMEOUT_SECONDS):
    future = _executor.submit(func)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeout as exc:
        raise EmbeddingTimeoutError(
            f"Embedding generation exceeded {timeout_seconds}s"
        ) from exc


def generate_embedding(text):
    if not text:
        text = ""

    def _encode():
        model = get_embedding_model()
        return model.encode(text, convert_to_numpy=True)

    return _run_with_timeout(_encode)


def generate_embeddings_batch(texts, batch_size=16):
    if not texts:
        return []

    cleaned = [text if text else "" for text in texts]

    def _encode_batch():
        model = get_embedding_model()
        return model.encode(
            cleaned,
            convert_to_numpy=True,
            batch_size=batch_size,
            show_progress_bar=False,
        )

    embeddings = _run_with_timeout(
        _encode_batch,
        timeout_seconds=max(EMBEDDING_TIMEOUT_SECONDS, 10 + len(cleaned)),
    )

    return list(embeddings)


def cosine_similarity_score(vector_a, vector_b):
    vector_a = np.array(vector_a)
    vector_b = np.array(vector_b)

    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    similarity = np.dot(vector_a, vector_b) / (norm_a * norm_b)

    return float(similarity)