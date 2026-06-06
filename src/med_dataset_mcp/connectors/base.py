"""Connector interface shared by all dataset sources."""

from __future__ import annotations

import abc

import httpx

from med_dataset_mcp.schema import DatasetRecord


class Connector(abc.ABC):
    """Base class every source connector implements.

    A connector knows how to talk to one repository's API and normalize its
    responses into :class:`DatasetRecord` objects. Connectors are stateless
    apart from the shared HTTP client and should not cache (caching is handled
    one layer up in the registry).
    """

    #: Stable short name, e.g. "zenodo". Used as the `source` field and in ids.
    name: str
    #: Human-readable description shown by `list_sources`.
    description: str = ""
    #: Access tier most of this source's datasets fall under.
    default_access: str = "public"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @abc.abstractmethod
    async def search(self, query: str, limit: int) -> list[DatasetRecord]:
        """Return up to `limit` datasets matching `query`."""

    @abc.abstractmethod
    async def get_details(self, dataset_id: str) -> DatasetRecord | None:
        """Fetch a single dataset by its source-local id, or None if missing."""
