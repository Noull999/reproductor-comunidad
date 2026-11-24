"""
Arma la galería web (carpeta sitio/) a partir de catalogo.json: una sola página estática, sin servidor.
Lo corre GitHub solo cuando cambia el catálogo; para probarla: python herramientas/sitio.py y abrir sitio/index.html.
Todo el texto de las plantillas se escapa: lo que escribe cada persona nunca se interpreta como HTML.
"""
import html
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GITHUB = "https://github.com/Noull999/reproductor-comunidad"
APP = "https://github.com/Noull999/reproductor-visual"
NOMBRES = {"liquido": "Líquido", "headspace": "Headspace", "dosmil": "2000s", "ambiente": "Ambiente", "pixel": "Pixel", "neoy2k": "Neo Y2K",
           "psicodelico": "Psicodélico", "dreamcore": "Dreamcore", "anime": "Winamp"}

PLANTILLA = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Comunidad · Reproductor visual</title>
<meta name="description" content="Plantillas que la gente comparte para el reproductor visual: colores, fondos y estilos para que tu música se vea.">
<meta property="og:title" content="Comunidad del reproductor visual">
<meta property="og:description" content="Plantillas que la gente comparte para que su música se vea.">
<style>
  :root { --fondo: #0b0809; --texto: #f3eeee; --suave: #a99da0; --borde: rgba(255,255,255,.12); --acento: #ff3b4d; color-scheme: dark; }
  @media (prefers-color-scheme: light) { :root { --fondo: #f6f1f1; --texto: #1c1416; --suave: #6d5f63; --borde: rgba(0,0,0,.14); color-scheme: light; } }
  * { box-sizing: border-box; }
  body { margin: 0; background: radial-gradient(1200px 600px at 15% -10%, rgba(255,59,77,.18), transparent 60%), radial-gradient(900px 500px at 100% 0%, rgba(80,120,255,.14), transparent 60%), var(--fondo);
    color: var(--texto); font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; min-height: 100vh; }
  .envoltorio { max-width: 1120px; margin: 0 auto; padding: 0 20px 60px; }
  header { padding: 56px 0 24px; }
  h1 { font-size: clamp(30px, 5vw, 46px); line-height: 1.1; margin: 0 0 10px; letter-spacing: -.02em; }
  header p { color: var(--suave); max-width: 640px; margin: 0; font-size: 17px; }
  .pasos { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin: 26px 0 10px; padding: 0; list-style: none; counter-reset: p; }
  .pasos li { counter-increment: p; border: 1px solid var(--borde); border-radius: 14px; padding: 14px 16px; background: rgba(127,127,127,.07); color: var(--suave); font-size: 14.5px; }
  .pasos li::before { content: counter(p); display: inline-grid; place-items: center; width: 24px; height: 24px; border-radius: 50%; background: var(--acento); color: #fff; font-weight: 700; font-size: 13px; margin-right: 8px; }
  .pasos b { color: var(--texto); }
  .barra { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 22px 0 18px; }
  .barra input { flex: 1; min-width: 220px; max-width: 420px; padding: 11px 18px; border-radius: 999px; border: 1px solid var(--borde); background: rgba(127,127,127,.08); color: var(--texto); font: inherit; }
  .barra input:focus-visible, button:focus-visible, a:focus-visible { outline: 2px solid var(--acento); outline-offset: 2px; }
  .filtros { display: flex; gap: 8px; flex-wrap: wrap; }
  .filtros button { padding: 8px 16px; border-radius: 999px; border: 1px solid var(--borde); background: transparent; color: var(--suave); font: inherit; font-size: 14px; cursor: pointer; }
  .filtros button[aria-pressed="true"] { background: var(--texto); color: var(--fondo); border-color: transparent; }
  .rejilla { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; list-style: none; padding: 0; margin: 0; }
  .tarjeta { border: 1px solid var(--borde); border-radius: 18px; overflow: hidden; background: rgba(127,127,127,.07); display: flex; flex-direction: column; }
  .tarjeta img { width: 100%; height: auto; aspect-ratio: 16 / 9; object-fit: cover; display: block; background: #120a0c; }
  .cuerpo { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 6px; flex: 1; }
  .cuerpo h2 { margin: 0; font-size: 18px; }
  .autor { color: var(--suave); font-size: 13.5px; }
  .cuerpo p { margin: 0; color: var(--suave); font-size: 14.5px; flex: 1; }
  .pie { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 8px; flex-wrap: wrap; }
  .etiqueta { font: 12px ui-monospace, "Cascadia Mono", monospace; color: var(--suave); border: 1px solid var(--borde); border-radius: 999px; padding: 3px 10px; white-space: nowrap; }
  .descargar { padding: 8px 18px; border-radius: 999px; background: var(--acento); color: #fff; text-decoration: none; font-weight: 600; font-size: 14px; }
  .descargar:hover { filter: brightness(1.1); }
  #vacio { color: var(--suave); text-align: center; padding: 50px 10px; }
  footer { margin-top: 44px; padding-top: 22px; border-top: 1px solid var(--borde); color: var(--suave); font-size: 14px; display: flex; gap: 18px; flex-wrap: wrap; }
  footer a { color: var(--texto); }
  [hidden] { display: none !important; }
</style>
</head>
<body>
<div class="envoltorio">
  <header>
    <h1>Comunidad del reproductor visual</h1>
    <p>Plantillas que la gente comparte para que su música se vea: colores, fondos y estilos listos para usar.</p>
    <ol class="pasos">
      <li><b>Elige</b> una plantilla y descárgala.</li>
      <li>En la app, abre <b>Biblioteca</b> y toca <b>Importar plantilla…</b></li>
      <li>Elige el archivo: la app lo revisa y listo. <b>También puedes instalar directo desde la pestaña Comunidad.</b></li>
    </ol>
  </header>
  <div class="barra">
    <input id="buscar" type="search" placeholder="Buscar por nombre, autor o estilo…" aria-label="Buscar plantillas" autocomplete="off">
    <div class="filtros" role="group" aria-label="Tipo">
      <button type="button" data-t="" aria-pressed="true">Todas</button>
      <button type="button" data-t="ajustes" aria-pressed="false">Ajustes</button>
      <button type="button" data-t="plantilla" aria-pressed="false">Del Editor</button>
    </div>
  </div>
  <ul class="rejilla" id="rejilla">
__TARJETAS__
  </ul>
  <p id="vacio" hidden>Nada coincide con esa búsqueda.</p>
  <footer>
    <span>__CUENTA__ en la comunidad</span>
    <a href="__GITHUB__/blob/main/CONTRIBUIR.md">Compartir la tuya</a>
    <a href="__GITHUB__">Repositorio</a>
    <a href="__APP__">La app</a>
  </footer>
</div>
<script>
const tarjetas = [...document.querySelectorAll(".tarjeta")], vacio = document.getElementById("vacio");
let tipo = "";
function filtrar() {
  const q = document.getElementById("buscar").value.trim().toLowerCase();
  let n = 0;
  for (const t of tarjetas) { const ok = (!tipo || t.dataset.tipo === tipo) && (!q || t.dataset.texto.includes(q)); t.parentElement.hidden = !ok; if (ok) n++; }
  vacio.hidden = n > 0;
}
document.getElementById("buscar").addEventListener("input", filtrar);
for (const b of document.querySelectorAll(".filtros button")) b.addEventListener("click", () => {
  tipo = b.dataset.t; document.querySelectorAll(".filtros button").forEach(x => x.setAttribute("aria-pressed", x === b));
  filtrar();
});
</script>
</body>
</html>
"""


def tarjeta(p):
    e = html.escape
    etiqueta = f"Ajustes · {NOMBRES.get(p['base'], p['base'])}" if p["tipo"] == "ajustes" else "Plantilla del Editor"
    texto = f"{p['nombre']} {p['autor']} {p['descripcion']} {NOMBRES.get(p['base'], '')}".lower()
    return (f'    <li><article class="tarjeta" data-tipo="{e(p["tipo"])}" data-texto="{e(texto)}">\n'
            f'      <img src="previas/{e(p["id"])}.webp" alt="Vista previa de {e(p["nombre"])}" loading="lazy" width="1000" height="563">\n'
            f'      <div class="cuerpo"><h2>{e(p["nombre"])}</h2><span class="autor">por {e(p["autor"])}</span><p>{e(p["descripcion"])}</p>\n'
            f'      <div class="pie"><span class="etiqueta">{e(etiqueta)}</span>'
            f'<a class="descargar" href="plantillas/{e(p["id"])}.plantilla" download>Descargar</a></div></div>\n'
            f'    </article></li>')


def construir(raiz=RAIZ):
    raiz = Path(raiz)
    catalogo = json.loads((raiz / "catalogo.json").read_text(encoding="utf-8"))["plantillas"]
    salida = raiz / "sitio"
    for sub in ("previas", "plantillas"):   # la galería es una copia exacta del catálogo: lo que ya no está, se va
        shutil.rmtree(salida / sub, ignore_errors=True)
        (salida / sub).mkdir(parents=True, exist_ok=True)
    for p in catalogo:
        shutil.copy2(raiz / "previas" / f"{p['id']}.webp", salida / "previas")
        shutil.copy2(raiz / "plantillas" / f"{p['id']}.plantilla", salida / "plantillas")
    cuerpo = "\n".join(tarjeta(p) for p in catalogo) or ""
    cuenta = f"{len(catalogo)} plantilla" + ("" if len(catalogo) == 1 else "s")
    pagina = PLANTILLA.replace("__TARJETAS__", cuerpo).replace("__CUENTA__", cuenta).replace("__GITHUB__", GITHUB).replace("__APP__", APP)
    (salida / "index.html").write_text(pagina, encoding="utf-8")
    return len(catalogo)


if __name__ == "__main__":
    print(f"sitio/: {construir()} plantillas")
