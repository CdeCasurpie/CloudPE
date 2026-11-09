"""Verify the bundled gallery; --write updates its committed SHA-256 manifest."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("bunny", "fachada", "esfera", "esquina", "cuadra_dense", "cuadra_sparse")
ASSETS = ("original.ply", "processed.ply", "mesh.ply", "report.json")


def inventory():
    result = {}
    for name in NAMES:
        for asset in ASSETS:
            relative = f"{name}/{asset}"
            path = ROOT / "examples" / relative
            if not path.is_file():
                raise ValueError(f"Falta examples/{relative}")
            result[relative] = {
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    path = ROOT / "examples/manifest.json"
    actual = inventory()
    if args.write:
        path.write_text(json.dumps(actual, indent=2) + "\n")
    elif json.loads(path.read_text()) != actual:
        raise SystemExit("Los ejemplos no coinciden con manifest.json")
    print(
        f"OK: {len(NAMES)} ejemplos, {len(actual)} archivos, {sum(v['bytes'] for v in actual.values()) / 2**20:.2f} MiB"
    )


if __name__ == "__main__":
    main()
