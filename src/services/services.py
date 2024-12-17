import json
import requests


class FileStorageData:
    """."""
    
    def file_info_data(self, file_id):
        url = f"http://127.0.0.1:5001/api/files/{file_id}"
        response = requests.request("GET", url)
        if response.status_code == 200:
            return json.loads(response.text)
    
    def file_download(self, file_id):
        url = f"http://127.0.0.1:5001/api/files/{file_id}/download"
        response = requests.request("GET", url)
        return response
    
    def file_upload(self, file_name, file_path, upload_path):
        url = "http://127.0.0.1:5001/api/upload"

        payload = {'upload_path': upload_path}
        files=[
          ('',(file_name, open(file_path,'rb'),'image/jpeg'))
        ]
        response = requests.request("POST", url, data=payload, files=files)
        return json.loads(response.text)
    
