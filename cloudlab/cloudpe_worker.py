"""Isolated CloudPE jobs. Intermediates live on disk, never in the web process."""
import json
from pathlib import Path
import sys
import traceback
import numpy as np
from .core import (load_cloud, save_cloud, clean, crop, estimate_normals, segment,
                   reconstruct, mesh_report, repair_planar_holes, write_json, reconstruction_diagnostics)
from .safe_io import load_bounded


def package(folder, cloud, mesh=None, extra=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    save_cloud(cloud,folder/'cloud.ply')
    origin=cloud.xyz.mean(0);scale=max(float(np.linalg.norm(np.ptp(cloud.xyz,axis=0)))/2,1e-8)
    n=len(cloud.xyz);data=np.zeros((n,11),dtype='<f4')
    data[:,:3]=(cloud.xyz-origin)/scale
    data[:,3:6]=cloud.attrs.get('rgb',np.tile([220,230,237],(n,1)))/255.
    data[:,6:9]=cloud.attrs.get('normals',np.zeros((n,3)))
    data[:,9]=cloud.attrs.get('segment',np.full(n,-1))
    data[:,10]=cloud.attrs.get('normal_confidence',np.zeros(n))
    # Shuffle just the presentation buffer so progressive draw reveals the whole scene.
    data=data[np.random.default_rng(42).permutation(n)]
    data.tofile(folder/'points.bin')
    meta={'points':n,'origin':origin.tolist(),'scale':scale,'attributes':list(cloud.attrs),
          'history':cloud.history,'triangles':0,'diagnostics':reconstruction_diagnostics(cloud),**(extra or {})}
    if mesh is not None and len(mesh.triangles):
        import open3d as o3d
        mesh.compute_vertex_normals()
        o3d.io.write_triangle_mesh(str(folder/'mesh.ply'),mesh)
        v=np.column_stack([(np.asarray(mesh.vertices)-origin)/scale,np.asarray(mesh.vertex_normals)]).astype('<f4')
        t=np.asarray(mesh.triangles,dtype='<u4')
        with (folder/'mesh.bin').open('wb') as f:
            np.asarray([len(v),len(t)],dtype='<u4').tofile(f);v.tofile(f);t.tofile(f)
        meta.update(triangles=len(t),mesh_report=mesh_report(mesh))
    write_json(folder/'result.json',meta)
    return meta


def main():
    request=Path(sys.argv[1]);r=json.loads(request.read_text());folder=request.parent
    try:
        op=r['operation'];params=r.get('params',{});mesh=None;extra={}
        if op=='open':
            cloud=load_bounded(r['path'],min(50000,max(1000,int(params.get('budget',30000)))))
            if r.get('history_report'):
                previous=json.loads(Path(r['history_report']).read_text())
                cloud.history=previous.get('history',[])+cloud.history
                if previous.get('bpa_config'):extra['bpa_config']=previous['bpa_config']
            if r.get('mesh'):
                import open3d as o3d
                mesh=o3d.io.read_triangle_mesh(r['mesh'])
            extra['title']=r.get('title',Path(r['path']).stem)
            extra['view_up']=r.get('view_up','y+')
        else:
            cloud=load_cloud(Path(r['source'])/'cloud.ply')
            previous=json.loads((Path(r['source'])/'result.json').read_text())
            cloud.history=previous.get('history',cloud.history)
            extra['view_up']=previous.get('view_up','y+')
            if len(cloud.xyz)>50000:raise ValueError('Límite de seguridad: 50k puntos')
            if op=='clean':
                cloud,removed,report=clean(cloud,voxel=float(params.get('voxel',0)),std_ratio=float(params.get('std',2.5)))
                extra['cleaning']=report
            elif op=='normals':cloud=estimate_normals(cloud,k=int(params.get('k',30)),max_radius=float(params.get('normal_radius',0)),orient=bool(params.get('orient',True)))
            elif op=='segment':cloud=segment(cloud,method=params.get('method','regions'),angle=float(params.get('angle',20)),color_weight=float(params.get('color',.5)),scale=float(params.get('scale',2)))
            elif op=='bpa':
                if params.get('recompute_normals',False):
                    cloud=estimate_normals(cloud,k=int(params.get('k',30)),max_radius=float(params.get('normal_radius',0)))
                radii=params.get('radii',[2.5,4,6]);mode=params.get('radius_mode','median')
                mesh=reconstruct(cloud,radii,radius_mode=mode)
                normals=cloud.attrs['normals'];lengths=np.linalg.norm(normals,axis=1)
                valid=cloud.attrs.get('normal_valid',np.ones(len(cloud.xyz),bool)).astype(bool)&np.isfinite(lengths)&(lengths>1e-12)
                h=1. if mode=='absolute' else reconstruction_diagnostics(cloud.select(valid))['spacing'][mode]
                extra['bpa_config']={'radii':radii,'radius_mode':mode,'effective_radii':[h*r for r in sorted(radii)],'recompute_normals':bool(params.get('recompute_normals',False)),'k':int(params.get('k',30))}
                cloud.history.append({'operation':'BPA',**extra['bpa_config']})
            else:raise ValueError('Operación desconocida')
        if len(cloud.xyz)<4:raise ValueError('No quedan suficientes puntos')
        package(folder,cloud,mesh,extra)
    except Exception:
        (folder/'error.txt').write_text(traceback.format_exc());sys.exit(1)


if __name__=='__main__':main()
