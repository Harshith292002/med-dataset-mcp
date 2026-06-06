"""Shared data model for datasets normalized across all sources."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DatasetRecord(BaseModel):
    """A single dataset, normalized to a common schema across all sources.

    Every connector converts its source-specific response into this shape so
    that search results can be aggregated and ranked uniformly.
    """

    id: str = Field(description="Source-local identifier (unique within a source).")
    source: str = Field(description="Connector name, e.g. 'zenodo', 'physionet'.")
    title: str
    description: str = ""
    url: str = ""
    modalities: list[str] = Field(
        default_factory=list,
        description="Signal/data modalities, e.g. ['psg', 'imu', 'eeg', 'ecg'].",
    )
    subjects: int | None = Field(
        default=None, description="Number of subjects/participants if known."
    )
    license: str | None = None
    tags: list[str] = Field(default_factory=list)
    access: str = Field(
        default="public",
        description="Access level: 'public', 'credentialed', 'dua', 'restricted'.",
    )

    @property
    def global_id(self) -> str:
        """Fully-qualified id usable to fetch this record back from its source."""
        return f"{self.source}:{self.id}"
