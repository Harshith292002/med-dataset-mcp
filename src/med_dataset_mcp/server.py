"""MedDataMCP — MCP server exposing federated medical dataset discovery tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from med_dataset_mcp.modalities import known_modalities
from med_dataset_mcp.registry import Registry

mcp = FastMCP("MedDataMCP")
_registry = Registry()


@mcp.tool()
async def list_sources() -> list[dict]:
    """List every registered dataset source and its access requirements."""
    return _registry.list_sources()


@mcp.tool()
async def list_modalities() -> list[str]:
    """List the canonical modality keywords usable in search/filter tools."""
    return known_modalities()


@mcp.tool()
async def search_datasets(
    query: str,
    sources: list[str] | None = None,
    modalities: list[str] | None = None,
    per_source_limit: int = 10,
) -> list[dict]:
    """Search medical/biosignal datasets across all sources at once.

    Args:
        query: Free-text query, e.g. "polysomnography wrist actigraphy".
        sources: Optional subset of source names (see `list_sources`). Defaults
            to all sources.
        modalities: Optional list of canonical modalities (see
            `list_modalities`) to keep only datasets exhibiting them.
        per_source_limit: Max results requested from each source before merging.

    Returns:
        Datasets normalized to a shared schema, ranked by query relevance.
    """
    records = await _registry.search(query, sources, modalities, per_source_limit)
    return [r.model_dump() for r in records]


@mcp.tool()
async def get_dataset_details(source: str, dataset_id: str) -> dict | None:
    """Fetch full metadata for one dataset by its source and source-local id.

    The `source` and `dataset_id` correspond to the `source` and `id` fields of
    a `search_datasets` result.
    """
    record = await _registry.get_details(source, dataset_id)
    return record.model_dump() if record else None


@mcp.tool()
async def find_paired_datasets(
    modality_a: str,
    modality_b: str,
    sources: list[str] | None = None,
) -> list[dict]:
    """Find datasets that contain BOTH modalities (e.g. PSG and wrist IMU).

    Useful for discovering paired studies such as polysomnography recorded
    alongside wearable accelerometry.
    """
    records = await _registry.find_paired(modality_a, modality_b, sources)
    return [r.model_dump() for r in records]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
