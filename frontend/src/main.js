import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import './style.css';
import './advanced.css';
import '@fontsource/dm-sans/400.css';
import '@fontsource/dm-sans/500.css';
import '@fontsource/dm-sans/600.css';
import '@fontsource/space-grotesk/400.css';
import '@fontsource/space-grotesk/500.css';

const $=s=>document.querySelector(s);
const icons={cube:'◇',points:'⠿',clean:'◌',normals:'↗',regions:'▦',mesh:'△',folder:'⊞',fit:'⌖',play:'▶',pause:'Ⅱ',arrow:'↗',close:'×'};
const stages=[['open','Entrada','Un conjunto de posibilidades.'],['clean','Limpieza','Conserva la superficie. Quita el ruido.'],['normals','Normales','Encuentra la orientación de cada punto.'],['segment','Segmentación','Dale estructura a la geometría.'],['bpa','Superficie','De puntos a una superficie tangible.']];
const state={id:null,meta:null,stage:0,mode:'mono',busy:false,job:null,mesh:null,points:null,normals:null,reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,loadTime:-100,replay:false,replayProgress:1,examples:[],title:'Sin título',replaySpeed:1};
state.viewUp='y+';state.smooth=true;state.showEdges=false;state.edges=null;
$('#app').innerHTML=`
<div id="viewport" aria-label="Visor 3D interactivo"></div><div class="vignette"></div>
<div class="brand floating"><button id="home" aria-label="Abrir galería"><span class="brand-mark">✳</span> Cloud<span class="pe">PE</span><small>POINT CLOUD ATELIER</small></button></div>
<div class="top-right floating"><span class="live-dot"></span> LOCAL / CPU <button id="motion" title="Reducir movimiento" aria-label="Alternar animaciones">◐</button></div>
<nav class="tools glass floating"><button id="gallery-button" title="Galería" aria-label="Galería">⊞</button><span></span><button id="fit" title="Centrar nube" aria-label="Centrar nube">⌖</button><button id="turn" title="Rotación suave" aria-label="Rotación suave">↻</button><button id="screenshot" title="Capturar vista" aria-label="Capturar vista">▣</button></nav>
<aside id="panel" class="glass floating"><div class="panel-head"><span class="eyebrow">ESPACIO DE TRABAJO</span><button id="collapse" aria-label="Ocultar controles">−</button></div><h2 id="project-name">Tu próxima superficie.</h2><div class="step-list"></div><div id="stage-body"></div><div class="panel-footer"><span>ORIGINALES INTACTOS</span><span>↗</span></div></aside>
<button id="expand" class="glass floating hidden" aria-label="Mostrar controles">☷</button>
<div class="bottom-left floating"><div class="status"><i></i><span id="status-label">Elige un ejemplo para empezar</span></div><div class="statistics"><div><strong id="point-count">—</strong><span>PUNTOS</span></div><div><strong id="face-count">—</strong><span>TRIÁNGULOS</span></div></div><p id="hint">Arrastra para explorar · rueda para acercar</p></div>
<div id="viewbar" class="glass floating"><button data-mode="mono" class="active">Puntos</button><button data-mode="rgb">Color</button><button data-mode="normals">Normales</button><button data-mode="segments">Regiones</button><button data-mode="mesh">Malla</button></div>
<div id="replaybar" class="glass floating hidden"><button id="replay-toggle" aria-label="Reproducir animación">▶</button><input id="replay-progress" aria-label="Progreso de reproducción" type="range" min="0" max="1" step=".001" value="0"><button id="replay-speed">1×</button><small>REPRODUCCIÓN VISUAL · NO TRAZADO INTERNO BPA</small></div>
<div id="loading" class="glass floating hidden" role="status" aria-live="polite"><div class="orbit-loader"><i></i><i></i><i></i></div><div><span class="eyebrow" id="load-kicker">PREPARANDO</span><h3 id="load-title">Encontrando la forma.</h3><p id="load-detail">Trabajo aislado en CPU. Tu original permanece intacto.</p><div class="load-track"><span></span></div></div><button id="cancel">Cancelar</button></div>
<div id="toast" role="status" class="glass floating"></div>
<div id="welcome"><div class="welcome-shell"><div class="welcome-intro"><span class="eyebrow"><i class="live-dot"></i> UN LABORATORIO, INFINITAS FORMAS</span><h1>La forma<br>entre los <em>puntos.</em></h1><p>Explora, limpia y reconstruye.<br>Geometría que puedes tocar, paso a paso.</p><div class="welcome-note"><span>01 — 06</span> Colección de estudio / CPU</div></div><div class="collection"><div class="collection-head"><span class="eyebrow">ELIGE TU PUNTO DE PARTIDA</span><button id="close-welcome" aria-label="Cerrar galería">×</button></div><div id="cards"></div><div class="file-entry"><span>¿Tienes tu propia nube?</span><button id="open-local">Abrir archivo local ↗</button></div></div></div><span class="welcome-bottom">CLOUDPE — GEOMETRÍA EN SU FORMA MÁS SIMPLE</span></div>
<div id="file-modal" class="modal hidden"><div class="glass"><button id="file-close" aria-label="Cerrar">×</button><span class="eyebrow">ARCHIVO LOCAL</span><h2>Trae tu propia geometría.</h2><p>Lectura segura: hasta 50k puntos. La nube original nunca se modifica.</p><label>Ruta del archivo<input id="file-path" placeholder="/home/usuario/nube.ply"></label><label>Conjunto de trabajo<select id="budget"><option value="10000">10 000 · ligero</option><option value="30000" selected>30 000 · equilibrado</option><option value="50000">50 000 · detallado</option></select></label><button id="load-file" class="primary">Abrir nube ↗</button><small>PLY recomendado. El muestreo reduce detalle; recorta el original antes si necesitas estudiar una región.</small></div></div>
<div id="splash"><div class="splash-field"></div><div class="splash-word"><span>Cloud</span><b>PE</b></div><div class="splash-sub">DE LOS PUNTOS, LA FORMA.</div><div class="splash-line"></div></div>`;

