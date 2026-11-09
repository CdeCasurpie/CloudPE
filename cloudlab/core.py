from dataclasses import dataclass, field
from pathlib import Path
import json
import time

import numpy as np
from scipy.spatial import cKDTree, Delaunay, ConvexHull


@dataclass
class Cloud:
    xyz: np.ndarray
    attrs: dict = field(default_factory=dict)
    history: list = field(default_factory=list)

    def __post_init__(self):
        self.xyz = np.asarray(self.xyz, dtype=np.float64)
        if self.xyz.ndim != 2 or self.xyz.shape[1] != 3:
            raise ValueError("Las coordenadas deben tener forma N × 3")
        if any(len(v) != len(self.xyz) for v in self.attrs.values()):
            raise ValueError("Los atributos deben tener un valor por punto")

    def select(self, ids, operation="selección"):
        return Cloud(self.xyz[ids], {k: v[ids] for k, v in self.attrs.items()},
                     self.history + [{"operation": operation}])

    def copy(self):
        return self.select(np.arange(len(self.xyz)), "copia")


def load_cloud(path):
    path = Path(path)
    if path.suffix.lower() == ".ply":
        from plyfile import PlyData
        ply = PlyData.read(str(path))
        vertex = ply["vertex"].data
        xyz = np.column_stack([vertex[k] for k in ("x", "y", "z")])
        attrs = {}
        names = vertex.dtype.names
        for keys, name in [(("red", "green", "blue"), "rgb"),
                           (("nx", "ny", "nz"), "normals")]:
            if all(k in names for k in keys):
                attrs[name] = np.column_stack([vertex[k] for k in keys])
        excluded = {"x", "y", "z", "red", "green", "blue", "nx", "ny", "nz"}
        for key in names:
            if key not in excluded and vertex[key].dtype.kind in "biuf":
                attrs[key] = np.array(vertex[key])
    elif path.suffix.lower() in (".xyz", ".txt"):
        data = np.loadtxt(path, ndmin=2)
        if data.shape[1] not in (3, 6):
            raise ValueError("XYZ/TXT: se aceptan exactamente XYZ o XYZ RGB (0–255)")
        xyz, attrs = data[:, :3], {}
        if data.shape[1] == 6:
            attrs["rgb"] = np.clip(data[:, 3:], 0, 255).astype(np.uint8)
    elif path.suffix.lower() == ".pcd":
        import open3d as o3d
        pc = o3d.io.read_point_cloud(str(path))
        xyz, attrs = np.asarray(pc.points), {}
        if pc.has_colors():
            attrs["rgb"] = np.rint(np.asarray(pc.colors) * 255).astype(np.uint8)
        if pc.has_normals():
            attrs["normals"] = np.asarray(pc.normals)
    else:
        raise ValueError("Formato no soportado: usa PLY, PCD o XYZ/TXT")
    if not len(xyz):
        raise ValueError("El archivo no contiene puntos")
    attrs.setdefault("source_index", np.arange(len(xyz), dtype=np.int64))
    return Cloud(xyz, attrs, [{"operation": "load", "path": str(path.resolve())}])


def save_cloud(cloud, path):
    from plyfile import PlyData, PlyElement
    fields = [(k, "f8") for k in ("x", "y", "z")]
    columns = {k: cloud.xyz[:, j] for j, k in enumerate(("x", "y", "z"))}
    for name, values in cloud.attrs.items():
        if name == "rgb":
            for j, key in enumerate(("red", "green", "blue")):
                fields.append((key, "u1")); columns[key] = np.clip(values[:, j], 0, 255)
        elif name == "normals":
            for j, key in enumerate(("nx", "ny", "nz")):
                fields.append((key, "f4")); columns[key] = values[:, j]
        elif values.ndim == 1:
            # PLY has no portable int64; preserve large integer IDs as float64.
            dtype = "i4" if values.dtype.kind in "biu" and (not len(values) or np.max(np.abs(values)) < 2**31) else "f8"
            fields.append((name, dtype)); columns[name] = values
    records = np.empty(len(cloud.xyz), dtype=fields)
    for key, value in columns.items():
        records[key] = value
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    PlyData([PlyElement.describe(records, "vertex")], text=False).write(str(path))


