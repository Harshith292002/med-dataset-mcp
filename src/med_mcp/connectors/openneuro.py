"""OpenNeuro connector — BIDS neuroimaging/electrophysiology datasets.

OpenNeuro exposes a GraphQL API. Full-text discovery goes through
``advancedSearch(query: DatasetSearchInput)`` using the ``keywords`` field;
each dataset's latest snapshot carries structured ``modalities`` and subject
counts, so we use those directly instead of inferring from text.
"""

from __future__ import annotations

from med_mcp.connectors.base import Connector
from med_mcp.modalities import normalize_modality
from med_mcp.schema import DatasetRecord

_GRAPHQL = "https://openneuro.org/crn/graphql"
_WEB = "https://openneuro.org/datasets/{id}"

_SEARCH_QUERY = """
query($q: DatasetSearchInput!, $n: Int) {
  advancedSearch(query: $q, first: $n) {
    edges { node { id latestSnapshot {
      tag description { Name } summary { modalities subjects }
    } } }
  }
}
"""

_DETAIL_QUERY = """
query($id: ID!) {
  dataset(id: $id) { id latestSnapshot {
    tag description { Name } summary { modalities subjects }
  } }
}
"""


class OpenNeuroConnector(Connector):
    name = "openneuro"
    description = "BIDS neuroimaging & electrophysiology datasets (EEG, MEG, fMRI) from OpenNeuro."
    default_access = "public"

    async def _gql(self, query: str, variables: dict) -> dict:
        resp = await self._client.post(
            _GRAPHQL, json={"query": query, "variables": variables}
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(payload["errors"][0].get("message", "graphql error"))
        return payload["data"]

    async def search(self, query: str, limit: int) -> list[DatasetRecord]:
        keywords = [t for t in query.split() if t]
        data = await self._gql(
            _SEARCH_QUERY,
            {"q": {"keywords": keywords, "publicOnly": True}, "n": limit},
        )
        edges = data.get("advancedSearch", {}).get("edges", []) or []
        return [self._to_record(e["node"]) for e in edges]

    async def get_details(self, dataset_id: str) -> DatasetRecord | None:
        data = await self._gql(_DETAIL_QUERY, {"id": dataset_id})
        node = data.get("dataset")
        return self._to_record(node) if node else None

    def _to_record(self, node: dict) -> DatasetRecord:
        ds_id = node.get("id", "")
        snapshot = node.get("latestSnapshot") or {}
        name = (snapshot.get("description") or {}).get("Name", "") or ds_id
        summary = snapshot.get("summary") or {}
        modalities = [
            normalize_modality(m) for m in (summary.get("modalities") or [])
        ]
        # OpenNeuro's `subjects` is a list of subject ids; we want the count.
        subjects = summary.get("subjects")
        subject_count = len(subjects) if isinstance(subjects, list) else subjects
        return DatasetRecord(
            id=ds_id,
            source=self.name,
            title=name,
            description=name,
            url=_WEB.format(id=ds_id),
            modalities=modalities,
            subjects=subject_count,
            access="public",
        )
