"""
La lógica de la subida directa: entrar con GitHub, nombre visible, enviar una plantilla, ver las propias, el catálogo público,
las descargas y el panel de aprobación. Cada endpoint es una función (contexto, petición) → respuesta, sin tocar la red ni la base
directamente, para poder probarla entera. El adaptador de Vercel está en vercel.py.

Seguridad en corto: nada se publica sin aprobación; todo lo que entra se revisa con los validadores de la app; la sesión es una cookie
firmada, HttpOnly y SameSite=Lax; las acciones que cambian algo exigen que la petición venga del propio sitio (cabecera Origin);
y hay topes de tamaño, de envíos por día y de pendientes por persona.
"""
import base64
import binascii
import hmac
import json
import os
import re
import secrets
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import envio
import sesion
from almacen import normalizar

_APP = Path(__file__).resolve().parent / "app"   # los revisores de la app (herramientas/sincronizar_app.py los copia aquí)
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))
import ajustes  # noqa: E402
import plantillas  # noqa: E402

LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
RESERVADOS = {"oficial", "admin", "administrador", "moderador", "soporte", "comunidad", "reproductor", "reproductorvisual", "github", "sistema", "staff", "vercel"}
VOLVER_PERMITIDOS = {"/enviar.html", "/admin.html", "/"}
MAX_CUERPO = 4_400_000   # Vercel corta en 4,5 MB
CAPTURA_PREFIJO = "https://avatars.githubusercontent.com/"


@dataclass
class Config:
    client_id: str = ""
    client_secret: str = ""
    session_secret: str = ""
    admins: frozenset = frozenset()
    site_url: str = "https://reproductor-comunidad.vercel.app"
    edad_minima_dias: int = 7
    max_pendientes: int = 5
    max_por_dia: int = 10

    @classmethod
    def desde_entorno(cls):
        e = os.environ
        return cls(client_id=e.get("GITHUB_CLIENT_ID", ""), client_secret=e.get("GITHUB_CLIENT_SECRET", ""), session_secret=e.get("SESSION_SECRET", ""),
                   admins=frozenset(x.strip().lower() for x in e.get("ADMIN_LOGINS", "").split(",") if x.strip()), site_url=e.get("SITE_URL", cls.site_url).rstrip("/"))


@dataclass
class Peticion:
    metodo: str = "GET"
    consulta: dict = field(default_factory=dict)
    cuerpo: bytes = b""
    cookies: dict = field(default_factory=dict)
    origen: str | None = None


@dataclass
class Respuesta:
    estado: int = 200
    cuerpo: bytes = b""
    tipo: str = "application/json; charset=utf-8"
    cabeceras: list = field(default_factory=list)
    cookies: list = field(default_factory=list)


@dataclass
class Contexto:
    config: Config
    almacen: object
    http: object = None                       # get_json(url, cabeceras) y post_json(url, datos, cabeceras): lo único que sale a internet
    ahora: object = None                      # () -> segundos desde 1970
    token: object = staticmethod(lambda: secrets.token_urlsafe(24))
    hex4: object = staticmethod(lambda: secrets.token_hex(2))


def _json(estado, datos, cookies=(), cache="no-store"):
    return Respuesta(estado, json.dumps(datos, ensure_ascii=False).encode("utf-8"), cabeceras=[("Cache-Control", cache)], cookies=list(cookies))


def _error(estado, mensaje, **extra):
    return _json(estado, {"ok": False, "error": mensaje, **extra})


def _redirigir(url, cookies=()):
    return Respuesta(302, b"", cabeceras=[("Location", url), ("Cache-Control", "no-store")], cookies=list(cookies))


def _cuerpo_json(req):
    try:
        d = json.loads(req.cuerpo.decode("utf-8"))
        return d if isinstance(d, dict) else None
    except (ValueError, UnicodeDecodeError):
        return None


def _mismo_sitio(ctx, req):
    """Las acciones que cambian algo solo valen si la petición viene de esta misma página (defensa contra CSRF, además de SameSite)."""
    return req.origen is not None and req.origen.rstrip("/") == ctx.config.site_url


def _usuario(ctx, req):
    datos = sesion.verificar(req.cookies.get(sesion.NOMBRE), ctx.config.session_secret, ctx.ahora())
    return ctx.almacen.usuario(datos["uid"]) if datos else None


def _es_admin(ctx, u):
    return bool(u) and u["login"].lower() in ctx.config.admins


