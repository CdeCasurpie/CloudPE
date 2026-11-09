# Proyecto final — CloudPE

## Objetivo

Recibir una nube de puntos y demostrar las tres operaciones del enunciado: **normales, segmentación y reconstrucción de malla**. Se añaden tareas habituales de preparación para obtener resultados interpretables, sin CUDA.

## Alcance de la versión presentada

1. Carga segura y exploración de nubes.
2. Eliminación de datos inválidos, duplicados y atípicos; reducción por vóxeles.
3. Estimación de normales mediante PCA local, confianza y orientación.
4. Segmentación geométrica y geométrico-cromática.
5. Reconstrucción con Ball Pivoting y parámetros editables.
6. Visualización de resultados, diagnóstico y exportación.

La galería precalculada permite una exposición sin depender de ejecutar operaciones costosas en vivo. Es posible volver a ejecutar cada etapa. Los originales permanecen intactos.

## Arquitectura

```text
Three.js / navegador
       ↕ API HTTP + datos binarios
FastAPI / servidor local
       ↓ subprocess (un trabajo simultáneo)
Worker Python → algoritmos CPU
       ↓
.cloudpe/<id>/ → nube, malla, reporte e historial
```

| Archivo | Responsabilidad |
|---|---|
| `cloudpe/core.py` | Modelo de nube, E/S, limpieza, PCA, orientación, segmentos y BPA |
| `cloudpe/safe_io.py` | Lectura limitada sin materializar toda la nube |
| `cloudpe/web.py` | API local, validación y ciclo de vida de trabajos |
| `cloudpe/worker.py` | Ejecutar una etapa y empaquetar resultados en un proceso aislado |
| `cloudpe/cli.py` | Experimentos reproducibles y evaluación con puntos reservados |
| `cloudpe/examples.py` | Generador de fachada |
| `cloudpe/experimental.py` | Reparación Delaunay opcional, separada del alcance principal |
| `frontend/src/` | Visor, shaders, pipeline y diseño de controles flotantes |

El servidor no conserva arrays de nubes en RAM. El navegador libera geometrías al sustituirlas. Cancelar termina el proceso de cálculo; apagar normalmente el servidor también termina sus trabajos activos.

## Qué es propio y qué se reutiliza

| Componente | Implementado en el proyecto | Biblioteca utilizada |
|---|---|---|
| Normales | Vecindarios, covarianzas, selección del autovector y confianza | SciPy busca vecinos; NumPy resuelve autovalores |
| Orientación | Propagación de signos sobre un bosque de expansión mínimo | SciPy calcula el bosque |
| Segmentación por regiones | Semillas y criterios espacial/angular/punto–plano | SciPy gestiona vecindad y matrices dispersas |
| Segmentación por grafo | Costos y fusión adaptativa de componentes | scikit-image convierte RGB a CIELAB |
| Limpieza | Reglas de deduplicación, vóxeles y descarte estadístico | NumPy y SciPy como herramientas numéricas |
| Reconstrucción | Preparación, escala de radios e integración | **BPA es Open3D**, no implementación propia |
| Visor y experiencia | Controles, estados, animaciones y shaders | Three.js renderiza y gestiona la cámara |
| Delaunay experimental | Detección/validación del contorno y soporte | SciPy realiza la triangulación |

No se afirma haber creado un algoritmo nuevo. La segmentación de grafos está inspirada en Felzenszwalb–Huttenlocher, adaptada al grafo espacial; no es una reproducción exacta del algoritmo para imágenes.

## Recorrido sugerido para la exposición (8–10 minutos)

1. **Problema y datos:** explicar el enunciado y abrir el Bunny precalculado.
2. **Limpieza:** utilizar la esquina/fachada para explicar ruido, duplicados y reducción. El filtro puede borrar geometría válida si se exagera.
3. **Normales:** mostrar vectores y explicar que PCA aproxima un plano local. `k` pequeño conserva detalle, `k` grande estabiliza pero mezcla bordes.
4. **Segmentación:** mostrar regiones y aclarar que agrupar superficies/color no equivale a reconocer edificios o vegetación.
5. **Malla:** abrir superficie del Bunny; comparar `2.5, 4, 6` con `3, 5, 8`. Mostrar bordes abiertos y advertir del riesgo de puentes artificiales.
6. **Datos reales:** abrir cuadra dense/sparse y explicar por qué una nube dispersa no asegura una buena superficie.
7. **Conclusiones:** presentar las métricas de `RESULTS.md` y las limitaciones, no solo resultados visuales.

La reproducción de malla se etiqueta como **visualización de caras**, no como los pasos reales de BPA. No hay progreso ficticio de cálculo: las fases sin avance disponible muestran actividad indeterminada.

## Qué no se promete

No hay semántica neuronal, visibilidad de cámaras, procesamiento out-of-core ni mallado garantizado de cinco millones de puntos. El límite interactivo es 50k puntos; muestrear reduce detalle. La orientación del visor no estima gravedad física. Los datasets sintéticos no sustituyen una evaluación de datos reales con ground truth.

## Referencias

- Hoppe et al., *Surface Reconstruction from Unorganized Points*, SIGGRAPH 1992.
- Bernardini et al., *The Ball-Pivoting Algorithm for Surface Reconstruction*, IEEE TVCG 1999.
- Felzenszwalb y Huttenlocher, *Efficient Graph-Based Image Segmentation*, IJCV 2004.
- [Open3D: surface reconstruction](https://www.open3d.org/docs/release/tutorial/geometry/surface_reconstruction.html).
