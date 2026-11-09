# Resultados y validación

## Contexto

Entorno probado: Linux, Python 3.10.18 de pyenv, Open3D 0.19.0, NumPy 2.2.6 y SciPy 1.15.3. Procesamiento CPU. Los tiempos son orientativos, no benchmarks controlados entre máquinas.

## Normales y segmentación

En la esquina sintética con ruido σ=0,002 y PCA k=30, una ejecución con puntos reservados obtuvo error angular sin signo **mediano 0,915° y p95 3,670°**, frente a normales conocidas. La segmentación por regiones obtuvo dos regiones principales. Las pruebas sintéticas también verifican que el peso cromático puede dividir un plano rojo/azul que sin color permanece unido.

No hay ground truth de normales, objetos ni superficies para la cuadra. La segmentación de escenas reales puede fragmentarse y dejar puntos residuales; no se presenta como reconocimiento semántico de edificios.

## Comparación controlada de radios BPA

Mismos puntos procesados y normales; solo se modificó la secuencia de radios, expresados como múltiplos del espaciado mediano al vecino más cercano. Sin rellenar huecos ni suavizar coordenadas.

| Ejemplo | Radios | Triángulos | Aristas de borde | Componentes |
|---|---|---:|---:|---:|
| Bunny | 1.5, 2.5, 4 | 24 594 | 10 530 | 87 |
| Bunny | **2.5, 4, 6** | **25 697** | **2 067** | **2** |
| Bunny | 3, 5, 8 | 24 871 | 855 | 2 |
| Bunny | 4, 6, 9 | 22 716 | 306 | 2 |
| Fachada | 1.5, 2.5, 4 | 31 098 | 15 682 | 127 |
| Fachada | **2.5, 4, 6** | **31 991** | **2 789** | **5** |
| Fachada | 3, 5, 8 | 30 171 | 1 411 | 4 |
| Fachada | 4, 6, 9 | 26 589 | 1 001 | 7 |

El ajuste recomendado redujo aristas de borde aproximadamente 80 % en Bunny y 82 % en fachada frente al inicial. **No equivale a ese porcentaje de huecos reparados ni a mayor exactitud**: las aristas incluyen el contorno exterior y los radios grandes pueden saltarse detalles o unir superficies separadas.

No se eligió automáticamente la configuración de menor borde. La fracción observada de parejas vecinas con normales opuestas fue pequeña (aproximadamente 0,034 % en Bunny y 0,040 % en fachada), pero no descarta errores locales.

Reproducción: `.venv/bin/python scripts/review_bpa.py`. Genera `outputs/bpa_radius_review.json` y actualiza mallas derivadas de esos dos ejemplos. Si decides conservar los cambios de galería, actualiza su manifiesto después.

## Carga segura y memoria

Un proceso lector limitado a 30k puntos obtuvo:

| Archivo | Puntos originales | Tiempo de lectura |
|---|---:|---:|
| PLY de registro fijo de la escena grande | 4 996 296 | 0,20 s |
| Cuadra densa, con listas variables OpenMVS | 1 685 281 | 12,85 s |
| Cuadra sparse | 19 707 | 0,003 s |

Pico acumulado de RSS del **proceso lector**: 205,4 MiB. No incluye todo el pipeline ni el navegador. Una ejecución posterior completa de CLI con muestra de 30k de la cuadra densa tardó 15,2 s, produjo 41 622 triángulos y registró aproximadamente 477 MiB de pico de RAM del proceso.

Estas medidas **no representan procesamiento de todos los millones de puntos**. La interfaz conserva hasta 50k activos, un trabajo aislado simultáneo y buffers del visor. No existe un límite duro de RAM del sistema operativo ni limpieza automática de sesiones en disco.

## Evaluación reproducible

La CLI reserva aproximadamente 10 % de los puntos limpios antes de PCA, segmentación y BPA. Reporta distancias punto→malla y malla→puntos, tiempos y RAM. La limpieza usa la muestra completa antes de reservar validación: no es una evaluación externa estrictamente independiente. Las distancias inversas dependen del espaciado del conjunto reservado. Ninguna sustituye una superficie de referencia real.

```bash
.venv/bin/cloudpe run examples/esquina/original.ply --output outputs/esquina
.venv/bin/cloudpe run examples/cuadra_dense/original.ply --output outputs/cuadra
```

## Pruebas de entrega

La versión reorganizada supera **19 pruebas Python y 4 pruebas de navegador**. Se retiraron las pruebas de la interfaz Streamlit eliminada y se añadieron comprobaciones de API. Los seis ejemplos conservan exactamente los mismos hashes; la reorganización no cambió sus datos.

- Pruebas Python: lectura PLY fija y variable (ASCII/binario), presupuesto de carga, atributos, limpieza, PCA, vecindarios degenerados, segmentación, color, BPA, radios relativos/absolutos equivalentes, extensión Delaunay aislada, buffers del worker, API y ejemplos íntegros.
- Cuatro pruebas Chromium/Playwright: recorrido visual, móvil sin desbordamiento horizontal, validación de peticiones y configuración avanzada BPA/orientación.
- La integridad de los **24 archivos de ejemplo** se verifica contra un manifiesto SHA-256.

Las capturas de interfaz son reales. Las pruebas de navegador utilizaron Chromium headless con renderizado de prueba; no se ha medido FPS sobre la GPU física de cada laptop.

## Extensión experimental

La reparación Delaunay está aislada en `cloudpe/experimental.py`, accesible con `cloudpe run ... --repair`. Solo considera contornos pequeños, convexos, planos y respaldados por puntos. Una prueba controlada verifica un hueco cuadrado. No se ha demostrado mejora general en datos reales ni ausencia de intersecciones globales. **No forma parte del resultado principal presentado.**