const scene=new THREE.Scene();scene.background=new THREE.Color('#090b0e');
const camera=new THREE.PerspectiveCamera(42,innerWidth/innerHeight,.005,100);camera.position.set(1.6,.9,2.7);
let renderer;
try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:true});}catch(error){$('#splash').remove();$('#app').innerHTML='<main style="padding:4rem;color:white">CloudPE necesita WebGL. Activa la aceleración gráfica del navegador.</main>';throw error;}
renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));renderer.outputColorSpace=THREE.SRGBColorSpace;
$('#viewport').appendChild(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.065;controls.minDistance=.25;controls.maxDistance=10;controls.autoRotateSpeed=.35;
scene.add(new THREE.HemisphereLight(0xe9f4ff,0x24202c,2));
const key=new THREE.DirectionalLight(0xffffff,3);key.position.set(3,5,4);scene.add(key);
const rim=new THREE.DirectionalLight(0x8dacc4,2);rim.position.set(-4,1,-2);scene.add(rim);
const group=new THREE.Group();scene.add(group);
const clock=new THREE.Clock();

const vertexShader=`
attribute vec3 aColor; attribute vec3 aNormal; attribute float aLabel; attribute float aConfidence;
uniform float uTime;uniform float uStart;uniform float uMotion;uniform float uMode;uniform float uPixelRatio;
varying vec3 vColor;varying float vAlpha;
vec3 palette(float t){return .58+.37*cos(6.28318*(vec3(.0,.33,.67)+t));}
void main(){
 vec3 p=position;float age=max(0.,uTime-uStart);float radius=length(p);
 float arrival=age-radius*.55;float front=exp(-pow((age*.9-radius-.05)*3.5,2.));
 vec3 direction=normalize(p+vec3(.0001));
 p+=direction*sin(radius*15.-age*7.)*front*.065*exp(-age*.3)*uMotion;
 p.y+=sin(radius*11.-age*6.)*front*.035*uMotion;
 vColor=vec3(.84,.89,.94);
 if(uMode>0.5&&uMode<1.5)vColor=aColor;
 if(uMode>1.5&&uMode<2.5)vColor=mix(vec3(.25,.38,.43),vec3(.34,.94,.86),aConfidence);
 if(uMode>2.5)vColor=aLabel<0.?vec3(.28,.31,.36):palette(fract(aLabel*.618034));
 vAlpha=smoothstep(0.,.3,age)*.94;
 vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;
 gl_PointSize=clamp((2.3*uPixelRatio)/max(.5,-mv.z*.42),1.,5.5);
}`;
const fragmentShader=`varying vec3 vColor;varying float vAlpha;void main(){float d=length(gl_PointCoord-.5);if(d>.5)discard;float a=(1.-smoothstep(.27,.5,d))*vAlpha;gl_FragColor=vec4(vColor,a);}`;

function toast(message){$('#toast').textContent=message;$('#toast').classList.add('shown');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').classList.remove('shown'),4500);}
function dispose(object){if(!object)return;group.remove(object);object.geometry?.dispose();if(Array.isArray(object.material))object.material.forEach(m=>m.dispose());else object.material?.dispose();}
function clearScene(){dispose(state.points);dispose(state.mesh);dispose(state.normals);dispose(state.edges);state.points=state.mesh=state.normals=state.edges=null;$('#replaybar').classList.add('hidden');state.replay=false;state.replayProgress=1;state.reveal=false;}
function orientView(up){state.viewUp=up;const x={'y+':0,'y-':Math.PI,'z+':-Math.PI/2,'z-':Math.PI/2}[up]??0;group.rotation.set(x,0,0);}
function fit(){controls.target.set(0,0,0);camera.position.set(1.25,.65,2.5);controls.update();}
function setMode(mode){
 if(mode==='mesh'&&!state.mesh){toast('Primero reconstruye la superficie en la etapa 5.');return;}
 if(mode==='normals'&&!state.meta?.attributes.includes('normals')){toast('Calcula las normales en la etapa 3.');return;}
 if(mode==='segments'&&!state.meta?.attributes.includes('segment')){toast('Segmenta la nube en la etapa 4.');return;}
 state.mode=mode;
 document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
 if(state.points){state.points.visible=mode!=='mesh';state.points.material.uniforms.uMode.value={mono:0,rgb:1,normals:2,segments:3}[mode]??0;}
 if(state.mesh)state.mesh.visible=mode==='mesh';if(state.normals)state.normals.visible=mode==='normals';
 if(state.edges)state.edges.visible=mode==='mesh'&&state.showEdges;
 $('#replaybar').classList.toggle('hidden',mode!=='mesh');
}
function showLoading(title,detail,kicker='PROCESANDO'){state.busy=true;$('#loading').classList.remove('hidden');$('#load-title').textContent=title;$('#load-detail').textContent=detail;$('#load-kicker').textContent=kicker;$('#status-label').textContent='Trabajo en curso';renderStage();}
function hideLoading(){state.busy=false;$('#loading').classList.add('hidden');$('#status-label').textContent='Listo para explorar';renderStage();}
async function api(path,body){const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});if(!r.ok){let error=await r.json();throw Error(error.detail||'No se pudo completar la solicitud');}return r.json();}
let generation=0;
async function startJob(body){
 if(state.busy)return;const ticket=++generation;
 const titles={open:'Preparando tu universo.',clean:'Separando señal y ruido.',normals:'Encontrando orientaciones.',segment:'Reconociendo superficies.',bpa:'Conectando los puntos.'};
 showLoading(titles[body.operation],'Cálculo aislado en CPU. Puedes cancelar sin cerrar la aplicación.');
 try{
  const job=await api('/api/jobs',body);if(ticket!==generation){await api(`/api/jobs/${job.id}/cancel`,{});return;}state.job=job.id;
  let result;
  while(ticket===generation){result=await api(`/api/jobs/${job.id}`);if(result.state==='error')throw Error(result.error);if(result.state==='complete')break;await new Promise(r=>setTimeout(r,350));}
  if(ticket!==generation)return;
  await loadProject(result,ticket,body.operation==='open');if(ticket!==generation)return;
  state.id=job.id;state.job=null;if(body.operation==='open')state.title=result.title||'Nube local';
  hideLoading();updateStats();renderStage();
  if(body.operation==='bpa')beginReplay();
  else if(body.operation==='normals')setMode('normals');
  else if(body.operation==='segment')setMode('segments');
 }catch(error){if(ticket===generation){if(state.transfer){clearScene();state.id=null;state.meta=null;state.transfer=false;updateStats();}hideLoading();state.job=null;toast(error.message);}}
}

