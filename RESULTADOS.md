# Resultados de implementación y validación

## Revisión de huecos BPA y controles avanzados

Se evaluó la misma nube procesada y las mismas normales cambiando únicamente los radios. No se rellenaron agujeros, suavizaron posiciones ni añadieron puntos.

| Ejemplo | Radios × mediana NN | Triángulos | Aristas de borde | Componentes |
|---|---|---:|---:|---:|
| Bunny | 1.5, 2.5, 4 (anterior) | 24 594 | 10 530 | 87 |
| Bunny | 2.5, 4, 6 (nuevo recomendado) | 25 697 | 2 067 | 2 |
| Bunny | 3, 5, 8 | 24 871 | 855 | 2 |
| Bunny | 4, 6, 9 | 22 716 | 306 | 2 |
| Fachada | 1.5, 2.5, 4 (anterior) | 31 098 | 15 682 | 127 |
| Fachada | 2.5, 4, 6 (nuevo recomendado) | 31 991 | 2 789 | 5 |
| Fachada | 3, 5, 8 | 30 171 | 1 411 | 4 |
| Fachada | 4, 6, 9 | 26 589 | 1 001 | 7 |

El cambio recomendado reduce las aristas de borde aproximadamente 80 % en Bunny y 82 % en fachada. No prueba una reducción equivalente del número de huecos ni mayor exactitud: más radio también puede descartar detalle o generar conexiones incorrectas. Por eso no se eligió automáticamente la configuración de mínimo borde. La fachada tiene superficies retranqueadas sin todos los laterales observados; no debe esperarse una malla cerrada.

Los diagnósticos no mostraron normales nulas/no finitas en esos ejemplos; la fracción de parejas de vecinos con normales opuestas fue aproximadamente 0,034 % (Bunny) y 0,040 % (fachada). No descarta errores locales, pero la comparación controlada identifica la secuencia de radios como un factor importante en el exceso de aberturas anterior. La animación no cambia la topología; se añadió mostrar el 100 % de caras para eliminar esa ambigüedad.

Los PLY originales se conservaron. Solo se actualizaron las mallas derivadas de la galería Bunny y fachada, con su configuración en `report.json`. Los radios efectivos, escala y reestimación de normales quedan registrados por trabajo CloudPE. Las nubes de cuadra dense/sparse ahora reciben una rotación de presentación de 180° sobre X (−Y arriba), heredada entre operaciones. No se rotan las coordenadas de cálculo ni los PLY exportados. Hay selección manual de ±Y/±Z para modelos con convenciones distintas.

Validación actual: **18 pruebas Python** y **4 pruebas Chromium/Playwright**, incluida igualdad entre radios relativos y absolutos equivalentes, reconstrucción con radios personalizados, overlay de bordes y orientación de la cuadra. Capturas: `frontend/test-results/bpa-advanced.png` y `frontend/test-results/cuadra-upright.png`. El usuario debe confirmar el encuadre deseado en su propia reconstrucción; no se ha inferido gravedad física desde cámaras.

---

## CloudPE: interfaz inmersiva (iteración actual)

Nueva aplicación en `http://127.0.0.1:8765`, ejecutada con `bash run_cloudpe.sh`. Three.js + Vite, API FastAPI, cálculos Python aislados por proceso. No se reemplaza ni elimina la aplicación Streamlit anterior.

Visor de pantalla completa, nube centrada hacia el espacio izquierdo, controles flotantes plegables, galería con seis miniaturas reales, intro CloudPE, revelado progresivo y onda radial por shader. La onda no modifica las coordenadas de cálculo. La transferencia muestra puntos recibidos; la animación posterior se etiqueta explícitamente como revelado visual.

La superficie puede reproducirse con pausa, velocidad y recorrido. Se ordenan caras radialmente: **no se ha implementado la esfera pivotando ni un trazado real del algoritmo BPA de Open3D**. El frontend actual conserva el pipeline principal, pero recorte y Delaunay siguen solo en la interfaz anterior/CLI.

Validación: **17 pruebas Python aprobadas** (incluye empaquetado binario en proceso aislado e historial). Pruebas Chromium/Playwright de galería, apertura del conejo, puntos, reproducción de malla, plegado del panel, limpieza y normales; adaptación móvil sin desbordamiento horizontal; rechazo de presupuestos inseguros y escrituras cross-origin. Capturas reales de navegador en `frontend/test-results/`. No se ha realizado benchmark de FPS en la GPU física de la laptop; Chromium headless empleó renderizado de prueba.

Memoria: máximo 50k por trabajo y un proceso de cálculo simultáneo. El servidor no conserva nubes en RAM; resultados en `.cloudpe/`. El navegador libera geometrías y materiales al cambiar de proyecto. Hay cancelación real del proceso, pero no un límite duro de RAM del sistema operativo. Las sesiones se acumulan en disco hasta que se gestionen manualmente.

