"""Zenodo connector — broad open-access research dataset repository."""

from __future__ import annotations

import re

from med_mcp.connectors.base import Connector
from med_mcp.modalities import detect_modalities
from med_mcp.schema import DatasetRecord

_API = "https://zenodo.org/api/records"
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


class ZenodoConnector(Connector):
    name = "zenodo"
    description = "Open-access research datasets across all disciplines (Zenodo)."
    default_access = "public"

    async def search(self, query: str, limit: int) -> list[DatasetRecord]:
        resp = await self._client.get(
            _API,
            params={"q": query, "size": limit, "type": "dataset", "sort": "bestmatch"},
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        return [self._to_record(h) for h in hits]

    async def get_details(self, dataset_id: str) -> DatasetRecord | None:
        resp = await self._client.get(f"{_API}/{dataset_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._to_record(resp.json())

    def _to_record(self, hit: dict) -> DatasetRecord:
        meta = hit.get("metadata", {})
        title = meta.get("title", "")
        description = _strip_html(meta.get("description", ""))
        keywords = [k for k in meta.get("keywords", []) if isinstance(k, str)]
        license_obj = meta.get("license") or {}
        access_right = meta.get("access_right", "open")
        return DatasetRecord(
            id=str(hit.get("id", "")),
            source=self.name,
            title=title,
            description=description,
            url=hit.get("links", {}).get("self_html") or hit.get("doi_url", ""),
            modalities=detect_modalities(title, description, " ".join(keywords)),
            license=license_obj.get("id") if isinstance(license_obj, dict) else None,
            tags=keywords,
            access="public" if access_right == "open" else access_right,
        )
