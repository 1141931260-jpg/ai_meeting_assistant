import hashlib
import math
from abc import ABC, abstractmethod

import httpx

from app.config import Settings, get_settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    dimension = 64

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embed(query)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in text:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(item * item for item in vector)) or 1.0
        return [item / norm for item in vector]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.settings.embedding_api_key or not self.settings.embedding_api_base_url:
            return MockEmbeddingProvider().embed_texts(texts)

        url = f"{self.settings.embedding_api_base_url.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.settings.embedding_api_key}",
            "Content-Type": "application/json",
        }
        body = {"model": self.settings.embedding_model, "input": texts}
        try:
            with httpx.Client(timeout=self.settings.ai_request_timeout) as client:
                response = client.post(url, headers=headers, json=body)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"Embedding API 调用失败：{exc}") from exc
        return [item["embedding"] for item in sorted(payload["data"], key=lambda row: row.get("index", 0))]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider.lower() == "mock":
        return MockEmbeddingProvider()
    return OpenAICompatibleEmbeddingProvider(settings)
