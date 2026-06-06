"""PhysioNet connector — physiological signal databases.

PhysioNet does not expose a JSON search API, but it publishes a stable,
machine-readable database index (the PhysioBank ``DBS`` file): one tab- or
space-separated ``slug<TAB>description`` line per database. We fetch that index
once (cached), then filter it locally by query. Each entry resolves to its
content page at ``https://physionet.org/content/<slug>/``.
"""

from __future__ import annotations

import re

from med_dataset_mcp.connectors.base import Connector
from med_dataset_mcp.modalities import detect_modalities
from med_dataset_mcp.schema import DatasetRecord

_DBS_URL = "https://physionet.org/physiobank/database/DBS"
_CONTENT = "https://physionet.org/content/{slug}/"
_LINE_RE = re.compile(r"^(?P<slug>\S+)\s+(?P<desc>.+?)\s*$")


class PhysioNetConnector(Connector):
    name = "physionet"
    description = "Physiological signal databases (ECG, EEG, PSG) from PhysioNet."
    default_access = "public"

    async def _load_index(self) -> list[tuple[str, str]]:
        resp = await self._client.get(_DBS_URL)
        resp.raise_for_status()
        entries: list[tuple[str, str]] = []
        for line in resp.text.splitlines():
            if not line.strip():
                continue
            m = _LINE_RE.match(line)
            if m:
                entries.append((m.group("slug"), m.group("desc")))
        return entries

    async def search(self, query: str, limit: int) -> list[DatasetRecord]:
        entries = await self._load_index()
        terms = [t for t in query.lower().split() if t]
        scored: list[tuple[int, str, str]] = []
        for slug, desc in entries:
            haystack = f"{slug} {desc}".lower()
            score = sum(1 for t in terms if t in haystack)
            if score or not terms:
                scored.append((score, slug, desc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._to_record(slug, desc) for _, slug, desc in scored[:limit]]

    async def get_details(self, dataset_id: str) -> DatasetRecord | None:
        for slug, desc in await self._load_index():
            if slug == dataset_id:
                return self._to_record(slug, desc)
        return None

    def _to_record(self, slug: str, desc: str) -> DatasetRecord:
        return DatasetRecord(
            id=slug,
            source=self.name,
            title=desc,
            description=desc,
            url=_CONTENT.format(slug=slug),
            modalities=detect_modalities(slug, desc),
            access="public",
        )