def spacing(xyz, sample=20000):
    if len(xyz) < 2:
        raise ValueError("Se necesitan al menos dos puntos")
    rng = np.random.default_rng(42)
    ids = rng.choice(len(xyz), min(sample, len(xyz)), replace=False)
    d = cKDTree(xyz).query(xyz[ids], k=min(8, len(xyz)), workers=2)[0]
    positive = np.where(d[:, 1:] > 1e-12, d[:, 1:], np.inf).min(axis=1)
    positive = positive[np.isfinite(positive)]
    if not len(positive):
        raise ValueError("No hay separación positiva entre puntos")
    return dict(zip(("p10", "median", "p90"), np.percentile(positive, [10, 50, 90]).tolist()))


def inspect_cloud(cloud):
    valid = np.isfinite(cloud.xyz).all(axis=1)
    xyz = cloud.xyz[valid]
    result = {"points": len(cloud.xyz), "invalid": int((~valid).sum()),
              "attributes": list(cloud.attrs)}
    if len(xyz):
        result.update(bounds=[xyz.min(0).tolist(), xyz.max(0).tolist()],
                      percentiles=np.percentile(xyz, [1, 50, 99], axis=0).tolist())
    if len(xyz) > 1:
        try:
            result["spacing"] = spacing(xyz)
        except ValueError:
            pass
    if "block_id" in cloud.attrs:
        ids, counts = np.unique(cloud.attrs["block_id"], return_counts=True)
        result["blocks"] = {str(i): int(n) for i, n in zip(ids, counts)}
    return result


def crop(cloud, lower=None, upper=None, block=None):
    mask = np.isfinite(cloud.xyz).all(1)
    if lower is not None:
        mask &= (cloud.xyz >= lower).all(1)
    if upper is not None:
        mask &= (cloud.xyz <= upper).all(1)
    if block is not None:
        if "block_id" not in cloud.attrs:
            raise ValueError("Esta nube no contiene block_id")
        mask &= cloud.attrs["block_id"] == block
    return cloud.select(mask, "recorte")


def clean(cloud, voxel=0., neighbors=20, std_ratio=2.5, radius=0., min_neighbors=3):
    if voxel < 0 or radius < 0 or std_ratio <= 0 or neighbors < 0:
        raise ValueError("Vóxel, radio y vecinos deben ser no negativos; σ debe ser positivo")
    start = time.perf_counter()
    cloud = cloud.select(np.isfinite(cloud.xyz).all(1), "eliminar no finitos")
    before = len(cloud.xyz)
    _, ids = np.unique(cloud.xyz, axis=0, return_index=True)
    out = cloud.select(np.sort(ids), "deduplicación exacta")
    dedup = before - len(out.xyz)
    if voxel > 0 and len(out.xyz):
        # Select an actual point per voxel: all custom attributes retain their meaning.
        keys = np.floor((out.xyz - out.xyz.min(0)) / voxel).astype(np.int64)
        _, ids = np.unique(keys, axis=0, return_index=True)
        out = out.select(np.sort(ids), "vóxeles: representante original")
    reduced = len(out.xyz)
    if len(out.xyz) >= 4:
        tree = cKDTree(out.xyz)
        keep = np.ones(len(out.xyz), dtype=bool)
        if neighbors > 0:
            k = min(neighbors + 1, len(out.xyz))
            means = np.empty(len(out.xyz))
            for begin in range(0, len(out.xyz), 10000):
                d = tree.query(out.xyz[begin:begin + 10000], k=k, workers=2)[0]
                means[begin:begin + len(d)] = d[:, 1:].mean(1)
            keep &= means <= means.mean() + std_ratio * means.std()
        if radius > 0:
            counts = tree.query_ball_point(out.xyz, radius, return_length=True, workers=2) - 1
            keep &= counts >= min_neighbors
        removed = out.select(~keep, "atípicos marcados")
        out = out.select(keep, "filtrado de atípicos")
    else:
        removed = out.select(np.zeros(len(out.xyz), dtype=bool))
    # Any old segmentation/normals are stale after changing neighborhoods.
    for key in ("normals", "normal_confidence", "surface_variation", "normal_valid", "segment"):
        out.attrs.pop(key, None)
    report = {"input_finite": before, "duplicates_removed": dedup,
              "after_voxel": reduced, "outliers_removed": len(removed.xyz),
              "output": len(out.xyz), "seconds": time.perf_counter() - start}
    out.history.append({"operation": "clean", "voxel": voxel, "neighbors": neighbors,
                        "std_ratio": std_ratio, "radius": radius, **report})
    return out, removed, report