def _fecha_iso(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------- entrar con GitHub
def login(ctx, req):
    c = ctx.config
    if not c.client_id or not c.session_secret:
        return _error(503, "La entrada con GitHub todavía no está configurada.")
    estado = ctx.token()
    volver = req.consulta.get("volver", "/enviar.html")
    volver = volver if volver in VOLVER_PERMITIDOS else "/enviar.html"
    url = "https://github.com/login/oauth/authorize?" + urlencode({"client_id": c.client_id, "redirect_uri": f"{c.site_url}/api/auth/callback", "state": estado})
    return _redirigir(url, [sesion.cookie("rv_estado", estado, 600, "/api/auth"), sesion.cookie("rv_volver", volver.replace("/", "_") or "_", 600, "/api/auth")])


def callback(ctx, req):
    c = ctx.config
    esperado = req.cookies.get("rv_estado", "")
    estado, codigo = req.consulta.get("state", ""), req.consulta.get("code", "")
    borrar = [sesion.cookie("rv_estado", "", 0, "/api/auth"), sesion.cookie("rv_volver", "", 0, "/api/auth")]
    volver = req.cookies.get("rv_volver", "_enviar.html").replace("_", "/")
    volver = volver if volver in VOLVER_PERMITIDOS else "/enviar.html"
    if not (esperado and estado and hmac.compare_digest(esperado, estado)) or not codigo or len(codigo) > 200:
        return _redirigir(f"{volver}?error=login", borrar)
    try:
        r = ctx.http.post_json("https://github.com/login/oauth/access_token", {"client_id": c.client_id, "client_secret": c.client_secret, "code": codigo,
                                                                              "redirect_uri": f"{c.site_url}/api/auth/callback"}, {"Accept": "application/json"})
        token = r.get("access_token")
        if not isinstance(token, str) or not token:
            return _redirigir(f"{volver}?error=login", borrar)
        gh = ctx.http.get_json("https://api.github.com/user", {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    except Exception:
        return _redirigir(f"{volver}?error=red", borrar)
    uid, nombre = gh.get("id"), gh.get("login")
    if not isinstance(uid, int) or isinstance(uid, bool) or not isinstance(nombre, str) or not LOGIN.match(nombre):
        return _redirigir(f"{volver}?error=login", borrar)
    avatar = gh.get("avatar_url") if isinstance(gh.get("avatar_url"), str) and gh["avatar_url"].startswith(CAPTURA_PREFIJO) else ""
    u = ctx.almacen.upsert_usuario(uid, nombre, avatar, _fecha_iso(gh.get("created_at")))
    if u.get("bloqueado"):
        return _redirigir(f"{volver}?error=bloqueado", borrar)
    return _redirigir(volver, borrar + [sesion.cookie(sesion.NOMBRE, sesion.firmar({"uid": uid}, c.session_secret, ctx.ahora()), sesion.DURACION)])


def salir(ctx, req):
    if not _mismo_sitio(ctx, req):
        return _error(403, "Petición no permitida.")
    return _json(200, {"ok": True}, [sesion.cookie(sesion.NOMBRE, "", 0)])


# ---------------------------------------------------------------- mi cuenta
def _validar_nombre_visible(ctx, u, nombre):
    if not isinstance(nombre, str):
        return None, "El nombre no es válido."
    nombre = " ".join(nombre.split())
    if not 2 <= len(nombre) <= 30 or any(not ch.isprintable() for ch in nombre):
        return None, "El nombre debe tener entre 2 y 30 caracteres."
    if normalizar(nombre) in RESERVADOS or not normalizar(nombre):
        return None, "Ese nombre está reservado."
    if ctx.almacen.nombre_ocupado(nombre, u["id"]):
        return None, "Ese nombre ya lo usa otra persona."
    return nombre, None


def yo(ctx, req):
    u = _usuario(ctx, req)
    if not u:
        return _error(401, "No has entrado.")
    if req.metodo == "POST":
        if not _mismo_sitio(ctx, req):
            return _error(403, "Petición no permitida.")
        d = _cuerpo_json(req) or {}
        nombre, motivo = _validar_nombre_visible(ctx, u, d.get("nombre_visible"))
        if motivo:
            return _error(400, motivo)
        ctx.almacen.cambiar_nombre(u["id"], nombre)
        u = ctx.almacen.usuario(u["id"])
    return _json(200, {"ok": True, "login": u["login"], "nombre_visible": u["nombre_visible"], "avatar": u["avatar"], "admin": _es_admin(ctx, u), "bloqueado": bool(u["bloqueado"])})


# ---------------------------------------------------------------- enviar y ver lo propio
def _slug(nombre):
    base = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:28].strip("-")
    return base or "plantilla"


def _decodificar(b64, maximo):
    if not isinstance(b64, str) or len(b64) > maximo * 4 // 3 + 8:
        return None
    try:
        datos = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        return None
    return datos if 0 < len(datos) <= maximo else None


def enviar(ctx, req):
    if req.metodo != "POST":
        return _error(405, "Usa POST.")
    u = _usuario(ctx, req)
    if not u:
        return _error(401, "Entra con GitHub para enviar una plantilla.")
    if not _mismo_sitio(ctx, req):
        return _error(403, "Petición no permitida.")
    if u["bloqueado"]:
        return _error(403, "Tu cuenta no puede enviar plantillas.")
    c = ctx.config
    creado_gh = u.get("creado_github")
    if creado_gh and ctx.ahora() - creado_gh < c.edad_minima_dias * 86400:
        return _error(403, f"Tu cuenta de GitHub es muy nueva: se puede enviar después de {c.edad_minima_dias} días.")
    if ctx.almacen.contar(u["id"], "pendiente") >= c.max_pendientes:
        return _error(429, f"Ya tienes {c.max_pendientes} plantillas esperando revisión. Espera a que se revisen.")
    if ctx.almacen.contar(u["id"], None, ctx.ahora() - 86400) >= c.max_por_dia:
        return _error(429, "Llegaste al máximo de envíos por día. Inténtalo mañana.")
    if len(req.cuerpo) > MAX_CUERPO:
        return _error(413, "El envío es demasiado grande (máx. unos 2,6 MB de archivo más la captura).")
    d = _cuerpo_json(req)
    if d is None:
        return _error(400, "El envío no se pudo leer.")
    errores = []
    meta = {k: envio.texto({"nombre": d.get("nombre"), "descripcion": d.get("descripcion"), "autor": u["nombre_visible"]}, k, errores, "envío") for k in envio.CAMPOS}
    archivo, previa = _decodificar(d.get("plantilla_b64"), envio.MAX_PLANTILLA), _decodificar(d.get("previa_b64"), envio.MAX_PREVIA)
    if archivo is None:
        errores.append("Falta el archivo .plantilla o es demasiado grande.")
    if previa is None:
        errores.append("Falta la captura o es demasiado grande (máx. 600 KB).")
    tipo, base, hay_imagenes = "", "", False
    if archivo is not None:
        try:
            tipo, base, hay_imagenes = envio.revisar_archivo(archivo, ajustes, plantillas)
        except plantillas.PlantillaInvalida as x:
            errores.append(f"El archivo no es válido ({x}).")
    if previa is not None:
        motivo = envio.revisar_previa(previa, "envío")
        if motivo:
            errores.append(motivo)
    origen = envio.origen_de_imagenes({"imagenes": d.get("imagenes")}, hay_imagenes, errores, "envío") if tipo else None
    if errores:
        return _error(400, "El envío tiene problemas.", errores=[e.replace("envío: ", "") for e in errores])
    for _ in range(5):
        id_ = f"{_slug(meta['nombre'])}-{ctx.hex4()}"
        if ctx.almacen.crear_plantilla({"id": id_, "usuario_id": u["id"], "nombre": meta["nombre"], "descripcion": meta["descripcion"], "tipo": tipo, "base": base,
                                        "imagenes_origen": origen["origen"] if origen else None, "imagenes_detalle": origen["detalle"] if origen else None,
                                        "archivo": archivo, "previa": previa, "creado": ctx.ahora()}):
            return _json(201, {"ok": True, "id": id_, "estado": "pendiente"})
    return _error(500, "No se pudo guardar el envío. Inténtalo de nuevo.")


def mis(ctx, req):
    u = _usuario(ctx, req)
    if not u:
        return _error(401, "No has entrado.")
    if req.metodo == "DELETE":
        if not _mismo_sitio(ctx, req):
            return _error(403, "Petición no permitida.")
        return _json(200, {"ok": True}) if ctx.almacen.borrar(req.consulta.get("id", ""), u["id"]) else _error(404, "No existe.")
    return _json(200, {"ok": True, "plantillas": [{k: p[k] for k in ("id", "nombre", "descripcion", "tipo", "base", "estado", "motivo", "creado", "imagenes_origen", "imagenes_detalle")}
                                                  for p in ctx.almacen.listar(usuario_id=u["id"])]})


# ---------------------------------------------------------------- lo público
def _entrada_publica(p):
    im = {"origen": p["imagenes_origen"], "detalle": p["imagenes_detalle"] or ""} if p.get("imagenes_origen") else None
    return {"id": p["id"], "nombre": p["nombre"], "autor": p["usuario"]["nombre_visible"], "github": p["usuario"]["login"], "descripcion": p["descripcion"], "tipo": p["tipo"],
            "base": p["base"], "fecha": datetime.fromtimestamp(p["creado"]).strftime("%Y-%m-%d"), "imagenes": im}


def catalogo(ctx, req):
    """Lo aprobado, con el mismo formato que catalogo.json (la app y la galería lo leen igual)."""
    return _json(200, {"version": 1, "plantillas": [_entrada_publica(p) for p in ctx.almacen.listar("aprobada")]}, cache="public, s-maxage=60, stale-while-revalidate=300")


def archivo(ctx, req):
    id_, tipo = req.consulta.get("id", ""), req.consulta.get("tipo", "")
    if not envio.SLUG.match(id_) or len(id_) > 60 or tipo not in ("plantilla", "previa"):
        return _error(404, "No existe.")
    p = ctx.almacen.obtener(id_, con_bytes=True)
    if p and p["estado"] != "aprobada":
        u = _usuario(ctx, req)   # lo pendiente solo lo ve quien lo envió o quien administra
        if not u or (u["id"] != p["usuario_id"] and not _es_admin(ctx, u)):
            p = None
    if not p:
        return _error(404, "No existe.")
    cab = [("X-Content-Type-Options", "nosniff"), ("Cache-Control", "public, max-age=300" if p["estado"] == "aprobada" else "private, no-store")]
    if tipo == "plantilla":
        return Respuesta(200, bytes(p["archivo"]), "application/octet-stream", cab + [("Content-Disposition", f'attachment; filename="{id_}.plantilla"')])
    return Respuesta(200, bytes(p["previa"]), "image/webp", cab)


# ---------------------------------------------------------------- panel de aprobación
def admin_pendientes(ctx, req):
    u = _usuario(ctx, req)
    if not _es_admin(ctx, u):
        return _error(403, "Solo para administración.")
    estado = req.consulta.get("estado", "pendiente")
    filas = ctx.almacen.listar(estado if estado in ("pendiente", "aprobada") else "pendiente")
    return _json(200, {"ok": True, "plantillas": [{**{k: p[k] for k in ("id", "nombre", "descripcion", "tipo", "base", "imagenes_origen", "imagenes_detalle", "creado")},
                                                    "usuario": p["usuario"]} for p in filas]})


def admin_decidir(ctx, req):
    u = _usuario(ctx, req)
    if req.metodo != "POST" or not _es_admin(ctx, u):
        return _error(403, "Solo para administración.")
    if not _mismo_sitio(ctx, req):
        return _error(403, "Petición no permitida.")
    d = _cuerpo_json(req) or {}
    id_, accion, motivo = d.get("id"), d.get("accion"), (d.get("motivo") or "")
    if not isinstance(id_, str) or accion not in ("aprobar", "rechazar", "retirar", "bloquear") or not isinstance(motivo, str) or len(motivo) > 200:
        return _error(400, "Datos no válidos.")
    p = ctx.almacen.obtener(id_)
    if not p:
        return _error(404, "No existe.")
    if accion == "bloquear":
        ctx.almacen.bloquear(p["usuario_id"], True)
        ctx.almacen.decidir(id_, "rechazada", motivo or "Cuenta bloqueada", ctx.ahora())
    else:
        ctx.almacen.decidir(id_, "aprobada" if accion == "aprobar" else "rechazada", "" if accion == "aprobar" else motivo, ctx.ahora())
    return _json(200, {"ok": True})


RUTAS = {"auth/login": login, "auth/callback": callback, "auth/salir": salir, "yo": yo, "enviar": enviar, "mis": mis, "catalogo": catalogo, "archivo": archivo,
         "admin/pendientes": admin_pendientes, "admin/decidir": admin_decidir}


def atender(ruta, req, ctx):
    """Despacha una petición; nunca deja escapar un error con detalles internos."""
    f = RUTAS.get(ruta)
    if not f:
        return _error(404, "No existe.")
    try:
        r = f(ctx, req)
    except Exception:   # noqa: BLE001 — el detalle queda en el registro del servidor, no en la respuesta
        import traceback
        traceback.print_exc()
        return _error(500, "Algo salió mal.")
    r.cabeceras = [("X-Content-Type-Options", "nosniff")] + [h for h in r.cabeceras if h[0] != "X-Content-Type-Options"]
    return r
