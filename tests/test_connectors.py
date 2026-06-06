"""Offline tests for connector response normalization (no network)."""

from med_mcp.connectors.huggingface import HuggingFaceConnector
from med_mcp.connectors.openneuro import OpenNeuroConnector


def test_huggingface_to_record_parses_tags_and_license():
    c = HuggingFaceConnector(client=None)
    rec = c._to_record(
        {
            "id": "someorg/eeg-sleep",
            "description": "An EEG sleep staging dataset",
            "tags": ["license:mit", "modality:eeg", "eeg", "region:us"],
            "gated": False,
        }
    )
    assert rec.source == "huggingface"
    assert rec.id == "someorg/eeg-sleep"
    assert rec.license == "mit"
    assert "license:mit" not in rec.tags  # namespaced tags stripped
    assert "eeg" in rec.modalities
    assert rec.access == "public"
    assert rec.url == "https://huggingface.co/datasets/someorg/eeg-sleep"


def test_huggingface_gated_marks_restricted():
    c = HuggingFaceConnector(client=None)
    rec = c._to_record({"id": "x/y", "description": "", "tags": [], "gated": "auto"})
    assert rec.access == "restricted"


def test_openneuro_to_record_counts_subjects_and_maps_modalities():
    c = OpenNeuroConnector(client=None)
    rec = c._to_record(
        {
            "id": "ds005207",
            "latestSnapshot": {
                "tag": "1.0.0",
                "description": {"Name": "Surrey cEEGrid sleep data set"},
                "summary": {"modalities": ["eeg"], "subjects": ["001", "002", "003"]},
            },
        }
    )
    assert rec.source == "openneuro"
    assert rec.title == "Surrey cEEGrid sleep data set"
    assert rec.subjects == 3  # list of ids collapsed to a count
    assert rec.modalities == ["eeg"]
    assert rec.url == "https://openneuro.org/datasets/ds005207"


def test_openneuro_handles_missing_snapshot():
    c = OpenNeuroConnector(client=None)
    rec = c._to_record({"id": "ds999999", "latestSnapshot": None})
    assert rec.title == "ds999999"
    assert rec.subjects is None
    assert rec.modalities == []
