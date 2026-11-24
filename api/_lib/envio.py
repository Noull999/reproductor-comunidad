"""
Las reglas de un envío a la comunidad, en un solo lugar: las usan el revisor de pull requests (herramientas/validar.py)
y el servidor de la subida directa. Nada de lo que viene en un envío se ejecuta: se revisa campo por campo.
Los módulos de la app (ajustes y plantillas) se pasan como argumento para que cada uso cargue los suyos.
"""
import io
import re
import tempfile
from pathlib import Path

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG = 40
MAX_PLANTILLA = 10 * 1024 * 1024
MAX_PREVIA = 600 * 1024
CAMPOS = {"nombre": 40, "autor": 30, "descripcion": 200}
ORIGENES = {"propio": "propias", "ia": "hechas con IA", "libre": "de licencia libre"}   # de dónde vienen las imágenes del archivo
MAX_DETALLE = 120


def texto(d, campo, errores, rotulo):
    v = d.get(campo)
    if not isinstance(v, str) or not v.strip():
        errores.append(f"{rotulo}: falta «{campo}».")
        return ""
    v = v.strip()
    if len(v) > CAMPOS[campo] or any(not c.isprintable() for c in v):
        errores.append(f"{rotulo}: «{campo}» es muy largo (máx. {CAMPOS[campo]}) o trae caracteres raros.")
    return v


def origen_de_imagenes(e, hay_imagenes, errores, rotulo):
    """La declaración de dónde salen las imágenes: obligatoria si el archivo trae imágenes, y no va si no las trae."""
    d = e.get("imagenes")
    if d is None:
        if hay_imagenes:
            errores.append(f"{rotulo}: el archivo trae imágenes y falta declarar de dónde vienen (campo «imagenes»: origen «propio», «ia» o «libre»).")
        return None
    if not hay_imagenes:
        errores.append(f"{rotulo}: declara «imagenes» pero el archivo no trae ninguna.")
        return None
    if not isinstance(d, dict) or set(d) - {"origen", "detalle"} or d.get("origen") not in ORIGENES:
        errores.append(f"{rotulo}: «imagenes» debe ser {{\"origen\": propio|ia|libre, \"detalle\": ...}}.")
        return None
    detalle = d.get("detalle", "")
    if not isinstance(detalle, str) or len(detalle.strip()) > MAX_DETALLE or any(not c.isprintable() for c in detalle):
        errores.append(f"{rotulo}: el detalle de «imagenes» es muy largo (máx. {MAX_DETALLE}) o trae caracteres raros.")
        return None
    if d["origen"] != "propio" and not detalle.strip():
        errores.append(f"{rotulo}: con origen «{d['origen']}» hay que decir cuál (la herramienta de IA, o la fuente y la licencia).")
        return None
    return {"origen": d["origen"], "detalle": detalle.strip()}


def revisar_archivo(datos, ajustes, plantillas):
    """Abre el .plantilla con los revisores de la app. Devuelve (tipo, base, hay_imagenes) o lanza PlantillaInvalida."""
    if len(datos) > MAX_PLANTILLA:
        raise plantillas.PlantillaInvalida(f"el archivo pesa más de {MAX_PLANTILLA // 1024 // 1024} MB")
    with tempfile.TemporaryDirectory() as tmp:
        if ajustes.es_de_ajustes(datos):
            r = ajustes.desempaquetar(datos, Path(tmp))
            tipo, base = "ajustes", r["plantilla"]
        else:
            r = plantillas.desempaquetar(datos, "pvalidar", Path(tmp))
            tipo, base = "plantilla", r.get("base") or ""
        return tipo, base, any(Path(tmp).glob("*.webp"))


def revisar_previa(datos, rotulo):
    """None si la captura sirve; si no, el motivo."""
    from PIL import Image
    if len(datos) > MAX_PREVIA:
        return f"{rotulo}: la vista previa pesa más de {MAX_PREVIA // 1024} KB."
    try:
        with Image.open(io.BytesIO(datos)) as im:
            if im.format != "WEBP" or im.width < 480 or im.height < 270 or abs(im.width / im.height - 16 / 9) > .12:
                return f"{rotulo}: la vista previa debe ser WebP, de al menos 480×270 y en proporción 16:9."
    except Exception:
        return f"{rotulo}: la vista previa no es una imagen válida."
    return None
