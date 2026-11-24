"""
Arma catalogo.json con todas las plantillas válidas (lo corre GitHub solo cuando se aprueba un envío).
El catálogo no trae rutas ni direcciones: la app arma ella misma las URL a partir del id.

    python herramientas/construir.py <carpeta de la app>
"""
import json
import subprocess
import sys
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


if __name__ == "__main__":
    app = sys.argv[1] if len(sys.argv) > 1 else str(RAIZ.parent / "visualizador")
    errores, registros = revisar(RAIZ, app)
    if errores:
        print("\n".join("✗ " + m for m in errores))
        sys.exit(1)
    for r in registros:
        r["fecha"] = fecha(r["id"])
    registros.sort(key=lambda r: (r["fecha"], r["id"]), reverse=True)   # lo nuevo primero
    (RAIZ / "catalogo.json").write_text(json.dumps({"version": 1, "plantillas": registros}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"catalogo.json: {len(registros)} plantillas")