def estimate_normals(cloud, k=30, max_radius=0., orient=True):
    if len(cloud.xyz) < 4 or not np.isfinite(cloud.xyz).all():
        raise ValueError("PCA necesita al menos cuatro puntos finitos")
    if k < 3:
        raise ValueError("k debe ser al menos 3")
    out = cloud.copy(); xyz = out.xyz - out.xyz.mean(0)
    tree = cKDTree(xyz); k = min(k, len(xyz))
    normals = np.zeros_like(xyz); variation = np.ones(len(xyz))
    confidence = np.zeros(len(xyz)); valid = np.zeros(len(xyz), dtype=bool)
    for begin in range(0, len(xyz), 4096):
        d, ids = tree.query(xyz[begin:begin + 4096], k=k, workers=2)
        local = xyz[ids]
        weights = np.ones(d.shape, dtype=bool) if max_radius <= 0 else d <= max_radius
        count = weights.sum(1)
        center = (local * weights[..., None]).sum(1) / np.maximum(count[:, None], 1)
        centered = (local - center[:, None]) * weights[..., None]
        cov = np.einsum("nki,nkj->nij", centered, centered) / np.maximum(count[:, None, None], 1)
        eigen, vectors = np.linalg.eigh(cov)
        ok = (count >= 3) & (eigen[:, 1] > 1e-12 * np.maximum(eigen[:, 2], 1e-20))
        sl = slice(begin, begin + len(d))
        normals[sl] = vectors[:, :, 0]
        variation[sl] = np.maximum(eigen[:, 0], 0) / np.maximum(eigen.sum(1), 1e-30)
        confidence[sl] = np.clip((eigen[:, 1] - eigen[:, 0]) / np.maximum(eigen[:, 2], 1e-30), 0, 1)
        valid[sl] = ok
    if orient:
        # Propagation on a minimum spanning forest, with a bounded spatial graph.
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import minimum_spanning_tree
        limit = max_radius if max_radius > 0 else 5 * spacing(xyz)["median"]
        d, ids = tree.query(xyz, k=min(9, len(xyz)), workers=2)
        rows = np.repeat(np.arange(len(xyz)), ids.shape[1] - 1)
        cols = ids[:, 1:].ravel(); distances = d[:, 1:].ravel()
        mask = (distances <= limit) & valid[rows] & valid[cols]
        rows, cols = rows[mask], cols[mask]
        costs = 1 - np.abs(np.einsum("ij,ij->i", normals[rows], normals[cols])) + 1e-6
        graph = coo_matrix((costs, (rows, cols)), shape=(len(xyz), len(xyz))).tocsr()
        forest = minimum_spanning_tree(graph.maximum(graph.T))
        forest = (forest + forest.T).tocsr()
        seen = np.zeros(len(xyz), bool)
        for root in range(len(xyz)):
            if seen[root] or not valid[root]:
                continue
            seen[root] = True; stack = [root]
            while stack:
                u = stack.pop()
                for v in forest.indices[forest.indptr[u]:forest.indptr[u + 1]]:
                    if not seen[v]:
                        if normals[u] @ normals[v] < 0:
                            normals[v] *= -1
                        seen[v] = True; stack.append(v)
    out.attrs.update(normals=normals, normal_confidence=confidence,
                     surface_variation=variation, normal_valid=valid.astype(np.uint8))
    out.attrs.pop("segment", None)
    out.history.append({"operation": "PCA normals", "k": k, "max_radius": max_radius,
                        "oriented": orient, "valid": int(valid.sum())})
    return out


