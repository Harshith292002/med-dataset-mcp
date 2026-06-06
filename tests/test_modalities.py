from med_mcp.modalities import detect_modalities, normalize_modality


def test_detects_psg_and_imu():
    mods = detect_modalities("Polysomnography with wrist actigraphy (Empatica E4)")
    assert "psg" in mods
    assert "imu" in mods


def test_detects_ecg_synonyms():
    assert "ecg" in detect_modalities("12-lead EKG recordings")


def test_no_false_positive():
    assert detect_modalities("a study about nutrition surveys") == []


def test_normalize_synonym_to_canonical():
    assert normalize_modality("actigraphy") == "imu"
    assert normalize_modality("EEG") == "eeg"
    assert normalize_modality("unknown-thing") == "unknown-thing"
