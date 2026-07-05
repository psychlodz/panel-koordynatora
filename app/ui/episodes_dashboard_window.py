"""Dashboard epizodów.

Moduł zachowuje zgodność z dotychczasową nazwą ``episodes_window``.
"""

from app.ui.episodes_window import EpisodesWindow as _EpisodesWindow


class EpisodesDashboardWindow(_EpisodesWindow):
    """Główny dashboard pacjentów uczestniczących w programach."""


# Zgodność dla kodu oczekującego historycznej nazwy klasy.
EpisodesWindow = EpisodesDashboardWindow
