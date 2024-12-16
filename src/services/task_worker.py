import os
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from PIL import Image
from sqlalchemy.orm import Session as PGSession

from base_module import sa_operator
from base_module.exceptions import ModuleException
from base_module.logger import ClassesLoggerAdapter
from base_module.mule import BaseMule
from base_module.rabbit import TaskIdentMessageModel
from base_module.sevices.rabbit import RabbitService
from models.orm_models import FileInfo, ImageProcessingTask, TaskStatus


class TasksWorker(BaseMule):
    """Сервис обработки задач"""

    def __init__(
        self,
        rabbit: RabbitService,
        pg_connection: PGSession,
        storage_dir: str,
    ):
        """Инициализация сервиса"""
        self._rabbit = rabbit
        self._pg = pg_connection
        self._storage_dir = storage_dir
        self._logger = ClassesLoggerAdapter.create(self)

    def _handle(self, task: ImageProcessingTask):
        """Обработка задачи"""
        self._logger.info("Обработка задачи", extra={"task": task.task_id})
        task = ImageProcessingTask.load(task.dump())
        file_id = task.file_id
        file = self._pg.query(FileInfo).filter(FileInfo.id == file_id).first()
        file_path = os.path.join(file.path_file, file.name + file.extension)

        try:
            image = Image.open(file_path)
            scale_percent = task.processing_parameters.get("scale", 100)
            new_width = int(image.size[0] * (scale_percent / 100))
            new_height = int(image.size[1] * (scale_percent / 100))
            new_size = (new_width, new_height)
            resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
            rotate_angle = task.processing_parameters.get("angle_rotate", 0)
            changed_image = resized_image.rotate(rotate_angle, expand=True)

            new_name = f"{file.name}_{str(task.task_id)}"
            new_path = os.path.join(self._storage_dir, new_name + file.extension)
            changed_image.save(new_path)
            file_size = os.path.getsize(new_path) / 1024
            new_file_info = FileInfo(
                name=new_name,
                extension=str(file.extension),
                path_file=self._storage_dir,
                size=file_size,
            )
            self._pg.add(new_file_info)
            self._pg.commit()
            self._update_task_info(task, TaskStatus.DONE, new_file_info.id)
        except Exception as e:
            self._logger.critical(
                "Ошибка обработки задачи",
                exc_info=True,
                extra={"e": e, "task": task.task_id},
            )
            self._update_task_info(task, TaskStatus.ERROR)
        finally:
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
        # with self._pg.begin():
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
