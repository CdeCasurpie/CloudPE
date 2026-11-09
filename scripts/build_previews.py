"""Actual cloud thumbnails for the offline CloudPE gallery."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cloudpe.core import load_cloud


def main():
    folder = Path("frontend/public/previews")
    folder.mkdir(parents=True, exist_ok=True)
    for path in Path("examples").glob("*/processed.ply"):
        xyz = load_cloud(path).xyz
        lo, hi = np.percentile(xyz, [1, 99], axis=0)
        xyz = xyz[((xyz >= lo) & (xyz <= hi)).all(1)]
        xyz -= xyz.mean(0)
        if path.parent.name == "bunny":
            uv = xyz[:, [0, 1]]
            depth = xyz[:, 2]
        elif path.parent.name in ("cuadra_dense", "cuadra_sparse"):
            xyz *= np.array([1.0, -1.0, -1.0])
            uv = np.column_stack([xyz[:, 0] + xyz[:, 2] * 0.35, xyz[:, 1] + xyz[:, 2] * 0.1])
            depth = xyz[:, 2]
        elif path.parent.name == "fachada":
            uv = np.column_stack([xyz[:, 0] + xyz[:, 1] * 0.35, xyz[:, 2] + xyz[:, 1] * 0.1])
            depth = xyz[:, 1]
        else:
            uv = np.column_stack([xyz[:, 0] - 0.35 * xyz[:, 1], xyz[:, 2] + 0.2 * xyz[:, 1]])
            depth = xyz[:, 1]
        uv -= (uv.max(0) + uv.min(0)) / 2
        extent = np.ptp(uv, axis=0)
        uv /= max(extent[0] / 1.15, extent[1] / 0.67, 1e-8)
        fig, ax = plt.subplots(figsize=(4, 2), dpi=120)
        fig.patch.set_facecolor("#12191e")
        ax.set_facecolor("#12191e")
        ax.scatter(uv[:, 0], uv[:, 1], s=0.1, c=depth, cmap="bone", alpha=0.6, rasterized=True)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(-0.65, 0.65)
        ax.set_ylim(-0.4, 0.4)
        fig.subplots_adjust(0, 0, 1, 1)
        fig.savefig(folder / f"{path.parent.name}.png", facecolor=fig.get_facecolor())
        plt.close(fig)


if __name__ == "__main__":
    main()
