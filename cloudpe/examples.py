"""Fachada sintética reproducible con ventanas retranqueadas, ruido y atípicos."""

import numpy as np

from .core import Cloud


def facade(n=20000, seed=21):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-4, 4, n)
    z = rng.uniform(0, 5, n)
    y = np.zeros(n)
    label = np.zeros(n, dtype=np.int32)
    rgb = np.tile([193, 165, 128], (n, 1))
    for center in (-2.6, 0.0, 2.6):
        window = (np.abs(x - center) < 0.7) & (z > 1.5) & (z < 3.5)
        y[window] = 0.25
        label[window] = 1
        rgb[window] = [47, 96, 135]
    xyz = np.column_stack([x, y, z])
    # Windows are recessed sampled surfaces; no claim of realistic LiDAR visibility.
    xyz += rng.normal(0, 0.008, xyz.shape)
    rgb = np.clip(rgb + rng.normal(0, 6, rgb.shape), 0, 255).astype(np.uint8)
    count = n // 100
    xyz = np.vstack([xyz, rng.uniform([-4, -1, 0], [4, 1, 5], (count, 3))])
    rgb = np.vstack([rgb, np.tile([200, 60, 60], (count, 1))])
    label = np.r_[label, np.full(count, -1)]
    return Cloud(
        xyz,
        {"rgb": rgb, "gt_segment": label.astype(np.int32), "source_index": np.arange(len(xyz))},
        [{"operation": "synthetic_facade", "seed": seed, "noise_sigma": 0.008}],
    )
