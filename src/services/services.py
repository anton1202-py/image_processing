import json
from typing import Optional

import requests
from PIL import Image


class FileStorageData:
    """."""

    def file_info_data(self, file_id) -> Optional[dict]:
        url = f"http://file-sync:5001/api/files/{file_id}"
        response = requests.request("GET", url)
        if response.status_code == 200:
            return json.loads(response.text)

    def file_download(self, file_id) -> requests.Response:
        url = f"http://file-sync:5001/api/files/{file_id}/download"
        response = requests.request("GET", url)
        return response

    def file_upload(self, file_name, file_path, upload_path=None) -> dict:
        url = "http://file-sync:5001/api/upload"

        payload = {"upload_path": upload_path}
        files = [("", (file_name, open(file_path, "rb"), "image/jpeg"))]
        response = requests.request("POST", url, data=payload, files=files)
        return json.loads(response.text)


class ImageProcessor:
    """."""

    def image_process(self, image, task_type, task_type_value):
        if task_type == "scale":
            return self._image_scale(image, task_type_value)
        elif task_type == "rotate":
            return self._image_rotate(image, task_type_value)

    def _image_scale(self, image, scale_percent):
        """Масштабирование изображения"""
        new_width = int(image.size[0] * (scale_percent / 100))
        new_height = int(image.size[1] * (scale_percent / 100))
        new_size = (new_width, new_height)
        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
        return resized_image

    def _image_rotate(self, image, rotate_angle):
        """Поворот изображения"""
        return image.rotate(rotate_angle, expand=True)
