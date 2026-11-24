"""El catálogo: el usuario de GitHub verificado se consulta una vez y se conserva."""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
APP = Path(os.environ.get("APP_REPRODUCTOR", RAIZ.parent / "visualizador"))
sys.path.insert(0, str(RAIZ / "herramientas"))
import construir  # noqa: E402


@pytest.fixture
def raiz(tmp_path):
    for c in ("entradas", "plantillas", "previas"):
        shutil.copytree(RAIZ / c, tmp_path / c)
    return tmp_path


def test_guarda_el_usuario_que_devuelve_github(raiz, monkeypatch):
    monkeypatch.setattr(construir, "RAIZ", raiz)
    errores, registros = construir.construir(raiz, APP, quien=lambda sha: "ana-gh")
    assert errores == [] and registros and all(r["github"] == "ana-gh" for r in registros)


def test_no_inventa_un_usuario_si_no_hay(raiz):
    _, registros = construir.construir(raiz, APP, quien=lambda sha: "")
    assert all("github" not in r for r in registros)


def test_lo_ya_guardado_no_se_consulta_de_nuevo(raiz):
    previo = {"version": 1, "plantillas": [{"id": "ambiente-menta", "github": "carlos", "fecha": "2026-01-01"}]}
    (raiz / "catalogo.json").write_text(json.dumps(previo), encoding="utf-8")
    consultados = []
    _, registros = construir.construir(raiz, APP, quien=lambda sha: consultados.append(sha) or "otro")
    menta = [r for r in registros if r["id"] == "ambiente-menta"][0]
    assert menta["github"] == "carlos" and menta["fecha"] == "2026-01-01"
    assert len(consultados) == len(registros) - 1


def test_usuario_de_github_exige_token_y_login_valido(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert construir.usuario_de_github("abc") == ""                       # fuera de GitHub Actions no consulta nada
    monkeypatch.setenv("GH_TOKEN", "x"); monkeypatch.setenv("GITHUB_REPOSITORY", "a/b")
    respuestas = iter([[{"user": {"login": "<script>"}}]])
    monkeypatch.setattr(construir, "urllib", type("U", (), {"request": type("R", (), {
        "Request": staticmethod(lambda *a, **k: None),
        "urlopen": staticmethod(lambda *a, **k: type("X", (), {"__enter__": lambda s: s, "__exit__": lambda s, *a: False, "read": lambda s: json.dumps(next(respuestas)).encode()})())})}))
    assert construir.usuario_de_github("abc") == ""                       # un nombre raro se descarta
    assert construir.usuario_de_github("") == ""


def test_el_catalogo_publicado_pasa_el_revisor():
    errores, registros = construir.construir(RAIZ, APP, quien=lambda sha: "")
    assert errores == [] and len(registros) >= 3
