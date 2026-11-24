"""
Arma catalogo.json con todas las plantillas válidas (lo corre GitHub solo cuando se aprueba un envío).
El catálogo no trae rutas ni direcciones: la app arma ella misma las URL a partir del id.

    python herramientas/construir.py <carpeta de la app>
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validar import RAIZ, revisar  # noqa: E402


def fecha(slug):
    """Cuándo entró la plantilla (la fecha de su primer commit); vacío si no hay historial."""
    try:
        sal = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cs", "--", f"entradas/{slug}.json"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.split()
        return sal[-1] if sal else ""
    except Exception:
        return ""


LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


def primer_commit(slug):
    """El commit que agregó la entrada (vacío si no hay historial)."""
    try:
        sal = subprocess.run(["git", "log", "--diff-filter=A", "--format=%H", "--", f"entradas/{slug}.json"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.split()
        return sal[-1] if sal else ""
    except Exception:
        return ""


def usuario_de_github(sha):
    """Quién subió esa plantilla, según GitHub: quien abrió el pull request (verificado), o, si se subió directo, quien hizo el commit.
    Solo funciona dentro de GitHub Actions (necesita GH_TOKEN); fuera de ahí devuelve vacío."""
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GH_TOKEN")
    if not (sha and repo and token):
        return ""

    def pedir(ruta):
        r = urllib.request.Request(f"https://api.github.com/repos/{repo}{ruta}", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "catalogo-bot"})
        with urllib.request.urlopen(r, timeout=20) as x:
            return json.load(x)
    try:
        pulls = pedir(f"/commits/{sha}/pulls")
        login = pulls[0]["user"]["login"] if pulls else (pedir(f"/commits/{sha}").get("author") or {}).get("login", "")
    except Exception:
        return ""
    return login if isinstance(login, str) and LOGIN.match(login) else ""


def construir(raiz, app, quien=usuario_de_github):
    """Valida todo y arma el catálogo. El usuario de GitHub se consulta una sola vez por plantilla: lo ya guardado se conserva."""
    errores, registros = revisar(raiz, app)
    if errores:
        return errores, []
    previo = {}
    try:
        previo = {p["id"]: p for p in json.loads((Path(raiz) / "catalogo.json").read_text(encoding="utf-8"))["plantillas"]}
    except (OSError, ValueError, KeyError):
        pass
    for r in registros:
        antes = previo.get(r["id"], {})
        r["fecha"] = antes.get("fecha") or fecha(r["id"])
        gh = antes.get("github") or quien(primer_commit(r["id"]))
        if gh:
            r["github"] = gh
    registros.sort(key=lambda r: (r["fecha"], r["id"]), reverse=True)   # lo nuevo primero
    return [], registros


if __name__ == "__main__":
    app = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ.parent / "visualizador")
    errores, registros = construir(RAIZ, app)
    if errores:
        for m in errores:
            print("✗", m)
        sys.exit(1)
    (RAIZ / "catalogo.json").write_text(json.dumps({"version": 1, "plantillas": registros}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"catalogo.json: {len(registros)} plantillas")
