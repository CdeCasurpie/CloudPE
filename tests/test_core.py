import numpy as np
import pytest
from cloudlab.core import (Cloud, synthetic, save_cloud, load_cloud, clean, crop,
                           estimate_normals, segment, reconstruct, mesh_report,
                           repair_planar_holes, spacing)


def test_ply_roundtrip(tmp_path):
    cloud = synthetic(n=200, outliers=0)
    cloud.attrs["block_id"] = np.ones(200, dtype=np.uint16)
    path = tmp_path / "test.ply"; save_cloud(cloud, path); restored = load_cloud(path)
    np.testing.assert_allclose(restored.xyz, cloud.xyz)
    np.testing.assert_array_equal(restored.attrs["rgb"], cloud.attrs["rgb"])
    np.testing.assert_array_equal(restored.attrs["block_id"], cloud.attrs["block_id"])


def test_clean_duplicates_outliers():
    cloud = synthetic("plane", n=1000, noise=0, outliers=0)
    cloud = Cloud(np.vstack([cloud.xyz, cloud.xyz[:20], [[100, 100, 100]], [[np.nan, 0, 0]]]))
    result, removed, report = clean(cloud)
    assert report["duplicates_removed"] == 20
    assert len(removed.xyz) >= 1
    assert len(result.xyz) <= 1000


def test_normals_plane():
    cloud = estimate_normals(synthetic("plane", n=1500, noise=.0001, outliers=0))
    assert np.median(np.abs(cloud.attrs["normals"][:, 2])) > .999
    assert cloud.attrs["normal_valid"].all()


def test_degenerate_normals():
    cloud = Cloud(np.column_stack([np.arange(30), np.zeros((30, 2))]))
    result = estimate_normals(cloud, orient=False)
    assert not result.attrs["normal_valid"].any()


def test_regions_corner():
    cloud = estimate_normals(synthetic("corner", n=2500, noise=.0001, outliers=0))
    result = segment(cloud, min_size=100)
    labels = result.attrs["segment"]
    assert len(np.unique(labels[labels >= 0])) >= 2
    assert np.mean(labels >= 0) > .7


def test_graph_no_color():
    cloud = estimate_normals(synthetic("plane", n=500, noise=0, outliers=0))
    cloud.attrs.pop("rgb")
    result = segment(cloud, "graph", scale=10, min_size=5)
    assert np.any(result.attrs["segment"] >= 0)


def test_bpa_and_repair():
    cloud = estimate_normals(synthetic("sphere", n=2500, noise=.0001, outliers=0))
    mesh = reconstruct(cloud)
    assert len(mesh.triangles) > 1000
    report = mesh_report(mesh, cloud)
    assert report["point_to_mesh_p50_p95"][1] < .1
    repaired, info = repair_planar_holes(mesh, cloud)
    assert len(repaired.triangles) >= len(mesh.triangles)


def test_crop_and_errors():
    cloud = synthetic(n=100)
    assert len(crop(cloud, [-.2, -.2, -.2], [.2, .2, .2]).xyz) < len(cloud.xyz)
    with pytest.raises(ValueError):
        crop(cloud, block=1)
    with pytest.raises(ValueError):
        reconstruct(cloud)
    with pytest.raises(ValueError):
        spacing(np.zeros((10, 3)))


def test_graph_color_splits_plane():
    x, y = np.meshgrid(np.linspace(-1, 1, 25), np.linspace(-1, 1, 25))
    xyz = np.column_stack([x.ravel(), y.ravel(), np.zeros(x.size)])
    rgb = np.where((xyz[:, 0] < 0)[:, None], [255, 0, 0], [0, 0, 255]).astype(np.uint8)
    cloud = estimate_normals(Cloud(xyz, {"rgb": rgb}))
    geometric = segment(cloud, "graph", color_weight=0, scale=2, min_size=10)
    colored = segment(cloud, "graph", color_weight=2, scale=2, min_size=10)
    assert len(np.unique(geometric.attrs["segment"])) == 1
    assert len(np.unique(colored.attrs["segment"])) == 2


def test_local_repair_supported_square():
    import open3d as o3d
    # Four quads surrounding a missing central square, all coplanar.
    vertices = np.array([[-2,-2,0], [2,-2,0], [2,2,0], [-2,2,0],
                         [-.5,-.5,0], [.5,-.5,0], [.5,.5,0], [-.5,.5,0]], float)
    triangles = np.array([[0,1,5], [0,5,4], [1,2,6], [1,6,5],
                          [2,3,7], [2,7,6], [3,0,4], [3,4,7]])
    mesh = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(vertices), o3d.utility.Vector3iVector(triangles))
    x, y = np.meshgrid(np.linspace(-2,2,17), np.linspace(-2,2,17))
    support = Cloud(np.column_stack([x.ravel(), y.ravel(), np.zeros(x.size)]))
    repaired, info = repair_planar_holes(mesh, support)
    assert info["accepted_loops"] == 1
    assert len(repaired.triangles) == len(triangles) + 2


def test_absolute_bpa_radii_match_relative():
    cloud=estimate_normals(synthetic('sphere',n=800,noise=0,outliers=0))
    h=spacing(cloud.xyz)['median']
    relative=reconstruct(cloud,[2.5,4,6])
    absolute=reconstruct(cloud,[h*r for r in [2.5,4,6]],radius_mode='absolute')
    np.testing.assert_array_equal(np.asarray(relative.triangles),np.asarray(absolute.triangles))
    with pytest.raises(ValueError):reconstruct(cloud,[np.nan])
    with pytest.raises(ValueError):reconstruct(cloud,[1],radius_mode='unknown')
