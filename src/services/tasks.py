from typing import Optional
from flask import jsonify
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
    
    def _task_type_checker(self, request_data: dict) -> dict:
        req_task_type = None
        task_type_value = None

        if "rotate" in request_data:
            req_task_type = 'rotate'
        elif "scale" in request_data:
            req_task_type = 'scale'
        
        if req_task_type:
            task_type_value = request_data.get(req_task_type)

        if req_task_type and task_type_value:
            return {'task_type': TaskType.from_value(req_task_type), 'task_type_value': task_type_value}
        else:
            return

    def create_task(
        self, file_id: int, request_data: dict
    ) -> ImageProcessingTask:

        task_proc_type = self._task_type_checker(request_data)
        if not task_proc_type:
            return jsonify({"error": "Проверьте введенные данные"}), 400

        task_type = task_proc_type.get('task_type')
        task_type_value = task_proc_type.get('task_type_value')
            
        if self.check_exists(file_id): 
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
