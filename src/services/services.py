import os
from datetime import datetime
from pathlib import Path

from flask import Response, abort, send_file
from sqlalchemy.orm import Session as PGSession

from models.orm_models import FileInfo


class SyncFileWithDb:
    """Синхронизация файлов с базой данных"""

    def __init__(self, pg_connection: PGSession, storage_dir: str):
        self._pg = pg_connection
        self.storage_dir = storage_dir

    def _add_files(self, directory: str) -> None:
        """Добавлет файлы в БД"""
        files_to_insert = []
        with self._pg.begin():
            for root, dirs, files in os.walk(directory):
                data = (
                    self._pg.query(FileInfo)
                    .filter(FileInfo.path_file == str(root).replace("\\", "/"))
                    .all()
                )
                if data:
                    for file_obj in data:
                        common_file_path = os.path.join(
                            file_obj.path_file, file_obj.name + file_obj.extension
                        )
                        if not common_file_path:
                            self._pg.delete(file_obj)
                # Записываю в БД файлы, которые еще не записаны
                for i, file in enumerate(files):
                    common_file_data = Path(file)
                    path_with_file_and_extension = os.path.join(root, file)
                    file_path = str(Path(path_with_file_and_extension).parent).replace(
                        "\\", "/"
                    )
                    file_name = common_file_data.stem
                    file_extension = common_file_data.suffix
                    try:
                        file_size = round(
                            os.path.getsize(path_with_file_and_extension) / 1024, 2
                        )
                    except:
                        file_size = 0
                    file_obj = (
                        self._pg.query(FileInfo)
                        .filter(
                            FileInfo.name == str(file_name),
                            FileInfo.path_file == file_path,
                            FileInfo.extension == file_extension,
                        )
                        .first()
                    )
                    if not file_obj:
                        db_file_info = FileInfo(
                            name=str(file_name),
                            extension=str(file_extension),
                            path_file=file_path,
                            size=file_size,
                        )
                        files_to_insert.append(db_file_info)
                    if (len(files_to_insert) >= 7000 and i < (len(files) - 2)) or (
                        i == (len(files) - 1) and files_to_insert
                    ):
                        self._pg.bulk_save_objects(files_to_insert)
                        files_to_insert = []

    def _del_files_from_db(self, directory: str) -> None:
        """Удаляет файлы из БД, если нет в файловом хранилище"""
        with self._pg.begin():
            for root, dirs, files in os.walk(directory):
                data = (
                    self._pg.query(FileInfo)
                    .filter(FileInfo.path_file == str(root).replace("\\", "/"))
                    .all()
                )
                if data:
                    for file_obj in data:
                        common_file_path = os.path.join(
                            file_obj.path_file, file_obj.name + file_obj.extension
                        )
                        if not common_file_path:
                            self._pg.delete(file_obj)

    def sync_local_storage_with_db(self, directory):
        """Синхронизирует локальное хранилище файлов с базой данных"""
        self._add_files(directory)
        self._del_files_from_db(directory)

    def sync_files(self) -> list[FileInfo]:
        self.sync_local_storage_with_db(self.storage_dir)
        response = (
            self._pg.query(FileInfo)
            .filter(FileInfo.path_file.like(f"%{self.storage_dir }%"))
            .all()
        )
        return response


