"""Embedding service – Ollama via ngrok (nomic-embed-text-v2-moe)"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Iterable

import requests

from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging(__name__)


class EmbeddingService:
    # Exact same candidates as embed_nodes.py
    OLLAMA_ENDPOINT_CANDIDATES = [
        ("/api/embed",      "input",  "embeddings"),
        ("/api/embed",      "prompt", "embeddings"),
        ("/api/embeddings", "prompt", "embeddings"),
        ("/api/embeddings", "input",  "embeddings"),
        ("/api/embed",      "prompt", "embedding"),
        ("/api/embeddings", "prompt", "embedding"),
    ]

    def __init__(self) -> None:
        # ---- settings must be defined in your .env ----
        self.ollama_base_url = (
            (settings.OLLAMA_BASE_URL or settings.NGROK_URL or "").rstrip("/")
        )
        self.ollama_model = settings.OLLAMA_EMBED_MODEL   # "nomic-embed-text-v2-moe"
        self.ollama_timeout = int(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 60))
        self.batch_size = int(getattr(settings, "EMBEDDING_BATCH_SIZE", 32))

        # Will be set after endpoint detection
        self.vector_dimension = int(getattr(settings, "EMBEDDING_DIM", 768))
        self._embedder = None          # callable that returns list[list[float]]
        self._detected = False

    # ── helpers (same as embed_nodes.py) ────────────────────────────────────
    @staticmethod
    def _vector_list(payload: Any) -> list[list[float]]:
        if payload is None:
            return []
        if isinstance(payload, list):
            if not payload:
                return []
            first = payload[0]
            if isinstance(first, list):
                return [[float(v) for v in vec] for vec in payload]
            if isinstance(first, (int, float)):
                return [[float(v) for v in payload]]
        return []

    def _detect_ollama_endpoint(self) -> None:
        """Detect working endpoint, batch support, and embedding dimension."""
        if self._detected:
            return
        self._detected = True

        if not self.ollama_base_url:
            raise RuntimeError("OLLAMA_BASE_URL or NGROK_URL is not configured.")

        base = self.ollama_base_url
        logger.info("Detecting Ollama API on %s", base)

        for ep, inp_field, out_field in self.OLLAMA_ENDPOINT_CANDIDATES:
            url = f"{base}{ep}"
            try:
                # 1. check single
                r = requests.post(url, json={"model": self.ollama_model, inp_field: "probe"},
                                  timeout=self.ollama_timeout)
                if r.status_code >= 400:
                    continue
                vectors = self._vector_list(r.json().get(out_field))
                if not vectors:
                    continue
                dims = len(vectors[0])

                # 2. check batch
                batch_support = False
                r2 = requests.post(url, json={"model": self.ollama_model, inp_field: ["p1", "p2"]},
                                   timeout=self.ollama_timeout)
                if r2.status_code < 400:
                    batch_vecs = self._vector_list(r2.json().get(out_field))
                    batch_support = len(batch_vecs) == 2 and all(isinstance(v, list) for v in batch_vecs)

                # 3. build closure
                if batch_support:
                    def batch_embed(texts: list[str]) -> list[list[float]]:
                        clean = [t.strip() or "leer" for t in texts]
                        resp = requests.post(url,
                                             json={"model": self.ollama_model, inp_field: clean},
                                             headers={"Content-Type": "application/json"},
                                             timeout=120)
                        resp.raise_for_status()
                        vecs = self._vector_list(resp.json().get(out_field))
                        if len(vecs) != len(texts):
                            raise RuntimeError(f"Expected {len(texts)} vectors, got {len(vecs)}")
                        return vecs
                    self._embedder = batch_embed
                else:
                    def sequential_embed(texts: list[str]) -> list[list[float]]:
                        clean = [t.strip() or "leer" for t in texts]
                        out = []
                        for text in clean:
                            r = requests.post(url,
                                              json={"model": self.ollama_model, inp_field: text},
                                              headers={"Content-Type": "application/json"},
                                              timeout=60)
                            r.raise_for_status()
                            vecs = self._vector_list(r.json().get(out_field))
                            if not vecs:
                                raise RuntimeError("Empty embedding from Ollama")
                            out.append(vecs[0])
                        return out
                    self._embedder = sequential_embed

                self.vector_dimension = dims
                logger.info("Ollama ready: %s (dims=%d, batch=%s)", url, dims, batch_support)
                return
            except Exception as e:
                logger.debug("Probe %s failed: %s", url, e)
                continue

        raise ConnectionError(f"No working Ollama endpoint found at {base}")

    def embed_batch_sync(self, texts: Iterable[str]) -> list[list[float]]:
        # Ensure detection happened
        self._detect_ollama_endpoint()
        text_list = [str(t) for t in texts]
        return self._embedder(text_list)

    def embed_sync(self, text: str) -> list[float]:
        return self.embed_batch_sync([text])[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_batch_sync, texts)

    async def embed(self, text: str) -> list[float]:
        return await asyncio.to_thread(self.embed_sync, text)