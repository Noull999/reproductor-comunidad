"""La subida directa: entrar con GitHub, enviar, aprobar y publicar, con un almacén en memoria y un GitHub de mentira."""
import base64
import json
import sys
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api" / "_lib"))
import servicio  # noqa: E402
import sesion  # noqa: E402
from almacen import AlmacenMemoria  # noqa: E402

SITIO = "https://reproductor-comunidad.vercel.app"
AHORA = 1_800_000_000.0
VIEJA = AHORA - 400 * 86400


class GitHubFalso:
    def __init__(self):
        self.usuario = {"id": 7, "login": "Ana", "avatar_url": "https://avatars.githubusercontent.com/u/7", "created_at": "2020-01-01T00:00:00Z"}
        self.token = "tok"

    def post_json(self, url, datos, cab):
        return {"access_token": self.token} if datos["code"] == "buen-codigo" else {"error": "bad_verification_code"}

    def get_json(self, url, cab):
        return self.usuario


@pytest.fixture
def ctx():
    cfg = servicio.Config("cid", "sec", "secreto-de-prueba", frozenset({"jefa"}), SITIO)
    n = iter(range(10_000))
    return servicio.Contexto(cfg, AlmacenMemoria(), GitHubFalso(), lambda: AHORA, lambda: "estado123", lambda: f"{next(n):04x}")


def pedir(ctx, ruta, metodo="GET", consulta=None, cuerpo=None, cookies=None, origen=SITIO):
    b = json.dumps(cuerpo).encode() if cuerpo is not None else b""
    return servicio.atender(ruta, servicio.Peticion(metodo, consulta or {}, b, cookies or {}, origen), ctx)


def destino(r):
    return dict(r.cabeceras).get("Location", "")


def datos(r):
    return json.loads(r.cuerpo)


def entrar(ctx, login="Ana", uid=7, creado=VIEJA):
    ctx.almacen.upsert_usuario(uid, login, "", creado)
    return {sesion.NOMBRE: sesion.firmar({"uid": uid}, ctx.config.session_secret, AHORA)}


def envio_valido():
    return {"nombre": "Menta fresca", "descripcion": "Un ambiente verde.",
            "plantilla_b64": base64.b64encode((RAIZ / "plantillas" / "ambiente-menta.plantilla").read_bytes()).decode(),
            "previa_b64": base64.b64encode((RAIZ / "previas" / "ambiente-menta.webp").read_bytes()).decode()}


# ---- sesión
def test_cookie_firmada_no_se_puede_falsificar():
    t = sesion.firmar({"uid": 1}, "a", AHORA)
    assert sesion.verificar(t, "a", AHORA)["uid"] == 1
    assert sesion.verificar(t, "b", AHORA) is None
    assert sesion.verificar(t, "a", AHORA + sesion.DURACION + 5) is None
    cuerpo, firma = t.split(".")
    assert sesion.verificar(cuerpo + "." + firma[::-1], "a", AHORA) is None


# ---- entrar con GitHub
def test_login_redirige_a_github_con_estado(ctx):
    r = pedir(ctx, "auth/login", consulta={"volver": "https://malo.com"})
    assert r.estado == 302 and destino(r).startswith("https://github.com/login/oauth/authorize?") and "state=estado123" in destino(r)
    assert any("rv_estado=estado123" in c and "HttpOnly" in c and "Secure" in c for c in r.cookies)
    assert any("rv_volver=_enviar.html" in c for c in r.cookies)   # un destino ajeno se cambia por el propio


def test_callback_crea_la_sesion(ctx):
    r = pedir(ctx, "auth/callback", consulta={"code": "buen-codigo", "state": "estado123"}, cookies={"rv_estado": "estado123", "rv_volver": "_enviar.html"})
    assert r.estado == 302 and destino(r) == "/enviar.html"
    assert any(c.startswith(sesion.NOMBRE + "=") and "HttpOnly" in c for c in r.cookies)
    assert ctx.almacen.usuario(7)["login"] == "Ana"


def test_callback_rechaza_estado_distinto_o_codigo_malo(ctx):
    mal = pedir(ctx, "auth/callback", consulta={"code": "buen-codigo", "state": "otro"}, cookies={"rv_estado": "estado123"})
    assert "error=login" in destino(mal) and not any(c.startswith(sesion.NOMBRE + "=") and "Max-Age=0" not in c for c in mal.cookies)
    sin = pedir(ctx, "auth/callback", consulta={"code": "malo", "state": "estado123"}, cookies={"rv_estado": "estado123"})
    assert "error=login" in destino(sin)
    assert ctx.almacen.usuario(7) is None


def test_cuenta_bloqueada_no_entra(ctx):
    ctx.almacen.upsert_usuario(7, "Ana", "", VIEJA)
    ctx.almacen.bloquear(7)
    r = pedir(ctx, "auth/callback", consulta={"code": "buen-codigo", "state": "estado123"}, cookies={"rv_estado": "estado123"})
    assert "error=bloqueado" in destino(r)


