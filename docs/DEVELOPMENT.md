# CloudLab / CloudPE — notas de desarrollo e historial de uso

## CloudPE — nueva interfaz inmersiva

### Configuración avanzada de BPA y orientación

En **05 · Superficie** se pueden introducir de uno a seis radios personalizados, elegir escala **mediana / p90 / unidades originales**, ver sus radios efectivos y reestimar normales con `k` configurable. Los valores se guardan en el resultado del trabajo. Los presets solo ayudan a empezar: los campos son editables. Recomendación inicial revisada: **2.5, 4, 6** multiplicados por el espaciado mediano. Para comparar cobertura: **3, 5, 8**, vigilando conexiones entre superficies separadas.

Un radio pequeño puede generar muchos huecos y conexiones iniciales que otras pasadas no reparan. Un radio grande puede reducir bordes abiertos, pero saltar detalles o unir lados de una ventana. La base p90 es mayor que la mediana: no cambiar ambas cosas sin observar los radios efectivos. Radios absolutos usan las unidades del modelo (no asumir metros).

Se muestran **aristas de borde y componentes** y se pueden resaltar bordes en coral. No se llama a esas aristas “número de huecos”: incluyen el contorno exterior. **Mostrar malla completa · 100 %** permite descartar que una reproducción a medias sea el origen de lo que parece un hueco. Sombreado suave solo cambia iluminación, no repara geometría.

En **03 · Normales**, ajustes avanzados permiten limitar el radio PCA y activar/desactivar orientación. Para BPA, mantener la orientación activada. No basta con aumentar radios si las normales o los puntos son malos.

Las dos nubes de cuadra se muestran con **−Y hacia arriba** por defecto, corrigiendo la inversión del visor. La fachada sintética usa Z hacia arriba. **01 · Entrada → Orientación del visor** permite cambiar entre ±Y y ±Z. Es una rotación de presentación, aplicada también a normales y malla; los archivos descargados conservan sus coordenadas originales.

Los ejemplos Bunny y fachada fueron recalculados con radios revisados. Investigación reproducible: `.venv/bin/python scripts/review_bpa.py`, resultados en `outputs/bpa_radius_review.json`.

**Abrir http://127.0.0.1:8765**. La nueva experiencia usa Three.js a pantalla completa, sin barra superior, con paneles flotantes y galería. La interfaz Streamlit anterior permanece disponible mediante `run_app.sh`, pero no es la nueva aplicación.

```bash
# Python siempre dentro del entorno local creado con pyenv:
.venv/bin/python -m pip install -r requirements-web.txt
# Dependencias frontend locales, no globales:
cd frontend
npm ci
npm run build
cd ..
bash run_cloudpe.sh
```

La galería abre resultados precalculados. Cada apertura empaqueta un conjunto pequeño para el visor; no vuelve a ejecutar PCA, segmentación o BPA. El menú flotante permite ejecutar las etapas con parámetros y descargar PLY. El botón **−** oculta el panel para disfrutar del visor completo; **⌖** reencuadra y **▣** guarda una captura. **◐** reduce movimiento. Las fuentes y miniaturas son locales: no se necesita internet para la interfaz instalada.

### Animaciones y honestidad del progreso

- Intro CloudPE y galería con miniaturas reales.
- Transferencia binaria con contador de puntos recibidos. Después, revelado visual de aproximadamente 1,6 s; se identifica como animación, no progreso de lectura del archivo original.
- Onda radial amortiguada en el shader del navegador: no altera las coordenadas exportadas ni el cálculo en CPU.
- BPA devuelve la malla final. La reproducción ordena caras radialmente para mostrar su aparición; **no es el trazado interno del algoritmo ni la esfera pivotando realmente**. Tiene pausa, velocidad y desplazamiento temporal. Se inicia automáticamente al reconstruir; en un ejemplo precalculado, etapa 05 → reproducir.
- Limpieza, PCA, regiones/grafo y BPA corren en un proceso Python separado. Un solo trabajo activo, hasta 50k puntos. **Cancelar** termina ese proceso, liberando su memoria. La API principal no importa Open3D ni conserva arrays de nubes en RAM.
- Intermedios inmutables en `.cloudpe/`, sin sobrescribir originales. Se acumulan en disco; aún no hay limpieza automática ni gestor de proyectos persistente en la interfaz. No exponer esta API local a internet: permite abrir rutas locales.
- El nuevo frontend aún no incluye el recorte interactivo ni la reparación Delaunay del explorador anterior. Es una iteración centrada en la experiencia visual y pipeline principal.

