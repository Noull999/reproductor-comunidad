"""
Dónde se guardan usuarios y plantillas. Hay dos: AlmacenMemoria (para las pruebas) y AlmacenPostgres (Neon). Tienen la misma interfaz.
Las fechas son segundos desde 1970 (float) en los dos.
"""
import re
import threading

ESTADOS = ("pendiente", "aprobada", "rechazada")
_LISTA = ("id", "usuario_id", "nombre", "descripcion", "tipo", "base", "imagenes_origen", "imagenes_detalle", "estado", "motivo", "creado", "decidido")


def _sin_bytes(p: dict, usuario: dict | None) -> dict:
    d = {k: p.get(k) for k in _LISTA}
    d["usuario"] = {"id": usuario["id"], "login": usuario["login"], "nombre_visible": usuario["nombre_visible"]} if usuario else None
    return d


def normalizar(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]", "", nombre.casefold())


class AlmacenMemoria:
    def __init__(self):
        self.usuarios, self.plantillas, self._cerrojo = {}, {}, threading.Lock()

    def crear_tablas(self):
        pass

    # ---- usuarios ----
    def upsert_usuario(self, id_, login, avatar, creado_github):
        with self._cerrojo:
            u = self.usuarios.get(id_)
            if u:
                u.update(login=login, avatar=avatar, creado_github=creado_github)
            else:
                self.usuarios[id_] = u = {"id": id_, "login": login, "nombre_visible": login, "avatar": avatar, "creado_github": creado_github, "bloqueado": False}
            return dict(u)

    def usuario(self, id_):
        u = self.usuarios.get(id_)
        return dict(u) if u else None

    def nombre_ocupado(self, nombre, excepto_id):
        n = normalizar(nombre)
        return any(u["id"] != excepto_id and n in (normalizar(u["login"]), normalizar(u["nombre_visible"])) for u in self.usuarios.values())

    def cambiar_nombre(self, id_, nombre):
        with self._cerrojo:
            self.usuarios[id_]["nombre_visible"] = nombre

    def bloquear(self, id_, si=True):
        with self._cerrojo:
            if id_ in self.usuarios:
                self.usuarios[id_]["bloqueado"] = si

    # ---- plantillas ----
    def crear_plantilla(self, p):
        with self._cerrojo:
            if p["id"] in self.plantillas:
                return False
            self.plantillas[p["id"]] = {**p, "estado": "pendiente", "motivo": "", "decidido": None}
            return True

    def contar(self, usuario_id, estado=None, desde=0):
        return sum(1 for p in self.plantillas.values() if p["usuario_id"] == usuario_id and (estado is None or p["estado"] == estado) and p["creado"] >= desde)

    def obtener(self, id_, con_bytes=False):
        p = self.plantillas.get(id_)
        if not p:
            return None
        return dict(p, usuario=self.usuario(p["usuario_id"])) if con_bytes else _sin_bytes(p, self.usuario(p["usuario_id"]))

    def listar(self, estado=None, usuario_id=None):
        filas = [p for p in self.plantillas.values() if (estado is None or p["estado"] == estado) and (usuario_id is None or p["usuario_id"] == usuario_id)]
        return [_sin_bytes(p, self.usuario(p["usuario_id"])) for p in sorted(filas, key=lambda p: p["creado"], reverse=True)]

    def decidir(self, id_, estado, motivo, ahora):
        with self._cerrojo:
            p = self.plantillas.get(id_)
            if not p or estado not in ESTADOS:
                return False
            p.update(estado=estado, motivo=motivo, decidido=ahora)
            return True

    def borrar(self, id_, usuario_id=None):
        with self._cerrojo:
            p = self.plantillas.get(id_)
            if not p or (usuario_id is not None and p["usuario_id"] != usuario_id):
                return False
            del self.plantillas[id_]
            return True


ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id BIGINT PRIMARY KEY, login TEXT NOT NULL, nombre_visible TEXT NOT NULL, avatar TEXT NOT NULL DEFAULT '',
  creado_github DOUBLE PRECISION, bloqueado BOOLEAN NOT NULL DEFAULT FALSE, creado TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE UNIQUE INDEX IF NOT EXISTS usuarios_nombre_unico ON usuarios (lower(nombre_visible));
CREATE TABLE IF NOT EXISTS plantillas (
  id TEXT PRIMARY KEY, usuario_id BIGINT NOT NULL REFERENCES usuarios(id), nombre TEXT NOT NULL, descripcion TEXT NOT NULL,
  tipo TEXT NOT NULL, base TEXT NOT NULL DEFAULT '', imagenes_origen TEXT, imagenes_detalle TEXT, archivo BYTEA NOT NULL, previa BYTEA NOT NULL,
  estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','aprobada','rechazada')), motivo TEXT NOT NULL DEFAULT '',
  creado DOUBLE PRECISION NOT NULL, decidido DOUBLE PRECISION);
