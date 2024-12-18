from typing import Optional
import pika
import sqlalchemy as sa
from sqlalchemy.orm import Session as PGSession

from base_module import sa_operator
from base_module.exceptions import ModuleException
from base_module.rabbit import TaskIdentMessageModel
from base_module.services.rabbit import RabbitService
from models.orm_models import ImageProcessingTask, TaskStatus, TaskType
from services.services import FileStorageData


class ImageProcessing:

    def __init__(
        self,
        pg_connection: PGSession,
        rabbit: RabbitService,
        file_request: FileStorageData
    ):
        self._pg = pg_connection
        self._rabbit = rabbit
        self._f_req = file_request

    def check_exists(self, file_id: int) -> Optional[dict]:
        check_response = self._f_req.file_info_data(file_id)
        return check_response

    def create_task(
        self, file_id: int, request_data: dict
    ) -> ImageProcessingTask:
        if "rotate" in request_data:
            req_task_type = 'rotate'
        elif "scale" in request_data:
            req_task_type = 'scale'
        else:
            req_task_type = "error"
        task_type_value = request_data.get(req_task_type, None)
        task_type = TaskType.from_value(req_task_type)
            
        if self.check_exists(file_id) and req_task_type and task_type_value: 
            task = ImageProcessingTask(
                file_id=file_id,
                task_type=task_type,
                task_type_value=task_type_value
            )
        else:
            task = ImageProcessingTask(
                file_id=file_id,
                task_type=task_type,
                task_type_value=task_type_value,
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
            q_list = [q_obj.dump() for q_obj in q]
            return q_list

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
