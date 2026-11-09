import argparse
from pathlib import Path
import time
import numpy as np
import psutil
from .core import (load_cloud, save_cloud, inspect_cloud, synthetic, crop, clean,
                   spacing, estimate_normals, segment, reconstruct, mesh_report,
                   repair_planar_holes, write_json)
from .safe_io import load_bounded, ply_header


def main():
    parser = argparse.ArgumentParser(description="CloudLab CPU")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inspect"); p.add_argument("input")
    p = sub.add_parser("generate")
    p.add_argument("output"); p.add_argument("--kind", choices=["corner", "plane", "sphere"], default="corner")
    p.add_argument("--points", type=int, default=12000); p.add_argument("--noise", type=float, default=.002)
    p = sub.add_parser("run")
    p.add_argument("input"); p.add_argument("--output", default="outputs/run")
    p.add_argument("--block", type=int); p.add_argument("--lower", nargs=3, type=float); p.add_argument("--upper", nargs=3, type=float)
    p.add_argument("--max-points", type=int, default=50000)
    p.add_argument("--allow-full-memory", action="store_true", help="Autoriza lectura completa en RAM; puede agotar memoria")
    p.add_argument("--voxel", type=float, default=0.)
    p.add_argument("--std-ratio", type=float, default=2.5)
    p.add_argument("--k", type=int, default=30)
    p.add_argument("--method", choices=["regions", "graph"], default="regions")
    p.add_argument("--angle", type=float, default=20.)
    p.add_argument("--color-weight", type=float, default=.5)
    p.add_argument("--scale", type=float, default=.4)
    p.add_argument("--min-size", type=int, default=40)
    p.add_argument("--radii", nargs="+", type=float, default=[2.5, 4., 6.])
    p.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    if args.command == "inspect":
        import json
        data = {"sample_statistics": inspect_cloud(load_bounded(args.input, 30000))}
        if Path(args.input).suffix.lower() == '.ply':
            data['header'] = ply_header(args.input)
        print(json.dumps(data, indent=2)); return
    if args.command == "generate":
        save_cloud(synthetic(args.kind, args.points, args.noise), args.output)
        print(args.output); return
    import open3d as o3d
    started = time.perf_counter(); timings = {}; out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    if args.allow_full_memory:
        cloud = load_cloud(args.input)
    else:
        if not 100 <= args.max_points <= 100000:
            raise ValueError("Modo seguro: --max-points entre 100 y 100000. Lectura completa exige --allow-full-memory explícito")
        cloud = load_bounded(args.input, args.max_points)
    cloud = crop(cloud, args.lower, args.upper, args.block)
    if len(cloud.xyz) < 4:
        raise ValueError("El recorte contiene menos de cuatro puntos")
    report = {"input": inspect_cloud(cloud), "parameters": vars(args), "timings_seconds": timings}
    # Optional deterministic development cap, explicitly recorded; prefer spatial crops for final evaluation.
    if args.max_points > 0 and len(cloud.xyz) > args.max_points:
        ids = np.sort(np.random.default_rng(42).choice(len(cloud.xyz), args.max_points, replace=False))
        cloud = cloud.select(ids, "submuestra aleatoria de desarrollo")
    t = time.perf_counter()
    cloud, removed, cleaning = clean(cloud, voxel=args.voxel, std_ratio=args.std_ratio)
    timings["clean"] = time.perf_counter() - t; report["cleaning"] = cleaning
    save_cloud(removed, out / "outliers.ply")
    # Validation points are excluded from estimation, segmentation and reconstruction.
    if len(cloud.xyz) < 30:
        raise ValueError("Quedaron muy pocos puntos después de limpiar")
    validation_mask = np.random.default_rng(7).random(len(cloud.xyz)) < .1
    validation = cloud.select(validation_mask, "validación 10%")
    cloud = cloud.select(~validation_mask, "entrenamiento geométrico 90%")
    save_cloud(validation, out / "validation.ply")
    t = time.perf_counter(); cloud = estimate_normals(cloud, args.k)
    timings["normals"] = time.perf_counter() - t
    gt_keys = ["gt_normal_x", "gt_normal_y", "gt_normal_z"]
    if all(k in cloud.attrs for k in gt_keys):
        gt = np.column_stack([cloud.attrs[k] for k in gt_keys])
        valid = (np.linalg.norm(gt, axis=1) > .5) & cloud.attrs["normal_valid"].astype(bool)
        errors = np.rad2deg(np.arccos(np.clip(np.abs(np.einsum("ij,ij->i", gt[valid], cloud.attrs["normals"][valid])), 0, 1)))
        report["normal_unsigned_error_deg_p50_p95"] = np.percentile(errors, [50, 95]).tolist()
    t = time.perf_counter()
    cloud = segment(cloud, args.method, angle=args.angle, min_size=args.min_size,
                    color_weight=args.color_weight, scale=args.scale)
    timings["segmentation"] = time.perf_counter() - t
    labels, counts = np.unique(cloud.attrs["segment"], return_counts=True)
    report["segments"] = {str(k): int(v) for k, v in zip(labels, counts)}
    save_cloud(cloud, out / "processed.ply")
    t = time.perf_counter(); mesh = reconstruct(cloud, args.radii)
    timings["BPA"] = time.perf_counter() - t
    o3d.io.write_triangle_mesh(str(out / "mesh_bpa.ply"), mesh)
    report["mesh"] = mesh_report(mesh, validation)
    if args.repair:
        repaired, repair = repair_planar_holes(mesh, cloud)
        o3d.io.write_triangle_mesh(str(out / "mesh_repaired.ply"), repaired)
        report["repair"] = repair; report["repaired_mesh"] = mesh_report(repaired, validation)
    report["history"] = cloud.history
    report["elapsed_seconds"] = time.perf_counter() - started
    report["rss_at_end_MiB"] = psutil.Process().memory_info().rss / 2**20
    import resource
    report["peak_rss_MiB_linux"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    write_json(out / "report.json", report)
    print(f"Resultados: {out.resolve()} | triángulos: {len(mesh.triangles)} | {report['elapsed_seconds']:.1f} s")


if __name__ == "__main__":
    main()
