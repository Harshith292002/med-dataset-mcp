"""HuggingFace Datasets connector — growing biomedical/ML dataset collection."""

from __future__ import annotations

from med_dataset_mcp.connectors.base import Connector
from med_dataset_mcp.modalities import detect_modalities
from med_dataset_mcp.schema import DatasetRecord

_API = "https://huggingface.co/api/datasets"
_WEB = "https://huggingface.co/datasets/{id}"


class HuggingFaceConnector(Connector):
    name = "huggingface"
    description = "ML-ready datasets on the HuggingFace Hub (incl. biomedical/biosignal)."
    default_access = "public"

    async def search(self, query: str, limit: int) -> list[DatasetRecord]:
        resp = await self._client.get(
            _API, params={"search": query, "limit": limit, "full": "true"}
        )
        resp.raise_for_status()
        return [self._to_record(d) for d in resp.json()]

    async def get_details(self, dataset_id: str) -> DatasetRecord | None:
        resp = await self._client.get(f"{_API}/{dataset_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._to_record(resp.json())

    def _to_record(self, d: dict) -> DatasetRecord:
        ds_id = d.get("id", "")
        description = d.get("description", "") or ""
        raw_tags = [t for t in d.get("tags", []) if isinstance(t, str)]
        # HF tags are namespaced, e.g. "license:mit", "modality:tabular", "eeg".
        license_ = next(
            (t.split(":", 1)[1] for t in raw_tags if t.startswith("license:")), None
        )
        plain_tags = [t for t in raw_tags if ":" not in t]
        # Infer modalities from the id, description, and bare tags (e.g. "eeg").
        modalities = detect_modalities(ds_id, description, " ".join(plain_tags))
        return DatasetRecord(
            id=ds_id,
            source=self.name,
            title=ds_id,
            description=description,
            url=_WEB.format(id=ds_id),
            modalities=modalities,
            license=license_,
            tags=plain_tags,
            access="restricted" if d.get("gated") else "public",
        )
