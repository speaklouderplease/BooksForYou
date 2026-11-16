import sys

from .app import run

if __name__ == "__main__":
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None and not sys.stdout.isatty():
        reconfigure(errors="replace")
    sys.exit(run())
