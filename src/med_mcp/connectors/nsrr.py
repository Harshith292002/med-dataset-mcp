"""NSRR connector — the National Sleep Research Resource.

The NSRR public API (``/api/v1/datasets.json``) lists every dataset (name +
slug) without auth, paginated 10 per page. Full per-dataset metadata and file
access require a Data Use Agreement and a personal token; if ``NSRR_TOKEN`` is
set in the environment it is forwarded so authorized users get richer detail.
Records are tagged ``access="dua"`` to flag that approval is required.
"""

from __future__ import annotations

import os

from med_mcp.connectors.base import Connector
from med_mcp.modalities import detect_modalities
from med_mcp.schema import DatasetRecord

_LIST = "https://sleepdata.org/api/v1/datasets.json"
_WEB = "https://sleepdata.org/datasets/{slug}"
_MAX_PAGES = 20


class NSRRConnector(Connector):
    name = "nsrr"
    description = "Sleep studies (PSG, actigraphy) from the National Sleep Research Resource."
    default_access = "dua"

    def _auth_params(self) -> dict[str, str]:
        token = os.environ.get("NSRR_TOKEN")
        return {"auth_token": token} if token else {}

    async def _load_index(self) -> list[dict]:
        datasets: list[dict] = []
        for page in range(1, _MAX_PAGES + 1):
            resp = await self._client.get(
                _LIST, params={"page": page, **self._auth_params()}
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            datasets.extend(batch)
        return datasets

    async def search(self, query: str, limit: int) -> list[DatasetRecord]:
        terms = [t for t in query.lower().split() if t]
        results: list[DatasetRecord] = []
        for ds in await self._load_index():
            name = ds.get("name", "")
            slug = ds.get("slug", "")
            if not terms or any(t in f"{name} {slug}".lower() for t in terms):
                results.append(self._to_record(ds))
            if len(results) >= limit:
                break
        return results

    async def get_details(self, dataset_id: str) -> DatasetRecord | None:
        for ds in await self._load_index():
            if ds.get("slug") == dataset_id:
                return self._to_record(ds)
        return None

    def _to_record(self, ds: dict) -> DatasetRecord:
        name = ds.get("name", "")
        slug = ds.get("slug", "")
        # NSRR is sleep-focused; PSG is implied even when not in the title.
        modalities = detect_modalities(name) or ["psg"]
        return DatasetRecord(
            id=slug,
            source=self.name,
            title=name,
            description=name,
            url=_WEB.format(slug=slug),
            modalities=modalities,
            access="dua",
        )
