from supervisely.app.widgets import Card, Transfer, Button, Container, Progress

projects_transfer = Transfer(
    filterable=True,
    filter_placeholder="Input project name",
    titles=["Available projects", "Project to copy"],
)

select_projects_button = Button("Select projects")
change_selection_button = Button("Change selection")
change_selection_button.hide()

card = Card(
    title="2️⃣ Selection",
    description="PLACEHOLDER: Input description here.",
    content="",  # ! ADD CONTENT HERE
    lock_message="Connect to the CVAT server on step 1️⃣",
    collapsable=True,
)
card.lock()
card.collapse()
