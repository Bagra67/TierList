from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.services.image_storage import ImageStorage
from app.services.images import ImageService
from app.services.moderation_log import ModerationLogService
from app.services.report_queue import ReportQueueService
from app.services.templates import TemplateService

MaintenanceSessionFactory = Callable[[], AbstractContextManager[Session]]


def purge_deleted_templates(session_factory: MaintenanceSessionFactory, settings: Settings) -> int:
    with session_factory() as session:
        return TemplateService(session, settings).purge_deleted()


def purge_unused_images(
    session_factory: MaintenanceSessionFactory, settings: Settings, storage: ImageStorage
) -> int:
    with session_factory() as session:
        return ImageService(session, settings, storage).purge_unused()


def purge_moderation_log(session_factory: MaintenanceSessionFactory, settings: Settings) -> int:
    with session_factory() as session:
        return ModerationLogService(session, settings).purge_expired()


def purge_closed_reports(session_factory: MaintenanceSessionFactory, settings: Settings) -> int:
    with session_factory() as session:
        return ReportQueueService(
            session, settings, ModerationLogService(session, settings)
        ).purge_closed()
