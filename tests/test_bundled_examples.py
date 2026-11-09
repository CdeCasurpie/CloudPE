import hashlib
import json
from pathlib import Path


def test_gallery_assets_are_bundled_and_intact():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "examples/manifest.json").read_text())
    assert len(manifest) == 24
    for relative, expected in manifest.items():
        path = root / "examples" / relative
        assert path.is_file(), str(path)
        assert path.stat().st_size == expected["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected["sha256"]
