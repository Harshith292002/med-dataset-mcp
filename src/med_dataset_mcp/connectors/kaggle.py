"""Kaggle connector — community ML datasets, filtered to biosignal/medical ones.

Kaggle's dataset list/metadata API is public (no auth required for reads), so
this connector needs no credentials. Kaggle search is noisy, however, so a
**biosignal quality floor** is applied to search results: a dataset is only kept
if at least one modality is detected in its title/subtitle/tags. The floor is
not applied to explicit `get_details` fetches, which return whatever was asked
for by reference.
"""

from __future__ import annotations

from med_dataset_mcp.connectors.base import Connector
from med_dataset_mcp.modalities import detect_modalities
from med_dataset_mcp.schema import DatasetRecord

_LIST = "https://www.kaggle.com/api/v1/datasets/list"
_VIEW = "https://www.kaggle.com/api/v1/datasets/view/{ref}"
_WEB = "https://www.kaggle.com/datasets/{ref}"
_PAGE_SIZE = 20
_MAX_PAGES = 5


class KaggleConnector(Connector):
    name = "kaggle"
    description = "Community ML datasets on Kaggle (filtered to biosignal/medical datasets)."
    default_access = "public"

    async def search(self, query: str, limit: int) -> list[DatasetRecord]:
        # Page through results because the biosignal floor can drop most of a
        # page; keep going until we have `limit` survivors or run out of pages.
        records: list[DatasetRecord] = []
        for page in range(1, _MAX_PAGES + 1):
            resp = await self._client.get(
                _LIST, params={"search": query, "page": page}
            )
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break
            records.extend(self._records_from_payload(items))
            if len(records) >= limit or len(items) < _PAGE_SIZE:
                break
        return records[:limit]

    async def get_details(self, dataset_id: str) -> DatasetRecord | None:
        resp = await self._client.get(_VIEW.format(ref=dataset_id))
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        item = resp.json()
        # The view endpoint omits `ref`; carry the requested id through.
        item.setdefault("ref", dataset_id)
        return self._to_record(item)

    def _records_from_payload(self, items: list[dict]) -> list[DatasetRecord]:
        """Normalize raw Kaggle items and apply the biosignal quality floor."""
        records = [self._to_record(item) for item in items]
        return [r for r in records if r.modalities]

    def _to_record(self, item: dict) -> DatasetRecord:
        ref = item.get("ref", "")
        title = item.get("title") or item.get("titleNullable") or ref
        subtitle = item.get("subtitle") or ""
        description = item.get("description") or subtitle
        tags = [t.get("name", "") for t in item.get("tags", []) if isinstance(t, dict)]
        tags = [t for t in tags if t]
        return DatasetRecord(
            id=ref,
            source=self.name,
            title=title,
            description=description,
            url=item.get("url") or _WEB.format(ref=ref),
            modalities=detect_modalities(title, description, " ".join(tags)),
            license=item.get("licenseName"),
            tags=tags,
            access="restricted" if item.get("isPrivate") else "public",
        )
