# CloudPE

**Laboratorio visual de procesamiento de nubes de puntos en CPU.** Proyecto final de gráficos 3D: estimación de normales, segmentación y reconstrucción de superficies.

![CloudPE: galería de ejemplos](docs/images/gallery.png)

## Qué hace

```text
Entrada → Limpieza → Normales PCA → Segmentación → Malla Ball Pivoting
```

- Visor 3D a pantalla completa con controles flotantes y animaciones.
- Limpieza de duplicados y atípicos, reducción por vóxeles y lectura PLY con memoria acotada.
- Normales **PCA propias**, orientación coherente e indicadores de confianza.
- **Segmentación propia** por regiones geométricas o grafos con geometría + color CIELAB.
- **Ball Pivoting de Open3D**, con radios personalizados y diagnóstico de bordes abiertos.
- Trabajos aislados y cancelables, exportación PLY e historial.
- **Seis ejemplos precalculados incluidos**: Bunny, fachada, esfera, esquina y una cuadra fotogramétrica dense/sparse.

No requiere CUDA ni una GPU NVIDIA. El cálculo usa CPU; el navegador necesita WebGL.

## Instalar y ejecutar

Requisitos: **Git, pyenv, Node.js 22 LTS y npm**. En Arch Linux, instala previamente las dependencias de compilación que necesite pyenv para construir Python.

```bash
git clone git@github.com:CdeCasurpie/CloudPE.git
cd CloudPE

pyenv install -s 3.10.18
PYENV_VERSION=3.10.18 pyenv exec python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e .

cd frontend
npm ci
npm run build
cd ..

bash run_cloudpe.sh
```

Abre **http://127.0.0.1:8765**. Para las siguientes sesiones, basta con `bash run_cloudpe.sh`. Es **la única aplicación y el único script de inicio** del proyecto. Todo se instala localmente, sin paquetes Python ni npm globales.

`requirements.txt` declara dependencias de ejecución; `requirements-lock.txt` fija las versiones y dependencias transitivas del entorno probado con Python 3.10/Linux. `requirements-dev.txt` añade pruebas y herramientas de desarrollo. El frontend usa `package-lock.json`.

## Probar en un minuto

1. Elige **Stanford Bunny** en la galería: el resultado ya está calculado.
2. Alterna entre puntos, color, normales, regiones y malla.
3. En **05 · Superficie**, prueba radios `2.5, 4, 6` y compara con `3, 5, 8`.
4. Activa **bordes abiertos** o muestra la malla completa al 100 %.
5. Descarga la nube o la malla PLY desde el panel.

El botón **−** oculta el panel, **⌖** o **F** centra la vista y **◐** reduce animaciones. En **01 · Entrada**, puedes cambiar la orientación ±Y/±Z sin alterar las coordenadas exportadas.

![BPA: configuración y bordes abiertos](docs/images/bpa-advanced.png)

### Radios de Ball Pivoting

Se admiten de uno a seis radios positivos, aplicados de menor a mayor. Pueden ser múltiplos del espaciado **mediano**, del **p90**, o valores absolutos en las unidades del modelo. El panel explica cada parámetro y muestra los radios efectivos.

Radios pequeños pueden dejar huecos; radios grandes pueden saltar detalles o unir superficies distintas. **Menos aristas de borde no demuestra por sí solo mayor exactitud.** El sombreado suave solo cambia iluminación.

### Abrir tus propios datos

Usa **Abrir archivo local**. El espacio de trabajo admite **10k–50k puntos**, seleccionados durante la lectura PLY, no después de cargar todo el archivo.

- PLY binario fijo: memory mapping. PLY con listas variables OpenMVS: lectura secuencial omitiendo observaciones.
- PCD/XYZ/TXT: máximo 8 MiB en la interfaz. XYZ acepta exactamente `XYZ` o `XYZ RGB` con colores 0–255.
- El muestreo pierde detalle; para estudiar una fachada usa un archivo previamente recortado. No es procesamiento completo out-of-core.

## Tecnología y estructura

| Parte | Tecnología |
|---|---|
| Interfaz y renderizado | JavaScript ES modules, Three.js, HTML/CSS, Vite |
| Servidor local y trabajos | FastAPI, Uvicorn, procesos Python aislados |
| Cálculo propio | NumPy, SciPy, KD-tree, PCA y grafos |
| Reconstrucción y mallas | Open3D |
| Archivos y color | plyfile, lector acotado propio, scikit-image |
| Validación | pytest, Playwright/Chromium |

```text
cloudpe/                  Paquete Python: algoritmos, API, worker y CLI
frontend/                 Visor, diseño, recursos locales y pruebas de navegador
examples/                 Seis ejemplos completos, resultados y manifiesto SHA-256
scripts/                  Generación de ejemplos y experimentos reproducibles
tests/                    Pruebas Python
docs/                     Arquitectura, resultados y guía para la presentación
run_cloudpe.sh            Único punto de inicio de la aplicación
```

Las fuentes y miniaturas se sirven localmente; no se requiere internet para explorar la galería instalada. Open3D puede traer dependencias transitivas como Plotly; CloudPE **no utiliza Plotly ni Streamlit como interfaz**.

## Ejemplos incluidos y procedencia

Los **24 archivos** de [`examples/`](examples/) ocupan unos **18,3 MiB**. Cada ejemplo incluye entrada, nube procesada, malla y reporte. No necesitas Git LFS ni los originales completos de la tesis. Consulta [`examples/README.md`](examples/README.md).

Stanford Bunny deriva de una malla de Stanford muestreada con ruido añadido; fachada, esfera y esquina son sintéticos. La cuadra dense/sparse procede de datos fotogramétricos del autor. El Bunny y la fachada **no son capturas LiDAR simuladas físicamente**.

## Desarrollo y validación

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/python scripts/verify_examples.py
.venv/bin/ruff check cloudpe scripts tests
.venv/bin/ruff format --check cloudpe scripts tests

# CLI reproducible, sin interfaz
.venv/bin/cloudpe inspect examples/bunny/original.ply
.venv/bin/cloudpe run examples/bunny/original.ply --output outputs/bunny_run

# Con CloudPE ejecutándose en otra terminal:
cd frontend
npx playwright install chromium
npm run test:e2e
npm run format:check
```

Documentación específica:

- **[Proyecto y presentación](docs/PROJECT.md):** objetivos, arquitectura, aportes propios y recorrido para exponer.
- **[Resultados y límites](docs/RESULTS.md):** comparación de radios, memoria y pruebas.
- **[Herramientas de desarrollo](scripts/README.md):** regenerar datos, miniaturas y manifiestos.

## Límites y créditos

La segmentación es geométrica/cromática, no semántica neuronal. No se garantiza una malla cerrada para cualquier nube. La animación de caras **no es el trazado interno de BPA ni una esfera pivotando realmente**; los efectos visuales no cambian los datos. Delaunay permanece como extensión experimental de CLI, no como parte del pipeline principal del visor.

Las sesiones se acumulan en `.cloudpe/`; no hay limpieza automática. La API abre rutas locales: **mantener en localhost, no exponer a internet**.

Proyecto de **CdeCasurpie**. Stanford Bunny: **Stanford University Computer Graphics Laboratory**, obtenido mediante Open3D. Sus condiciones permiten investigación y redistribución gratuita con atribución, pero restringen usos comerciales sin permiso. Véase [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). No se ha elegido una licencia general para el código propio.
