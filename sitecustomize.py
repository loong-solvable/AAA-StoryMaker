import os
import sys


def _reconfigure_stream(stream) -> None:
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        return


if os.name == "nt":
    _reconfigure_stream(sys.stdout)
    _reconfigure_stream(sys.stderr)
