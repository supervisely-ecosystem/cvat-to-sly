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

    projects_table.read_json(
        {
            "columns": COLUMNS,
            "data": rows,
        }
    )

    projects_table.loading = False
    projects_table.show()
