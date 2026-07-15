from dataclasses import dataclass
from typing import Any, TYPE_CHECKING
from urllib import request
from pathlib import Path
from uuid import uuid4
import json
from .utils import sort_snapshots
from . import __version__

if TYPE_CHECKING: 
    from http.client import HTTPResponse

class Http:
    headers: dict[str, str] = {
        "User-Agent": f"squarecloud-restorer/{__version__}"
    }

    def set_api_key(self, api_key: str) -> None:
        self.headers = self.headers | {"Authorization": api_key}

    def error_handler(self, status: int) -> None: ...

    def request(self, url: str, method: str, data: dict[str, Any]|bytes) -> HTTPResponse:
        if isinstance(data, dict): 
            _request = request.Request(url, json.dumps(data).encode("utf-8"), headers=self.headers, method=method.upper())
        else:
            _request = request.Request(url, data, headers=self.headers, method=method.upper())
        response: HTTPResponse = request.urlopen(_request, timeout=40.0)
        return response

    def get_snapshots(self, apps: bool = False, databases: bool = False):
        API_URL = 'https://api.squarecloud.app/v2/users/snapshots?scope={scope}'
        user_id = self.get_user()
        requests: dict[str, HTTPResponse] = {}
        if apps: requests["apps"] = self.request(API_URL.format(scope='applications'), 'get', {})
        if databases: requests["databases"] = self.request(API_URL.format(scope='databases'), 'get', {})
        all_snapshots: dict[str, list[BaseSnapshot]] = {}
        for k,v in requests.items():
            response_json: dict[str, Any] = json.loads(v.read())
            v.close()
            snaps_unfiltered = sort_snapshots(response_json["response"])
            filtered: dict[str, dict] = {snap["name"]: snap for snap in snaps_unfiltered}
            match k:
                case 'apps': 
                    all_snapshots[k] = [ApplicationSnapshot(**data, account_id=user_id) for data in sorted(filtered.values(), key=lambda data: data["modified"], reverse=True)]
                case 'databases':
                    all_snapshots[k] = [DatabaseSnapshot(**data, account_id=user_id) for data in sorted(filtered.values(), key=lambda data: data["modified"], reverse=True)]
        return all_snapshots
        
    def get_user(self) -> str:
        _request = self.request(f"https://api.squarecloud.app/v2/users/me", 'get', {})
        response = json.loads(_request.read())
        _request.close()
        return response["response"]["user"]["id"]


@dataclass(init=True, repr=True)
class BaseSnapshot:
    name: str
    size: int
    modified: str
    key: str
    account_id: str

    @property
    def url(self):
        return f"https://snapshots.squarecloud.app/applications/{self.account_id}/{self.name}.zip?{self.key}"

    def restore(self, api_key: str): ...

class DatabaseSnapshot(BaseSnapshot):
    def restore(self, api_key: str):
        ...


class ApplicationSnapshot(BaseSnapshot):
    DOWNLOAD_SPEED = 1024 * 1024
    def download(self) -> Path|None:
        _http = Http()
        _request = _http.request(self.url, "get", {})
        path = Path.home()/f'downloads/{self.name}.zip'
        file = open(path, 'wb')
        if _request.status != 200: return _http.error_handler(_request.status)
        try:
            while True:
                data = _request.read(self.DOWNLOAD_SPEED)
                if not data: break
                file.write(data)
        finally:
            file.close()
            _request.close()
        return path
        
    def upload(self, fp: Path, api_key: str):
        _http = Http()
        _http.set_api_key(api_key)
        file = open(fp, 'rb')
        boundary = uuid4().hex
        form_data_struct: list[bytes] = [
            f'--{boundary}'.encode(),
            f'Content-Disposition: form-data; name="file"; filename="application.zip"'.encode(),
            b'Content-Type: application/octet-stream',
            b'',
            file.read(),
            f'--{boundary}--'.encode(),
            b''
        ]
        form_data = b'\r\n'.join(form_data_struct)
        _request = _http.request('https://api.squarecloud.app/v2/apps', 'post', form_data)
        if _request.status != 200: _http.error_handler(_request.status)    
        file.close()
        _request.close()

    def restore(self, api_key: str):
        fp = self.download()
        if not fp: return
        self.upload(fp, api_key)