"""Adaptador entre las funciones de Vercel (http.server) y servicio.py. Cada archivo de api/ hace `handler = vercel.handler("<ruta>")`."""
import json
import os
import time
import urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qsl, urlsplit

import servicio
from almacen import AlmacenPostgres

_almacen = None


class Http:
    """Lo único que sale a internet: GitHub. Con tiempo límite y sin seguir redirecciones."""

    def _abrir(self, req):
        class SinRedireccion(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        with urllib.request.build_opener(SinRedireccion).open(req, timeout=8) as r:
            return json.loads(r.read(200_000).decode("utf-8"))

    def get_json(self, url, cabeceras):
        return self._abrir(urllib.request.Request(url, headers={"User-Agent": "reproductor-comunidad", **cabeceras}))

    def post_json(self, url, datos, cabeceras):
        return self._abrir(urllib.request.Request(url, json.dumps(datos).encode(), {"User-Agent": "reproductor-comunidad", "Content-Type": "application/json", **cabeceras}, method="POST"))


def _almacen_unico():
    global _almacen
    if _almacen is None:
        url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        if not url:
            raise RuntimeError("falta DATABASE_URL")
        a = AlmacenPostgres(url)
        a.crear_tablas()   # CREATE IF NOT EXISTS: barato y evita un paso manual
        _almacen = a
    return _almacen


def handler(ruta):
    class H(BaseHTTPRequestHandler):
        def _atender(self):
            partes = urlsplit(self.path)
            n = int(self.headers.get("Content-Length") or 0)
            if n > servicio.MAX_CUERPO:
                cuerpo = b"x" * (servicio.MAX_CUERPO + 1)   # que servicio lo rechace con su mensaje, sin leer todo
            else:
                cuerpo = self.rfile.read(n) if n else b""
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            req = servicio.Peticion(self.command, dict(parse_qsl(partes.query)), cuerpo, {k: m.value for k, m in cookies.items()}, self.headers.get("Origin"))
            try:
                ctx = servicio.Contexto(servicio.Config.desde_entorno(), _almacen_unico(), Http(), time.time)
                r = servicio.atender(ruta, req, ctx)
            except Exception:   # noqa: BLE001 — p. ej. sin base de datos: respuesta genérica, detalle al registro
                import traceback
                traceback.print_exc()
                r = servicio._error(503, "El servicio no está disponible ahora.")
            self.send_response(r.estado)
            self.send_header("Content-Type", r.tipo)
            self.send_header("Content-Length", str(len(r.cuerpo)))
            for k, v in r.cabeceras:
                self.send_header(k, v)
            for c in r.cookies:
                self.send_header("Set-Cookie", c)
            self.end_headers()
            self.wfile.write(r.cuerpo)

        do_GET = do_POST = do_DELETE = _atender

        def log_message(self, *a):
            pass

    return H
