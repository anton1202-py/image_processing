from base_module.services.rabbit import RabbitService
from config import config

from services.task_worker import TasksWorker
from services.tasks import ImageProcessing

from . import connections



def rabbit() -> RabbitService:
    """."""
    return RabbitService(config.rabbit)


def processing_injector() -> ImageProcessing:
    """."""
    return ImageProcessing(
        pg_connection=connections.pg.acquire_session(),
        rabbit=rabbit()
    )

def tasks_mule() -> TasksWorker:
    """."""
    return TasksWorker(
        rabbit=rabbit(),
        pg_connection=connections.pg.acquire_session(),
        storage_dir=config.storage_dir
    )
