# Herramientas de desarrollo

Estos scripts **no son necesarios para iniciar CloudPE**: la galería ya está incluida. Ejecutarlos desde la raíz del repositorio, con el proyecto instalado en `.venv`.

| Script | Función | ¿Modifica ejemplos? |
|---|---|---|
| `verify_examples.py` | Comprueba los 24 archivos contra SHA-256 | No, salvo `--write` |
| `build_gallery.py` | Genera ejemplos sintéticos y opcionalmente Bunny/cuadra | Sí |
| `review_bpa.py` | Compara radios y guarda reporte en `outputs/` | Sí, mallas y reportes Bunny/fachada |
| `build_previews.py` | Regenera miniaturas reales de la galería | Solo `frontend/public/previews/` |

## Verificar sin modificar nada

```bash
.venv/bin/python scripts/verify_examples.py
```

## Regenerar

```bash
.venv/bin/python scripts/build_gallery.py --bunny
.venv/bin/python scripts/review_bpa.py
.venv/bin/python scripts/build_previews.py
.venv/bin/python scripts/verify_examples.py --write
cd frontend
npm run build
```

Bunny necesita internet la primera vez y mantiene las condiciones de Stanford. Para regenerar también la cuadra desde sus originales, añade `--user-data-dir /ruta/a/las/nubes` a `build_gallery.py`; se esperan `cuadra-025_0-10s_dense.ply` y `cuadra-025_0-10s_sparse.ply`. Si no se indica esa carpeta, los ejemplos de cuadra distribuidos no se modifican.

Actualiza el manifiesto únicamente cuando hayas revisado y decidido conservar cambios en los ejemplos. Las pruebas fallan si sus datos cambian sin actualizarlo.
