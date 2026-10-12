"""Immutable storage of raw downloads.

Each retrieval is written to a new timestamped directory
``data/raw/<category>/<dataset_id>/<YYYYMMDDTHHMMSSZ>/`` together with a
``metadata.json`` sidecar (request, retrieval time, SHA-256 of every file). Existing
snapshots are never modified; repeated runs reuse the latest snapshot unless a
refresh is requested.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.data_pipeline import PIPELINE_VERSION
from app.data_pipeline.source_registry import DatasetSpec

METADATA_FILENAME = "metadata.json"
_TAG_FORMAT = "%Y%m%dT%H%M%SZ"


@dataclass(frozen=True, slots=True)
class RawFile:
    name: str
    content: bytes


@dataclass(slots=True)
class RawSnapshot:
    dataset_id: str
    source_kind: str
    retrieved_at: datetime
    files: list[RawFile]
    request: dict[str, Any] = field(default_factory=dict)
    source_metadata: dict[str, Any] = field(default_factory=dict)
    directory: Path | None = None

    def file(self, name: str) -> RawFile:
        for f in self.files:
            if f.name == name:
                return f
        raise KeyError(f"{self.dataset_id}: raw file {name!r} not in snapshot")


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class RawStore:
    def __init__(self, raw_dir: Path) -> None:
        self._raw_dir = raw_dir

    def dataset_dir(self, spec: DatasetSpec) -> Path:
        return self._raw_dir / spec.category.value / spec.dataset_id

    def save(self, spec: DatasetSpec, snapshot: RawSnapshot) -> Path:
        tag = snapshot.retrieved_at.astimezone(UTC).strftime(_TAG_FORMAT)
        base = self.dataset_dir(spec)
        base.mkdir(parents=True, exist_ok=True)
        target, n = base / tag, 0
        while target.exists():  # same-second retrievals get a suffix, never overwrite
            n += 1
            target = base / f"{tag}_{n}"
        target.mkdir()
        for f in snapshot.files:
            with (target / f.name).open("xb") as fh:
                fh.write(f.content)
        metadata = {
            "dataset_id": snapshot.dataset_id,
            "source_kind": snapshot.source_kind,
            "retrieved_at": snapshot.retrieved_at.astimezone(UTC).isoformat(),
            "pipeline_version": PIPELINE_VERSION,
            "request": snapshot.request,
            "source_metadata": snapshot.source_metadata,
            "files": [
                {"name": f.name, "bytes": len(f.content), "sha256": sha256(f.content)}
                for f in snapshot.files
            ],
        }
        with (target / METADATA_FILENAME).open("x", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, sort_keys=True, default=str)
        snapshot.directory = target
        return target

    def latest(self, spec: DatasetSpec) -> RawSnapshot | None:
        """Load the most recent complete snapshot, verifying file checksums."""
        base = self.dataset_dir(spec)
        if not base.is_dir():
            return None
        for candidate in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
            meta_path = candidate / METADATA_FILENAME
            if not meta_path.is_file():
                continue  # incomplete snapshot (interrupted write)
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            files = []
            for entry in meta["files"]:
                content = (candidate / entry["name"]).read_bytes()
                if sha256(content) != entry["sha256"]:
                    raise ValueError(f"Checksum mismatch for {candidate / entry['name']}")
                files.append(RawFile(entry["name"], content))
            return RawSnapshot(
                dataset_id=meta["dataset_id"],
                source_kind=meta["source_kind"],
                retrieved_at=datetime.fromisoformat(meta["retrieved_at"]),
                files=files,
                request=meta.get("request", {}),
                source_metadata=meta.get("source_metadata", {}),
                directory=candidate,
            )
        return None
