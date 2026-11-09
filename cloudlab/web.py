"""Local API and static CloudPE frontend. One isolated calculation at a time."""
from pathlib import Path
import json
import os
import subprocess
import sys
import uuid
import threading
import math
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/'.cloudpe';STORE.mkdir(exist_ok=True)
app=FastAPI(title='CloudPE',docs_url='/api/docs')
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
jobs={};lock=threading.Lock()
TITLES={'bunny':'Stanford Bunny','fachada':'Fachada / 03 ventanas','esfera':'Esfera','esquina':'Encuentro de planos','cuadra_dense':'Cuadra / Densa','cuadra_sparse':'Cuadra / Sparse'}


@app.middleware('http')
async def local_only(request:Request,call_next):
    # Reject cross-origin browser writes to this local file-access application.
    origin=request.headers.get('origin')
    if request.method=='POST' and origin and origin!=str(request.base_url).rstrip('/'):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'Origen no permitido'},status_code=403)
    return await call_next(request)


def directory(identifier):
    if not isinstance(identifier,str) or len(identifier)!=32 or any(c not in '0123456789abcdef' for c in identifier):
        raise HTTPException(404,'Proyecto no encontrado')
    folder=STORE/identifier
    if not folder.exists():raise HTTPException(404,'Proyecto no encontrado')
    return folder


@app.get('/api/examples')
def examples():
    return [{'id':p.parent.name,'title':TITLES.get(p.parent.name,p.parent.name),
             **json.loads(p.read_text())} for p in sorted((ROOT/'examples').glob('*/report.json'))]


@app.post('/api/jobs')
def start(body:dict):
    with lock:
        if any(j['process'].poll() is None for j in jobs.values()):
            raise HTTPException(409,'Un cálculo sigue activo. Espera o cancélalo.')
        op=body.get('operation');params=body.get('params',{})
        if not isinstance(params,dict):raise HTTPException(400,'Parámetros inválidos')
        bounds={'budget':(1000,50000),'k':(3,80),'std':(.1,10),'voxel':(0,1e9),'angle':(1,80),'color':(0,5),'scale':(.01,100),'normal_radius':(0,1e9)}
        for key,(lo,hi) in bounds.items():
            if key in params:
                try:value=float(params[key])
                except (TypeError,ValueError):raise HTTPException(400,f'{key}: valor no numérico')
                if not math.isfinite(value) or not lo<=value<=hi:raise HTTPException(400,f'{key}: fuera de rango')
        if 'radii' in params:
            radii=params['radii']
            if not isinstance(radii,list) or not 1<=len(radii)<=6 or any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<v<=100 for v in radii):
                raise HTTPException(400,'Radios inválidos')
        if params.get('radius_mode','median') not in ('median','p90','absolute'):
            raise HTTPException(400,'Escala de radios inválida')
        for key in ('orient','recompute_normals'):
            if key in params and not isinstance(params[key],bool):raise HTTPException(400,f'{key}: se requiere booleano')
        request={'operation':op,'params':params}
        if op=='open':
            example=body.get('example')
            if example:
                if example not in TITLES:raise HTTPException(400,'Ejemplo desconocido')
                folder=ROOT/'examples'/example;processed=bool(body.get('processed',True))
                request.update(path=str(folder/('processed.ply' if processed else 'original.ply')),title=TITLES[example])
                request['view_up']='y-' if example in ('cuadra_dense','cuadra_sparse') else ('z+' if example=='fachada' else 'y+')
                if processed:
                    request['mesh']=str(folder/'mesh.ply')
                    request['history_report']=str(folder/'report.json')
            else:
                path=Path(body.get('path','')).expanduser().resolve()
                if not path.is_file() or path.suffix.lower() not in ('.ply','.pcd','.xyz','.txt'):
                    raise HTTPException(400,'Ruta o formato no válido')
                request['path']=str(path)
        elif op in ('clean','normals','segment','bpa'):
            request['source']=str(directory(body.get('source','')))
        else:raise HTTPException(400,'Operación no válida')
        identifier=uuid.uuid4().hex;folder=STORE/identifier;folder.mkdir()
        (folder/'request.json').write_text(json.dumps(request))
        env={**os.environ,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'}
        log=(folder/'worker.log').open('w')
        try:
            process=subprocess.Popen([sys.executable,'-m','cloudlab.cloudpe_worker',str(folder/'request.json')],cwd=ROOT,env=env,stdout=log,stderr=log)
        finally:log.close()
        jobs[identifier]={'process':process}
        return {'id':identifier}


@app.get('/api/jobs/{identifier}')
def status(identifier:str):
    folder=directory(identifier)
    if (folder/'result.json').exists():return {'state':'complete','id':identifier,**json.loads((folder/'result.json').read_text())}
    job=jobs.get(identifier)
    if job and job['process'].poll() is None:return {'state':'running','id':identifier}
    error=(folder/'error.txt').read_text() if (folder/'error.txt').exists() else 'Trabajo cancelado o proceso finalizado inesperadamente'
    return {'state':'error','error':error.splitlines()[-1],'id':identifier}


@app.post('/api/jobs/{identifier}/cancel')
def cancel(identifier:str):
    directory(identifier);job=jobs.get(identifier)
    if job and job['process'].poll() is None:
        job['process'].kill();job['process'].wait()
    return {'state':'cancelled'}


@app.get('/api/projects/{identifier}/{asset}')
def asset(identifier:str,asset:str):
    if asset not in ('points.bin','mesh.bin','cloud.ply','mesh.ply','result.json'):raise HTTPException(404)
    path=directory(identifier)/asset
    if not path.exists():raise HTTPException(404)
    return FileResponse(path,filename=asset)


@app.get('/api/health')
def health():return {'status':'ok'}


DIST=ROOT/'frontend'/'dist'
if DIST.exists():app.mount('/',StaticFiles(directory=DIST,html=True),name='frontend')
