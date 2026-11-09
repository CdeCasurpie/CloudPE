import numpy as np
import pytest
from plyfile import PlyData, PlyElement
from cloudlab.core import synthetic, save_cloud
from cloudlab.safe_io import load_bounded, ply_header


def test_bounded_scalar(tmp_path):
    original = synthetic(n=10000, outliers=0)
    path = tmp_path/'big.ply'; save_cloud(original,path)
    cloud = load_bounded(path,1000)
    assert len(cloud.xyz) == 1000
    np.testing.assert_allclose(cloud.xyz, original.xyz[cloud.attrs['source_index'].astype(int)])
    assert cloud.history[0]['original_points'] == 10000


@pytest.mark.parametrize('text',[False,True])
def test_variable_list_ply(tmp_path,text):
    records = np.empty(1000,dtype=[('x','f4'),('y','f4'),('z','f4'),('view_indices','O'),('view_weights','O')])
    records['x'] = np.arange(1000);records['y']=1;records['z']=2
    for i in range(1000):
        records['view_indices'][i]=np.arange(i%5,dtype=np.uint32)
        records['view_weights'][i]=np.ones(i%5,dtype=np.float32)
    path=tmp_path/'lists.ply'
    PlyData([PlyElement.describe(records,'vertex')],text=text).write(path)
    cloud=load_bounded(path,100)
    assert len(cloud.xyz)==100
    np.testing.assert_array_equal(cloud.xyz[:,0],cloud.attrs['source_index'])
    assert 'view_indices' not in cloud.attrs


def test_invalid_budget(tmp_path):
    with pytest.raises(ValueError):
        load_bounded(tmp_path/'unused.ply',5000000)
