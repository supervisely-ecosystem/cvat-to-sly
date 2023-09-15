import os
import shutil
import supervisely as sly

from supervisely.app.widgets import Container, Card, Table, Button, Progress, Text

import src.globals as g
import src.cvat as cvat

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

    for project_id in g.STATE.selected_projects:
        sly.logger.debug(f"Copying project with id: {project_id}")
        update_status_in_table(project_id, g.COPYING_STATUS.working)

        task_ids_with_errors = []

        for task in cvat.cvat_data(project_id=project_id):
            sly.logger.debug(f"Copying task with id: {task.id}")
            if not g.STATE.continue_copying:
                sly.logger.debug("Copying is stopped by the user.")
                continue

            project_name = g.STATE.project_names[project_id]
            project_dir_name = f"{project_id}_{project_name}"
            task_dir_name = f"{task.id}_{task.name}"
            task_dir = os.path.join(g.TEMP_DIR, project_dir_name, task_dir_name)

            sly.logger.debug(f"Creating task directory: {task_dir}")
            sly.fs.mkdir(task_dir)

            task_path = os.path.join(task_dir, f"{task.id}.zip")
            download_status = save_task_to_zip(task.id, task_path)
            if download_status is False:
                sly.logger.debug(
                    f"Download status for task {task.id} is {download_status}."
                )
                task_ids_with_errors.append(task.id)

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


@stop_button.click
def stop_copying():
    sly.logger.debug("Stop button is clicked.")

    g.STATE.continue_copying = False
    copy_button.text = "Stopping..."

    stop_button.hide()
