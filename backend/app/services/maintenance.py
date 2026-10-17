"""Tâches de maintenance, partagées par les scripts (scripts/purge_*.py, en ligne de commande) et
par les tâches de nuit du processus (app/services/nightly_scheduler.py).

Chacune ouvre sa propre session et ne supprime que ce qui a expiré : la relancer ne pose aucun
problème.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.image_storage import ImageStorage
from app.services.images import ImageService
from app.services.templates import TemplateService

# Ouvre une session de base de données (Session(engine) en production, celle du test sinon)
MaintenanceSessionFactory = Callable[[], AbstractContextManager[Session]]


def purge_deleted_templates(session_factory: MaintenanceSessionFactory, settings: Settings) -> int:
    """Supprime définitivement les templates supprimés depuis plus de
    DELETED_TEMPLATE_RETENTION_DAYS ; renvoie leur nombre."""
    with session_factory() as session:
        return TemplateService(session, settings).purge_deleted()


def purge_unused_images(
    session_factory: MaintenanceSessionFactory, settings: Settings, storage: ImageStorage
) -> int:
    """Efface les images qu'aucune tuile n'utilise depuis plus de UNUSED_IMAGE_RETENTION_DAYS ;
    renvoie leur nombre."""
    with session_factory() as session:
        return ImageService(session, settings, storage).purge_unused()
