# Ejemplos distribuidos con CloudPE

Estas seis carpetas se incluyen directamente en Git. Cada una contiene:

- `original.ply`: entrada del ejemplo (muestra, nube sintética o nube suministrada).
- `processed.ply`: nube preparada con atributos y etiquetas.
- `mesh.ply`: resultado BPA precalculado.
- `report.json`: procedencia, parámetros disponibles y métricas.

| Carpeta | Procedencia |
|---|---|
| `bunny` | Stanford Bunny, descargado con `Open3D.data.BunnyMesh`, muestreado y perturbado con ruido gaussiano. Crédito: Stanford University Computer Graphics Laboratory. Ver condiciones en `../THIRD_PARTY_NOTICES.md`. |
| `fachada` | Generador propio: pared y tres superficies de ventana retranqueadas, ruido y puntos espurios. No simula visibilidad física ni LiDAR. |
| `esfera` | Generador propio de esfera con ruido y outliers; conserva normales de referencia como atributos. |
| `esquina` | Generador propio de dos planos perpendiculares con ruido y outliers. |
| `cuadra_dense` | Muestra de hasta 25k puntos de `cuadra-025_0-10s_dense.ply`, proporcionado por el autor del proyecto. El original completo no se distribuye. |
| `cuadra_sparse` | Entrada derivada de `cuadra-025_0-10s_sparse.ply`, proporcionado por el autor del proyecto. |

La galería no vuelve a ejecutar los algoritmos al abrir un ejemplo. Empaqueta estos resultados para el visor; posteriormente puedes recalcular las etapas.

Los datos de la cuadra se muestran con −Y arriba; las coordenadas almacenadas no se rotaron. Las mallas pueden contener aberturas: son resultados de estudio, no modelos reparados manualmente.

`manifest.json` registra tamaño y SHA-256 de los 24 archivos de datos/resultados, para comprobar que el clon incluye todos los ejemplos intactos.
