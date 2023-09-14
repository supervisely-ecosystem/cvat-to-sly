from typing import Dict, Generator, List
from collections import namedtuple
import supervisely as sly
from cvat_sdk.api_client import Configuration, ApiClient, exceptions

import src.globals as g

CONFIGURATION = Configuration(
    host=g.STATE.cvat_server_address,
    username=g.STATE.cvat_username,
    password=g.STATE.cvat_password,
)

# Entity of CVAT data: project or task.
CVATData = namedtuple(
    "CVATData",
    ["entity", "id", "name", "status", "owner_username", "labels_count", "url"],
)

# Exporter or importer format from CVAT API.
CVATFormat = namedtuple(
    "CVATFormat", ["dimension", "enabled", "ext", "name", "version"]
)


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
        try:
            owner_username = results.get("owner").get("username")
        except AttributeError:
            owner_username = None
        try:
            labels_count = results.get("labels").get("count")
        except AttributeError:
            labels_count = None

        url = result.get("url")
        url = url.replace("/api/", "/") if url else None

        yield CVATData(
            entity=entity,
            id=result.get("id"),
            name=result.get("name"),
            status=result.get("status"),
            owner_username=owner_username,
            labels_count=labels_count,
            url=url,
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


def retreive_formats() -> Dict[str, List[CVATFormat]]:
    """Retreive all available formats from CVAT API (exporters and importers).

    CVATFormat is a namedtuple with the following fields:
        - dimension: str
        - enabled: bool
        - ext: str
        - name: str
        - version: str

    :return: dictionary with exporters and importers keys and lists of CVATFormat objects as values
    :rtype: Dict[str, List[CVATFormat]]
    """
    with ApiClient(CONFIGURATION) as api_client:
        try:
            (data, response) = api_client.server_api.retrieve_annotation_formats()
        except exceptions.ApiException as e:
            sly.logger.error(f"Exception when calling CVAT API projects_api.list: {e}")
            return

    exporters = data.get("exporters")
    importers = data.get("importers")

    formats = {
        "exporters": [],
        "importers": [],
    }

    for exporter in exporters:
        formats["exporters"].append(
            CVATFormat(
                dimension=exporter.get("dimension"),
                enabled=exporter.get("enabled"),
                ext=exporter.get("ext"),
                name=exporter.get("name"),
                version=exporter.get("version"),
            )
        )

    for importer in importers:
        formats["importers"].append(
            CVATFormat(
                dimension=importer.get("dimension"),
                enabled=importer.get("enabled"),
                ext=importer.get("ext"),
                name=importer.get("name"),
                version=importer.get("version"),
            )
        )

    return formats
