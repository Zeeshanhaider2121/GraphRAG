"""Registry service for document metadata and processing status."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentRegistryService:
    """Manage a local JSON registry for uploaded documents."""

    def __init__(self) -> None:
        self.registry_path = settings.documents_path / "registry.json"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self.registry_path.write_text("[]", encoding="utf-8")

    def _load_all(self) -> list[dict[str, Any]]:
        raw = self.registry_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = []
        return data if isinstance(data, list) else []

    def _save_all(self, records: list[dict[str, Any]]) -> None:
        self.registry_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def upsert(self, record: dict[str, Any]) -> dict[str, Any]:
        """Insert or update a document record by id."""
        if "id" not in record or not record["id"]:
            raise ValueError("Record requires non-empty 'id'.")

        records = self._load_all()
        now = _utc_now_iso()
        existing = None
        for item in records:
            if item.get("id") == record["id"]:
                existing = item
                break

        if existing is None:
            merged = {
                "id": record["id"],
                "created_at": now,
                "updated_at": now,
                **record,
            }
            records.append(merged)
            self._save_all(records)
            return merged

        existing.update(record)
        existing["updated_at"] = now
        self._save_all(records)
        return existing

    def get(self, document_id: str) -> dict[str, Any] | None:
        """Fetch one record by id."""
        for item in self._load_all():
            if item.get("id") == document_id:
                return item
        return None

    def list_active(self) -> list[dict[str, Any]]:
        """Return active (non-deleted) records sorted by updated date desc."""
        records = [item for item in self._load_all() if item.get("status") != "deleted"]
        records.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return records

    def mark_deleted(self, document_id: str) -> dict[str, Any] | None:
        """Mark one record as deleted."""
        existing = self.get(document_id)
        if existing is None:
            return None
        return self.upsert({"id": document_id, "status": "deleted"})
