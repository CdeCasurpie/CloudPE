import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from cloudlab.core import synthetic, save_cloud


def execute(folder, request):
    folder.mkdir()
    path=folder/'request.json';path.write_text(json.dumps(request))
    subprocess.run([sys.executable,'-m','cloudlab.cloudpe_worker',str(path)],check=True,capture_output=True)
    return json.loads((folder/'result.json').read_text())


def test_isolated_worker_buffers_and_history(tmp_path):
    path=tmp_path/'source.ply';save_cloud(synthetic('plane',500,0,0),path)
    first=tmp_path/'first';meta=execute(first,{'operation':'open','path':str(path)})
    data=np.fromfile(first/'points.bin',dtype='<f4').reshape(-1,11)
    assert len(data)==meta['points']==500
    assert np.isfinite(data).all()
    assert np.max(np.linalg.norm(data[:,:3],axis=1))<=1.1
    second=tmp_path/'second'
    meta2=execute(second,{'operation':'normals','source':str(first),'params':{'k':20}})
    assert 'normals' in meta2['attributes']
    assert meta2['history'][0]['operation']=='bounded_load'
    assert meta2['history'][-1]['operation']=='PCA normals'