# ---- nombre visible
def test_yo_y_cambio_de_nombre(ctx):
    c = entrar(ctx)
    assert datos(pedir(ctx, "yo", cookies=c))["nombre_visible"] == "Ana"
    assert pedir(ctx, "yo").estado == 401
    assert pedir(ctx, "yo", "POST", cuerpo={"nombre_visible": "Ana Dj"}, cookies=c).estado == 200
    assert datos(pedir(ctx, "yo", cookies=c))["nombre_visible"] == "Ana Dj"


@pytest.mark.parametrize("nombre", ["a", "x" * 31, "Oficial", "Admin", "O f i c i a l", "  ", 5])
def test_nombres_no_validos(ctx, nombre):
    assert pedir(ctx, "yo", "POST", cuerpo={"nombre_visible": nombre}, cookies=entrar(ctx)).estado == 400


def test_nombre_ocupado_y_csrf(ctx):
    entrar(ctx, "Beto", 8)
    c = entrar(ctx)
    assert pedir(ctx, "yo", "POST", cuerpo={"nombre_visible": "beto"}, cookies=c).estado == 400
    assert pedir(ctx, "yo", "POST", cuerpo={"nombre_visible": "Nuevo"}, cookies=c, origen="https://malo.com").estado == 403
    assert pedir(ctx, "yo", "POST", cuerpo={"nombre_visible": "Nuevo"}, cookies=c, origen=None).estado == 403


# ---- enviar
def test_enviar_queda_pendiente_y_no_es_publico(ctx):
    c = entrar(ctx)
    r = pedir(ctx, "enviar", "POST", cuerpo=envio_valido(), cookies=c)
    assert r.estado == 201, r.cuerpo
    id_ = datos(r)["id"]
    assert id_.startswith("menta-fresca-")
    assert datos(pedir(ctx, "catalogo"))["plantillas"] == []
    assert pedir(ctx, "archivo", consulta={"id": id_, "tipo": "plantilla"}).estado == 404          # un extraño no la ve
    assert pedir(ctx, "archivo", consulta={"id": id_, "tipo": "plantilla"}, cookies=c).estado == 200  # quien la envió, sí
    assert [p["id"] for p in datos(pedir(ctx, "mis", cookies=c))["plantillas"]] == [id_]


def test_enviar_exige_sesion_origen_y_cuenta_vieja(ctx):
    assert pedir(ctx, "enviar", "POST", cuerpo=envio_valido()).estado == 401
    c = entrar(ctx)
    assert pedir(ctx, "enviar", "POST", cuerpo=envio_valido(), cookies=c, origen="https://malo.com").estado == 403
    nueva = entrar(ctx, "Nueva", 9, creado=AHORA - 86400)
    assert pedir(ctx, "enviar", "POST", cuerpo=envio_valido(), cookies=nueva).estado == 403


def test_enviar_rechaza_basura(ctx):
    c = entrar(ctx)
    for malo in ({**envio_valido(), "plantilla_b64": base64.b64encode(b"no es zip").decode()},
                 {**envio_valido(), "previa_b64": base64.b64encode(b"no es imagen").decode()},
                 {**envio_valido(), "plantilla_b64": "%%%%"},
                 {**envio_valido(), "nombre": ""},
                 {k: v for k, v in envio_valido().items() if k != "previa_b64"}):
        r = pedir(ctx, "enviar", "POST", cuerpo=malo, cookies=c)
        assert r.estado == 400 and datos(r)["errores"]
    assert servicio.atender("enviar", servicio.Peticion("POST", {}, b"{no json", {k: v for k, v in c.items()}, SITIO), ctx).estado == 400
    assert ctx.almacen.listar() == []


def test_limites_de_pendientes_y_por_dia(ctx):
    c = entrar(ctx)
    for _ in range(ctx.config.max_pendientes):
        assert pedir(ctx, "enviar", "POST", cuerpo=envio_valido(), cookies=c).estado == 201
    assert pedir(ctx, "enviar", "POST", cuerpo=envio_valido(), cookies=c).estado == 429
    ctx.config.max_pendientes, ctx.config.max_por_dia = 99, 5   # sin tope de pendientes, queda el de por día
    assert pedir(ctx, "enviar", "POST", cuerpo=envio_valido(), cookies=c).estado == 429


def test_cuerpo_enorme(ctx):
    r = servicio.atender("enviar", servicio.Peticion("POST", {}, b"x" * (servicio.MAX_CUERPO + 1), entrar(ctx), SITIO), ctx)
    assert r.estado == 413


# ---- aprobar y publicar
def _enviar_uno(ctx, c):
    r = pedir(ctx, "enviar", "POST", cuerpo=envio_valido(), cookies=c)
    assert r.estado == 201, r.cuerpo
    return datos(r)["id"]


def test_panel_solo_para_admins(ctx):
    c = entrar(ctx)
    assert pedir(ctx, "admin/pendientes", cookies=c).estado == 403
    assert pedir(ctx, "admin/decidir", "POST", cuerpo={"id": "x", "accion": "aprobar"}, cookies=c).estado == 403


