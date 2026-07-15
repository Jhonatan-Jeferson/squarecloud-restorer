from typing import TYPE_CHECKING
from datetime import datetime
from queue import Queue
from getpass import getpass
from .utils import get_api_key
from .core import BaseSnapshot, Http

if TYPE_CHECKING:
    from .__main__ import RestorerClient


def help(client: RestorerClient) -> None:
    """Shows all commands available."""
    msg: str = f""
    for name, func in client.COMMANDS.items():
        msg += f"{name:^23}- {func.__doc__}\n"
    print(msg)

@get_api_key
def list(client: RestorerClient) -> None:
    """List all Snapshots ordering by most recent for restore."""
    _http = Http()
    _http.set_api_key(client.api_key)
    all_snapshots = _http.get_snapshots(True, True)
    queue: Queue[BaseSnapshot] = Queue()
    for k,v in all_snapshots.items():
        print(f"{k:^23} - {'date(dd/mm/yyyy)':^20}")
        for app in v:
            print(f"{app.name:<} - {datetime.fromisoformat(app.modified).strftime("%d/%m/%Y")} ")
            queue.put(app)
    while not queue.empty():
        snapshot = queue.get()
        restore = input(f'Restore {snapshot.name}({datetime.fromisoformat(snapshot.modified).strftime("%d/%m/%Y")})?(y/n)\n>')
        match restore.lower():
            case 'y': snapshot.restore(client.api_key)
            case 'n': ...
            case _: ...
        queue.task_done()
    

@get_api_key
def today(client: RestorerClient) -> None:
    "List only today Snapshots for restore."
    ...

@get_api_key
def applications(client: RestorerClient) -> None:
    "List only applications Snapshots for restore."
    ...

@get_api_key
def databases(client: RestorerClient) -> None:
    """list only databases Snapshots for restore."""
    ...
