"""La galería web: refleja el catálogo y nunca interpreta como HTML lo que escribe la gente."""
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "herramientas"))
import sitio  # noqa: E402


def copia(tmp_path):
    for c in ("plantillas", "previas"):
        shutil.copytree(RAIZ / c, tmp_path / c)
    shutil.copy(RAIZ / "catalogo.json", tmp_path / "catalogo.json")
    return tmp_path


def test_refleja_el_catalogo(tmp_path):
    raiz = copia(tmp_path)
    n = sitio.construir(raiz)
    pagina = (raiz / "sitio" / "index.html").read_text(encoding="utf-8")
    assert n >= 3 and pagina.count('class="tarjeta"') == n
    for p in json.loads((raiz / "catalogo.json").read_text(encoding="utf-8"))["plantillas"]:
        assert f'href="plantillas/{p["id"]}.plantilla"' in pagina and (raiz / "sitio" / "previas" / f"{p['id']}.webp").is_file()


def test_escapa_html_y_quita_lo_que_ya_no_esta(tmp_path):
    raiz = copia(tmp_path)
    cat = json.loads((raiz / "catalogo.json").read_text(encoding="utf-8"))
    cat["plantillas"][0].update(nombre='<script>alert(1)</script>', autor='"><img src=x onerror=1>')
    quitada = cat["plantillas"].pop()["id"]
    (raiz / "catalogo.json").write_text(json.dumps(cat), encoding="utf-8")
    (raiz / "sitio" / "previas").mkdir(parents=True); (raiz / "sitio" / "previas" / f"{quitada}.webp").write_bytes(b"viejo")
    sitio.construir(raiz)
    pagina = (raiz / "sitio" / "index.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in pagina and "&lt;script&gt;" in pagina and "<img src=x" not in pagina
    assert not (raiz / "sitio" / "previas" / f"{quitada}.webp").exists()