Pruebas de navegador: `cd frontend && npx playwright install chromium && npm run test:e2e` (servidor CloudPE activo). Capturas en `frontend/test-results/`.

---

Proyecto de procesamiento de nubes: limpieza, normales PCA propias, segmentación geométrica y por grafos con color CIELAB, reconstrucción Ball Pivoting y reparación Delaunay local experimental. Sin CUDA. Los archivos originales no se modifican.

## Entorno local (Arch Linux)

El entorno `.venv` se crea con Python de **pyenv**, no con paquetes globales:

```bash
pyenv install -s 3.10.18
PYENV_VERSION=3.10.18 pyenv exec python -m venv .venv
.venv/bin/python -m pip install -e .
```

Para reproducir exactamente las versiones del entorno probado: ` .venv/bin/python -m pip install -r requirements-lock.txt`.

## Probar la aplicación

```bash
.venv/bin/streamlit run app.py --server.address 127.0.0.1
```

Abrir **http://localhost:8501**. Se abre automáticamente una **fachada precalculada**. La galería ofrece fachada con ventanas, Stanford Bunny, esfera, esquina y el par fotogramétrico dense/sparse del usuario. **Ver resultado** carga puntos, normales, etiquetas y malla sin recalcular; **Desde cero** carga los puntos originales del ejemplo. Después puedes recorrer las etapas superiores. La aplicación es local; no expongas su puerto públicamente.

```bash
bash run_app.sh
# Regenerar ejemplos (opcional; Bunny requiere internet solo la primera vez):
.venv/bin/python scripts/build_gallery.py --bunny
```

### Seguridad de memoria (versión revisada)

- La interfaz nunca carga un PLY completo para luego reducirlo: `safe_io.py` selecciona hasta **50k puntos durante la lectura**. PLY binario de registro fijo usa memory mapping; PLY con listas variables, como OpenMVS, se recorre secuencialmente omitiendo las listas. No construye arrays de objetos por observación.
- Conserva **un solo estado anterior**, no cuatro nubes completas. Dibuja hasta 12k puntos y 250 normales. Los ejemplos contienen aproximadamente 12k–25k puntos.
- Las coordenadas del visor se centran para mejorar precisión WebGL. Se sustituyó la opción obsoleta `use_container_width`.
- PCD/XYZ grandes se rechazan en la interfaz: su lector no es streaming; límite de archivo 8 MiB.
- La CLI también usa carga segura por defecto (50k). `inspect` reporta cabecera original y estadísticas de una muestra, no estadísticas globales. `--max-points 0` requiere `--allow-full-memory`, autorización explícita para cargar todo con riesgo de RAM.
- **Recortar después de cargar opera sobre la muestra**, no recupera la densidad original de esa región. Para estudiar detalle se recomienda abrir un PLY ya recortado, como la nueva cuadra. Procesamiento de la escena entera out-of-core sigue fuera del alcance.
- Estos límites reducen mucho el riesgo, pero no son un aislamiento duro de RAM del sistema: otras aplicaciones, múltiples sesiones y Open3D también consumen memoria.

Con Barranco: preferir **Tu cuadra · densa** en la galería. Para otra nube usa **Archivo propio**, inspecciona cabecera y carga con presupuesto de 10k–50k. Las operaciones siguen siendo síncronas: no hay cancelación inmediata de Open3D.

## Línea de comandos reproducible

```bash
.venv/bin/cloudlab inspect dense_preview_5M.ply
.venv/bin/cloudlab generate outputs/corner.ply --kind corner --points 12000
.venv/bin/cloudlab run outputs/corner.ply --output outputs/corner_run
.venv/bin/cloudlab run outputs/corner.ply --method graph --scale 2 --color-weight 1 --output outputs/graph_run
.venv/bin/cloudlab run /ruta/a/cuadra-025_0-10s_dense.ply --max-points 30000 --output outputs/cuadra_safe
.venv/bin/pytest -q
```

