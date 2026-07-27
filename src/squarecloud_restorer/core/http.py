import socket
import json
from uuid import uuid4
from io import BufferedReader
from dataclasses import dataclass
from typing import Any, Generator, Literal, cast, TYPE_CHECKING
from ssl import create_default_context, SSLSocket

from squarecloud_restorer.core import data
from .. import __version__


@dataclass(init=True)
class URL:
    host: str
    endpoint: str = "/"

    def __add__(self, other: str):
        self.endpoint += other

    @classmethod
    def get_snapshot_list(cls, scope: Literal['databases', 'applications']):
        return cls('api.squarecloud.app', f'/v2/users/snapshots?scope={scope}')
    
    @classmethod
    def upload(cls):
        return cls('api.squarecloud.app', '/v2/apps')

    @classmethod
    def get_snapshot(cls, account_id: str, name: str, key: str):
        return cls('snapshots.squarecloud.app', f'/applications/{account_id}/{name}.zip?{key}')
    
    @classmethod
    def restore_database(cls, db_id: str):
        return cls('api.squarecloud.app', f'/v2/databases/{db_id}/snapshots/restore')

    @classmethod
    def upload_database(cls):
        return cls('api.squarecloud.app', '/v2/databases')

class HTTPResponse:
    def __init__(self, socket: SSLSocket):
        self._socket = socket
        self._headers = {}
        self.status_code: int = 0
        self._data = b''
        self._gen: Generator[bytes, int|None, None]|None = None
        self._parse_headers()
    
    @property
    def headers(self):
        if not self._headers: self._parse_headers()
        return self._headers

    @property
    def json(self) -> dict[str, Any]:
        if not self._data: self.read()
        return json.loads(self._data)

    def _parse_headers(self):
        buffer = b''
        if not self._gen: self._gen = self._read(1024)
        while b'\r\n\r\n' not in buffer:
            buffer += next(self._gen)
        raw_headers, raw_data = buffer.split(b'\r\n\r\n', 1)
        header_lines = raw_headers.split(b'\r\n')
        _, code, _ = header_lines[0].split(b' ')
        self.status_code = int(code)
        self._data += raw_data
        for line in header_lines[1:]:
            k, _, v = line.partition(b':')
            self._headers[k.decode('utf-8')] = v.strip(b'').decode('utf-8')

    def _read(self, buffer_size: int) -> Generator[bytes, int|None, None]:
        while True:
            data = self._socket.recv(buffer_size)
            if not data: break
            n_buffer_size = yield data
            if n_buffer_size: buffer_size = n_buffer_size
        self._socket.close()

    def read(self, buffer_size: int=0) -> bytes|None:
        if buffer_size == 0:
            gen = cast(Generator[bytes, int|None, None], self._gen)
            self._data += gen.send(5*1024*1024)
            for data in gen:
                self._data += data
            self._socket.close()
            return self._data
        else:
            data = b''
            if self._data: 
                data += self._data
                self._data = b''
            buffer_size = buffer_size-len(data)
            gen = cast(Generator[bytes, int|None, None], self._gen)
            if buffer_size > 0: return data+gen.send(buffer_size)
            return data
            
    def close(self):
        self._socket.close()

class HTTPRequest:
    MAX_CHUNK_SIZE: int = 5*1024*1024
    def __init__(self, url: URL, headers: dict[str, Any], data: dict[str, Any]|BufferedReader, method: str):
        self._socket: None|SSLSocket = None
        self.headers: dict[str, Any] = {
            "Host": url.host,
            "User-Agent": f"squarecloud-restorer/{__version__}",
            "Accept": "application/json, application/octet-stream"
        } | headers
        self.data = data
        self.url = url
        self.method = method.upper()

    def _create_connection(self, endpoint: str) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.url+endpoint, 443))
        ctx = create_default_context()
        sock = ctx.wrap_socket(sock)
        self._socket = sock

    def _parse_headers(self) -> bytes:
        headers: list[bytes] = [
            f'{self.method.upper()} {self.url.endpoint}'.encode('utf-8'),
        ]
        for k,v in self.headers.items():
            headers.append(f'{k}: {v}'.encode('utf-8'))
        headers.append(b"Connection: close\r\n")
        result = b"\r\n".join(headers)
        return result

    def _read_large_data(self) -> Generator[bytes, None, None]:
        data = cast(BufferedReader, self.data)
        while True:
            chunk = data.read(self.MAX_CHUNK_SIZE)
            if not chunk: break
            yield chunk

    def _parse_form_data(self) -> tuple[str,bytes]:
        boundary = uuid4().hex
        form_data_struct: list[bytes] = [
            f'--{boundary}'.encode(),
            f'Content-Disposition: form-data; name="file"; filename="application.zip"'.encode(),
            b'Content-Type: application/octet-stream',
            b'\r\n',
        ]
        form_data = b'\r\n'.join(form_data_struct)
        return (boundary, form_data)

    def request(self, endpoint: str ="") -> HTTPResponse:
        self._create_connection(endpoint)
        sock = cast(SSLSocket, self._socket)
        try:
            if isinstance(self.data, BufferedReader):
                boundary, form_data = self._parse_form_data()
                form_data_end = f'\r\n--{boundary}--\r\n\r\n'.encode()
                length = len(form_data) + len(form_data_end)
                self.headers['Content-Length'] += length
                headers = self._parse_headers()
                sock.sendall(headers+form_data)
                for chunk in self._read_large_data():
                    sock.sendall(chunk)
                sock.sendall(form_data_end)
            else:
                headers = self._parse_headers()
                data = json.dumps(self.data).encode('utf-8')
                headers += f"\r\nContent-Length: {len(data)}".encode('utf-8')
                sock.sendall(headers+data)
        except Exception as e:
            sock.close()
            raise e
        return HTTPResponse(sock)
