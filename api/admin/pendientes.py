import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "_lib"))
import vercel  # noqa: E402


class handler(BaseHTTPRequestHandler):
    do_GET = do_POST = do_DELETE = vercel.atender("admin/pendientes")

    def log_message(self, *a):
        pass
