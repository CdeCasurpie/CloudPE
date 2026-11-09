# Procedencia y condiciones de terceros

## Stanford Bunny

Los archivos de `examples/bunny/` y su miniatura derivan del **Stanford Bunny**, del **Stanford University Computer Graphics Laboratory**. Se obtuvo la malla mediante `Open3D.data.BunnyMesh`, se muestrearon puntos, se añadió ruido gaussiano y se aplicó el pipeline de CloudPE.

- Fuente y condiciones: https://graphics.stanford.edu/data/3Dscanrep/
- Recurso usado por Open3D: https://github.com/isl-org/open3d_downloads/releases/download/20220201-data/BunnyMesh.ply
- Reconstrucción original: Greg Turk y Marc Levoy, *Zippered Polygon Meshes from Range Images*, SIGGRAPH 1994.

La página de Stanford permite uso para investigación y redistribución gratuita, solicita reconocer la fuente y restringe el uso comercial o en productos para venta sin su permiso. Esta nota es un resumen: prevalecen las condiciones de la fuente. No se presenta este dataset como MIT, CC0 ni dominio público. Las imágenes y resultados derivados deben mantener la atribución correspondiente.

Stanford también advierte que una malla reconstruida muestreada no sustituye datos crudos reales para evaluar rigurosamente reconstrucción de superficies. El ejemplo de CloudPE es didáctico, no un benchmark de sensor físico.

## Dependencias y fuentes tipográficas

CloudPE usa Three.js, Vite, FastAPI, Uvicorn, NumPy, SciPy, Open3D, plyfile, scikit-image y herramientas adicionales enumeradas en sus archivos de dependencias. Cada paquete mantiene su propia licencia; las dependencias no se incluyen como código vendorizado.

Las fuentes DM Sans y Space Grotesk se sirven desde paquetes `@fontsource`, instalados localmente por npm. Sus archivos de licencia se encuentran en los paquetes correspondientes dentro de `frontend/node_modules/`; las fuentes están distribuidas bajo SIL Open Font License. Esta atribución no cambia sus condiciones.

## Datos del autor y código propio

Las muestras de cuadra fueron proporcionadas por el autor para su publicación con el proyecto. La fachada, esfera y esquina son generadores del proyecto. No se ha seleccionado todavía una licencia general para el código y datasets propios. No inferir permisos de terceros a partir de la visibilidad pública del repositorio.
