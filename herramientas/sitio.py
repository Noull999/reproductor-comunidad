"""
Arma la galería web (carpeta sitio/) a partir de catalogo.json y herramientas/pagina.html: una sola página estática, sin servidor.
Lo corre GitHub solo cuando cambia el catálogo; para probarla: python herramientas/sitio.py y abrir sitio/index.html.
Todo el texto de las plantillas se escapa: lo que escribe cada persona nunca se interpreta como HTML.
"""
import html
import json
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GITHUB = "https://github.com/Noull999/reproductor-comunidad"
APP = "https://github.com/Noull999/reproductor-visual"
ORIGENES = {"propio": "propias", "ia": "hechas con IA", "libre": "de licencia libre"}
# Las 9 plantillas de la app: id, nombre y una frase (la foto está en assets/incluidas/<id>.webp)
INCLUIDAS = [
    ("liquido", "Líquido", "Vidrio líquido sobre un haz de luz que late con el bajo."),
    ("headspace", "Headspace", "Una cabeza Y2K con el reproductor adentro."),
    ("dosmil", "2000s", "Metal, pantalla LCD y visuales tipo Windows Media Player."),
    ("ambiente", "Ambiente", "La carátula manda: sus colores tiñen todo."),
    ("pixel", "Pixel", "8 bits, con paletas que puedes cambiar."),
    ("anime", "Winamp", "Skins clásicos de Winamp que tú eliges."),
    ("psicodelico", "Psicodélico", "Un ojo pixel art sobre un caleidoscopio."),
    ("neoy2k", "Neo Y2K", "Portada de rap con cromo, destellos y japonés vertical."),
    ("dreamcore", "Dreamcore", "VHS, ventanas de Windows 95 y popups de «virus»."),
]
NOMBRES = {i: n for i, n, _ in INCLUIDAS}


def autor_html(p):
    """«por Ana · @ana»: el nombre que eligió y, si GitHub lo verificó, su usuario."""
    e = html.escape
    gh = f' · <a href="https://github.com/{e(p["github"])}" rel="noopener">@{e(p["github"])}</a>' if p.get("github") else ""
    return f'por {e(p["autor"])}{gh}'


def origen_html(p):
    im = p.get("imagenes")
    if not im:
        return ""
    e = html.escape
    return f'<span class="etiqueta" title="{e(im.get("detalle", ""))}">Imágenes {e(ORIGENES.get(im.get("origen"), ""))}</span>'


def tarjeta(p):
    e = html.escape
    etiqueta = f"Ajustes · {NOMBRES.get(p['base'], p['base'])}" if p["tipo"] == "ajustes" else "Plantilla del Editor"
    texto = f"{p['nombre']} {p['autor']} {p.get('github', '')} {p['descripcion']} {NOMBRES.get(p['base'], '')}".lower()
    return (f'    <li><article class="tarjeta" data-base="{e(p["base"])}" data-texto="{e(texto)}">\n'
            f'      <button type="button" class="foto" data-titulo="{e(p["nombre"])}" aria-label="Ver grande la vista previa de {e(p["nombre"])}">'
            f'<img src="previas/{e(p["id"])}.webp" alt="Vista previa de {e(p["nombre"])}" loading="lazy" width="1000" height="563"></button>\n'
            f'      <div class="cuerpo"><h3>{e(p["nombre"])}</h3><span class="autor">{autor_html(p)}</span><p>{e(p["descripcion"])}</p>\n'
            f'      <div class="pie"><span class="etiqueta">{e(etiqueta)}</span>{origen_html(p)}'
            f'<a class="descargar" href="plantillas/{e(p["id"])}.plantilla" download>Descargar</a></div></div>\n'
            f'    </article></li>')


def incluida(id_, nombre, frase):
    e = html.escape
    return (f'      <li><img src="img/incluidas/{id_}.webp" alt="Vista previa de la plantilla {e(nombre)}" loading="lazy" width="1000" height="563">'
            f'<div><b>{e(nombre)}</b><span>{e(frase)}</span></div></li>')


def construir(raiz=RAIZ):
    raiz = Path(raiz)
    catalogo = json.loads((raiz / "catalogo.json").read_text(encoding="utf-8"))["plantillas"]
    salida = raiz / "sitio"
    for sub in ("previas", "plantillas", "img/incluidas"):   # la galería es una copia exacta del catálogo: lo que ya no está, se va
        shutil.rmtree(salida / sub, ignore_errors=True)
        (salida / sub).mkdir(parents=True, exist_ok=True)
    for p in catalogo:
        shutil.copy2(raiz / "previas" / f"{p['id']}.webp", salida / "previas")
        shutil.copy2(raiz / "plantillas" / f"{p['id']}.plantilla", salida / "plantillas")
    for id_, _, _ in INCLUIDAS:
        shutil.copy2(raiz / "assets" / "incluidas" / f"{id_}.webp", salida / "img" / "incluidas")
    bases = [i for i, _, _ in INCLUIDAS if any(p["base"] == i for p in catalogo)]   # solo los filtros que tienen algo
    filtros = "\n".join(f'        <button type="button" data-f="{b}" aria-pressed="false">{html.escape(NOMBRES[b])}</button>' for b in bases)
    cuenta = f"{len(catalogo)} plantilla" + ("" if len(catalogo) == 1 else "s")
    vacio = "Todavía no hay plantillas en la comunidad. ¡Puedes ser la primera persona en compartir una!" if not catalogo else "Nada coincide con esa búsqueda."
    pagina = (Path(__file__).with_name("pagina.html").read_text(encoding="utf-8")
              .replace("__TARJETAS__", "\n".join(tarjeta(p) for p in catalogo)).replace("__INCLUIDAS__", "\n".join(incluida(*i) for i in INCLUIDAS))
              .replace("__FILTROS__", filtros).replace("__CUENTA__", cuenta).replace("__VACIO__", html.escape(vacio))
              .replace("__GITHUB__", GITHUB).replace("__APP__", APP))
    (salida / "index.html").write_text(pagina, encoding="utf-8")
    return len(catalogo)


if __name__ == "__main__":
    print(f"sitio/: {construir()} plantillas")
