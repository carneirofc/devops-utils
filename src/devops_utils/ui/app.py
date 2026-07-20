"""Minimal Qt (PySide6) UI stub.

Requires the ``qt`` optional dependency: ``pip install devops-utils[qt]``.
Full windows are follow-up work; this stub only proves the surface launches and
is wired to the core package.
"""

import sys


def main() -> None:
    """Launch the Qt UI."""
    try:
        from PySide6.QtWidgets import QApplication, QLabel
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise SystemExit(
            "The Qt UI requires the 'qt' extra. "
            "Install it with: pip install devops-utils[qt]"
        ) from exc

    app = QApplication(sys.argv)
    label = QLabel("devops-utils — coming soon.")
    label.setWindowTitle("devops-utils")
    label.resize(320, 120)
    label.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
