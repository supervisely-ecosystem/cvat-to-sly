from supervisely.app.widgets import Container, Card

card = Card(
    title="3️⃣ Copying",
    description="Copy selected projects from CVAT to Supervisely.",
    content=Container(),
    collapsable=True,
)
card.lock()
card.collapse()
