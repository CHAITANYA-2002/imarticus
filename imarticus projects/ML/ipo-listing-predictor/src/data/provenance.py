"""Keeps data/raw/manifest.json: where each raw file came from, when, and its hash."""

import hashlib
import json
from datetime import datetime, timezone

from src.config import MANIFEST_PATH, PROJECT_ROOT


def sha256_of(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(manifest_path=MANIFEST_PATH):
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def record(path, source, note="", manifest_path=MANIFEST_PATH):
    key = path.resolve().relative_to(PROJECT_ROOT).as_posix()
    entry = {
        "file": key,
        "source": source,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": path.stat().st_size,
        "sha256": sha256_of(path),
        "note": note,
    }
    manifest = {**load_manifest(manifest_path), key: entry}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest
