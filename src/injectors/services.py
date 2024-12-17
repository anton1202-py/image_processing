from base_module.services.rabbit import RabbitService
from config import config

from services.services import FileStorageData
from services.task_worker import TasksWorker
from services.tasks import ImageProcessing

from . import connections



def rabbit() -> RabbitService:
    """."""
    return RabbitService(config.rabbit)


def file_storage_req() -> FileStorageData:
    """."""
    return FileStorageData()


def processing_injector() -> ImageProcessing:
    """."""
    return ImageProcessing(
        pg_connection=connections.pg.acquire_session(),
        rabbit=rabbit(),
        file_request=file_storage_req()
    )


def tasks_mule() -> TasksWorker:
    """."""
    return TasksWorker(
        rabbit=rabbit(),
        pg_connection=connections.pg.acquire_session(),
        file_request=file_storage_req(),
        storage_dir=config.storage_dir
    )