class WorkerWithFIles:

    def __init__(
        self,
        pg_connection: PGSession,
        storage_dir: str,
        synchron: SyncFileWithDb = None,
    ):
        self._pg = pg_connection
        self.synchron = synchron
        self.storage_dir = storage_dir

    def get_files_info(self) -> list[FileInfo]:
        """
        Информация по всем файлам

        Для получения полного списка файлов используйте
        пагинацию с помощью **per_page** и **page**.
        **per_page** - число строк, выдаваемое на странице (по умолчанию 100)
        **page** - номер страницы (по умолчанию 1)
        """
        query = self._pg.query(FileInfo).all()
        response = [file.load(file) for file in query]
        return response

    def files_in_folder(self, directory_name: str = None) -> list[FileInfo]:
        """
        Информация по файлам из введенной папки

        Для получения полного списка файлов используйте
        пагинацию с помощью **per_page** и **page**.
        **per_page** - число строк, выдаваемое на странице (по умолчанию 100)
        **page** - номер страницы (по умолчанию 1)
        """
        if not directory_name:
            return {"message": "directory_name is required"}, 400
        response = (
            self._pg.query(FileInfo)
            .filter(FileInfo.path_file.like(f"%{directory_name}%"))
            .all()
        )
        return response

    def one_file_info(self, file_id: int = None) -> FileInfo:
        """Информация по одному файлу"""
        if not file_id:
            return {"message": "file_id is required"}
        file = self._pg.query(FileInfo).filter(FileInfo.id == file_id).first()
        if not file:
            return {"message": "File not found."}
        return file.load(file)

    def get_download_file(self, file_id: int = None) -> Response:
        """Скачать файл по ID"""
        try:
            if not file_id:
                return {"message": "file_id is required"}
            file = self._pg.query(FileInfo).filter(FileInfo.id == file_id).first()
            if not file:
                return {"message": "File not found."}
            file_path = os.path.join(file.path_file, file.name + file.extension)
            if not os.path.isfile(file_path):
                abort(404, description="File not found on server")
            return send_file(file_path, as_attachment=True)
        except Exception as e:
            return {"message": str(e)}

    def upload_file(self, file_obj=None, upload_path: str = None) -> dict:
        """Загрузить файл в базу данных"""

        if file_obj is None or file_obj.filename == "":
            return {"error": "No selected file"}
        if not upload_path:
            upload_path = self.storage_dir
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        file_path = os.path.join(upload_path, file_obj.filename)
        file_obj.save(file_path)
        path = Path(file_path)
        file_name = path.stem
        file_extension = path.suffix
        file_size = round(os.path.getsize(path) / 1024, 2)
        new_file_info = FileInfo(
            name=str(file_name),
            extension=str(file_extension),
            path_file=upload_path,
            size=file_size,
        )
        try:
            with self._pg.begin():
                file = (
                    self._pg.query(FileInfo)
                    .filter(
                        FileInfo.name == file_name,
                        FileInfo.extension == file_extension,
                        FileInfo.path_file == upload_path,
                    )
                    .first()
                )
                if not file:
                    self._pg.add(new_file_info)
                    return {"file_id": new_file_info.id}
                else:
                    return {"error": "Файл уже существет"}
        except Exception as e:
            return {"error": str(e)}

    def delete_file(self, file_id: int = None) -> dict:
        """Удаляет файл из базы данных и из файловой системы."""
        if not file_id:
            return {"message": "file_id is required"}
        with self._pg.begin():
            file = self._pg.query(FileInfo).filter(FileInfo.id == file_id).first()
            if not file:
                return {"message": "File not found."}

            file_path = os.path.join(file.path_file, file.name + file.extension)
            if not os.path.isfile(file_path):
                abort(404, description="File not found on server")
            try:
                os.remove(file_path)
                self._pg.delete(file)
                return {"message": "File deleted successfully"}
            except Exception as e:
                self._pg.rollback()  # Откат транзакции в случае ошибки
                return {"error": str(e)}

    def update_file(
        self,
        file_id: int = None,
        new_name: str = None,
        new_comment: str = None,
        new_path_file: str = None,
    ) -> FileInfo:
        """Обновляет информацию о файле"""
        try:
            with self._pg.begin():
                file_obj = (
                    self._pg.query(FileInfo).filter(FileInfo.id == int(file_id)).first()
                )
                if file_obj is None:
                    return {"message": "File not found."}

                old_file_path = os.path.join(
                    file_obj.path_file, file_obj.name + file_obj.extension
                )

                if new_name:
                    file_obj.name = new_name
                if new_comment:
                    file_obj.comment = new_comment
                if new_path_file:
                    file_obj.path_file = new_path_file

                file_obj.date_change = datetime.now()

            new_file_path = os.path.join(
                file_obj.path_file, file_obj.name + file_obj.extension
            )
            if os.path.exists(old_file_path):
                os.rename(old_file_path, new_file_path)
            else:
                return {"message": "Old file not found."}

            return file_obj.load(file_obj)
        except Exception as e:
            return {"error": str(e)}
