import pytest

from med_mcp.registry import Registry
from med_mcp.schema import DatasetRecord


class _FakeConnector:
    """In-memory connector used to test registry logic without network."""

    description = "fake source"
    default_access = "public"

    def __init__(self, records, fail=False, name="fake"):
        self.name = name
        self._records = records
        self._fail = fail
        self.calls = 0

    async def search(self, query, limit):
        self.calls += 1
        if self._fail:
            raise RuntimeError("boom")
        return self._records[:limit]

    async def get_details(self, dataset_id):
        return next((r for r in self._records if r.id == dataset_id), None)


def _rec(id, mods, title="t"):
    return DatasetRecord(id=id, source="fake", title=title, modalities=mods)


@pytest.fixture
def registry():
    reg = Registry()
    reg.connectors = {}  # replace real connectors with fakes per-test
    return reg


async def test_modality_filter(registry):
    c = _FakeConnector([_rec("1", ["psg"]), _rec("2", ["eeg"])])
    registry.connectors = {"fake": c}
    out = await registry.search("x", modalities=["psg"])
    assert [r.id for r in out] == ["1"]


async def test_connector_failure_isolated(registry):
    good = _FakeConnector([_rec("1", ["psg"])], name="good")
    bad = _FakeConnector([], fail=True, name="bad")
    registry.connectors = {"good": good, "bad": bad}
    out = await registry.search("x")
    assert [r.id for r in out] == ["1"]  # bad source swallowed


async def test_caching_avoids_second_call(registry):
    c = _FakeConnector([_rec("1", ["psg"])])
    registry.connectors = {"fake": c}
    await registry.search("same")
    await registry.search("same")
    assert c.calls == 1


async def test_find_paired_requires_both(registry):
    c = _FakeConnector(
        [_rec("1", ["psg", "imu"]), _rec("2", ["psg"]), _rec("3", ["imu"])]
    )
    registry.connectors = {"fake": c}
    out = await registry.find_paired("psg", "actigraphy")  # actigraphy -> imu
    assert [r.id for r in out] == ["1"]


async def test_unknown_source_raises(registry):
    registry.connectors = {"fake": _FakeConnector([])}
    with pytest.raises(ValueError):
        await registry.search("x", sources=["nope"])
