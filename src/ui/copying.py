import os
import shutil
import supervisely as sly
from typing import List
from collections import defaultdict

from supervisely.app.widgets import Container, Card, Table, Button, Progress, Text
import xml.etree.ElementTree as ET

import src.globals as g
import src.cvat as cvat
import src.converters as converters

COLUMNS = [
    "COPYING STATUS",
    "ID",
    "NAME",
    "STATUS",
    "OWNER",
    "LABELS",
    "CVAT URL",
    "SUPERVISELY URL",
]

projects_table = Table(fixed_cols=3, per_page=20, sort_column_id=1)
projects_table.hide()

copy_button = Button("Copy", icon="zmdi zmdi-copy")
stop_button = Button("Stop", icon="zmdi zmdi-stop", button_type="danger")
stop_button.hide()

copying_progress = Progress()
copying_results = Text()
copying_results.hide()

card = Card(
    title="3️⃣ Copying",
    description="Copy selected projects from CVAT to Supervisely.",
    content=Container([projects_table, copy_button, copying_progress, copying_results]),
    content_top_right=stop_button,
    collapsable=True,
)
card.lock()
card.collapse()


def build_projects_table():
    sly.logger.debug("Building projects table...")
    projects_table.loading = True
    rows = []

    for project in cvat.cvat_data():
        if project.id in g.STATE.selected_projects:
            rows.append(
                [
                    g.COPYING_STATUS.waiting,
                    project.id,
                    project.name,
                    project.status,
                    project.owner_username,
                    project.labels_count,
                    f'<a href="{project.url}" target="_blank">{project.url}</a>',
                    "",
                ]
            )

    sly.logger.debug(f"Prepared {len(rows)} rows for the projects table.")

    projects_table.read_json(
        {
            "columns": COLUMNS,
            "data": rows,
        }
    )

    projects_table.loading = False
    projects_table.show()

    sly.logger.debug("Projects table is built.")


@copy_button.click
def start_copying():
    sly.logger.debug(
        f"Copying button is clicked. Selected projects: {g.STATE.selected_projects}"
    )

    stop_button.show()
    copy_button.text = "Copying..."

    def save_task_to_zip(task_id: int, task_path: str, retry: int = 0) -> bool:
        """Tries to download the task data from CVAT API and save it to the zip archive.
        Functions tries to download the task data 10 times if the archive is empty and
        returns False if it can't download the data after 10 retries. Otherwise returns True.

        :param task_id: task ID in CVAT
        :type task_id: int
        :param task_path: path for saving task data in zip archive
        :type task_path: str
        :param retry: current number of retries, defaults to 0
        :type retry: int, optional
        :return: download status (True if the archive is not empty, False otherwise)
        :rtype: bool
        """
        sly.logger.debug("Trying to retreive task data from API...")
        task_data = cvat.retreive_dataset(task_id=task.id)

        with open(task_path, "wb") as f:
            shutil.copyfileobj(task_data, f)

        sly.logger.debug(f"Saved data to path: {task_path}, will check it's size...")

        # Check if the archive has non-zero size.
        if os.path.getsize(task_path) == 0:
            sly.logger.debug(f"The archive for task {task_id} is empty, removing it...")
            sly.fs.silent_remove(task_path)
            sly.logger.debug(f"The archive with path {task_path} was removed.")
            if retry < 10:
                # Try to download the task data again.
                retry += 1
                sly.logger.info(f"Retry {retry} to download task {task_id}...")
                save_task_to_zip(task_id, task_path, retry)
            else:
                # If the archive is empty after 10 retries, return False.
                sly.logger.error(f"Can't download task {task_id} after 10 retries.")
                return False
        else:
            sly.logger.debug(f"Archive for task {task_id} was downloaded correctly.")
            return True

    # TODO: Add progress bar for copying.
    for project_id in g.STATE.selected_projects:
        sly.logger.debug(f"Copying project with id: {project_id}")
        update_status_in_table(project_id, g.COPYING_STATUS.working)

        task_ids_with_errors = []
        task_archive_paths = []

        for task in cvat.cvat_data(project_id=project_id):
            sly.logger.debug(f"Copying task with id: {task.id}")
            if not g.STATE.continue_copying:
                sly.logger.debug("Copying is stopped by the user.")
                continue

            project_name = g.STATE.project_names[project_id]
            project_dir = os.path.join(g.ARCHIVE_DIR, f"{project_id}_{project_name}")
            sly.fs.mkdir(project_dir)
            task_filename = f"{task.id}_{task.name}.zip"

            task_path = os.path.join(project_dir, task_filename)
            download_status = save_task_to_zip(task.id, task_path)
            if download_status is False:
                task_ids_with_errors.append(task.id)
            else:
                task_archive_paths.append(task_path)

        if task_archive_paths:
            convert_and_upload(project_id, project_name, task_archive_paths)
            pass

        if task_ids_with_errors:
            sly.logger.warning(
                f"Project ID {project_id} was downloaded with errors. Task IDs with errors: {task_ids_with_errors}."
            )
            new_status = g.COPYING_STATUS.error
        else:
            sly.logger.info(f"Project ID {project_id} was downloaded successfully.")
            new_status = g.COPYING_STATUS.copied

        update_status_in_table(project_id, new_status)

    copy_button.text = "Copy"


