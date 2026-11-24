import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "_lib"))
import puente  # noqa: E402


class handler(BaseHTTPRequestHandler):
    do_GET = do_POST = do_DELETE = puente.atender("catalogo")

    def log_message(self, *a):
        pass
