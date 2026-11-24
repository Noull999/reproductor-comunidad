"""
Copia los revisores de la app (plantillas.py, ajustes.py y el esquema) a api/_lib/app/, que es lo que usa el servidor.
Se corre cada vez que cambian en la app:  python herramientas/sincronizar_app.py <carpeta de la app>
Una prueba avisa si la copia quedó distinta de la app.
"""
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVOS = ["plantillas.py", "ajustes.py", "web/esquema.js"]


def sincronizar(app, destino=RAIZ / "api" / "_lib" / "app"):
    for f in ARCHIVOS:
        (destino / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(app) / f, destino / f)


if __name__ == "__main__":
    sincronizar(sys.argv[1] if len(sys.argv) > 1 else RAIZ.parent / "visualizador")
    print("copiados:", ", ".join(ARCHIVOS))
