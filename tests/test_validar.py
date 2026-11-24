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
