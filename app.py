"""CloudLab: bounded-memory local explorer and precalculated gallery."""
from pathlib import Path
import json
import time
import numpy as np
import psutil
import plotly.graph_objects as go
import streamlit as st
from cloudlab.core import (load_cloud, save_cloud, crop, clean, spacing, estimate_normals,
                           segment, reconstruct, mesh_report, repair_planar_holes, write_json)
from cloudlab.safe_io import load_bounded, ply_header
from cloudlab.examples import facade

st.set_page_config(page_title="CloudLab", page_icon="◈", layout="wide")
st.markdown('''<style>
.block-container{padding-top:1.5rem;max-width:1600px}
h1{letter-spacing:-.06em;font-weight:750!important}
[data-testid="stMetric"]{background:rgba(110,145,175,.09);border:1px solid rgba(130,150,170,.18);border-radius:12px;padding:12px}
[data-testid="stSidebar"]{border-right:1px solid rgba(120,150,170,.2)}
div.stButton>button{border-radius:9px}
</style>''', unsafe_allow_html=True)
s=st.session_state
MAX_WORK=50000


def reset_results():
    for key in ('mesh','mesh_metrics','preview','repair_report'):
        s.pop(key,None)


def commit(cloud, undo=True):
    if len(cloud.xyz)>MAX_WORK:
        raise ValueError('El espacio de trabajo admite hasta 50 000 puntos. Reduce al cargar.')
    if undo and 'cloud' in s:
        s.previous=s.cloud  # ONE bounded state, not an ever-growing stack.
    else:
        s.pop('previous',None)
    s.cloud=cloud; reset_results()


def run(fn):
    try:
        with st.spinner('Procesando el conjunto de trabajo en CPU…'):
            start=time.perf_counter();fn();s.seconds=time.perf_counter()-start
        st.toast(f'Listo · {s.seconds:.2f} s')
    except Exception as exc:
        st.error(f'{type(exc).__name__}: {exc}')


gallery={p.parent.name:p.parent for p in sorted(Path('examples').glob('*/report.json'))}
titles={'fachada':'Fachada · ventanas y ruido','bunny':'Stanford Bunny · ruido',
        'esfera':'Esfera · superficie curva','esquina':'Esquina · dos planos',
        'cuadra_dense':'Tu cuadra · densa','cuadra_sparse':'Tu cuadra · dispersa'}


def open_example(name, processed=True):
    folder=gallery[name]
    commit(load_bounded(folder/('processed.ply' if processed else 'original.ply'),MAX_WORK),False)
    s.example=name
    if processed and (folder/'mesh.ply').exists():
        import open3d as o3d
        s.mesh=o3d.io.read_triangle_mesh(str(folder/'mesh.ply'))
        s.mesh_metrics=json.loads((folder/'report.json').read_text())['mesh']
    s.view='Malla' if processed else 'Color'


with st.sidebar:
    st.markdown('## ◈ CloudLab')
    st.caption('LABORATORIO DE NUBES · CPU')
    source=st.radio('Abrir', ['Ejemplos listos','Archivo propio'])
    if source=='Ejemplos listos':
        if gallery:
            name=st.selectbox('Colección',list(gallery),format_func=lambda x:titles.get(x,x))
            report=json.loads((gallery[name]/'report.json').read_text())
            st.caption(report['description'])
            c1,c2=st.columns(2)
            if c1.button('Ver resultado',type='primary',width='stretch'):
                run(lambda:open_example(name,True))
            if c2.button('Desde cero',width='stretch'):
                run(lambda:open_example(name,False))
        else:
            st.info('Genera la galería: python scripts/build_gallery.py --bunny')
    else:
        path=st.text_input('Ruta local', 'dense_preview_5M.ply')
        budget=st.select_slider('Puntos de trabajo',options=[10000,20000,30000,50000],value=30000)
        st.caption('El original no se carga completo en RAM. Muestreo estratificado reproducible durante la lectura PLY.')
        if st.button('Inspeccionar cabecera',width='stretch'):
            run(lambda:s.update(header=ply_header(Path(path).expanduser())))
        if 'header' in s:
            st.json(s.header,expanded=False)
        if st.button('Cargar de forma segura',type='primary',width='stretch'):
            def load():
                commit(load_bounded(path,budget),False);s.example=None;s.view='Color'
            run(load)
    st.divider()
    if st.button('Generar fachada nueva',width='stretch'):
        run(lambda:commit(facade(),False))
    if 'cloud' in s:
        if st.button('↶ Deshacer último cambio',disabled='previous' not in s,width='stretch'):
            previous=s.previous;s.pop('previous');s.cloud=previous;reset_results();st.rerun()
    st.caption('Un solo estado para deshacer · máximo 50k puntos activos · sin CUDA')
    st.caption('Memoria del proceso: %.0f MiB'%(psutil.Process().memory_info().rss/2**20))

