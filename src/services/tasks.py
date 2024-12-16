from typing import Optional

import pika
import sqlalchemy as sa
from sqlalchemy.orm import Session as PGSession

from base_module import sa_operator
from base_module.exceptions import ModuleException
from base_module.rabbit import TaskIdentMessageModel
from base_module.sevices.rabbit import RabbitService
from models.orm_models import FileInfo, ImageProcessingTask, TaskStatus


class ImageProcessing:

    def __init__(
        self,
        pg_connection: PGSession,
        rabbit: RabbitService,
    ):
        self._pg = pg_connection
        self._rabbit = rabbit

    def check_exists(self, file_id: int) -> Optional[FileInfo]:
        return self._pg.query(FileInfo).filter(FileInfo.id == file_id).first()

    def create_task(
        self, file_id: int, processing_parameters: dict
    ) -> ImageProcessingTask:

        if self.check_exists(file_id):
            task = ImageProcessingTask(
                file_id=file_id,
                processing_parameters=processing_parameters,
            )
        else:
            task = ImageProcessingTask(
                file_id=file_id,
                processing_parameters=processing_parameters,
                status=TaskStatus.ERROR,
            )

        self._pg.add(task)
        self._pg.commit()

        message = TaskIdentMessageModel.lazy_load(TaskIdentMessageModel.T(task.task_id))

        published = self._rabbit.publish(message, properties=pika.BasicProperties())
        if published:
            return task.dump()

        with self._pg.begin():
            self._pg.delete(task)

    def get_all(self) -> list[ImageProcessingTask]:
        """."""
        with self._pg.begin():
            q = self._pg.query(ImageProcessingTask)
            q = q.order_by(sa.desc(ImageProcessingTask.created_at))
            return q.all()

    def get(self, task_id: int) -> ImageProcessingTask:
        with self._pg.begin():
            task: ImageProcessingTask = (
                self._pg.query(ImageProcessingTask)
                .filter(
                    sa.and_(
                        sa_operator.eq(ImageProcessingTask.task_id, task_id),
                    )
                )
                .one_or_none()
            )
            if task:
                return task.dump()

        raise ModuleException("Задача не найдена", code=404)