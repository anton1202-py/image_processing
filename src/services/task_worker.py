import os
from datetime import datetime
import shutil

import sqlalchemy as sa
from PIL import Image
from sqlalchemy.orm import Session as PGSession
from services.services import FileStorageData
from base_module import sa_operator
from base_module.exceptions import ModuleException
from base_module.logger import ClassesLoggerAdapter
from base_module.mule import BaseMule
from base_module.rabbit import TaskIdentMessageModel
from base_module.services.rabbit import RabbitService
from models.orm_models import ImageProcessingTask, TaskStatus


class TasksWorker(BaseMule):
    """Сервис обработки задач"""

    def __init__(
        self,
        rabbit: RabbitService,
        pg_connection: PGSession,
        file_request: FileStorageData,
        storage_dir: str,
    ):
        """Инициализация сервиса"""
        self._rabbit = rabbit
        self._pg = pg_connection
        self._storage_dir = storage_dir
        self._logger = ClassesLoggerAdapter.create(self)
        self._f_req = file_request
    
    def _temp_dir(self, task_id: int) -> str:
        """Создание временной папки"""
        temp_dir = os.path.join(self._storage_dir, str(task_id))
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

    def _handle(self, task: ImageProcessingTask):
        """Обработка задачи"""
        self._logger.info("Обработка задачи", extra={"task": task.task_id})
        task = ImageProcessingTask.load(task.dump())
        temp_dir = self._temp_dir(task.task_id)
        file_id = task.file_id

        try:
            data = self._f_req.file_download(file_id)
            storage_file_data = self._f_req.file_info_data(file_id)

            temp_file = f"{file_id}_{str(task.task_id)}{storage_file_data.get('extension', 'jpg')}"
            temp_file_path = os.path.join(temp_dir, temp_file)

            with open(temp_file_path, 'wb') as f:
                f.write(data.content)

            image = Image.open(temp_file_path)

            scale_percent = task.processing_parameters.get("scale", 100)
            new_width = int(image.size[0] * (scale_percent / 100))

            new_height = int(image.size[1] * (scale_percent / 100))
            new_size = (new_width, new_height)

            resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
            rotate_angle = task.processing_parameters.get("angle_rotate", 0)
            changed_image = resized_image.rotate(rotate_angle, expand=True)
            
            new_name = f"{storage_file_data.get('name')}_{str(task.task_id)}{storage_file_data.get('extension', 'jpg')}"
            new_path = os.path.join(self._storage_dir, new_name)
            changed_image.save(new_path)
            
            upload_file = self._f_req.file_upload(new_name, new_path, self._storage_dir)
           
            new_file_id = upload_file.get('file_id')
            self._update_task_info(task, TaskStatus.DONE, new_file_id)
            
            
        except Exception as e:
            self._logger.critical(
                "Ошибка обработки задачи",
                exc_info=True,
                extra={"e": e, "task": task.task_id},
            )
            self._update_task_info(task, TaskStatus.ERROR)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            self._logger.info(
                "Обработка задачи завершена", extra={"task": task.task_id}
            )

    def _update_task_info(
        self, task: ImageProcessingTask, status: TaskStatus, processed_file_id=0
    ):
        """Обновление статуса задачи"""
        task.status = status
        updated = datetime.now()
        task.updated_at = updated
        task.processed_file_id = processed_file_id
        self._logger.info(
            "Обновление данных задачи",
            extra={
                "task_id": task.task_id,
                "status": task.status,
                "processed_file_id": processed_file_id,
            },
        )
        if self._pg.get(ImageProcessingTask, task.task_id, with_for_update=True):
            self._pg.merge(task)
            self._pg.commit()
            return task.reload()

    def _get_task(self, task_id: int) -> ImageProcessingTask | None:
        """Получение задачи из БД"""
        with self._pg.begin():
            task: ImageProcessingTask = self._pg.execute(
                sa.select(ImageProcessingTask)
                .filter(
                    sa.and_(
                        sa_operator.eq(ImageProcessingTask.task_id, task_id),
                        sa_operator.in_(
                            ImageProcessingTask.status,
                            [
                                TaskStatus.NEW,
                                # В случае ручного восстановления работы
                                TaskStatus.PROCESSING,
                            ],
                        ),
                    )
                )
                .limit(1)
            ).scalar()
            if not task:
                return

            task.status = TaskStatus.PROCESSING
            task.updated_at = datetime.now()
            self._pg.merge(task)
            return task.reload()

    def _handle_message(self, message: TaskIdentMessageModel, **_):
        """Обработка сообщения от брокера"""
        task_id = message.payload.task_id
        task = self._get_task(task_id)
        if not task:
            self._logger.warn("Задача не найдена", extra={"task_id": task_id})
            return

        try:
            self._handle(task)
        except Exception as e:
            exc_data = {"e": e}
            if isinstance(e, ModuleException):
                exc_data.update(e.data)
            self._logger.critical(
                "Ошибка верхнего уровня обработчика задачи",
                extra=exc_data,
                exc_info=True,
            )
            self._update_task_info(task, TaskStatus.ERROR)

    def run(self):
        """Запуск прослушивания очереди брокера сообщений"""
        self._rabbit.run_consume(self._handle_message, TaskIdentMessageModel)
