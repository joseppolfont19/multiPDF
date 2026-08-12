"""``python -m archivepdf`` opens the GUI; the CLI lives in ``archivepdf.cli``."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from .gui import launch
    except ImportError as exc:
        print(
            "No se pudo cargar la interfaz gráfica: "
            f"{exc}\nInstala las dependencias con: pip install 'archive-pdf-toolkit[gui]'",
            file=sys.stderr,
        )
        return 2

    launch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
