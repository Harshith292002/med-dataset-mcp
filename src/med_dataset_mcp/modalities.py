"""Lightweight modality detection from free text.

Connectors rarely expose structured modality fields, so we infer modalities
from titles/descriptions/keywords using a curated synonym map. This keeps
`find_paired_datasets` and modality filtering working across heterogeneous
sources without per-source special casing.
"""

from __future__ import annotations

import re

# Canonical modality -> regex-ready synonyms (matched case-insensitively on
# word boundaries where sensible).
_MODALITY_SYNONYMS: dict[str, list[str]] = {
    "psg": ["psg", "polysomnograph", "polysomnogram", "sleep study"],
    "eeg": ["eeg", "electroencephalogra"],
    "meg": ["meg", "magnetoencephalogra"],
    "ieeg": ["ieeg", "intracranial eeg", "ecog", "electrocorticogra"],
    "pet": ["pet scan", "positron emission"],
    "ecg": ["ecg", "ekg", "electrocardiogra"],
    "emg": ["emg", "electromyogra"],
    "eog": ["eog", "electrooculogra"],
    "ppg": ["ppg", "photoplethysmogra"],
    "imu": ["imu", "accelerometer", "actigraph", "actigraphy", "wrist movement", "gyroscope"],
    "eda": ["eda", "electrodermal", "gsr", "skin conductance"],
    "spo2": ["spo2", "oximetry", "pulse ox", "oxygen saturation"],
    "respiration": ["respirat", "airflow", "breathing"],
    "temperature": ["skin temperature", "body temperature"],
    "fmri": ["fmri", "functional mri", "functional magnetic"],
    "mri": ["mri", "magnetic resonance"],
    "ct": ["ct scan", "computed tomograph"],
}


def _compile(synonym: str) -> re.Pattern[str]:
    """Build a boundary-aware regex for a synonym.

    A leading word boundary is always required. Short acronyms (<=5 alnum
    chars, e.g. "imu", "psg") also get a trailing boundary so they don't match
    inside longer words ("stimulation" must not match "imu"). Word stems like
    "polysomnograph" keep only the leading boundary so inflections still match.
    """
    escaped = re.escape(synonym)
    is_acronym = synonym.isalnum() and len(synonym) <= 5
    suffix = r"\b" if is_acronym else ""
    return re.compile(rf"\b{escaped}{suffix}", re.IGNORECASE)


_COMPILED: dict[str, list[re.Pattern[str]]] = {
    modality: [_compile(s) for s in synonyms]
    for modality, synonyms in _MODALITY_SYNONYMS.items()
}


def detect_modalities(*texts: str) -> list[str]:
    """Return the canonical modalities mentioned anywhere in the given texts."""
    haystack = " ".join(t for t in texts if t)
    found: list[str] = []
    for modality, patterns in _COMPILED.items():
        if any(p.search(haystack) for p in patterns):
            found.append(modality)
    return found


def normalize_modality(value: str) -> str:
    """Map a user-supplied modality string to a canonical key when possible."""
    value = value.strip().lower()
    if value in _MODALITY_SYNONYMS:
        return value
    for modality, synonyms in _MODALITY_SYNONYMS.items():
        if value in synonyms:
            return modality
    return value


def known_modalities() -> list[str]:
    return list(_MODALITY_SYNONYMS)
