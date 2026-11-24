import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "_lib"))
import vercel  # noqa: E402

handler = vercel.handler("admin/pendientes")
