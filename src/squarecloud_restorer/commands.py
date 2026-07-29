from typing import TYPE_CHECKING, Any, List
from datetime import datetime
from queue import Queue
from getpass import getpass

from .core import URL, HTTPRequest, ApplicationSnapshot, BaseSnapshot, DatabaseSnapshot
from .utils import get_api_key, sort_snapshots

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
    "List all Snapshots ordering by most recent for restore."
    apps_endpoint = URL.get_snapshot_list('applications')
    databases_endpoint = URL.get_snapshot_list('databases')
    user_endpoint = URL.user()
    HEADERS = {
        'Content-Type': 'application/json',
        'Authorization': client.api_key
    }
    user_request = HTTPRequest(user_endpoint, HEADERS, {}, 'GET')
    user_response = user_request.request()
    if user_response.status_code != 200: raise Exception('Cannot get user data.')
    user_response.read()
    account_id = user_response.json["response"]["user"]["id"]
    requests = HTTPRequest(apps_endpoint, HEADERS, {}, 'GET'), \
        HTTPRequest(databases_endpoint, HEADERS, {}, 'GET')
    responses = tuple([request.request() for request in requests])
    all_snapshots: dict[str, List[BaseSnapshot]] = {'apps': [], 'dbs': []}
    for index, response in enumerate(responses): 
        if response.status_code != 200: raise Exception('Requests do not received a correct response.')
        response.read()
        list_of_snapshots: List[dict[str, Any]] = response.json["response"]
        snapshots = sort_snapshots(list_of_snapshots)
        filtered_snapshots = {item['name']: item for item in snapshots}
        sorted_snapshots = sort_snapshots([snap for snap in filtered_snapshots.values()], reverse=True)
        if index == 0: all_snapshots['apps'].extend([ApplicationSnapshot(**snap_data, account_id=account_id) for snap_data in sorted_snapshots])
        else: all_snapshots['dbs'].extend([DatabaseSnapshot(**snap_data, account_id=account_id) for snap_data in sorted_snapshots])
    queue: Queue[BaseSnapshot] = Queue()
    for k,v in all_snapshots.items():
        print(f"{k:^32} - {'date(dd/mm/yyyy)':^20}")
        for app in v:
            print(f"{app.name:<} - {datetime.fromisoformat(app.modified).strftime("%d/%m/%Y")} ")
            queue.put(app)
    # while not queue.empty():
    #     snapshot = queue.get()
    #     restore = input(f'Restore {snapshot.name}({datetime.fromisoformat(snapshot.modified).strftime("%d/%m/%Y")})?(y/n)\n>')
    #     match restore.lower():
    #         case 'y': snapshot.restore(client.api_key)
    #         case 'n': ...
    #         case _: ...
    #     queue.task_done()
    

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
    "list only databases Snapshots for restore."
    ...
