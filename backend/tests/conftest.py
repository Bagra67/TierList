"""Fixtures communes à tous les tests (celles des tests d'intégration sont dans integration/)."""

import logging
import sys

import pytest

from app.constants.logging import APP_LOGGER


@pytest.fixture(autouse=True)
def app_logs_to_captured_stderr() -> None:
    """Les logs de l'application vont dans la sortie capturée du test.

    configure_logging (app/main.py) lie son handler au sys.stderr du moment de l'import. Sans
    xdist, c'est déjà celui que pytest capture ; dans un worker de pytest-xdist, app.main est
    importé avant la capture : les logs iraient sur le vrai stderr et s'afficheraient en vrac
    dans la sortie de pytest. Chaque test rebranche donc le handler sur le stderr capturé.
    """
    app_logger: logging.Logger = logging.getLogger(APP_LOGGER)
    for handler in app_logger.handlers:
        # Type exact : pytest ajoute aussi ses handlers (LogCaptureHandler, sous-classe de
        # StreamHandler), qui doivent garder leur propre flux
        if type(handler) is logging.StreamHandler:
            # Pas setStream(), qui vide l'ancien flux : celui de capsys d'un test précédent
            # (test_errors.py rappelle configure_logging) est déjà fermé
            handler.stream = sys.stderr
