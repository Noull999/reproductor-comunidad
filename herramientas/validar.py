"""
Revisa los envíos de la comunidad: cada plantilla son tres archivos con el mismo nombre (slug):
  entradas/<slug>.json      nombre, autor y descripción (y de dónde vienen las imágenes, si las hay)
  plantillas/<slug>.plantilla   el archivo que exporta la app (una plantilla del Editor o los ajustes de una incluida)
  previas/<slug>.webp       una captura de cómo se ve

Usa los mismos validadores que la app (plantillas.py y ajustes.py del repo reproductor-visual) y las mismas reglas de envío
que el servidor (api/_lib/envio.py), así que un archivo que pasa aquí también se puede importar allá. Nada de lo que viene
en los archivos se ejecuta.

    python herramientas/validar.py <carpeta de la app>
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api" / "_lib"))
import envio  # noqa: E402
from envio import CAMPOS, MAX_SLUG, SLUG  # noqa: E402


def cargar_app(carpeta):
    sys.path.insert(0, str(Path(carpeta).resolve()))
    import ajustes
    import plantillas
    return ajustes, plantillas


def revisar(raiz, app):
    """Devuelve (errores, registros). Un registro por plantilla válida, listo para el catálogo."""
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
            if not isinstance(e, dict) or set(e) - set(CAMPOS) - {"imagenes"}:
                errores.append(f"{slug}: la entrada solo puede traer {', '.join(CAMPOS)} e imagenes.")
                e = e if isinstance(e, dict) else {}
        except (ValueError, UnicodeDecodeError):
            errores.append(f"{slug}: la entrada no es un JSON válido.")
            e = {}
        meta = {c: envio.texto(e, c, errores, slug) for c in CAMPOS}
        tipo, base_, hay_imagenes = "", "", False
        try:
            tipo, base_, hay_imagenes = envio.revisar_archivo((raiz / "plantillas" / f"{slug}.plantilla").read_bytes(), ajustes, plantillas)
        except plantillas.PlantillaInvalida as x:
            errores.append(f"{slug}: el archivo no es válido ({x}).")
        motivo = envio.revisar_previa((raiz / "previas" / f"{slug}.webp").read_bytes(), slug)
        if motivo:
            errores.append(motivo)
        origen = envio.origen_de_imagenes(e, hay_imagenes, errores, slug) if tipo else None
        if len(errores) == antes:
            registros.append({"id": slug, **meta, "tipo": tipo, "base": base_, **({"imagenes": origen} if origen else {})})
    return errores, registros


if __name__ == "__main__":
    app = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ.parent / "visualizador")
    errores, registros = revisar(RAIZ, app)
    for m in errores:
        print("✗", m)
    print(f"{len(registros)} plantillas válidas, {len(errores)} problemas.")
    sys.exit(1 if errores else 0)