---

## Revisión: memoria y galería precalculada

La interfaz inicial conservaba varias nubes completas y cargaba los archivos antes de reducirlos. Eso podía multiplicar el consumo de RAM; SIGKILL por sí solo no confirma OOM, pero había un riesgo real en el diseño. Se reemplazó por carga acotada previa a la construcción de arrays, un único estado para deshacer y galería en disco. La CLI también es segura por defecto; leer todo exige autorización explícita.

### Archivos nuevos verificados

| Archivo | Puntos originales | Tamaño | Atributos |
|---|---:|---:|---|
| `cuadra-025_0-10s_dense.ply` | 1 685 281 | 118,03 MiB | XYZ, RGB, normales, listas de observaciones `view_indices` y `view_weights` |
| `cuadra-025_0-10s_sparse.ply` | 19 707 | 0,282 MiB | XYZ y RGB |

Ambos carecen de caras. Son coherentes en rangos espaciales generales, pero esto no verifica registro perfecto ni escala física. La muestra densa y la nube sparse no mostraron coordenadas no finitas. Sparse presenta Z máximo 71,04 frente a 41,87 en la muestra densa: revisar extremos, sin asumir que todo punto extremo sea un error.

### Lectura segura medida

En un proceso nuevo, con muestreo limitado a 30k:

- PLY de **4 996 296 puntos**: **0,20 s** para obtener la muestra.
- Nueva densa de **1 685 281 puntos**, listas variables: **12,85 s** para obtener la muestra recorriendo el archivo sin materializar observaciones.
- Sparse de **19 707 puntos**: **0,003 s**, se conservan todos.
- Pico acumulado de RSS del proceso lector: **205,4 MiB**, incluyendo importaciones y páginas de memory mapping. **No es el pico de toda la aplicación ni del pipeline.**

Registro: `outputs/safe_loading_report.json`. Las estadísticas y espaciados de las muestras no son estadísticas de las nubes completas. El muestreo reduce detalle; no es procesamiento out-of-core de los millones de puntos.

### Ejemplos listos (sin recalcular al abrir)

| Ejemplo | Puntos procesados | Triángulos BPA |
|---|---:|---:|
| Fachada sintética con ventanas retranqueadas | 20 032 | 31 098 |
| Esfera ruidosa | 15 025 | 25 668 |
| Esquina | 12 014 | 20 117 |
| Cuadra densa, muestra de hasta 25k | 24 477 | 38 096 |
| Cuadra sparse | 18 872 | 21 517 |
| Stanford Bunny con ruido | 14 821 | 24 594 |

Los originales de cada ejemplo, resultados, malla y parámetros están en `examples/<nombre>/`. Bunny se descargó del recurso Open3D `https://github.com/isl-org/open3d_downloads/releases/download/20220201-data/BunnyMesh.ply` (Stanford 3D Scanning Repository); se muestreó su malla y añadió ruido gaussiano. No es una captura LiDAR ni COLMAP. La fachada es un generador propio, no simulación física de rayos ni sensor. Las nuevas nubes del usuario sí sirven como ejemplos fotogramétricos reales. Consultar condiciones de uso de Stanford antes de redistribuir su modelo.

### Validación revisada

**16 pruebas aprobadas**, incluidas lectura acotada, listas variables PLY en binario y ASCII, límites de presupuesto, galería precalculada y nuevo recorrido de interfaz. Se eliminó el uso obsoleto de `use_container_width`. La interfaz se reorganizó con galería lateral, indicadores, etapas y visor central. La verificación de interfaz es automatizada mediante AppTest, no una evaluación de usabilidad ni revisión visual humana.

---

Los siguientes resultados corresponden a la implementación inicial y se conservan como historial experimental; sus tiempos no describen el nuevo lector seguro.

## Entorno

Python 3.10.18 de pyenv, entorno local `.venv`, Open3D 0.19.0, NumPy 2.2.6 y SciPy 1.15.3. Sin CUDA. Dependencias verificadas con `pip check`. Originales PLY sin modificar.

## Pruebas automatizadas

**11 pruebas aprobadas**: PLY con atributos, limpieza de duplicados/no finitos/atípicos, PCA en plano, rechazo de vecindarios colineales, regiones de una esquina, grafo sin RGB, separación por color de un plano, BPA en esfera, Delaunay sobre hueco cuadrado respaldado y recorrido de interfaz sintética hasta generar malla. Prueba de interfaz mediante Streamlit AppTest; no sustituye inspección visual humana del navegador.

El test de color confirma que el mismo plano se mantiene en una región con peso cromático cero y se separa en dos al introducir rojo/azul. No demuestra segmentación semántica.

## Ejecuciones medidas

