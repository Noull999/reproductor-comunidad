"""
Revisa los envíos de la comunidad: cada plantilla son tres archivos con el mismo nombre (slug):
  entradas/<slug>.json      nombre, autor y descripción
  plantillas/<slug>.plantilla   el archivo que exporta la app (una plantilla del Editor o los ajustes de una incluida)
  previas/<slug>.webp       una captura de cómo se ve

Usa los mismos validadores que la app (plantillas.py y ajustes.py del repo reproductor-visual), así que
un archivo que pasa aquí también se puede importar allá. Nada de lo que viene en los archivos se ejecuta.

    python herramientas/validar.py <carpeta de la app>
"""
import io
import json
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG = 40
MAX_PLANTILLA = 10 * 1024 * 1024
MAX_PREVIA = 600 * 1024
CAMPOS = {"nombre": 40, "autor": 30, "descripcion": 200}


def cargar_app(carpeta):
    sys.path.insert(0, str(Path(carpeta).resolve()))
    import ajustes
    import plantillas
    return ajustes, plantillas


def _texto(d, campo, errores, slug):
    v = d.get(campo)
    if not isinstance(v, str) or not v.strip():
        errores.append(f"{slug}: falta «{campo}».")
        return ""
    v = v.strip()
    if len(v) > CAMPOS[campo] or any(not c.isprintable() for c in v):
        errores.append(f"{slug}: «{campo}» es muy largo (máx. {CAMPOS[campo]}) o trae caracteres raros.")
    return v


def revisar(raiz, app):
    """Devuelve (errores, registros). Un registro por plantilla válida, listo para el catálogo."""
    from PIL import Image
    ajustes, plantillas = cargar_app(app)
    raiz = Path(raiz)
    errores, registros = [], []
    carpetas = {"entradas": ".json", "plantillas": ".plantilla", "previas": ".webp"}
    nombres = {}
    for carpeta, ext in carpetas.items():
        base = raiz / carpeta
        nombres[carpeta] = set()
        for f in (base.iterdir() if base.is_dir() else []):
            if f.name == ".gitkeep":
                continue
            if f.suffix != ext or not SLUG.match(f.stem) or len(f.stem) > MAX_SLUG:
                errores.append(f"{carpeta}/{f.name}: el nombre debe ser minúsculas, números y guiones (máx. {MAX_SLUG}), terminado en {ext}.")
            else:
                nombres[carpeta].add(f.stem)
    todos = set().union(*nombres.values())
    for slug in sorted(todos):
        faltan = [c for c in carpetas if slug not in nombres[c]]
        if faltan:
            errores.append(f"{slug}: faltan archivos en {', '.join(faltan)} (cada plantilla lleva los tres).")
    for slug in sorted(set.intersection(*nombres.values()) if all(nombres.values()) else set()):
        antes = len(errores)
        try:
            e = json.loads((raiz / "entradas" / f"{slug}.json").read_text(encoding="utf-8"))
            if not isinstance(e, dict) or set(e) - set(CAMPOS):
                errores.append(f"{slug}: la entrada solo puede traer {', '.join(CAMPOS)}.")
                e = e if isinstance(e, dict) else {}
        except (ValueError, UnicodeDecodeError):
            errores.append(f"{slug}: la entrada no es un JSON válido.")
            e = {}
        meta = {c: _texto(e, c, errores, slug) for c in CAMPOS}
        archivo = raiz / "plantillas" / f"{slug}.plantilla"
        datos = archivo.read_bytes()
        tipo, base_ = "", ""
        if len(datos) > MAX_PLANTILLA:
            errores.append(f"{slug}: el archivo pesa más de {MAX_PLANTILLA // 1024 // 1024} MB.")
        else:
            with tempfile.TemporaryDirectory() as tmp:
                try:
                    if ajustes.es_de_ajustes(datos):
                        r = ajustes.desempaquetar(datos, Path(tmp))
                        tipo, base_ = "ajustes", r["plantilla"]
                    else:
                        r = plantillas.desempaquetar(datos, "pvalidar", Path(tmp))
                        tipo, base_ = "plantilla", r.get("base") or ""
                except plantillas.PlantillaInvalida as x:
                    errores.append(f"{slug}: el archivo no es válido ({x}).")
        previa = raiz / "previas" / f"{slug}.webp"
        if previa.stat().st_size > MAX_PREVIA:
            errores.append(f"{slug}: la vista previa pesa más de {MAX_PREVIA // 1024} KB.")
        else:
            try:
                with Image.open(previa) as im:
                    if im.format != "WEBP" or im.width < 480 or im.height < 270 or abs(im.width / im.height - 16 / 9) > .12:
                        errores.append(f"{slug}: la vista previa debe ser WebP, de al menos 480×270 y en proporción 16:9.")
            except Exception:
                errores.append(f"{slug}: la vista previa no es una imagen válida.")
        if len(errores) == antes:
            registros.append({"id": slug, **meta, "tipo": tipo, "base": base_})
    return errores, registros


if __name__ == "__main__":
    app = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ.parent / "visualizador")
    errores, registros = revisar(RAIZ, app)
    for m in errores:
        print("✗", m)
    print(f"{len(registros)} plantillas válidas, {len(errores)} problemas.")
    sys.exit(1 if errores else 0)
