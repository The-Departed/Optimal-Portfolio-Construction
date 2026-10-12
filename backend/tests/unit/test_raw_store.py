import json
from datetime import UTC, datetime

import pytest

from app.data_pipeline.raw_store import RawFile, RawSnapshot, RawStore
from app.data_pipeline.source_registry import BY_ID


def _snap(ts: datetime) -> RawSnapshot:
    return RawSnapshot(
        "TCS", "yahoo_finance", ts, [RawFile("history.csv", b"Date,Close\n")], {"symbol": "TCS.NS"}
    )


def test_roundtrip_and_latest(tmp_path) -> None:
    store = RawStore(tmp_path)
    spec = BY_ID["TCS"]
    store.save(spec, _snap(datetime(2026, 1, 1, tzinfo=UTC)))
    store.save(spec, _snap(datetime(2026, 1, 2, tzinfo=UTC)))
    latest = store.latest(spec)
    assert latest is not None and latest.directory.name == "20260102T000000Z"
    meta = json.loads((latest.directory / "metadata.json").read_text())
    assert meta["files"][0]["sha256"] and meta["request"] == {"symbol": "TCS.NS"}


def test_raw_snapshots_are_never_overwritten(tmp_path) -> None:
    store = RawStore(tmp_path)
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    first = store.save(BY_ID["TCS"], _snap(ts))
    original = (first / "history.csv").read_bytes()
    second = store.save(BY_ID["TCS"], _snap(ts))
    assert second != first and second.name == "20260101T000000Z_1"
    assert (first / "history.csv").read_bytes() == original
    assert store.latest(BY_ID["TCS"]).directory == second


def test_tampered_raw_file_is_detected(tmp_path) -> None:
    store = RawStore(tmp_path)
    path = store.save(BY_ID["TCS"], _snap(datetime(2026, 1, 1, tzinfo=UTC)))
    (path / "history.csv").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Checksum"):
        store.latest(BY_ID["TCS"])


def test_incomplete_snapshot_is_ignored(tmp_path) -> None:
    store = RawStore(tmp_path)
    (store.dataset_dir(BY_ID["TCS"]) / "20990101T000000Z").mkdir(parents=True)
    assert store.latest(BY_ID["TCS"]) is None