Tiempos de una ejecución local; no son benchmarks comparables rigurosos: hubo ejecuciones concurrentes, cachés y tamaños diferentes. El pico de RAM corresponde al proceso completo, incluyendo lectura del PLY original e importaciones, no solo al algoritmo.

| Caso | Entrada seleccionada | Tras limpieza | Triángulos BPA | Tiempo total | Pico RAM |
|---|---:|---:|---:|---:|---:|
| Esquina sintética, regiones + reparación | 12 240 | 12 014 | 18 304 | 8,74 s | 476 MiB |
| Densa bloque 25, submuestra + reparación | 30 000 | 29 240 | 36 434 | 19,26 s | 783 MiB |
| Combined bloque 1, submuestra, grafo | 30 000 | 29 270 | 28 008 | 2,76 s | 614 MiB |
| Densa bloque 25 completo, sin reparación | 53 482 | 52 060 | 65 884 | 4,43 s | 794 MiB |
| Esquina sintética, grafo | 12 240 | 12 014 | 18 304 | 1,28 s | 476 MiB |

Se excluye aproximadamente 10 % de los puntos limpios de la reconstrucción para validación. Las cantidades tras limpieza incluyen ese 10 %; la nube de trabajo exportada no. BPA usa la región de trabajo completa, no solo los segmentos asignados: cambiar la segmentación no cambia por sí mismo su malla.

### Normales

En la esquina con ruido σ=0,002, PCA k=30 obtuvo error angular sin signo **mediano 0,915° y p95 3,670°**, frente a las normales sintéticas conocidas. Incluye efectos de vecindarios cercanos a la esquina.

### Segmentación

- Esquina por regiones: **2 segmentos**, de 5 241 y 5 278 puntos; 291 residuales.
- Esquina por grafo con escala 2 y peso cromático 1: **13 segmentos**, 2 661 residuales. Los parámetros de ejemplo sobresegmentan esta nube ruidosa: no se presenta como mejora sobre regiones.
- Densa bloque 25 completo: **127 regiones y 23 819 puntos residuales**. La segmentación predeterminada es conservadora y fragmentada; requiere ajustar escala espacial, ángulo y tolerancia en una fachada seleccionada.
- Combined bloque 1, submuestra por grafo: **75 regiones y 20 549 residuales**. No se ha demostrado una segmentación satisfactoria de objetos en este conjunto.

### Malla del bloque 25 completo

65 884 triángulos, 958 componentes y 32 428 aristas de borde. No se detectaron aristas con más de dos caras en este ensayo. La gran fragmentación evidencia que **no tenemos una superficie urbana completa ni cerrada**.

Distancia validación → superficie: mediana **0,133**, p95 **1,358**, en unidades del modelo. Distancia superficie → puntos de validación: mediana **1,454**, p95 **3,849**. La segunda está condicionada por el muestreo escaso del conjunto de validación; no debe interpretarse como error contra una superficie verdadera. No hay ground truth para Barranco ni unidades físicas verificadas.

### Reparación Delaunay

En el ensayo de 30k del bloque 25 se aceptaron 103 contornos y se propusieron 116 triángulos; en la esquina, 108 contornos y 113 triángulos. Esto demuestra ejecución, **no mejora geométrica**. La prueba controlada del hueco cuadrado sí confirma que añade dos caras al hueco esperado y rechaza el contorno exterior por tamaño. Falta revisión visual de reparaciones reales, control global de intersecciones y evaluación externa para afirmar mejoras; mantenerla desactivada en resultados principales.

## Cómo reproducir y explorar

1. `bash run_app.sh` y abrir http://localhost:8501.
2. Elegir ejemplo sintético `corner`, generar, estimar normales y segmentar por regiones. Ver **Segmentos** y activar vectores normales.
3. Ejecutar BPA y seleccionar **Malla** en el visor.
4. Cargar `dense_preview_5M.ply`, recortar por bloque 25 y previsualizar limpieza. Confirmar, ejecutar PCA y BPA. Ajustar recortes menores para estudiar fachadas.
5. Exportar a una carpeta propia. Los resultados ya calculados están en `outputs/corner_run`, `outputs/corner_graph`, `outputs/barranco25`, `outputs/barranco25_full` y `outputs/combined1`.

## Pendientes y límites honestos

La versión entrega el recorrido funcional completo, no una solución universal ni un sistema de producción. No implementa semántica neuronal, LAS/LAZ, procesamiento out-of-core, trabajos cancelables, correspondencias completas de vóxeles ni reparación general de huecos. No se evaluó la escena entera de cinco millones con todos los algoritmos. El siguiente trabajo experimental es seleccionar una fachada bien cubierta, ajustar parámetros y revisar visualmente el resultado; no rellenar todos los huecos automáticamente.