`run` reserva aproximadamente 10 % de los puntos limpios para validación antes de PCA, segmentación y BPA. Su limpieza inicial sí usa toda la muestra de trabajo: no es una evaluación externa estrictamente independiente. `--max-points` establece una muestra estratificada reproducible **de desarrollo**, no un recorte geométrico. Para experimentos finales abre un PLY previamente recortado. `--lower X Y Z --upper X Y Z` recorta la muestra cargada; `--voxel` controla reducción. Radios de BPA: `--radii 1.5 2.5 4`, multiplicados por el espaciado mediano. `--repair` activa reparación experimental.

Cada ejecución guarda nube procesada, puntos de validación, atípicos, malla y `report.json` con parámetros, historial, tiempos por etapa, memoria pico del proceso y métricas bidireccionales. Mediana y percentil 95 se expresan en unidades del modelo, no necesariamente metros. La CLI estima error angular sin signo si existen normales sintéticas de referencia. Puntos no asignados: segmento `-1`.

## Arquitectura

- `cloudlab/core.py`: modelo de datos, E/S, limpieza, PCA por lotes, orientación por bosque de expansión mínimo, regiones, grafo adaptativo, BPA, diagnóstico y reparación.
- `cloudlab/cli.py`: ejecuciones reproducibles con validación y reportes.
- `app.py`: interfaz Streamlit + visor Plotly WebGL; no requiere OpenGL nativo para dibujar.
- `tests/`: pruebas sintéticas de algoritmos y E/S.

### Decisiones y límites

- PLY preserva atributos escalares numéricos personalizados. PCD usa el lector clásico de Open3D: no preserva campos arbitrarios. XYZ/TXT acepta exactamente 3 columnas XYZ o 6 XYZ RGB en rango 0–255. No hay soporte LAS/LAZ todavía.
- Vóxeles seleccionan un punto original (no centroide): sus atributos y `source_index` permanecen coherentes. No se guarda una correspondencia completa de todos los puntos descartados por vóxel.
- La limpieza invalida normales/segmentos anteriores. PCA invalida segmentos. Se conserva un solo estado previo acotado para deshacer en la interfaz.
- PCA usa coordenadas centradas para estabilidad numérica y marca vecindarios degenerados. Orientación local no equivale a normal exterior; desconexiones y superficies próximas pueden generar ambigüedad.
- Regiones: restricciones vecinales y respecto al plano/normal de la semilla para evitar deriva. Grafo: fusión adaptativa por diferencia interna y tamaño, inspirada en Felzenszwalb–Huttenlocher sobre vecindad espacial, no segmentación semántica ni reproducción exacta del algoritmo para imágenes.
- El grafo usa límites de distancia, ángulo y plano; RGB es opcional y nunca conecta puntos lejanos. La escala de fusión controla mucho la fragmentación. Las sombras y diferencias de exposición pueden romper regiones.
- BPA es Open3D, no una implementación propia. PCA y segmentación sí están implementadas aquí con NumPy/SciPy.
- Delaunay solo intenta pequeños contornos simples **estrictamente convexos**, aproximadamente planos y cercanos a puntos observados. No repara polígonos generales, no garantiza ausencia de intersecciones globales, no usa cámaras y puede no aceptar ningún hueco. Es una extensión experimental, no un reconstructor general.
- Ninguna técnica garantiza una buena malla para cualquier nube: muestreo insuficiente, ruido, escalas mixtas o normales ambiguas pueden impedirlo. El sistema no asume edificios, RGB, bloques ni unidades métricas.
- La interfaz ejecuta operaciones bajo demanda; para grandes nubes la selección previa es obligatoria en la práctica. No se implementa procesamiento out-of-core.

## Referencias de los métodos

- Open3D: https://www.open3d.org/docs/release/tutorial/geometry/surface_reconstruction.html
- Ball Pivoting: Bernardini et al., *The Ball-Pivoting Algorithm for Surface Reconstruction*, IEEE TVCG, 1999.
- Normales PCA/orientación: Hoppe et al., *Surface Reconstruction from Unorganized Points*, SIGGRAPH, 1992.
- Grafos: Felzenszwalb y Huttenlocher, *Efficient Graph-Based Image Segmentation*, IJCV, 2004.

Ver `RESULTADOS.md` para los ensayos realizados y sus limitaciones.
