"""Registry that owns connectors and runs federated, cached queries."""

from __future__ import annotations

import asyncio
import logging
import ssl

import httpx
import truststore

from med_dataset_mcp.cache import TTLCache
from med_dataset_mcp.connectors.base import Connector
from med_dataset_mcp.connectors.huggingface import HuggingFaceConnector
from med_dataset_mcp.connectors.nsrr import NSRRConnector
from med_dataset_mcp.connectors.openneuro import OpenNeuroConnector
from med_dataset_mcp.connectors.physionet import PhysioNetConnector
from med_dataset_mcp.connectors.zenodo import ZenodoConnector
from med_dataset_mcp.modalities import normalize_modality
from med_dataset_mcp.schema import DatasetRecord

logger = logging.getLogger("med_dataset_mcp")

_CONNECTOR_CLASSES: list[type[Connector]] = [
    ZenodoConnector,
    PhysioNetConnector,
    NSRRConnector,
    HuggingFaceConnector,
    OpenNeuroConnector,
]


class Registry:
    """Holds the shared HTTP client, the connectors, and a result cache.

    All MCP tools call through this object so caching, error isolation, and
    fan-out concurrency live in one place.
    """

    def __init__(self, ttl_seconds: float = 900.0, timeout: float = 30.0) -> None:
        # Use the OS trust store (handles AIA-fetched intermediates that some
        # sources, e.g. NSRR, fail to serve) instead of certifi alone.
        ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=ssl_ctx,
            headers={"User-Agent": "med-dataset-mcp/0.1 (dataset discovery)"},
        )
        self._cache = TTLCache(ttl_seconds)
        self.connectors: dict[str, Connector] = {
            cls.name: cls(self._client) for cls in _CONNECTOR_CLASSES
        }

    async def aclose(self) -> None:
        await self._client.aclose()

    def list_sources(self) -> list[dict]:
        return [
            {
                "name": c.name,
                "description": c.description,
                "default_access": c.default_access,
            }
            for c in self.connectors.values()
        ]

    async def _search_one(
        self, connector: Connector, query: str, limit: int
    ) -> list[DatasetRecord]:
        key = f"search:{connector.name}:{limit}:{query.lower().strip()}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            results = await connector.search(query, limit)
        except Exception as exc:  # isolate one source's failure from the rest
            logger.warning("connector %s search failed: %s", connector.name, exc)
            return []
        self._cache.set(key, results)
        return results

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        modalities: list[str] | None = None,
        per_source_limit: int = 10,
    ) -> list[DatasetRecord]:
        chosen = self._select(sources)
        batches = await asyncio.gather(
            *(self._search_one(c, query, per_source_limit) for c in chosen)
        )
        records = [r for batch in batches for r in batch]
        if modalities:
            wanted = {normalize_modality(m) for m in modalities}
            records = [r for r in records if wanted & set(r.modalities)]
        records.sort(key=lambda r: self._score(r, query), reverse=True)
        return records

    async def get_details(self, source: str, dataset_id: str) -> DatasetRecord | None:
        connector = self.connectors.get(source)
        if connector is None:
            raise ValueError(f"unknown source '{source}'")
        try:
            return await connector.get_details(dataset_id)
        except Exception as exc:
            logger.warning("connector %s get_details failed: %s", source, exc)
            return None

    async def find_paired(
        self,
        modality_a: str,
        modality_b: str,
        sources: list[str] | None = None,
        per_source_limit: int = 25,
    ) -> list[DatasetRecord]:
        a = normalize_modality(modality_a)
        b = normalize_modality(modality_b)
        # Query each modality term so sources that need a search string return
        # candidates; then keep only records exhibiting BOTH modalities.
        results = await self.search(
            f"{modality_a} {modality_b}", sources, None, per_source_limit
        )
        return [r for r in results if a in r.modalities and b in r.modalities]

    def _select(self, sources: list[str] | None) -> list[Connector]:
        if not sources:
            return list(self.connectors.values())
        chosen = []
        for name in sources:
            if name not in self.connectors:
                raise ValueError(f"unknown source '{name}'")
            chosen.append(self.connectors[name])
        return chosen

    @staticmethod
    def _score(record: DatasetRecord, query: str) -> int:
        terms = [t for t in query.lower().split() if t]
        text = f"{record.title} {record.description} {' '.join(record.tags)}".lower()
        return sum(text.count(t) for t in terms)