def segment(cloud, method="regions", k=12, radius=0., angle=20., plane=0.,
            min_size=40, color_weight=0.5, scale=0.4):
    if k < 1 or not 0 < angle <= 90 or plane < 0 or radius < 0 or min_size < 1 or scale <= 0 or color_weight < 0:
        raise ValueError("Parámetros de segmentación fuera del rango válido")
    if "normals" not in cloud.attrs:
        raise ValueError("Calcula primero las normales")
    if method not in ("regions", "graph"):
        raise ValueError("Método desconocido")
    n = len(cloud.xyz)
    if n < 4:
        raise ValueError("No hay suficientes puntos")
    xyz = cloud.xyz - cloud.xyz.mean(0); normals = cloud.attrs["normals"]
    valid = cloud.attrs.get("normal_valid", np.ones(n, bool)).astype(bool)
    h = spacing(xyz)["median"]; radius = radius or 4 * h; plane = plane or h
    d, ids = cKDTree(xyz).query(xyz, k=min(k + 1, n), workers=2)
    row = np.repeat(np.arange(n), ids.shape[1] - 1); col = ids[:, 1:].ravel()
    delta = xyz[col] - xyz[row]
    normal_diff = np.arccos(np.clip(np.abs(np.einsum("ij,ij->i", normals[row], normals[col])), 0, 1))
    residual = np.maximum(np.abs(np.einsum("ij,ij->i", delta, normals[row])),
                          np.abs(np.einsum("ij,ij->i", delta, normals[col])))
    allowed = (d[:, 1:].ravel() <= radius) & valid[row] & valid[col]
    allowed &= (normal_diff <= np.deg2rad(angle)) & (residual <= plane)
    row, col = row[allowed], col[allowed]
    costs = normal_diff[allowed] / max(np.deg2rad(angle), 1e-12) + residual[allowed] / plane
    if method == "graph" and "rgb" in cloud.attrs and color_weight > 0:
        from skimage.color import rgb2lab
        lab = rgb2lab(np.clip(cloud.attrs["rgb"] / 255., 0, 1).reshape(-1, 1, 3)).reshape(-1, 3)
        costs += color_weight * np.linalg.norm(lab[row] - lab[col], axis=1) / 30.
    labels = np.full(n, -1, dtype=np.int32)
    if method == "regions":
        from scipy.sparse import coo_matrix
        adjacency = coo_matrix((np.ones(len(row)), (row, col)), shape=(n, n)).tocsr()
        adjacency = adjacency.maximum(adjacency.T)
        variation = cloud.attrs.get("surface_variation", np.zeros(n))
        label = 0
        for root in np.argsort(variation):
            if labels[root] != -1 or not valid[root]:
                continue
            labels[root] = -2; members = [root]; queue = [root]
            while queue:
                u = queue.pop()
                for v in adjacency.indices[adjacency.indptr[u]:adjacency.indptr[u + 1]]:
                    if labels[v] != -1:
                        continue
                    # Seed plane prevents gradual drift over a curved surface.
                    if abs((xyz[v] - xyz[root]) @ normals[root]) > 2 * plane:
                        continue
                    if abs(normals[v] @ normals[root]) < np.cos(np.deg2rad(angle)):
                        continue
                    labels[v] = -2; members.append(v)
                    if variation[v] <= 0.08:
                        queue.append(v)
            if len(members) >= min_size:
                labels[members] = label; label += 1
        labels[labels < 0] = -1
    else:
        parent = np.arange(n); size = np.ones(n, dtype=np.int64); internal = np.zeros(n)
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a
        for edge in np.argsort(costs):
            a, b = find(row[edge]), find(col[edge]); w = costs[edge]
            if a == b or w > min(internal[a] + scale / size[a], internal[b] + scale / size[b]):
                continue
            if size[a] < size[b]:
                a, b = b, a
            parent[b] = a; size[a] += size[b]; internal[a] = w
        roots = np.array([find(i) for i in range(n)])
        good = np.unique(roots[valid & (size[roots] >= min_size)])
        for label, root in enumerate(good):
            labels[(roots == root) & valid] = label
    out = cloud.copy(); out.attrs["segment"] = labels
    out.history.append({"operation": "segment", "method": method, "k": k,
                        "radius": radius, "angle": angle, "plane": plane,
                        "min_size": min_size, "color_weight": color_weight, "scale": scale})
    return out


