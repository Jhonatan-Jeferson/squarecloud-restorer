from dataclasses import dataclass
from pathlib import Path
from .http import URL, HTTPRequest

@dataclass(init=True, repr=True)
class BaseSnapshot:
    name: str
    size: int
    modified: str
    key: str
    account_id: str

    def restore(self, api_key: str) -> None: 
        raise Exception('Not implemented')

class ApplicationSnapshot(BaseSnapshot):
    def download(self, api_key: str) -> Path|None:
        endpoint = URL.get_snapshot(self.account_id, self.name, self.key)
        request = HTTPRequest(
            endpoint, 
            {
                'Authorization': api_key
            },
            {},
            'GET'
            )
        response = request.request()
        if response.status_code != 200:
            print(f'Failed Download({response.status_code}): {self.name}')
            return
        fp = Path.home() / 'downloads' / f'{self.name}.zip'
        with open(fp, 'wb') as file:
            while True:
                buffer = response.read(5*1024*1024)
                if not buffer: break
                file.write(buffer)
        return fp

    def upload(self, fp: Path, api_key: str):
        endpoint = URL.upload()
        with open(fp, 'rb') as file: 
            request = HTTPRequest(
                endpoint,
                {
                    'Authorization': api_key
                },
                file,
                'POST'
            )
            response = request.request()
            print(f'Upload app result: {response.status_code}')

    def restore(self, api_key: str) -> None:
        fp = self.download(api_key)
        if not fp: return
        self.upload(fp, api_key)

class DatabaseSnapshot(BaseSnapshot):
    def upload(self, api_key: str): ...
    def restore(self, api_key: str): ...
