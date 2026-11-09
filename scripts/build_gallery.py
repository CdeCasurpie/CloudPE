"""Build small on-disk examples; no processing needed when opening the gallery."""
from pathlib import Path
import argparse
import numpy as np
from cloudlab.core import (synthetic, save_cloud, clean, estimate_normals, segment,
                           reconstruct, mesh_report, write_json, Cloud)
from cloudlab.examples import facade
from cloudlab.safe_io import load_bounded


def build(name, cloud, description):
    import open3d as o3d
    folder = Path('examples') / name; folder.mkdir(parents=True, exist_ok=True)
    save_cloud(cloud, folder/'original.ply')
    prepared, _, cleaning = clean(cloud)
    prepared = estimate_normals(prepared)
    prepared = segment(prepared, min_size=50)
    save_cloud(prepared, folder/'processed.ply')
    mesh = reconstruct(prepared)
    o3d.io.write_triangle_mesh(str(folder/'mesh.ply'),mesh)
    write_json(folder/'report.json', {'name':name,'description':description,
               'cleaning':cleaning,'mesh':mesh_report(mesh,prepared), 'history':prepared.history})
    print(name,len(prepared.xyz),len(mesh.triangles),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bunny',action='store_true')
    parser.add_argument('--user-data-dir',type=Path,help='Carpeta opcional con cuadra-025_0-10s_dense/sparse.ply')
    args=parser.parse_args()
    build('fachada',facade(), 'Fachada sintética con tres ventanas retranqueadas, ruido gaussiano y 1 % de puntos espurios. No es una simulación física de LiDAR.')
    build('esfera',synthetic('sphere',15000,.003), 'Superficie curva sintética con ruido y puntos atípicos; útil para inspeccionar BPA, no segmentación planar.')
    build('esquina',synthetic('corner',12000,.002), 'Dos superficies perpendiculares: normales PCA y segmentación geométrica.')
    for kind in ['dense','sparse']:
        path=args.user_data_dir/f'cuadra-025_0-10s_{kind}.ply' if args.user_data_dir else None
        if path is not None and path.exists():
            build(f'cuadra_{kind}',load_bounded(path,25000),f'Nube fotogramétrica del usuario ({kind}), hasta 25k puntos, precalculada sin alterar el original.')
    if args.bunny:
        import open3d as o3d
        data=o3d.data.BunnyMesh(data_root=str(Path('examples/.downloads').resolve()))
        mesh=o3d.io.read_triangle_mesh(data.path)
        o3d.utility.random.seed(42)
        pc=mesh.sample_points_uniformly(15000)
        xyz=np.asarray(pc.points).copy();h=np.linalg.norm(np.ptp(xyz,axis=0))
        xyz+=np.random.default_rng(42).normal(0,h*.001,xyz.shape)
        cloud=Cloud(xyz,history=[{'operation':'sample_bunny','source':'Open3D BunnyMesh / Stanford 3D Scanning Repository','noise_sigma':h*.001}])
        build('bunny',cloud,'Stanford Bunny obtenido mediante Open3D: 15k muestras de una malla con ruido gaussiano. No es una captura LiDAR ni COLMAP.')


if __name__=='__main__':main()
