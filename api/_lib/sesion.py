"""Sesión en una cookie firmada (HMAC-SHA256): sin base de datos de sesiones y sin contraseñas. Quien no tiene el secreto no puede fabricar una."""
import base64
import hashlib
import hmac
import json

NOMBRE = "rv_sesion"
DURACION = 14 * 24 * 3600


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _desb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def firmar(datos: dict, secreto: str, ahora: float, duracion: int = DURACION) -> str:
    cuerpo = _b64(json.dumps({**datos, "exp": int(ahora) + duracion}, separators=(",", ":")).encode())
    return f"{cuerpo}.{_b64(hmac.new(secreto.encode(), cuerpo.encode(), hashlib.sha256).digest())}"


def verificar(token, secreto: str, ahora: float):
    """Los datos de la sesión, o None si la firma no cuadra, está vencida o viene rara."""
    if not secreto or not isinstance(token, str) or token.count(".") != 1 or len(token) > 2048:
        return None
    cuerpo, firma = token.split(".")
    try:
        esperada = _b64(hmac.new(secreto.encode(), cuerpo.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(firma, esperada):
            return None
        datos = json.loads(_desb64(cuerpo))
    except (ValueError, TypeError):
        return None
    if not isinstance(datos, dict) or not isinstance(datos.get("uid"), int) or not isinstance(datos.get("exp"), int) or datos["exp"] < ahora:
        return None
    return datos


def cookie(nombre: str, valor: str, max_age: int, ruta: str = "/") -> str:
    """Set-Cookie seguro: no la lee JavaScript (HttpOnly), solo viaja por HTTPS y no se manda desde otros sitios (SameSite=Lax)."""
    return f"{nombre}={valor}; Max-Age={max_age}; Path={ruta}; HttpOnly; Secure; SameSite=Lax"