def to_open3d(cloud, origin=None):
    import open3d as o3d
    pc = o3d.geometry.PointCloud()
    pc.points = o3d.utility.Vector3dVector(cloud.xyz if origin is None else cloud.xyz - origin)
    if "rgb" in cloud.attrs:
        pc.colors = o3d.utility.Vector3dVector(np.clip(cloud.attrs["rgb"] / 255., 0, 1))
    if "normals" in cloud.attrs:
        pc.normals = o3d.utility.Vector3dVector(cloud.attrs["normals"])
    return pc


def reconstruct(cloud, multipliers=(2.5, 4., 6.), radius_mode="median"):
    import open3d as o3d
    if "normals" not in cloud.attrs:
        raise ValueError("BPA requiere normales: ejecuta PCA primero")
    valid = cloud.attrs.get("normal_valid", np.ones(len(cloud.xyz), bool)).astype(bool)
    normal_lengths = np.linalg.norm(cloud.attrs['normals'], axis=1)
    valid &= np.isfinite(cloud.xyz).all(1) & np.isfinite(normal_lengths) & (normal_lengths > 1e-12)
    selected = cloud.select(valid)
    if len(selected.xyz) < 4:
        raise ValueError("Se necesitan al menos cuatro puntos con normales válidas")
    multipliers = sorted(float(r) for r in multipliers)
    if not multipliers or len(multipliers) > 6 or not np.isfinite(multipliers).all() or min(multipliers) <= 0:
        raise ValueError("Los radios deben ser positivos")
    if radius_mode not in ("median", "p90", "absolute"):
        raise ValueError("Escala de radios desconocida")
    h = 1. if radius_mode == 'absolute' else spacing(selected.xyz)[radius_mode]
    origin = selected.xyz.mean(0)
    selected.attrs['normals'] = selected.attrs['normals'] / normal_lengths[valid, None]
    mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
        to_open3d(selected, origin), o3d.utility.DoubleVector([h * r for r in multipliers]))
    mesh.remove_duplicated_triangles(); mesh.remove_degenerate_triangles(); mesh.remove_unreferenced_vertices()
    mesh.translate(origin); mesh.compute_vertex_normals()
    return mesh


def reconstruction_diagnostics(cloud):
    result = {'spacing': spacing(cloud.xyz)}
    if 'normals' in cloud.attrs:
        normals=cloud.attrs['normals'];lengths=np.linalg.norm(normals,axis=1)
        valid=np.isfinite(lengths)&(lengths>1e-12)
        ids=np.random.default_rng(42).choice(len(cloud.xyz),min(20000,len(cloud.xyz)),replace=False)
        _,neighbors=cKDTree(cloud.xyz).query(cloud.xyz[ids],k=2,workers=2)
        other=neighbors[:,1];ok=valid[ids]&valid[other]
        dots=np.einsum('ij,ij->i',normals[ids[ok]],normals[other[ok]])/(lengths[ids[ok]]*lengths[other[ok]])
        result.update(invalid_normals=int((~valid).sum()),neighbor_opposite_fraction=float(np.mean(dots<0)) if len(dots) else None)
    return result