async function loadProject(meta,ticket,recenter){
 $('#load-title').textContent='Los puntos encuentran su lugar.';$('#load-kicker').textContent='TRANSFERENCIA AL VISOR';
 const response=await fetch(`/api/projects/${meta.id}/points.bin`);if(!response.ok)throw Error('Error al cargar puntos');
 const reader=response.body.getReader();const bytes=new Uint8Array(meta.points*44);let offset=0;
 state.transfer=true;clearScene();state.meta=meta;if(recenter)orientView(meta.view_up||'y+');
 const packed=new Float32Array(bytes.buffer);const interleaved=new THREE.InterleavedBuffer(packed,11);interleaved.setUsage(THREE.DynamicDrawUsage);
 const geometry=new THREE.BufferGeometry();
 geometry.setAttribute('position',new THREE.InterleavedBufferAttribute(interleaved,3,0));geometry.setAttribute('aColor',new THREE.InterleavedBufferAttribute(interleaved,3,3));geometry.setAttribute('aNormal',new THREE.InterleavedBufferAttribute(interleaved,3,6));geometry.setAttribute('aLabel',new THREE.InterleavedBufferAttribute(interleaved,1,9));geometry.setAttribute('aConfidence',new THREE.InterleavedBufferAttribute(interleaved,1,10));geometry.setDrawRange(0,0);
 const material=new THREE.ShaderMaterial({vertexShader,fragmentShader,transparent:true,depthWrite:false,uniforms:{uTime:{value:clock.getElapsedTime()},uStart:{value:clock.getElapsedTime()},uMotion:{value:state.reduced?0:1},uMode:{value:0},uPixelRatio:{value:renderer.getPixelRatio()}}});
 state.points=new THREE.Points(geometry,material);state.points.frustumCulled=false;group.add(state.points);if(recenter)fit();
 while(true){const {done,value}=await reader.read();if(done)break;if(ticket!==generation){await reader.cancel();return;}bytes.set(value,offset);offset+=value.byteLength;interleaved.needsUpdate=true;geometry.setDrawRange(0,Math.floor(offset/44));$('#load-detail').textContent=`${Math.floor(offset/44).toLocaleString('es')} / ${meta.points.toLocaleString('es')} puntos recibidos`;
 }
 if(offset!==bytes.byteLength)throw Error('Transferencia de puntos incompleta');
 geometry.computeBoundingSphere();
 state.loadTime=clock.getElapsedTime();material.uniforms.uStart.value=state.loadTime;
 state.reveal=true;setMode('mono');
 // Display a deliberate arrival animation after real transfer. Do not present it as memory progress.
 $('#load-kicker').textContent='REVELADO VISUAL';$('#load-detail').textContent='Transferencia completa. Animación de entrada; no altera tus coordenadas.';
 buildNormals(packed);
 if(meta.triangles){
  const res=await fetch(`/api/projects/${meta.id}/mesh.bin`);if(!res.ok)throw Error('Error al cargar malla');
  const buffer=await res.arrayBuffer();if(ticket!==generation)return;
  const header=new Uint32Array(buffer,0,2),nv=header[0],nt=header[1];
  const raw=new Float32Array(buffer,8,nv*6),indices=new Uint32Array(buffer,8+nv*24,nt*3);
  const meshGeometry=new THREE.BufferGeometry();const b=new THREE.InterleavedBuffer(raw,6);
  meshGeometry.setAttribute('position',new THREE.InterleavedBufferAttribute(b,3,0));meshGeometry.setAttribute('normal',new THREE.InterleavedBufferAttribute(b,3,3));
  // Radial face ordering is a visual reveal, explicitly not the internal BPA trace.
  const order=Array.from({length:nt},(_,i)=>i);const center=(i)=>{let sum=0;for(let v=0;v<3;v++){const k=indices[i*3+v]*6;sum+=raw[k]**2+raw[k+1]**2+raw[k+2]**2;}return sum;};
  const distances=order.map(center);order.sort((a,b)=>distances[a]-distances[b]);const sorted=new Uint32Array(nt*3);order.forEach((v,i)=>sorted.set(indices.subarray(v*3,v*3+3),i*3));meshGeometry.setIndex(new THREE.BufferAttribute(sorted,1));
  const mesh=new THREE.Mesh(meshGeometry,new THREE.MeshStandardMaterial({color:0xc5d1d7,metalness:.15,roughness:.65,side:THREE.DoubleSide,flatShading:!state.smooth}));mesh.visible=false;state.mesh=mesh;group.add(mesh);
  const counts=new Map();for(let i=0;i<indices.length;i+=3){for(let e=0;e<3;e++){let a=indices[i+e],b=indices[i+(e+1)%3];if(a>b)[a,b]=[b,a];const code=a*nv+b;counts.set(code,(counts.get(code)||0)+1);}}
  const line=[];for(const [code,count] of counts){if(count!==1)continue;const a=Math.floor(code/nv)*6,b=(code%nv)*6;line.push(raw[a],raw[a+1],raw[a+2],raw[b],raw[b+1],raw[b+2]);}
  const edgeGeometry=new THREE.BufferGeometry();edgeGeometry.setAttribute('position',new THREE.Float32BufferAttribute(line,3));state.edges=new THREE.LineSegments(edgeGeometry,new THREE.LineBasicMaterial({color:0xff8e75,depthTest:false,transparent:true,opacity:.75}));state.edges.visible=false;group.add(state.edges);
 }
 if(!state.reduced)await new Promise(r=>setTimeout(r,1700));if(ticket!==generation)return;state.reveal=false;geometry.setDrawRange(0,meta.points);state.transfer=false;
}
function buildNormals(packed){const n=Math.min(220,state.meta.points),lines=new Float32Array(n*6);for(let j=0;j<n;j++){const i=Math.floor(j*state.meta.points/n)*11;for(let a=0;a<3;a++){lines[j*6+a]=packed[i+a];lines[j*6+3+a]=packed[i+a]+packed[i+6+a]*.035;}}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(lines,3));state.normals=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0x64e6d0,transparent:true,opacity:.7}));state.normals.visible=false;group.add(state.normals);
}
function updateStats(){const m=state.meta;$('#point-count').textContent=m?m.points.toLocaleString('es'):'—';$('#face-count').textContent=m?.triangles?m.triangles.toLocaleString('es'):'—';$('#project-name').textContent=state.title;}
function renderStage(){
 const m=state.meta;
 $('.step-list').innerHTML=stages.map(([op,label],i)=>{const complete=m&&(i===0||i===1&&m.history.some(h=>h.operation==='clean')||i===2&&m.attributes.includes('normals')||i===3&&m.attributes.includes('segment')||i===4&&m.triangles>0);return `<button class="step ${i===state.stage?'selected':''} ${complete?'complete':''}" data-step="${i}"><span class="step-num">${complete?'✓':String(i+1).padStart(2,'0')}</span><span>${label}</span><span class="step-dot"></span></button>`;}).join('');
 document.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>{state.stage=Number(b.dataset.step);renderStage();});
 const [op,label,desc]=stages[state.stage];
 let content=`<div class="stage-description"><span class="eyebrow">${String(state.stage+1).padStart(2,'0')} / ${label.toUpperCase()}</span><p>${desc}</p></div>`;
 if(op==='open')content+=`<p class="muted">Empieza con un ejemplo listo o tu propio archivo. Hasta 50 000 puntos de trabajo; nada se modifica en el original.</p><button class="secondary full" id="choose-example">Explorar colección ↗</button><button class="text-button full" id="choose-local">Abrir archivo local</button><label>Orientación del visor<select id="view-up"><option value="y+">Y hacia arriba / original</option><option value="y-">−Y hacia arriba / invertir</option><option value="z+">Z hacia arriba</option><option value="z-">−Z hacia arriba</option></select></label><small class="disclaimer">Gira puntos, normales y malla juntos. No modifica ni exporta rotaciones a tu PLY.</small>`;
 if(op==='clean')content+=`<label>Tolerancia al ruido <span id="std-value">2.5 σ</span><input id="std" type="range" min="1" max="5" step=".1" value="2.5"></label><details><summary>Ajustes avanzados</summary><label>Tamaño de vóxel<input type="number" id="voxel" min="0" value="0" step="0.001"></label><small>0 conserva la resolución. Unidades del modelo.</small></details>`;
 if(op==='normals')content+=`<label>Detalle local <span id="k-value">30 vecinos</span><input id="k" type="range" min="10" max="70" step="5" value="30"></label><p class="muted">Menos vecinos conservan detalle; más vecinos estabilizan ruido, pero mezclan bordes.</p><details><summary>Ajustes avanzados</summary><label>Radio máximo PCA<input id="normal-radius" type="number" value="0" min="0" step="any"></label><small>0: k vecinos sin límite de distancia. Un radio positivo evita mezclar superficies lejanas; muy pequeño deja normales inválidas.</small><label class="check-label"><input id="orient-normals" type="checkbox" checked> Orientar normales coherentemente</label><small>Recomendado para BPA. Desactivarlo deja la ambigüedad de signo de PCA.</small></details>`;
 if(op==='segment')content+=`<label>Criterio<select id="method"><option value="regions">Superficies / geometría</option><option value="graph">Grafo / geometría + color</option></select></label><details><summary>Ajustes avanzados</summary><label>Ángulo máximo °<input id="angle" type="number" value="20" min="1" max="80"></label><label>Peso del color<input id="color-weight" type="number" value="0.5" min="0" max="3" step=".1"></label></details><p class="muted">Regiones geométricas, no categorías semánticas.</p>`;
 if(op==='bpa'){
  const config=m?.bpa_config||{radii:[2.5,4,6],radius_mode:'median'};
  content+=`<label>Punto de partida<select id="preset"><option value="2.5,4,6">Equilibrado / recomendado</option><option value="1.5,2.5,4">Fino / puede dejar más huecos</option><option value="3,5,8">Cobertura / revisa conexiones</option><option value="custom">Personalizado</option></select></label><details open><summary>Configuración avanzada BPA</summary><label>Radios de las esferas<input id="custom-radii" type="text" value="${config.radii.join(', ')}" placeholder="2.5, 4, 6"></label><small>De 1 a 6 valores positivos, separados por comas. Se aplican de menor a mayor. El primer radio condiciona las conexiones iniciales; no siempre se arreglan añadiendo otro mayor.</small><label>Unidades de los radios<select id="radius-mode"><option value="median">Múltiplos del espaciado mediano</option><option value="p90">Múltiplos del espaciado p90</option><option value="absolute">Unidades originales del modelo</option></select></label><small>Mediana: distancia típica al vecino más cercano. P90: referencia mayor para densidad irregular. Unidades originales: radios directos, no necesariamente metros.</small><p id="effective-radii" class="radius-readout"></p><label class="check-label"><input id="recompute-normals" type="checkbox"> Reestimar normales antes de BPA</label><label>Vecinos PCA de la reestimación<input id="bpa-k" type="number" value="30" min="3" max="80"></label><small>Útil si cambiaste la preparación. Orientación coherente activada. No crea puntos ni rellena huecos.</small></details><p class="muted">Radios pequeños pueden dejar aberturas; radios grandes pueden puentear ventanas y superficies distintas. Más cobertura no siempre significa más exactitud.</p>`;
  if(m?.mesh_report)content+=`<div class="mesh-diagnostics"><div><b>${m.mesh_report.boundary_edges.toLocaleString('es')}</b><span>aristas de borde</span></div><div><b>${m.mesh_report.components.toLocaleString('es')}</b><span>componentes</span></div></div><small class="disclaimer">Las aristas de borde incluyen el contorno exterior: no son una cuenta de huecos.</small>`;
  if(state.mesh)content+=`<label class="check-label"><input id="show-boundaries" type="checkbox" ${state.showEdges?'checked':''}> Resaltar bordes abiertos / coral</label><label class="check-label"><input id="smooth-shading" type="checkbox" ${state.smooth?'checked':''}> Sombreado suave</label><small class="disclaimer">El sombreado solo cambia la iluminación; no repara la geometría.</small><button id="full-mesh" class="secondary full">Mostrar malla completa · 100 %</button><button id="replay" class="secondary full">▶ Ver cómo aparece la superficie</button><small class="disclaimer">Reproducción visual de caras, no ejecución paso a paso de Open3D.</small>`;
 }
 if(op!=='open'){const disabled=state.busy||!state.id||((op==='bpa'||op==='segment')&&!m?.attributes.includes('normals'));content+=`<button id="execute" class="primary full" ${disabled?'disabled':''}>${state.busy?'Procesando…':{clean:'Limpiar nube',normals:'Estimar normales',segment:'Separar regiones',bpa:'Reconstruir superficie'}[op]} <span>↗</span></button>`;if((op==='bpa'||op==='segment')&&!m?.attributes.includes('normals'))content+='<small class="warning">Antes, estima normales en el paso 03.</small>';}
 if(state.id)content+=`<div class="downloads"><a href="/api/projects/${state.id}/cloud.ply" download>↓ Nube PLY</a>${state.mesh?`<a href="/api/projects/${state.id}/mesh.ply" download>↓ Malla PLY</a>`:''}</div>`;
 $('#stage-body').innerHTML=content;
 if($('#choose-example'))$('#choose-example').onclick=openGallery;if($('#choose-local'))$('#choose-local').onclick=()=>$('#file-modal').classList.remove('hidden');
 if($('#std'))$('#std').oninput=e=>$('#std-value').textContent=`${e.target.value} σ`;
 if($('#k'))$('#k').oninput=e=>$('#k-value').textContent=`${e.target.value} vecinos`;
 if($('#view-up')){$('#view-up').value=state.viewUp;$('#view-up').onchange=e=>orientView(e.target.value);}
 if($('#radius-mode')){
  $('#radius-mode').value=m?.bpa_config?.radius_mode||'median';
  const readout=()=>{const radii=$('#custom-radii').value.split(',').map(v=>Number(v.trim()));const mode=$('#radius-mode').value;const h=mode==='absolute'?1:m?.diagnostics?.spacing?.[mode];$('#effective-radii').textContent=h&&radii.every(v=>Number.isFinite(v)&&v>0)?`Radios efectivos: ${radii.sort((a,b)=>a-b).map(v=>(v*h).toPrecision(4)).join(' · ')}`:'Introduce radios positivos válidos.';};
  $('#preset').value=m?.bpa_config?'custom':'2.5,4,6';
  $('#preset').onchange=e=>{if(e.target.value!=='custom'){$('#custom-radii').value=e.target.value;$('#radius-mode').value='median';readout();}};
  $('#custom-radii').oninput=()=>{$('#preset').value='custom';readout();};$('#radius-mode').onchange=readout;readout();
 }
 if($('#show-boundaries'))$('#show-boundaries').onchange=e=>{state.showEdges=e.target.checked;setMode('mesh');};
 if($('#smooth-shading'))$('#smooth-shading').onchange=e=>{state.smooth=e.target.checked;state.mesh.material.flatShading=!state.smooth;state.mesh.material.needsUpdate=true;};
 if($('#full-mesh'))$('#full-mesh').onclick=()=>{state.replay=false;state.replayProgress=1;$('#replay-toggle').textContent='▶';setMode('mesh');};
 if($('#execute'))$('#execute').onclick=()=>{let params={};if(op==='clean')params={std:Number($('#std').value),voxel:Number($('#voxel').value)};if(op==='normals')params={k:Number($('#k').value),normal_radius:Number($('#normal-radius').value),orient:$('#orient-normals').checked};if(op==='segment')params={method:$('#method').value,angle:Number($('#angle').value),color:Number($('#color-weight').value)};if(op==='bpa'){params={radii:$('#custom-radii').value.split(',').map(v=>Number(v.trim())),radius_mode:$('#radius-mode').value,recompute_normals:$('#recompute-normals').checked,k:Number($('#bpa-k').value)};if(!params.radii.length||params.radii.length>6||params.radii.some(v=>!Number.isFinite(v)||v<=0||v>100)){toast('Usa de 1 a 6 radios positivos, como 2.5, 4, 6.');return;}}startJob({operation:op,source:state.id,params});};
 if($('#replay'))$('#replay').onclick=beginReplay;
}
function beginReplay(){if(!state.mesh)return;setMode('mesh');state.replayProgress=0;state.replay=true;$('#replay-toggle').textContent='Ⅱ';}
function openGallery(){$('#welcome').classList.remove('dismissed');}
async function init(){try{state.examples=await api('/api/examples');$('#cards').innerHTML=state.examples.map((e,i)=>`<button class="example-card" data-example="${e.id}" style="--delay:${i*70}ms"><div class="example-image"><img src="/previews/${e.id}.png" alt="Vista de ${e.title}" loading="lazy"><span class="card-arrow">↗</span></div><div class="card-info"><span>${e.title}</span><small>${e.cleaning.output.toLocaleString('es')} PUNTOS · LISTO</small></div></button>`).join('');document.querySelectorAll('[data-example]').forEach(b=>b.onclick=()=>{if(state.busy)return;$('#welcome').classList.add('dismissed');state.stage=0;startJob({operation:'open',example:b.dataset.example,processed:true});});}catch(e){toast('No se pudo conectar con el servidor local.');}}

