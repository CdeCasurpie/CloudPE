"""Repeatable radius investigation; update only synthetic gallery meshes."""

import json
from pathlib import Path

import open3d as o3d

from cloudpe.core import (
    load_cloud,
    mesh_report,
    reconstruct,
    reconstruction_diagnostics,
    write_json,
)


def main():
    results = {}
    for name in ("bunny", "fachada"):
        folder = Path("examples") / name
        cloud = load_cloud(folder / "processed.ply")
        trials = []
        for radii in ([1.5, 2.5, 4], [2.5, 4, 6], [3, 5, 8], [4, 6, 9]):
            mesh = reconstruct(cloud, radii)
            report = mesh_report(mesh)
            trials.append({"radii": radii, **report})
            if radii == [2.5, 4, 6]:
                o3d.io.write_triangle_mesh(str(folder / "mesh.ply"), mesh)
                gallery = json.loads((folder / "report.json").read_text())
                gallery["mesh"] = report
                h = reconstruction_diagnostics(cloud)["spacing"]["median"]
                gallery["bpa_config"] = {
                    "radii": radii,
                    "radius_mode": "median",
                    "effective_radii": [h * r for r in radii],
                    "recompute_normals": False,
                }
                write_json(folder / "report.json", gallery)
        results[name] = {"diagnostics": reconstruction_diagnostics(cloud), "trials": trials}
    write_json("outputs/bpa_radius_review.json", results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