CREATE INDEX IF NOT EXISTS plantillas_estado ON plantillas (estado, creado);
CREATE INDEX IF NOT EXISTS plantillas_usuario ON plantillas (usuario_id, creado);
"""
_COLS = ", ".join(f"p.{c}" for c in _LISTA)


class AlmacenPostgres:
    """Neon (Postgres). Una conexión por petición: en una función sin estado es lo más simple y Neon la agrupa."""

    def __init__(self, url):
        self.url = url

    def _con(self):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(self.url, autocommit=True, row_factory=dict_row, connect_timeout=10)

    def _uno(self, sql, args=()):
        with self._con() as c:
            return c.execute(sql, args).fetchone()

    def _todos(self, sql, args=()):
        with self._con() as c:
            return c.execute(sql, args).fetchall()

    def crear_tablas(self):
        with self._con() as c:
            for sentencia in [s.strip() for s in ESQUEMA.split(";") if s.strip()]:
                c.execute(sentencia)

    def upsert_usuario(self, id_, login, avatar, creado_github):
        return self._uno(
            "INSERT INTO usuarios (id, login, nombre_visible, avatar, creado_github) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET login = EXCLUDED.login, avatar = EXCLUDED.avatar, creado_github = EXCLUDED.creado_github "
            "RETURNING id, login, nombre_visible, avatar, creado_github, bloqueado", (id_, login, login, avatar, creado_github))

    def usuario(self, id_):
        return self._uno("SELECT id, login, nombre_visible, avatar, creado_github, bloqueado FROM usuarios WHERE id = %s", (id_,))

    def usuario_por_nombre(self, nombre):
        return self._uno("SELECT id FROM usuarios WHERE lower(nombre_visible) = lower(%s) OR lower(login) = lower(%s)", (nombre, nombre))

    def nombre_ocupado(self, nombre, excepto_id):
        n = normalizar(nombre)
        return any(u["id"] != excepto_id and n in (normalizar(u["login"]), normalizar(u["nombre_visible"])) for u in self._todos("SELECT id, login, nombre_visible FROM usuarios"))

    def cambiar_nombre(self, id_, nombre):
        self._uno("UPDATE usuarios SET nombre_visible = %s WHERE id = %s RETURNING id", (nombre, id_))

    def bloquear(self, id_, si=True):
        self._uno("UPDATE usuarios SET bloqueado = %s WHERE id = %s RETURNING id", (si, id_))

    def crear_plantilla(self, p):
        fila = self._uno(
            "INSERT INTO plantillas (id, usuario_id, nombre, descripcion, tipo, base, imagenes_origen, imagenes_detalle, archivo, previa, creado) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING RETURNING id",
            (p["id"], p["usuario_id"], p["nombre"], p["descripcion"], p["tipo"], p["base"], p.get("imagenes_origen"), p.get("imagenes_detalle"), p["archivo"], p["previa"], p["creado"]))
        return fila is not None

    def contar(self, usuario_id, estado=None, desde=0):
        return self._uno("SELECT count(*) AS n FROM plantillas WHERE usuario_id = %s AND (%s::text IS NULL OR estado = %s) AND creado >= %s", (usuario_id, estado, estado, desde))["n"]

    def _con_usuario(self, fila):
        if not fila:
            return None
        u = {"id": fila.pop("u_id"), "login": fila.pop("u_login"), "nombre_visible": fila.pop("u_nombre")}
        fila["usuario"] = u
        return fila

    def obtener(self, id_, con_bytes=False):
        extra = ", p.archivo, p.previa" if con_bytes else ""
        fila = self._uno(f"SELECT {_COLS}{extra}, u.id AS u_id, u.login AS u_login, u.nombre_visible AS u_nombre FROM plantillas p JOIN usuarios u ON u.id = p.usuario_id WHERE p.id = %s", (id_,))
        return self._con_usuario(fila)

    def listar(self, estado=None, usuario_id=None):
        filas = self._todos(
            f"SELECT {_COLS}, u.id AS u_id, u.login AS u_login, u.nombre_visible AS u_nombre FROM plantillas p JOIN usuarios u ON u.id = p.usuario_id "
            "WHERE (%s::text IS NULL OR p.estado = %s) AND (%s::bigint IS NULL OR p.usuario_id = %s) ORDER BY p.creado DESC", (estado, estado, usuario_id, usuario_id))
        return [self._con_usuario(f) for f in filas]

    def decidir(self, id_, estado, motivo, ahora):
        if estado not in ESTADOS:
            return False
        return self._uno("UPDATE plantillas SET estado = %s, motivo = %s, decidido = %s WHERE id = %s RETURNING id", (estado, motivo, ahora, id_)) is not None

    def borrar(self, id_, usuario_id=None):
        return self._uno("DELETE FROM plantillas WHERE id = %s AND (%s::bigint IS NULL OR usuario_id = %s) RETURNING id", (id_, usuario_id, usuario_id)) is not None
