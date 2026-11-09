"""Extensión opcional de CLI: no forma parte del pipeline principal del visor.

Reparación conservadora Delaunay para contornos pequeños, convexos y planos.
No es una reconstrucción híbrida general ni garantiza ausencia de intersecciones.
"""

import numpy as np
from scipy.spatial import ConvexHull, Delaunay, QhullError, cKDTree

from .core import spacing


def repair_planar_holes(mesh, support, max_edges=30, max_diameter_factor=8.0, tolerance_factor=0.4):
    import open3d as o3d

    out = o3d.geometry.TriangleMesh(mesh)
    vertices = np.asarray(out.vertices)
    faces = np.asarray(out.triangles)
    if not len(faces):
        return out, {"added_triangles": 0, "accepted_loops": 0}
    h = spacing(support.xyz)["median"]
    tree = cKDTree(support.xyz)
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges, counts = np.unique(np.sort(directed, axis=1), axis=0, return_counts=True)
    boundary = edges[counts == 1]
    adjacency = {}
    for a, b in boundary:
        adjacency.setdefault(int(a), []).append(int(b))
        adjacency.setdefault(int(b), []).append(int(a))
    seen = set()
    additions = []
    loops = 0
    for root in adjacency:
        if root in seen:
            continue
        component = []
        stack = [root]
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            component.append(u)
            stack.extend(v for v in adjacency[u] if v not in seen)
        if not 3 <= len(component) <= max_edges or any(len(adjacency[u]) != 2 for u in component):
            continue
        order = [component[0]]
        previous = -1
        while len(order) < len(component):
            candidates = [v for v in adjacency[order[-1]] if v != previous]
            nxt = candidates[0]
            if nxt == order[0]:
                break
            previous = order[-1]
            order.append(nxt)
        if len(order) != len(component):
            continue
        points = vertices[order]
        centered = points - points.mean(0)
        _, _, basis = np.linalg.svd(centered, full_matrices=False)
        if np.max(np.abs(centered @ basis[2])) > tolerance_factor * h:
            continue
        uv = centered @ basis[:2].T
        if np.max(np.linalg.norm(uv[:, None] - uv[None, :], axis=2)) > max_diameter_factor * h:
            continue
        try:
            hull = ConvexHull(uv)
            if len(hull.vertices) != len(order):
                continue
            tri = Delaunay(uv).simplices
        except QhullError:
            continue
        candidate = np.asarray(order)[tri]
        probes = np.concatenate(
            [
                vertices[candidate].mean(1),
                (vertices[candidate[:, 0]] + vertices[candidate[:, 1]]) / 2,
                (vertices[candidate[:, 1]] + vertices[candidate[:, 2]]) / 2,
                (vertices[candidate[:, 2]] + vertices[candidate[:, 0]]) / 2,
            ]
        )
        if tree.query(probes)[0].max() > 1.5 * h:
            continue
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
            if (
                np.dot(
                    np.cross(vertices[t[1]] - vertices[t[0]], vertices[t[2]] - vertices[t[0]]),
                    normal,
                )
                < 0
            ):
                t = t[[0, 2, 1]]
            additions.append(t)
        loops += 1
    if additions:
        out.triangles = o3d.utility.Vector3iVector(np.vstack([faces, additions]))
        out.remove_duplicated_triangles()
        out.compute_vertex_normals()
    return out, {
        "added_triangles": len(additions),
        "accepted_loops": loops,
        "warning": "Reparación experimental, no demuestra existencia de superficie",
    }
