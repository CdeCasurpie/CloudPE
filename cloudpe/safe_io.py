"""Bounded-memory PLY reader, including OpenMVS variable-length properties.

Sampling occurs while reading, BEFORE constructing Cloud/attribute arrays.
List properties (camera observations) are skipped, never made into Python objects.
"""

import struct
from pathlib import Path

import numpy as np

from .core import Cloud

TYPES = {
    "char": "i1",
    "int8": "i1",
    "uchar": "u1",
    "uint8": "u1",
    "short": "i2",
    "int16": "i2",
    "ushort": "u2",
    "uint16": "u2",
    "int": "i4",
    "int32": "i4",
    "uint": "u4",
    "uint32": "u4",
    "float": "f4",
    "float32": "f4",
    "double": "f8",
    "float64": "f8",
}


def ply_header(path):
    with open(path, "rb") as f:
        if f.readline().strip() != b"ply":
            raise ValueError("No es un archivo PLY")
        properties = []
        count = None
        active = False
        fmt = None
        for _ in range(10000):
            line = f.readline()
            if not line:
                raise ValueError("Cabecera PLY incompleta")
            parts = line.decode("ascii").split()
            if not parts:
                continue
            if parts[0] == "format":
                fmt = parts[1]
            elif parts[0] == "element":
                active = parts[1] == "vertex"
                if active:
                    count = int(parts[2])
                elif count is None and int(parts[2]) > 0:
                    raise ValueError("Se requiere que vertex sea el primer elemento no vacío")
            elif parts[0] == "property" and active:
                properties.append(parts[1:])
            elif parts[0] == "end_header":
                break
        else:
            raise ValueError("Cabecera demasiado larga")
        if count is None or count <= 0:
            raise ValueError("PLY sin vértices")
        return {
            "points": count,
            "format": fmt,
            "properties": properties,
            "offset": f.tell(),
            "file_MiB": Path(path).stat().st_size / 2**20,
        }


def load_bounded(path, max_points=50000):
    """Deterministic stratified sample, at most max_points; no full-cloud allocation."""
    path = Path(path).expanduser()
    if not 100 <= max_points <= 100000:
        raise ValueError("El modo interactivo admite entre 100 y 100 000 puntos")
    if path.suffix.lower() != ".ply":
        # Other formats are only accepted when small: their readers aren't streaming.
        if path.stat().st_size > 8 * 2**20:
            raise ValueError("Para archivos grandes utiliza PLY; PCD/XYZ están limitados a 8 MiB")
        from .core import load_cloud

        cloud = load_cloud(path)
        if len(cloud.xyz) > max_points:
            cloud = cloud.select(np.linspace(0, len(cloud.xyz) - 1, max_points, dtype=int))
        return cloud
    header = ply_header(path)
    n = header["points"]
    props = header["properties"]
    rng = np.random.default_rng(42)
    if n > max_points:
        edges = np.linspace(0, n, max_points + 1, dtype=np.int64)
        selected = edges[:-1] + (rng.random(max_points) * np.diff(edges)).astype(np.int64)
    else:
        selected = np.arange(n)
    scalar = [p for p in props if p[0] != "list"]
    columns = {p[1]: np.empty(len(selected), dtype=TYPES[p[0]]) for p in scalar}
    fmt = header["format"]
    endian = "<" if fmt == "binary_little_endian" else ">"
    has_lists = any(p[0] == "list" for p in props)
    if fmt.startswith("binary") and not has_lists:
        dtype = np.dtype([(p[1], endian + TYPES[p[0]]) for p in scalar])
        if path.stat().st_size < header["offset"] + n * dtype.itemsize:
            raise ValueError("Archivo PLY truncado")
        data = np.memmap(path, mode="r", dtype=dtype, offset=header["offset"], shape=(n,))
        for key in columns:
            columns[key][:] = data[key][selected]
        del data
    else:
        # File is buffered. Reading skipped bytes avoids materializing list arrays.
        with path.open("rb") as f:
            f.seek(header["offset"])
            target = 0
            scalar_structs = {
                p[1]: struct.Struct(
                    endian
                    + {
                        "i1": "b",
                        "u1": "B",
                        "i2": "h",
                        "u2": "H",
                        "i4": "i",
                        "u4": "I",
                        "f4": "f",
                        "f8": "d",
                    }[TYPES[p[0]]]
                )
                for p in scalar
            }
            for i in range(n):
                take = target < len(selected) and i == selected[target]
                if fmt == "ascii":
                    tokens = f.readline().split()
                    cursor = 0
                    for p in props:
                        if p[0] == "list":
                            cursor += 1 + int(tokens[cursor])
                        else:
                            if take:
                                columns[p[1]][target] = float(tokens[cursor])
                            cursor += 1
                elif fmt.startswith("binary"):
                    for p in props:
                        if p[0] == "list":
                            dtype = np.dtype(endian + TYPES[p[1]])
                            raw = f.read(dtype.itemsize)
                            if len(raw) != dtype.itemsize:
                                raise ValueError("PLY truncado en lista")
                            length = int(np.frombuffer(raw, dtype=dtype)[0])
                            if not 0 <= length <= 1000000:
                                raise ValueError("Longitud de lista PLY inválida")
                            size = length * np.dtype(TYPES[p[2]]).itemsize
                            if len(f.read(size)) != size:
                                raise ValueError("PLY truncado en observaciones")
                        else:
                            decoder = scalar_structs[p[1]]
                            raw = f.read(decoder.size)
                            if len(raw) != decoder.size:
                                raise ValueError("PLY truncado en vértices")
                            if take:
                                columns[p[1]][target] = decoder.unpack(raw)[0]
                else:
                    raise ValueError(f"Formato PLY no soportado: {fmt}")
                if take:
                    target += 1
    xyz = np.column_stack([columns.pop(k) for k in ("x", "y", "z")])
    attrs = {}
    for keys, name in [(("red", "green", "blue"), "rgb"), (("nx", "ny", "nz"), "normals")]:
        if all(k in columns for k in keys):
            attrs[name] = np.column_stack([columns.pop(k) for k in keys])
    attrs.update(columns)
    attrs.setdefault("source_index", selected)
    valid = np.isfinite(xyz).all(1)
    cloud = Cloud(
        xyz[valid],
        {k: v[valid] for k, v in attrs.items()},
        [
            {
                "operation": "bounded_load",
                "path": str(path.resolve()),
                "original_points": n,
                "loaded_points": int(valid.sum()),
                "max_points": max_points,
                "sampling": "stratified deterministic seed 42",
                "skipped_list_attributes": has_lists,
            }
        ],
    )
    if len(cloud.xyz) < 4:
        raise ValueError("No hay suficientes puntos finitos")
    return cloud