def convert_and_upload(
    project_id: id, project_name: str, task_archive_paths: List[str]
):
    unpacked_project_path = os.path.join(g.UNPACKED_DIR, f"{project_id}_{project_name}")
    sly.logger.debug(f"Unpacked project path: {unpacked_project_path}")

    new_project_name = f"From CVAT {project_name}"
    project_info = g.api.project.create(g.STATE.selected_workspace, new_project_name)
    sly.logger.debug(f"Created project {new_project_name} in Supervisely.")

    project_meta = sly.ProjectMeta.from_json(g.api.project.get_meta(project_info.id))
    sly.logger.debug("Retrieved project meta from Supervisely.")

    for task_archive_path in task_archive_paths:
        unpacked_task_dir = sly.fs.get_file_name(task_archive_path)
        unpacked_task_path = os.path.join(unpacked_project_path, unpacked_task_dir)

        sly.fs.unpack_archive(task_archive_path, unpacked_task_path, remove_junk=True)
        sly.logger.debug(f"Unpacked from {task_archive_path} to {unpacked_task_path}")

        annotations_xml_path = os.path.join(unpacked_task_path, "annotations.xml")
        if not os.path.exists(annotations_xml_path):
            sly.logger.error(
                f"Can't find annotations.xml file in {unpacked_task_path}."
            )
            # TODO: Do something with this error.
            continue

        tree = ET.parse(annotations_xml_path)
        sly.logger.debug(f"Parsed annotations.xml from {annotations_xml_path}.")

        images = tree.findall("image")
        sly.logger.debug(f"Found {len(images)} images in annotations.xml.")

        sly_labels_in_task = defaultdict(list)

        for image in images:
            image_name = image.attrib["name"]

            geometries = list(converters.CONVERT_MAP.keys())
            for geometry in geometries:
                cvat_labels = image.findall(geometry)

                sly.logger.debug(
                    f"Found {len(cvat_labels)} with {geometry} geometry in {image_name}."
                )

                for cvat_label in cvat_labels:
                    sly_label = converters.CONVERT_MAP[geometry](cvat_label.attrib)
                    sly_labels_in_task[image_name].append(sly_label)
                    sly.logger.debug(
                        f"Adding converted sly label with geometry {geometry} to the list of {image_name}."
                    )

        sly.logger.debug(
            f"Prepared {len(sly_labels_in_task)} images with labels for upload."
        )


def update_status_in_table(project_id: int, new_status: str) -> None:
    """Updates the status of the project in the projects table.

    :param project_id: project ID in CVAT
    :type project_id: int
    :param new_status: new status for the project
    :type new_status: str
    """
    key_column_name = "ID"
    key_cell_value = project_id
    column_name = "COPYING STATUS"

    projects_table.update_cell_value(
        key_column_name, key_cell_value, column_name, new_status
    )


def add_sly_url_to_table():
    pass


@stop_button.click
def stop_copying():
    sly.logger.debug("Stop button is clicked.")

    g.STATE.continue_copying = False
    copy_button.text = "Stopping..."

    stop_button.hide()