$('#home').onclick=$('#gallery-button').onclick=openGallery;$('#close-welcome').onclick=()=>{if(state.id)$('#welcome').classList.add('dismissed');else toast('Selecciona un ejemplo o abre tu archivo.');};
$('#fit').onclick=fit;$('#turn').onclick=()=>{controls.autoRotate=!controls.autoRotate;$('#turn').classList.toggle('active',controls.autoRotate);};
$('#collapse').onclick=()=>{$('#panel').classList.add('collapsed');$('#expand').classList.remove('hidden');};$('#expand').onclick=()=>{$('#panel').classList.remove('collapsed');$('#expand').classList.add('hidden');};
$('#motion').onclick=()=>{state.reduced=!state.reduced;document.body.classList.toggle('reduced-motion',state.reduced);if(state.points)state.points.material.uniforms.uMotion.value=state.reduced?0:1;toast(state.reduced?'Movimiento reducido':'Animaciones activadas');};
$('#open-local').onclick=()=>$('#file-modal').classList.remove('hidden');$('#file-close').onclick=()=>$('#file-modal').classList.add('hidden');
$('#load-file').onclick=()=>{const path=$('#file-path').value.trim();if(!path)return;$('#file-modal').classList.add('hidden');$('#welcome').classList.add('dismissed');startJob({operation:'open',path,params:{budget:Number($('#budget').value)}});};
$('#cancel').onclick=async()=>{++generation;const id=state.job;state.job=null;if(id)await api(`/api/jobs/${id}/cancel`,{});if(state.transfer){clearScene();state.id=null;state.meta=null;state.transfer=false;updateStats();}hideLoading();toast('Trabajo cancelado');};
$('#screenshot').onclick=()=>{renderer.render(scene,camera);const a=document.createElement('a');a.download='CloudPE.png';a.href=renderer.domElement.toDataURL('image/png');a.click();};
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
$('#replay-toggle').onclick=()=>{if(state.replayProgress>=1)state.replayProgress=0;state.replay=!state.replay;$('#replay-toggle').textContent=state.replay?'Ⅱ':'▶';};
$('#replay-progress').oninput=e=>{state.replayProgress=Number(e.target.value);state.replay=false;$('#replay-toggle').textContent='▶';};
$('#replay-speed').onclick=()=>{state.replaySpeed=state.replaySpeed===1?2:state.replaySpeed===2?.5:1;$('#replay-speed').textContent=`${state.replaySpeed}×`;};
addEventListener('keydown',e=>{if(e.key==='Escape'){$('#file-modal').classList.add('hidden');if(state.id)$('#welcome').classList.add('dismissed');}if(e.key.toLowerCase()==='f'&&!['INPUT','SELECT'].includes(document.activeElement.tagName))fit();});
function resize(){camera.aspect=innerWidth/innerHeight;camera.setViewOffset(innerWidth,innerHeight,innerWidth*(innerWidth>700?.10:0),0,innerWidth,innerHeight);camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);}
addEventListener('resize',resize);resize();
let last=0;
function animate(){requestAnimationFrame(animate);const t=clock.getElapsedTime(),dt=Math.min(t-last,.1);last=t;controls.update();
 if(state.points){state.points.material.uniforms.uTime.value=t;if(state.reveal){const f=state.reduced?1:Math.min(1,(t-state.loadTime)/1.6);state.points.geometry.setDrawRange(0,Math.floor(state.meta.points*f));}}
 if(state.mesh){if(state.replay){state.replayProgress=Math.min(1,state.replayProgress+dt*state.replaySpeed/9);if(state.replayProgress===1){state.replay=false;$('#replay-toggle').textContent='▶';}}state.mesh.geometry.setDrawRange(0,Math.floor(state.meta.triangles*state.replayProgress)*3);$('#replay-progress').value=state.replayProgress;}
 renderer.render(scene,camera);
}
renderStage();init();animate();if(state.reduced)document.body.classList.add('reduced-motion');
setTimeout(()=>{$('#splash').classList.add('exit');setTimeout(()=>$('#splash').remove(),1000);},state.reduced?100:1900);
