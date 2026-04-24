"""Local storage service for uploaded documents and pipeline artifacts."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.core.config import settings


class StorageService:
    """Persist document binaries and JSON artifacts on disk."""

    def __init__(self) -> None:
        self.root = settings.documents_path
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        safe = filename.strip().replace("\\", "_").replace("/", "_")
        safe = re.sub(r"[^A-Za-z0-9._ -]", "_", safe)
        return safe or "document.bin"

    def get_document_dir(self, document_id: str) -> Path:
        """Return per-document directory path."""
        doc_dir = (self.root / document_id).resolve()
        if self.root.resolve() not in doc_dir.parents and doc_dir != self.root.resolve():
            raise ValueError("Invalid document directory path.")
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir

    def save_original_file(
        self,
        document_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Save uploaded file and return metadata."""
        doc_dir = self.get_document_dir(document_id)
        safe_name = self._sanitize_filename(filename)
        file_path = doc_dir / safe_name
        file_path.write_bytes(content)

        sha256_hash = hashlib.sha256(content).hexdigest()

        metadata = {
            "document_id": document_id,
            "filename": safe_name,
            "content_type": content_type or "application/octet-stream",
            "size": len(content),
            "sha256": sha256_hash,
            "path": str(file_path),
        }
        return metadata

    def save_json_artifact(self, document_id: str, artifact_name: str, payload: Any) -> str:
        """Save JSON payload under the document folder."""
        doc_dir = self.get_document_dir(document_id)
        artifact_path = doc_dir / artifact_name
        artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(artifact_path)

    def read_json_artifact(self, document_id: str, artifact_name: str) -> dict[str, Any]:
        """Read JSON artifact."""
        doc_dir = self.get_document_dir(document_id)
        artifact_path = doc_dir / artifact_name
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_name}")
        return json.loads(artifact_path.read_text(encoding="utf-8"))

    def delete_document_data(self, document_id: str) -> None:
        """Delete all local files for one document."""
        target = (self.root / document_id).resolve()
        if not target.exists():
            return
        if self.root.resolve() not in target.parents:
            raise ValueError("Refusing to delete path outside documents root.")
        shutil.rmtree(target)
