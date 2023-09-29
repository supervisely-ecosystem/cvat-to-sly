from typing import NamedTuple
import supervisely as sly
from supervisely.app.widgets import Card, Transfer, Button, Container

import migration_tool.src.globals as g
import migration_tool.src.ui.copying as copying

from cvat.api import cvat_data

projects_transfer = Transfer(
    filterable=True,
    filter_placeholder="Input project name",
    titles=["Available projects", "Project to copy"],
)

select_projects_button = Button("Select projects")
select_projects_button.disable()
change_selection_button = Button("Change projects")
change_selection_button.hide()

card = Card(
    title="2️⃣ Selection",
    description="Select projects to copy from CVAT to Supervisely.",
    content=Container([projects_transfer, select_projects_button]),
    content_top_right=change_selection_button,
    collapsable=True,
)
card.lock()
card.collapse()


def fill_transfer_with_projects() -> None:
    """Fills the transfer widget with projects sorted by id from CVAT API.
    On every launch clears the items in the widget and fills it with new projects."""

    sly.logger.debug("Starting to build transfer widget with projects.")
    transfer_items = []

    for project in cvat_data():
        g.STATE.project_names[project.id] = project.name
        transfer_items.append(
            Transfer.Item(key=project.id, label=f"[{project.id}] {project.name}")
        )

    sly.logger.debug(f"Prepared {len(transfer_items)} items for transfer.")

    transfer_items.sort(key=lambda item: item.key)
    projects_transfer.set_items(transfer_items)
    sly.logger.debug("Transfer widget filled with projects.")


@projects_transfer.value_changed
def project_changed(items: NamedTuple) -> None:
    """Enables or disables the select projects button depending on the selected
    projects in the transfer widget. If at least one project is selected, the button is enabled.
    Otherwise, the button is disabled.

    :param items: namedtuple containing two lists (transferred_items and untransferred_items)
    :type items: NamedTuple
    """
    if items.transferred_items:
        select_projects_button.enable()
    else:
        select_projects_button.disable()


@select_projects_button.click
def select_projects() -> None:
    """Saves the selected projects to the global state and builds the projects table."""

    project_ids = projects_transfer.get_transferred_items()

    sly.logger.debug(
        f"Select projects button clicked, selected projects: {project_ids}. Will save them to the global state."
    )
    g.STATE.selected_projects = project_ids

    copying.build_projects_table()

    card.lock()
    card.collapse()
    copying.card.unlock()
    copying.card.uncollapse()

    change_selection_button.show()


@change_selection_button.click
def change_selection() -> None:
    """Changes the widget states and resets the selected projects in the global state."""

    sly.logger.debug(
        "Change selection button clicked, will change widget states "
        "And reset selected projects in the global state."
    )

    g.STATE.project_names = dict()
    g.STATE.selected_projects = None

    card.unlock()
    card.uncollapse()

    copying.card.lock()
    copying.card.collapse()

    change_selection_button.hide()