st.title('Explora puntos. Construye superficies.')
st.caption('Abre un resultado precalculado para verlo al instante, o recorre las etapas con una nube pequeña y controlada.')
if 'cloud' not in s and gallery:
    default='fachada' if 'fachada' in gallery else next(iter(gallery))
    run(lambda:open_example(default,True))
if 'cloud' not in s:
    st.info('Selecciona una nube en la barra izquierda.');st.stop()

cloud=s.cloud
a,b,c,d=st.columns(4)
a.metric('Puntos activos',f'{len(cloud.xyz):,}')
b.metric('Normales','Calculadas' if 'normals' in cloud.attrs else 'Pendientes')
labels=cloud.attrs.get('segment',np.array([-1]));count=len(np.unique(labels[labels>=0]))
c.metric('Regiones',count)
d.metric('Triángulos',f'{len(s.mesh.triangles):,}' if 'mesh' in s else '—')
stage=st.radio('Flujo de trabajo',['Explorar','1 · Recortar','2 · Limpiar','3 · Normales','4 · Segmentar','5 · Reconstruir','Exportar'],horizontal=True,label_visibility='collapsed')
left,right=st.columns([3,1.15],gap='large')

with right:
    st.subheader(stage)
    if stage=='Explorar':
        st.markdown('**Resultados sin esperas**\n\nLa galería ya contiene normales, segmentos y malla. Cambia la vista para comparar representaciones.')
        st.info('Para modificar parámetros, elige una etapa superior. Los cambios invalidan la malla anterior.')
        if s.get('example') in gallery:
            with st.expander('Datos del ejemplo'):
                st.json(json.loads((gallery[s.example]/'report.json').read_text()),expanded=False)
    elif stage=='1 · Recortar':
        st.caption('Selecciona una región del conjunto de trabajo. La carga inicial es una muestra, no el archivo completo.')
        with st.form('crop'):
            block=None
            if 'block_id' in cloud.attrs:
                value=st.selectbox('Bloque',['Todos']+np.unique(cloud.attrs['block_id']).tolist())
                block=None if value=='Todos' else value
            lo=cloud.xyz.min(0);hi=cloud.xyz.max(0);lower=[];upper=[]
            for j,axis in enumerate('XYZ'):
                cols=st.columns(2)
                lower.append(cols[0].number_input(f'{axis} mín.',value=float(lo[j]),format='%.4f'))
                upper.append(cols[1].number_input(f'{axis} máx.',value=float(hi[j]),format='%.4f'))
            if st.form_submit_button('Aplicar recorte',type='primary',width='stretch'):
                def recut():
                    out=crop(s.cloud,lower,upper,block)
                    if len(out.xyz)<4:raise ValueError('Recorte demasiado pequeño')
                    commit(out)
                run(recut)
    elif stage=='2 · Limpiar':
        st.caption('Primero previsualiza. Rojo indica atípicos; no se eliminan del original.')
        with st.form('clean'):
            voxel=st.number_input('Vóxel (0 = sin reducir)',min_value=0.,value=0.,format='%.5f')
            std=st.slider('Tolerancia estadística σ',1.,5.,2.5,.1)
            neighbors=st.slider('Vecinos',5,60,20)
            if st.form_submit_button('Previsualizar',width='stretch'):
                def preview():
                    s.preview=clean(s.cloud,voxel=voxel,neighbors=neighbors,std_ratio=std);s.view='Atípicos'
                run(preview)
        if 'preview' in s:
            st.json(s.preview[2])
            if st.button('Confirmar limpieza',type='primary',width='stretch'):
                prepared=s.preview[0];commit(prepared);s.view='Color'
    elif stage=='3 · Normales':
        st.caption('PCA propia. Los autovectores estiman orientación local; no garantizan el exterior físico.')
        with st.form('normals'):
            k=st.slider('Vecinos PCA',5,80,30)
            radius=st.number_input('Radio máximo (0 = automático k-NN)',min_value=0.,value=0.,format='%.5f')
            if st.form_submit_button('Estimar normales',type='primary',width='stretch'):
                def normals():
                    commit(estimate_normals(s.cloud,k,radius));s.view='Normales'
                run(normals)
    elif stage=='4 · Segmentar':
        st.caption('Geometría agrupa superficies. El color aporta apariencia, no categorías semánticas.')
        with st.form('segment'):
            method=st.selectbox('Método',['regions','graph'],format_func=lambda x:'Regiones geométricas' if x=='regions' else 'Grafo: geometría + color')
            angle=st.slider('Ángulo máximo °',5.,60.,20.)
            minimum=st.number_input('Puntos mínimos por región',5,10000,40)
            weight=st.slider('Influencia del color (grafo)',0.,3.,.5,.1)
            scale=st.number_input('Escala del grafo',.01,100.,2.,.1)
            if st.form_submit_button('Segmentar',type='primary',width='stretch',disabled='normals' not in cloud.attrs):
                def segmentation():
                    commit(segment(s.cloud,method,angle=angle,min_size=minimum,color_weight=weight,scale=scale));s.view='Segmentos'
                run(segmentation)
        if 'normals' not in cloud.attrs:st.warning('Calcula normales en la etapa 3.')
    elif stage=='5 · Reconstruir':
        st.caption('Ball Pivoting. Los radios se multiplican por el espaciado mediano del conjunto activo.')
        with st.form('bpa'):
            radii=st.text_input('Radios relativos','1.5, 2.5, 4')
            if st.form_submit_button('Reconstruir Ball Pivoting',type='primary',width='stretch',disabled='normals' not in cloud.attrs):
                def bpa():
                    s.mesh=reconstruct(s.cloud,[float(x) for x in radii.split(',')]);s.mesh_metrics=mesh_report(s.mesh);s.view='Malla'
                run(bpa)
        if 'normals' not in cloud.attrs:st.warning('Calcula normales en la etapa 3.')
        if 'mesh' in s:
            with st.expander('Reparación experimental'):
                st.warning('Delaunay puede inventar superficie. Solo pequeños contornos convexos y planos; no garantiza una mejora.')
                if st.button('Intentar Delaunay local'):
                    def repair():
                        s.mesh,s.repair_report=repair_planar_holes(s.mesh,s.cloud);s.mesh_metrics=mesh_report(s.mesh)
                    run(repair)
                if 'repair_report' in s:st.json(s.repair_report)
    else:
        folder=st.text_input('Carpeta de salida','outputs/interactive')
        if st.button('Guardar nube, malla y parámetros',type='primary',width='stretch'):
            def export():
                import open3d as o3d
                dest=Path(folder);dest.mkdir(parents=True,exist_ok=True)
                save_cloud(s.cloud,dest/'processed.ply')
                if 'mesh' in s:o3d.io.write_triangle_mesh(str(dest/'mesh.ply'),s.mesh)
                write_json(dest/'session.json',{'history':s.cloud.history,'mesh':s.get('mesh_metrics')})
                st.success(str(dest.resolve()))
            run(export)
    if 'mesh_metrics' in s:
        with st.expander('Diagnóstico de malla'):
            st.json(s.mesh_metrics)

