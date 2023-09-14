from typing import Dict, Any, Generator
from collections import namedtuple
import supervisely as sly
from cvat_sdk.api_client import Configuration, ApiClient, exceptions

import src.globals as g

CONFIGURATION = Configuration(
    host=g.STATE.cvat_server_address,
    username=g.STATE.cvat_username,
    password=g.STATE.cvat_password,
)


CVATData = namedtuple("CVATData", ["entity", "id", "name", "status"])


def check_connection() -> bool:
    sly.logger.debug(
        f"Will try to connect to CVAT API at {g.STATE.cvat_server_address} "
        "to check the connection settings."
    )
    with ApiClient(CONFIGURATION) as api_client:
        try:
            (data, response) = api_client.server_api.retrieve_about()
        except Exception as e:
            sly.logger.error(
                f"Exception when calling CVAT API server_api.retrieve_about: {e}"
            )
            return False

    server_version = data.get("version")

    sly.logger.info(
        f"Connection was successful. CVAT server version: {server_version}."
    )

    return True


def cvat_data(**kwargs) -> Generator[CVATData, None, None]:
    if not kwargs:
        method = "projects_api.list()"
        entity = "project"
    if kwargs.get("project_id"):
        method = f"tasks_api.list(project_id={kwargs['project_id']})"
        entity = "task"

    sly.logger.debug(f"Will try to retreive {method} from CVAT API.")

    with ApiClient(CONFIGURATION) as api_client:
        try:
            (data, response) = eval(f"api_client.{method}")
        except exceptions.ApiException as e:
            sly.logger.error(f"Exception when calling CVAT API projects_api.list: {e}")
            return

    count = data.get("count")
    if count:
        sly.logger.debug(f"API reponsed with {data['count']} data entries.")

    results = data.get("results")
    if not results:
        sly.logger.debug("API reponsed with no data entries.")
        return

    for result in results:
        yield CVATData(
            entity=entity,
            id=result.get("id"),
            name=result.get("name"),
            status=result.get("status"),
        )


def retreive_dataset(task_id):
    with ApiClient(CONFIGURATION) as api_client:
        try:
            (data, response) = api_client.tasks_api.retrieve_dataset(
                format="COCO 1.0",
                id=task_id,
                action="download",
            )
        except exceptions.ApiException as e:
            sly.logger.error(f"Exception when calling CVAT API projects_api.list: {e}")
            return

    return data


def retreive_formats() -> Dict[str, Any]:
    with ApiClient(CONFIGURATION) as api_client:
        try:
            (data, response) = api_client.server_api.retrieve_annotation_formats()
        except exceptions.ApiException as e:
            sly.logger.error(f"Exception when calling CVAT API projects_api.list: {e}")
            return

    return data