def test_aprobar_publica_con_el_nombre_visible_actual(ctx):
    c = entrar(ctx)
    id_ = _enviar_uno(ctx, c)
    jefa = entrar(ctx, "jefa", 1)
    assert [p["id"] for p in datos(pedir(ctx, "admin/pendientes", cookies=jefa))["plantillas"]] == [id_]
    assert pedir(ctx, "admin/decidir", "POST", cuerpo={"id": id_, "accion": "aprobar"}, cookies=jefa, origen="https://malo.com").estado == 403
    assert pedir(ctx, "admin/decidir", "POST", cuerpo={"id": id_, "accion": "aprobar"}, cookies=jefa).estado == 200
    pedir(ctx, "yo", "POST", cuerpo={"nombre_visible": "DJ Ana"}, cookies=c)
    cat = datos(pedir(ctx, "catalogo"))
    assert cat["version"] == 1 and len(cat["plantillas"]) == 1
    e = cat["plantillas"][0]
    assert e["autor"] == "DJ Ana" and e["github"] == "Ana" and e["id"] == id_ and {"nombre", "descripcion", "tipo", "base", "fecha"} <= set(e)
    assert pedir(ctx, "archivo", consulta={"id": id_, "tipo": "plantilla"}).estado == 200
    assert pedir(ctx, "archivo", consulta={"id": id_, "tipo": "previa"}).cabeceras[0] == ("X-Content-Type-Options", "nosniff")


def test_rechazar_retirar_y_bloquear(ctx):
    c, jefa = entrar(ctx), entrar(ctx, "jefa", 1)
    a, b = _enviar_uno(ctx, c), _enviar_uno(ctx, c)
    assert pedir(ctx, "admin/decidir", "POST", cuerpo={"id": a, "accion": "rechazar", "motivo": "no cumple"}, cookies=jefa).estado == 200
    assert {p["id"]: p["motivo"] for p in datos(pedir(ctx, "mis", cookies=c))["plantillas"]}[a] == "no cumple"
    pedir(ctx, "admin/decidir", "POST", cuerpo={"id": b, "accion": "aprobar"}, cookies=jefa)
    pedir(ctx, "admin/decidir", "POST", cuerpo={"id": b, "accion": "retirar", "motivo": "copyright"}, cookies=jefa)
    assert datos(pedir(ctx, "catalogo"))["plantillas"] == []
    pedir(ctx, "admin/decidir", "POST", cuerpo={"id": b, "accion": "bloquear"}, cookies=jefa)
    assert pedir(ctx, "enviar", "POST", cuerpo=envio_valido(), cookies=c).estado == 403
    assert pedir(ctx, "admin/decidir", "POST", cuerpo={"id": b, "accion": "inventada"}, cookies=jefa).estado == 400


def test_borrar_solo_lo_propio(ctx):
    c, otra = entrar(ctx), entrar(ctx, "Otra", 2)
    id_ = _enviar_uno(ctx, c)
    assert pedir(ctx, "mis", "DELETE", {"id": id_}, cookies=otra).estado == 404
    assert pedir(ctx, "mis", "DELETE", {"id": id_}, cookies=c, origen="https://malo.com").estado == 403
    assert pedir(ctx, "mis", "DELETE", {"id": id_}, cookies=c).estado == 200


def test_archivo_con_id_raro_y_ruta_desconocida(ctx):
    assert pedir(ctx, "archivo", consulta={"id": "../../etc/passwd", "tipo": "plantilla"}).estado == 404
    assert pedir(ctx, "archivo", consulta={"id": "a", "tipo": "otra"}).estado == 404
    assert pedir(ctx, "no-existe").estado == 404


def test_la_copia_de_los_revisores_es_igual_a_la_de_la_app():
    import os
    app = Path(os.environ.get("APP_REPRODUCTOR", RAIZ.parent / "visualizador"))
    for f in ("plantillas.py", "ajustes.py", "web/esquema.js"):
        assert (RAIZ / "api" / "_lib" / "app" / f).read_bytes() == (app / f).read_bytes(), f"{f} cambió en la app: corre herramientas/sincronizar_app.py"


def test_cada_archivo_de_api_encuentra_su_carpeta__lib():
    """Vercel importa cada archivo de api/ suelto: la ruta que añade al sys.path tiene que llegar a api/_lib."""
    import re
    archivos = [f for f in (RAIZ / "api").rglob("*.py") if "_lib" not in f.parts]
    assert len(archivos) == len(servicio.RUTAS)
    for f in archivos:
        saltos = len(re.search(r"resolve\(\)((?:\.parent)+) / \"_lib\"", f.read_text(encoding="utf-8")).group(1)) // len(".parent")
        destino = f.resolve()
        for _ in range(saltos):
            destino = destino.parent
        assert (destino / "_lib" / "puente.py").exists(), f
        assert "class handler(BaseHTTPRequestHandler)" in f.read_text(encoding="utf-8")
        assert f'puente.atender("{f.relative_to(RAIZ / "api").with_suffix("").as_posix()}")' in f.read_text(encoding="utf-8")
