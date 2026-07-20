"""Minimal Textual TUI stub.

Requires the ``tui`` optional dependency: ``pip install devops-utils[tui]``.
Full screens are follow-up work; this stub only proves the surface launches and
is wired to the core package.
"""


def _build_app():
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import Footer, Header, Static
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise SystemExit(
            "The TUI requires the 'tui' extra. "
            "Install it with: pip install devops-utils[tui]"
        ) from exc

    class DevopsUtilsApp(App):
        """Placeholder TUI for devops-utils."""

        TITLE = "devops-utils"

        def compose(self) -> "ComposeResult":
            yield Header()
            yield Static("devops-utils TUI — coming soon.")
            yield Footer()

    return DevopsUtilsApp()


def main() -> None:
    """Launch the TUI."""
    _build_app().run()


if __name__ == "__main__":
    main()