with left:
    options=['Color','Altura','Normales','Segmentos','Atípicos','Malla']
    if s.get('view') not in options:s.view='Color'
    view=st.selectbox('Representación',options,key='view')
    cloud=s.cloud
    render_cloud=s.preview[0] if view=='Atípicos' and 'preview' in s else cloud
    limit=12000
    ids=np.random.default_rng(42).choice(len(render_cloud.xyz),min(limit,len(render_cloud.xyz)),replace=False)
    xyz=render_cloud.xyz[ids]
    # Center browser coordinates too: avoid WebGL precision loss for georeferenced data.
    origin=render_cloud.xyz.mean(0);points=xyz-origin
    fig=go.Figure()
    if view=='Malla' and 'mesh' in s and len(s.mesh.triangles):
        vertices=np.asarray(s.mesh.vertices)-origin;tri=np.asarray(s.mesh.triangles)
        fig.add_trace(go.Mesh3d(x=vertices[:,0],y=vertices[:,1],z=vertices[:,2],i=tri[:,0],j=tri[:,1],k=tri[:,2],color='#81c9be',flatshading=True,lighting=dict(ambient=.55,diffuse=.8)))
    else:
        if view=='Malla':st.info('Todavía no hay malla. Abre un resultado precalculado o ejecuta la etapa 5.')
        color=points[:,2]
        if view=='Color' and 'rgb' in render_cloud.attrs:
            color=[f'rgb({r},{g},{b})' for r,g,b in render_cloud.attrs['rgb'][ids].astype(int)]
        elif view=='Segmentos' and 'segment' in render_cloud.attrs:
            labels=render_cloud.attrs['segment'][ids]
            colors=np.random.default_rng(12).integers(45,240,(max(1,int(labels.max())+1),3))
            color=['rgb(100,110,120)' if label<0 else f'rgb({",".join(map(str,colors[label]))})' for label in labels]
        elif view=='Normales' and 'normal_confidence' in render_cloud.attrs:
            color=render_cloud.attrs['normal_confidence'][ids]
        fig.add_trace(go.Scatter3d(x=points[:,0],y=points[:,1],z=points[:,2],mode='markers',marker=dict(size=2,color=color,colorscale='Viridis'),name='Puntos'))
        if view=='Normales' and 'normals' in render_cloud.attrs:
            take=ids[:250];a=render_cloud.xyz[take]-origin
            length=np.linalg.norm(np.ptp(points,axis=0))*.02
            b=a+render_cloud.attrs['normals'][take]*length
            lines=np.stack([a,b,np.full_like(a,np.nan)],axis=1).reshape(-1,3)
            fig.add_trace(go.Scatter3d(x=lines[:,0],y=lines[:,1],z=lines[:,2],mode='lines',line=dict(color='#ffbf69',width=3),name='Normales'))
        if view=='Atípicos' and 'preview' in s:
            rejected=s.preview[1].xyz[:limit]-origin
            fig.add_trace(go.Scatter3d(x=rejected[:,0],y=rejected[:,1],z=rejected[:,2],mode='markers',marker=dict(size=3,color='#ff6666'),name='Atípicos'))
    fig.update_layout(height=650,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor='rgba(0,0,0,0)',
                      scene=dict(aspectmode='data',xaxis_title='X local',yaxis_title='Y local',zaxis_title='Z local'),
                      uirevision=str(s.cloud.history[0]))
    st.plotly_chart(fig,width='stretch',config={'displaylogo':False})
    st.caption(f'Arrastra para rotar · rueda para acercar · dibujo limitado a {limit:,} puntos · coordenadas relativas al centro de la nube')