def mesh_report(mesh, reference=None):
    vertices = np.asarray(mesh.vertices); triangles = np.asarray(mesh.triangles)
    result = {"vertices": len(vertices), "triangles": len(triangles)}
    if not len(triangles):
        return result
    edges = np.sort(np.concatenate([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    lengths = np.linalg.norm(vertices[unique[:, 0]] - vertices[unique[:, 1]], axis=1)
    _, sizes, _ = mesh.cluster_connected_triangles()
    result.update(boundary_edges=int((counts == 1).sum()), nonmanifold_edges=int((counts > 2).sum()),
                  components=len(sizes), edge_length_p50_p95=np.percentile(lengths, [50, 95]).tolist())
    if reference is not None and len(reference.xyz):
        import open3d as o3d
        # Translate for float32 raycasting precision.
        origin = vertices.mean(0)
        local = o3d.geometry.TriangleMesh(mesh); local.translate(-origin)
        scene = o3d.t.geometry.RaycastingScene()
        scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(local))
        rng = np.random.default_rng(42)
        ids = rng.choice(len(reference.xyz), min(20000, len(reference.xyz)), replace=False)
        distances = scene.compute_distance(o3d.core.Tensor((reference.xyz[ids] - origin).astype(np.float32))).numpy()
        o3d.utility.random.seed(42)
        samples = np.asarray(mesh.sample_points_uniformly(min(20000, max(1000, len(triangles)))).points)
        reverse = cKDTree(reference.xyz).query(samples, workers=2)[0]
        result["point_to_mesh_p50_p95"] = np.percentile(distances, [50, 95]).tolist()
        result["mesh_to_points_p50_p95"] = np.percentile(reverse, [50, 95]).tolist()
    return result


def repair_planar_holes(mesh, support, max_edges=30, max_diameter_factor=8., tolerance_factor=0.4):
    """Only small convex, planar boundary loops with observed point support."""
    import open3d as o3d
    out = o3d.geometry.TriangleMesh(mesh)
    vertices = np.asarray(out.vertices); faces = np.asarray(out.triangles)
    if not len(faces):
        return out, {"added_triangles": 0, "accepted_loops": 0}
    h = spacing(support.xyz)["median"]; tree = cKDTree(support.xyz)
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges, counts = np.unique(np.sort(directed, axis=1), axis=0, return_counts=True)
    boundary = edges[counts == 1]; adjacency = {}
    for a, b in boundary:
        adjacency.setdefault(int(a), []).append(int(b)); adjacency.setdefault(int(b), []).append(int(a))
    seen = set(); additions = []; loops = 0
    for root in adjacency:
        if root in seen:
            continue
        component = []; stack = [root]
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u); component.append(u); stack.extend(v for v in adjacency[u] if v not in seen)
        if not 3 <= len(component) <= max_edges or any(len(adjacency[u]) != 2 for u in component):
            continue
        order = [component[0]]; previous = -1
        while len(order) < len(component):
            candidates = [v for v in adjacency[order[-1]] if v != previous]
            nxt = candidates[0]
            if nxt == order[0]:
                break
            previous = order[-1]; order.append(nxt)
        if len(order) != len(component):
            continue
        points = vertices[order]; centered = points - points.mean(0)
        _, _, basis = np.linalg.svd(centered, full_matrices=False)
        if np.max(np.abs(centered @ basis[2])) > tolerance_factor * h:
            continue
        uv = centered @ basis[:2].T
        if np.max(np.linalg.norm(uv[:, None] - uv[None, :], axis=2)) > max_diameter_factor * h:
            continue
        try:
            hull = ConvexHull(uv)
            # Restrict to strictly convex boundaries: no unconstrained polygon filling.
            if len(hull.vertices) != len(order):
                continue
            tri = Delaunay(uv).simplices
        except Exception:
            continue
        candidate = np.asarray(order)[tri]
        probes = np.concatenate([vertices[candidate].mean(1),
                                 (vertices[candidate[:, 0]] + vertices[candidate[:, 1]]) / 2,
                                 (vertices[candidate[:, 1]] + vertices[candidate[:, 2]]) / 2,
                                 (vertices[candidate[:, 2]] + vertices[candidate[:, 0]]) / 2])
        if tree.query(probes)[0].max() > 1.5 * h:
            continue
        # Exclude an already existing face; align with adjacent face normals.
        existing = {tuple(sorted(t)) for t in faces}
        if any(tuple(sorted(t)) in existing for t in candidate):
            continue
        boundary_set = set(order)
        adjacent = [t for t in faces if sum(int(v) in boundary_set for v in t) >= 2]
        if not adjacent:
            continue
        adjacent = vertices[np.asarray(adjacent)]
        normal = np.cross(adjacent[:, 1] - adjacent[:, 0], adjacent[:, 2] - adjacent[:, 0]).sum(0)
        for t in candidate:
            if np.dot(np.cross(vertices[t[1]] - vertices[t[0]], vertices[t[2]] - vertices[t[0]]), normal) < 0:
                t = t[[0, 2, 1]]
            additions.append(t)
        loops += 1
    if additions:
        out.triangles = o3d.utility.Vector3iVector(np.vstack([faces, additions]))
        out.remove_duplicated_triangles(); out.compute_vertex_normals()
    return out, {"added_triangles": len(additions), "accepted_loops": loops,
                 "warning": "Reparación experimental, no demuestra existencia de superficie"}


def synthetic(kind="corner", n=12000, noise=0.002, outliers=0.02, seed=42):
    rng = np.random.default_rng(seed)
    if kind == "sphere":
        normals = rng.normal(size=(n, 3)); normals /= np.linalg.norm(normals, axis=1)[:, None]
        xyz = normals.copy(); labels = np.zeros(n, dtype=np.int32)
    elif kind in ("corner", "plane"):
        xyz = np.column_stack([rng.uniform(-1, 1, (n, 2)), np.zeros(n)])
        normals = np.tile([0., 0., 1.], (n, 1)); labels = np.zeros(n, dtype=np.int32)
        if kind == "corner":
            half = n // 2
            xyz[:half, 0] = np.abs(xyz[:half, 0])
            xyz[half:, 2] = np.abs(xyz[half:, 0]); xyz[half:, 0] = 0
            normals[half:] = [1., 0., 0.]; labels[half:] = 1
    else:
        raise ValueError("Usa corner, plane o sphere")
    rgb = np.where((xyz[:, 1] > 0)[:, None], [205, 65, 55], [60, 120, 210]).astype(np.uint8)
    xyz += rng.normal(scale=noise, size=xyz.shape)
    count = int(n * outliers)
    if count:
        xyz = np.vstack([xyz, rng.uniform(-3, 3, (count, 3))])
        normals = np.vstack([normals, np.zeros((count, 3))])
        labels = np.r_[labels, np.full(count, -1, dtype=np.int32)]
        rgb = np.vstack([rgb, np.tile([150, 150, 150], (count, 1))])
    return Cloud(xyz, {"rgb": rgb, "gt_normal_x": normals[:, 0], "gt_normal_y": normals[:, 1],
                       "gt_normal_z": normals[:, 2], "gt_segment": labels,
                       "source_index": np.arange(len(xyz))}, [{"operation": "synthetic", "kind": kind, "seed": seed}])


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, default=lambda x: x.item() if isinstance(x, np.generic) else str(x)))
