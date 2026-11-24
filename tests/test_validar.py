"""El revisor de envíos: acepta lo bueno y señala lo malo."""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
APP = Path(os.environ.get("APP_REPRODUCTOR", RAIZ.parent / "visualizador"))
sys.path.insert(0, str(RAIZ / "herramientas"))
import validar  # noqa: E402


@pytest.fixture
def raiz(tmp_path):
    for c in ("entradas", "plantillas", "previas"):
        shutil.copytree(RAIZ / c, tmp_path / c)
    return tmp_path


def problemas(raiz):
    return validar.revisar(raiz, APP)[0]


def test_lo_publicado_es_valido():
    errores, registros = validar.revisar(RAIZ, APP)
    assert errores == [] and len(registros) >= 3


def test_falta_un_archivo(raiz):
    (raiz / "previas" / "ambiente-menta.webp").unlink()
    assert any("faltan archivos en previas" in e for e in problemas(raiz))


def test_nombre_de_archivo_invalido(raiz):
    shutil.copy(raiz / "entradas" / "ambiente-menta.json", raiz / "entradas" / "Mala Entrada.json")
    assert any("minúsculas" in e for e in problemas(raiz))


def test_entrada_con_campos_de_mas_o_texto_largo(raiz):
    f = raiz / "entradas" / "ambiente-menta.json"
    f.write_text(json.dumps({"nombre": "x" * 80, "autor": "a", "descripcion": "d", "enlace": "http://malo"}))
    e = problemas(raiz)
    assert any("solo puede traer" in x for x in e) and any("muy largo" in x for x in e)


def test_archivo_que_no_es_una_plantilla(raiz):
    (raiz / "plantillas" / "ambiente-menta.plantilla").write_bytes(b"esto no es un zip")
    assert any("no es válido" in e for e in problemas(raiz))


def test_vista_previa_mala(raiz):
    Image.new("RGB", (300, 300)).save(raiz / "previas" / "ambiente-menta.webp", "WEBP")   # cuadrada y chica
    assert any("16:9" in e for e in problemas(raiz))
    (raiz / "previas" / "ambiente-menta.webp").write_bytes(b"no es imagen")
    assert any("no es una imagen" in e for e in problemas(raiz))


# ---- origen de las imágenes ----
def con_imagen(raiz, imagenes=None, slug="con-fondo"):
    """Agrega un envío cuyo archivo trae un fondo propio; `imagenes` es lo que declara la entrada."""
    ajustes, _ = validar.cargar_app(APP)
    origen = raiz / "_origen"
    origen.mkdir(exist_ok=True)
    Image.new("RGB", (64, 36), (10, 90, 200)).save(origen / "liquido-fondo.webp", "WEBP")
    datos = {"plantilla": "liquido", "variante": {}, "props": {"fondo": "/imagen?n=liquido-fondo.webp&v=1"}}
    (raiz / "plantillas" / f"{slug}.plantilla").write_bytes(ajustes.empaquetar(json.dumps(datos), origen))
    shutil.copy(raiz / "previas" / "ambiente-menta.webp", raiz / "previas" / f"{slug}.webp")
    entrada = {"nombre": "Con fondo", "autor": "Ana", "descripcion": "Trae una imagen."}
    if imagenes is not None:
        entrada["imagenes"] = imagenes
    (raiz / "entradas" / f"{slug}.json").write_text(json.dumps(entrada), encoding="utf-8")
    return validar.revisar(raiz, APP)


def test_imagenes_sin_declarar(raiz):
    errores, _ = con_imagen(raiz)
    assert any("falta declarar" in e for e in errores)


@pytest.mark.parametrize("imagenes", [{"origen": "propio"}, {"origen": "ia", "detalle": "Higgsfield"}, {"origen": "libre", "detalle": "CC0 · pexels.com"}])
def test_imagenes_declaradas(raiz, imagenes):
    errores, registros = con_imagen(raiz, imagenes)
    assert errores == []
    assert [r for r in registros if r["id"] == "con-fondo"][0]["imagenes"]["origen"] == imagenes["origen"]


@pytest.mark.parametrize("imagenes", [{"origen": "libre"}, {"origen": "ia", "detalle": "  "}, {"origen": "robado"}, {"origen": "propio", "x": 1}, "propio", {"origen": "propio", "detalle": "a" * 200}])
def test_declaracion_mala(raiz, imagenes):
    errores, _ = con_imagen(raiz, imagenes)
    assert errores


def test_declarar_imagenes_donde_no_hay(raiz):
    f = raiz / "entradas" / "ambiente-menta.json"
    e = json.loads(f.read_text(encoding="utf-8"))
    e["imagenes"] = {"origen": "propio"}
    f.write_text(json.dumps(e), encoding="utf-8")
    assert any("no trae ninguna" in x for x in problemas(raiz))
