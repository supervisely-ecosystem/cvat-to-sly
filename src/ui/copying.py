import os
import shutil
import supervisely as sly

from supervisely.app.widgets import Container, Card, Table, Button, Progress, Text

import src.globals as g
import src.cvat as cvat

COLUMNS = ["COPIED", "ID", "NAME", "STATUS", "OWNER", "LABELS", "URL"]

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
                    g.COPYING_STATUS.pending,
                    project.id,
                    project.name,
                    project.status,
                    project.owner_username,
                    project.labels_count,
                    f'<a href="{project.url}" target="_blank">{project.url}</a>',
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

    def save_task_to_zip(task_id, task_path):
        sly.logger.debug("Trying to retreive task data from API...")
        task_data = cvat.retreive_dataset(task_id=task.id)

        with open(task_path, "wb") as f:
            shutil.copyfileobj(task_data, f)

        sly.logger.debug(f"Saved data to path: {task_path}, will check it's size...")
        # Check if the archive has non-zero size.
        if os.path.getsize(task_path) == 0:
            sly.logger.debug(f"The archive for task {task_id} is empty, removing it...")
            sly.fs.silent_remove(task_path)
            save_task_to_zip(task_id, task_path)
            sly.logger.debug(f"The archive with path {task_path} was removed.")
        else:
            sly.logger.debug(f"Archive for task {task_id} was downloaded correctly.")

    for project_id in g.STATE.selected_projects:
        sly.logger.debug(f"Copying project with id: {project_id}")
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
            save_task_to_zip(task.id, task_path)

    copy_button.text = "Copy"


@stop_button.click
def stop_copying():
    sly.logger.debug("Stop button is clicked.")

    g.STATE.continue_copying = False
    copy_button.text = "Stopping..."

    stop_button.hide()
